"""N1/N2 Plan & 5-Layer Assembly Helper for `AssistantTurnEngine` (`AD-25`)."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from orcia_core.orchestration.ai_models_errors import ModelToolsUnsupportedError
from orcia_core.orchestration.assistant_agent_synthesis import classify_assistant_intent
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_harness_types import AssistantIntentKind
from orcia_core.orchestration.assistant_prompt_builder import (
    AssistantPromptBuilder,
    resolve_default_hat,
)
from orcia_core.orchestration.assistant_three_speed_models import (
    AssistantSpeedMode,
    detect_conversational_speed_mode,
)
from orcia_core.orchestration.errors import (
    DirectSiWriteRequiresProcessGateError,
    ObserverModeReadOnlyError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig


def run_n1_intent_guard(
    prompt_builder: AssistantPromptBuilder,
    user: UserIdentity,
    *,
    user_prompt: str,
    require_write: bool = True,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    requested_write_target_uri: str | None = None,
) -> AssistantIntentKind:
    """Enforce N1 observer/V5 read-only guards, Layer 1 immutability & classify intent."""
    if require_write and user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER"):
        raise ObserverModeReadOnlyError()
    if requested_write_target_uri and requested_write_target_uri.strip():
        raise DirectSiWriteRequiresProcessGateError()
    if (
        system_instructions_override
        and system_instructions_override.strip()
        and not allow_system_override
    ):
        prompt_builder.build_system_instructions(
            hat="ARCHITECT",
            speed_mode="SPEED_1_FAST",
            system_instructions_override=system_instructions_override,
            allow_system_override=False,
        )
    return classify_assistant_intent(user_prompt)


@dataclass(frozen=True, slots=True)
class PreparedTurnPlan:
    """Output of `N1 IntentGuard` + `N2 Planner & Ontology` for a turn."""

    intent: AssistantIntentKind
    speed_mode: AssistantSpeedMode
    active_hat: str
    assembled_5_layers_prompt: str
    layers_sha256: str
    system_instructions: str
    assembly_latency_ms: float
    supports_tools: bool


async def assemble_prepared_turn_plan_async(
    *,
    governance: AssistantFourLevelGovernanceService,
    prompt_builder: AssistantPromptBuilder,
    intent: AssistantIntentKind,
    user: UserIdentity,
    workspace_id: str,
    user_prompt: str,
    hat: str | None = None,
    requested_speed: AssistantSpeedMode | None = None,
    deep_audit_pill_active: bool = False,
    thinking_effort: str | None = None,
    requested_tier: str | None = None,
    endpoint: LlmEndpointConfig | None = None,
    ontology_concepts_summary: str | None = None,
    federated_evidence_summary: str | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    assembled_5_layers_prompt: str | None = None,
    base_assembly_latency_ms: float = 0.0,
    locale: str = "fr",
    instance: str = "/api/v1/assistant/turns",
) -> PreparedTurnPlan:
    """Resolve conversational speed, verify `supports_tools`, and build 5-layer prompt."""
    detected_speed, _ = detect_conversational_speed_mode(
        user_prompt,
        requested_speed=requested_speed,
        deep_audit_pill_active=deep_audit_pill_active,
    )
    supports_tools = endpoint.supports_tools if endpoint is not None else True
    if detected_speed in ("SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT") and not supports_tools:
        model_label = endpoint.model_name if endpoint is not None else "configured-chat-model"
        raise ModelToolsUnsupportedError(model_name=model_label, instance=instance)

    active_hat = resolve_default_hat(explicit_hat=hat, user=user)
    t0 = time.perf_counter()
    if assembled_5_layers_prompt is not None:
        assembled_text = assembled_5_layers_prompt
    else:
        layers = await governance.assemble_five_layers_preview_async(
            workspace_id=workspace_id,
            user_id=user.id,
            locale=locale,
        )
        assembled_text = "\n\n".join(f"### {layer.label}\n{layer.content}" for layer in layers)
    digest = hashlib.sha256(assembled_text.encode("utf-8")).hexdigest()
    assembly_ms = round(base_assembly_latency_ms + (time.perf_counter() - t0) * 1000.0, 3)

    system_msg = prompt_builder.build_system_instructions(
        hat=active_hat,
        speed_mode=detected_speed,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        assembled_5_layers_prompt=assembled_text,
        ontology_concepts_summary=ontology_concepts_summary,
        federated_evidence_summary=federated_evidence_summary,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )
    return PreparedTurnPlan(
        intent=intent,
        speed_mode=detected_speed,
        active_hat=active_hat,
        assembled_5_layers_prompt=assembled_text,
        layers_sha256=digest,
        system_instructions=system_msg,
        assembly_latency_ms=assembly_ms,
        supports_tools=supports_tools,
    )
