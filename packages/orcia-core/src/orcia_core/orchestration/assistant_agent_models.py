"""Assistant Agent Telemetry Models & Confidential Slice Filters (`Story 3.3`, `Story 26.1`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.orchestration.assistant_composer import (
    AssistantWorkflowProposal,
    XyFlowEdgeSpec,
    XyFlowNodeSpec,
)
from orcia_core.orchestration.assistant_harness import (
    AssembledAssistantPrompt,
    AssistantIntentKind,
)
from orcia_kernel.context_ports import ContextSliceRecord, VectorSearchHitRecord

ASSISTANT_WORKFLOW_URI: str = "orcia://system/workflows/assistant-agent"

AssistantNodeId = Literal[
    "1_INTENT_ROUTER",
    "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
    "3_PARALLEL_FAN_OUT",
    "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
    "5_PROFILE_ADAPTIVE_SYNTHESIZER",
]


@dataclass(frozen=True, slots=True)
class AssistantNodeTrace:
    """Execution telemetry for one node of the 5-node `assistant-agent` DAG (`AD-15`)."""

    node_id: AssistantNodeId
    node_order: int
    status: Literal["COMPLETED"]
    duration_ms: float
    summary: str
    output_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AssistantTurnResult:
    """Complete result of a 5-node `AssistantAgentService` conversational turn (`Story 3.3`)."""

    turn_id: str
    workflow_uri: str
    workspace_id: str
    human_profile_archetype: str
    intent: AssistantIntentKind
    response_text: str
    first_token_latency_ms: float
    node_traces: tuple[AssistantNodeTrace, ...]
    assembled_prompt: AssembledAssistantPrompt
    workflow_proposal: AssistantWorkflowProposal | None = None


def filter_authorized_context_slices(
    slices: tuple[ContextSliceRecord, ...],
    allowed_source_uris: frozenset[str] | None,
) -> tuple[ContextSliceRecord, ...]:
    """Filter out CONFIDENTIAL_RESTRICTED slices and unauthorized sources server-side."""
    kept: list[ContextSliceRecord] = []
    for s in slices:
        vis = str(s.structured_payload.get("visibility_mode") or "").strip().upper()
        is_confidential = (
            vis == "CONFIDENTIAL_RESTRICTED"
            or s.source_uri.startswith("confidential://")
            or "secret-vault" in s.source_uri
        )
        if is_confidential:
            if allowed_source_uris is None or s.source_uri not in allowed_source_uris:
                continue
        elif allowed_source_uris is not None and s.source_uri not in allowed_source_uris:
            continue
        kept.append(s)
    return tuple(kept)


def filter_authorized_vector_hits(
    hits: tuple[VectorSearchHitRecord, ...],
    allowed_source_uris: frozenset[str] | None,
) -> tuple[VectorSearchHitRecord, ...]:
    """Filter out RAG hits whose source URI is unauthorized when server allowlist is supplied."""
    if allowed_source_uris is None:
        return tuple(
            h
            for h in hits
            if not (h.source_uri.startswith("confidential://") or "secret-vault" in h.source_uri)
        )
    return tuple(h for h in hits if h.source_uri in allowed_source_uris)


__all__ = [
    "ASSISTANT_WORKFLOW_URI",
    "AssistantNodeId",
    "AssistantNodeTrace",
    "AssistantTurnResult",
    "AssistantWorkflowProposal",
    "XyFlowEdgeSpec",
    "XyFlowNodeSpec",
    "filter_authorized_context_slices",
    "filter_authorized_vector_hits",
]
