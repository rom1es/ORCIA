"""Unified `AssistantTurnEngine` Converging Speed 1, Speed 2/3 & MCP `assistant.ask` (`AD-25`).

Executes the fixed constitutional phase sequence:
`N1 IntentGuard -> N2 Planner & Ontology -> N3 Pre-fetch / Tool Loop ->
N4 Server EvidenceTable -> N5 Synthesis (AssistantPromptBuilder) -> CitationGuard`.

Zero framework/SDK imports (`fastapi`, `sqlalchemy`, `redis`, `litellm`, `dramatiq`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from orcia_core.orchestration._assistant_turn_engine_citations import (
    is_low_evidence_table,
    merge_tool_outputs_into_evidence_table,
    verify_turn_citations_with_guard_async,
)
from orcia_core.orchestration._assistant_turn_engine_mcp import (
    AssistantReadOnlyAskResult,
    run_speed_1_read_only_ask_async,
)
from orcia_core.orchestration._assistant_turn_engine_plan import (
    PreparedTurnPlan,
    assemble_prepared_turn_plan_async,
    run_n1_intent_guard,
)
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.assistant_citations_models import (
    CitationVerificationResult,
    EvidenceTable,
    RawToolOutputCandidate,
)
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_harness_types import AssistantIntentKind
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder
from orcia_core.orchestration.assistant_three_speed_models import AssistantSpeedMode
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamingPort
from orcia_core.ports.reflexive_runtime_ports import AssistantReflexiveRuntimePort


class AssistantTurnEngine:
    """Single hexagonal domain engine for Speed 1, Speed 2/3, and MCP `assistant.ask`."""

    def __init__(
        self,
        *,
        governance_service: AssistantFourLevelGovernanceService | None = None,
        citation_guard: AssistantCitationAndV5GuardService | None = None,
        prompt_builder: AssistantPromptBuilder | None = None,
        reflexive_runtime: AssistantReflexiveRuntimePort | None = None,
        llm_streaming_port: LlmStreamingPort | None = None,
    ) -> None:
        self._governance = governance_service or AssistantFourLevelGovernanceService()
        self._citation_guard = citation_guard or AssistantCitationAndV5GuardService()
        self._prompt_builder = prompt_builder or AssistantPromptBuilder()
        self._reflexive_runtime = reflexive_runtime
        self._llm_port = llm_streaming_port

    @property
    def citation_guard(self) -> AssistantCitationAndV5GuardService:
        return self._citation_guard

    @property
    def governance_service(self) -> AssistantFourLevelGovernanceService:
        return self._governance

    @property
    def reflexive_runtime(self) -> AssistantReflexiveRuntimePort | None:
        return self._reflexive_runtime

    def set_reflexive_runtime(self, runtime: AssistantReflexiveRuntimePort | None) -> None:
        """Bind or refresh the `ASSISTANT`-profile `AssistantReflexiveRuntimePort`."""
        self._reflexive_runtime = runtime

    def set_llm_streaming_port(self, port: LlmStreamingPort | None) -> None:
        """Bind or refresh `LlmStreamingPort` from the Composition Root."""
        self._llm_port = port

    def n1_intent_guard(
        self,
        user: UserIdentity,
        *,
        user_prompt: str,
        require_write: bool = True,
        system_instructions_override: str | None = None,
        allow_system_override: bool = False,
        requested_write_target_uri: str | None = None,
    ) -> AssistantIntentKind:
        """N1: Enforce observer/V5 read-only guards, Layer 1 immutability & classify intent."""
        return run_n1_intent_guard(
            self._prompt_builder,
            user,
            user_prompt=user_prompt,
            require_write=require_write,
            system_instructions_override=system_instructions_override,
            allow_system_override=allow_system_override,
            requested_write_target_uri=requested_write_target_uri,
        )

    async def n2_plan_and_assemble_async(
        self,
        user: UserIdentity,
        *,
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
        """N1+N2: Validate speed & `supports_tools`, assemble 5-layer Mode A prompt."""
        intent = self.n1_intent_guard(user, user_prompt=user_prompt, require_write=True)
        return await assemble_prepared_turn_plan_async(
            governance=self._governance,
            prompt_builder=self._prompt_builder,
            intent=intent,
            user=user,
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            hat=hat,
            requested_speed=requested_speed,
            deep_audit_pill_active=deep_audit_pill_active,
            thinking_effort=thinking_effort,
            requested_tier=requested_tier,
            endpoint=endpoint,
            ontology_concepts_summary=ontology_concepts_summary,
            federated_evidence_summary=federated_evidence_summary,
            response_tone=response_tone,
            response_format=response_format,
            personal_instructions=personal_instructions,
            workspace_instructions=workspace_instructions,
            folder_pinned_notes=folder_pinned_notes,
            assembled_5_layers_prompt=assembled_5_layers_prompt,
            base_assembly_latency_ms=base_assembly_latency_ms,
            locale=locale,
            instance=instance,
        )

    async def start_assistant_reflexive_session_async(
        self,
        *,
        turn_id: str,
        workspace_id: str,
        user_id: str,
        user_prompt: str,
        speed_mode: AssistantSpeedMode,
        locale: str = "fr",
    ) -> None:
        """Initialize `ASSISTANT` session in `reflexive_execution_sessions` for Speed 2/3."""
        if self._reflexive_runtime is None or speed_mode not in (
            "SPEED_2_AGENT_TOOLS",
            "SPEED_3_DEEP_AUDIT",
        ):
            return
        effort_mode: Literal["standard", "approfondi"] = (
            "approfondi" if speed_mode == "SPEED_3_DEEP_AUDIT" else "standard"
        )
        await self._reflexive_runtime.ensure_assistant_session(
            execution_id=turn_id,
            workspace_id=workspace_id,
            user_id=user_id,
            objective=user_prompt,
            effort_mode=effort_mode,
            locale=locale,
        )

    async def record_assistant_reflexive_step_async(
        self,
        *,
        turn_id: str,
        turn_index: int,
        action_kind: str,
        summary: str,
        tool_name: str = "",
        tokens_used: int = 0,
    ) -> None:
        """Record an N3 step into the `ASSISTANT` reflexive session when active."""
        if self._reflexive_runtime is not None:
            await self._reflexive_runtime.record_assistant_step(
                execution_id=turn_id,
                turn_index=turn_index,
                action_kind=action_kind,
                summary=summary,
                tool_name=tool_name,
                tokens_used=tokens_used,
            )

    async def complete_assistant_reflexive_session_async(
        self, *, turn_id: str, status: str, final_markdown: str, tokens_used: int = 0
    ) -> None:
        """Finalize the `ASSISTANT` reflexive session (`COMPLETED`, `CANCELLED`, or `FAILED`)."""
        if self._reflexive_runtime is None:
            return
        norm = (
            "CANCELLED" if status == "STOPPED" else ("FAILED" if status == "ERROR" else "COMPLETED")
        )
        await self._reflexive_runtime.complete_assistant_session(
            execution_id=turn_id,
            status=norm,  # type: ignore[arg-type]
            final_markdown=final_markdown,
            tokens_used=tokens_used,
        )

    def n4_build_evidence_table(
        self,
        *,
        base_table: EvidenceTable | None,
        tool_outputs: Sequence[RawToolOutputCandidate] = (),
    ) -> tuple[EvidenceTable, bool]:
        """N4: Assemble final server `EvidenceTable` and compute deterministic `low_evidence`."""
        table = merge_tool_outputs_into_evidence_table(
            self._citation_guard, base_table=base_table, tool_outputs=tool_outputs
        )
        return table, is_low_evidence_table(table)

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
    ) -> tuple[CitationVerificationResult, dict[str, Any], bool]:
        """N6 (`CitationGuard`): Verify tags strictly before `turn_completed` & emit map."""
        return await verify_turn_citations_with_guard_async(
            self._citation_guard,
            response_text=response_text,
            evidence_table=evidence_table,
            workspace_id=workspace_id,
            user_id=user_id,
            user_email=user_email,
            user_display_name=user_display_name,
            turn_id=turn_id,
            trace_id=trace_id,
        )

    async def execute_speed_1_read_only_async(
        self,
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
        return await run_speed_1_read_only_ask_async(
            self,
            user,
            workspace_id=workspace_id,
            prompt_text=prompt_text,
            evidence_table=evidence_table,
            ontology_concepts_summary=ontology_concepts_summary,
            federated_evidence_summary=federated_evidence_summary,
            endpoint=endpoint,
            llm_port=llm_port or self._llm_port,
            requested_write_target_uri=requested_write_target_uri,
            assembled_5_layers_prompt=assembled_5_layers_prompt,
            base_assembly_latency_ms=base_assembly_latency_ms,
            locale=locale,
            trace_id=trace_id,
        )


__all__ = ["AssistantReadOnlyAskResult", "AssistantTurnEngine", "PreparedTurnPlan"]
