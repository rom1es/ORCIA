"""Synchronous Speed 1 Read-Only Governed Execution for MCP `assistant.ask` (`D7`, `AD-25`)."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from orcia_core.observability.logging import scrub_sensitive_text
from orcia_core.orchestration._assistant_turn_engine_plan import PreparedTurnPlan
from orcia_core.orchestration.assistant_citations_models import (
    CitationVerificationResult,
    EvidenceTable,
    RawToolOutputCandidate,
)
from orcia_core.orchestration.assistant_harness_types import AssistantIntentKind
from orcia_core.orchestration.assistant_three_speed_models import AssistantSpeedMode
from orcia_core.orchestration.errors import TierModelNotConfiguredError, ValidationDomainError
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)
from orcia_kernel.ids import new_uuid7_str


class _ReadOnlyAskEnginePort(Protocol):
    def n1_intent_guard(
        self,
        user: UserIdentity,
        *,
        user_prompt: str,
        require_write: bool = True,
        system_instructions_override: str | None = None,
        allow_system_override: bool = False,
        requested_write_target_uri: str | None = None,
    ) -> AssistantIntentKind: ...

    async def n2_plan_and_assemble_async(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        user_prompt: str,
        requested_speed: AssistantSpeedMode | None = None,
        endpoint: LlmEndpointConfig | None = None,
        ontology_concepts_summary: str | None = None,
        federated_evidence_summary: str | None = None,
        assembled_5_layers_prompt: str | None = None,
        base_assembly_latency_ms: float = 0.0,
        locale: str = "fr",
        instance: str = "/api/v1/assistant/turns",
    ) -> PreparedTurnPlan: ...

    def n4_build_evidence_table(
        self,
        *,
        base_table: EvidenceTable | None,
        tool_outputs: Sequence[RawToolOutputCandidate] = (),
    ) -> tuple[EvidenceTable, bool]: ...

    async def n6_verify_citations_async(
        self,
        *,
        response_text: str,
        evidence_table: EvidenceTable,
        workspace_id: str,
        user_id: str,
        user_email: str | None = None,
        user_display_name: str | None = None,
        turn_id: str | None = None,
        trace_id: str = "",
    ) -> tuple[CitationVerificationResult, dict[str, Any], bool]: ...


@dataclass(frozen=True, slots=True)
class AssistantReadOnlyAskResult:
    """Synchronous Speed 1 read-only governed output for MCP `assistant.ask` (`D7`)."""

    invocation_id: str
    turn_id: str
    workspace_id: str
    sanitized_response_text: str
    citation_map: dict[str, Any]
    stripped_phantom_tags: tuple[str, ...]
    low_evidence: bool
    input_tokens: int
    output_tokens: int
    usage_source: str
    latency_ms: float
    evidence_tags: tuple[str, ...] = field(default_factory=tuple)


async def run_speed_1_read_only_ask_async(
    engine: _ReadOnlyAskEnginePort,
    user: UserIdentity,
    *,
    workspace_id: str,
    prompt_text: str,
    evidence_table: EvidenceTable | None = None,
    ontology_concepts_summary: str | None = None,
    federated_evidence_summary: str | None = None,
    endpoint: LlmEndpointConfig | None = None,
    llm_port: LlmStreamingPort | None = None,
    requested_write_target_uri: str | None = None,
    assembled_5_layers_prompt: str | None = None,
    base_assembly_latency_ms: float = 0.0,
    locale: str = "fr",
    trace_id: str = "",
) -> AssistantReadOnlyAskResult:
    """Execute synchronous Speed 1 read-only governed turn for MCP `assistant.ask` (`D7`)."""
    t0 = time.perf_counter()
    engine.n1_intent_guard(
        user,
        user_prompt=prompt_text,
        require_write=True,
        requested_write_target_uri=requested_write_target_uri,
    )
    plan = await engine.n2_plan_and_assemble_async(
        user,
        workspace_id=workspace_id,
        user_prompt=prompt_text,
        requested_speed="SPEED_1_FAST",
        endpoint=endpoint,
        ontology_concepts_summary=ontology_concepts_summary,
        federated_evidence_summary=federated_evidence_summary,
        assembled_5_layers_prompt=assembled_5_layers_prompt,
        base_assembly_latency_ms=base_assembly_latency_ms,
        locale=locale,
        instance="/api/v1/mcp/invoke",
    )
    table, low_ev = engine.n4_build_evidence_table(base_table=evidence_table)
    turn_id = new_uuid7_str()
    if llm_port is None or (
        endpoint is None and not getattr(llm_port, "is_cassette_adapter", False)
    ):
        raise TierModelNotConfiguredError(
            inference_tier="chat",
            detail_override="Active chat AI model is required for MCP assistant.ask.",
            instance="/api/v1/mcp/invoke",
        )
    eff_ep = endpoint or LlmEndpointConfig(
        provider="cassette",
        model_name="cassette-deterministic",
        endpoint_uri="http://localhost",
        auth_mode="none",
        supports_tools=False,
    )
    outcome = await llm_port.complete_chat(
        LlmStreamRequest(
            endpoint=eff_ep,
            messages=(
                {"role": "system", "content": plan.system_instructions},
                {"role": "user", "content": prompt_text},
            ),
            tools=(),
            stream=False,
            include_thoughts=False,
        )
    )
    if outcome is None or not outcome.content.strip():
        raise ValidationDomainError(
            detail_override="Governed LLM returned an empty response for MCP assistant.ask.",
            instance="/api/v1/mcp/invoke",
        )
    raw_reply = outcome.content
    in_tok, out_tok, usage_src = outcome.input_tokens, outcome.output_tokens, outcome.usage_source

    verification, cmap_payload, _ = await engine.n6_verify_citations_async(
        response_text=raw_reply,
        evidence_table=table,
        workspace_id=workspace_id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        turn_id=turn_id,
        trace_id=trace_id,
    )
    scrubbed_reply = scrub_sensitive_text(verification.sanitized_text)
    return AssistantReadOnlyAskResult(
        invocation_id=new_uuid7_str(),
        turn_id=turn_id,
        workspace_id=workspace_id,
        sanitized_response_text=scrubbed_reply,
        citation_map=cmap_payload,
        stripped_phantom_tags=verification.stripped_phantom_tags,
        low_evidence=low_ev,
        input_tokens=in_tok,
        output_tokens=out_tok,
        usage_source=usage_src,
        latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
        evidence_tags=verification.valid_tags,
    )


__all__ = ["AssistantReadOnlyAskResult", "run_speed_1_read_only_ask_async"]
