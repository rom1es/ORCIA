"""Per-Tool Audit Ledger Writer, Outbox Emitter & SSE Event Builder (`Story 26.6b`, `H-22`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from orcia_core.kernel.events import DomainEvent
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions.connector_invoker import scrub_connector_secrets
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutionRequest,
    AssistantToolSseEvent,
    ToolAuditEventType,
    ToolVerdict,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort, FinopsCostLedgerEntry

logger = get_logger("orcia.agents.tool_audit")

OutboxEnqueueCallback = Callable[[DomainEvent], Awaitable[str | None]]


def _parse_optional_uuid(raw_val: str | None) -> str | None:
    if not raw_val:
        return None
    try:
        return str(UUID(str(raw_val).strip()))
    except (ValueError, TypeError):
        return None


async def record_tool_audit_ledger(
    *,
    sink: AuditLedgerSinkPort | None,
    request: AssistantToolExecutionRequest,
    event_type: ToolAuditEventType,
    verdict: ToolVerdict,
    latency_ms: float,
    cost_usd: float = 0.0,
    reason_code: str = "",
) -> str | None:
    """Persist an immutable per-tool row into `audit_ledger` (`ASSISTANT_TOOL_INVOKED`/`DENIED`)."""
    if sink is None:
        return None
    masked_args = scrub_connector_secrets(dict(request.arguments))
    source_event_id = str(
        uuid5(
            NAMESPACE_URL,
            f"assistant-tool:{request.turn_id}:{request.iteration}:{request.tool_call_id}",
        )
    )
    entry = FinopsCostLedgerEntry(
        source_event_id=source_event_id,
        workspace_id=_parse_optional_uuid(request.workspace_id),
        scope_path=f"WORKSPACE/{request.workspace_id}" if request.workspace_id else "GLOBAL",
        actor_type="HUMAN",
        actor_id=request.user_id,
        actor_display_name=request.user_display_name,
        actor_email=request.user_email,
        event_type=event_type,
        summary=(
            f"Assistant tool '{request.tool_name}' {verdict.lower()}"
            + (f" ({reason_code})" if reason_code else "")
        ),
        cost_usd=max(0.0, float(cost_usd)),
        latency_ms=max(0, int(round(latency_ms))),
        trace_id=request.trace_id or get_current_trace_id(),
        metadata={
            "turn_id": request.turn_id,
            "iteration": request.iteration,
            "tool_call_id": request.tool_call_id,
            "tool_name": request.tool_name,
            "verdict": verdict,
            "reason_code": reason_code,
            "masked_arguments": masked_args,
            "workspace_slug": request.workspace_id,
        },
    )
    try:
        return await sink.record_entry(entry)
    except Exception as exc:
        logger.warning(
            "assistant_tool_audit_ledger_failed",
            turn_id=request.turn_id,
            tool_name=request.tool_name,
            error_type=type(exc).__name__,
        )
        return None


async def enqueue_arbitration_outbox_event(
    *,
    outbox_enqueue_fn: OutboxEnqueueCallback | None,
    event: DomainEvent | None,
) -> str | None:
    """Persist `HumanArbitrationRequested` into `domain_events_outbox`."""
    if outbox_enqueue_fn is None or event is None:
        return None
    try:
        return await outbox_enqueue_fn(event)
    except Exception as exc:
        logger.warning(
            "assistant_tool_outbox_enqueue_failed",
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            error_type=type(exc).__name__,
        )
        return None


def build_tool_sse_events(
    *,
    request: AssistantToolExecutionRequest,
    verdict: ToolVerdict,
    summary: str,
    latency_ms: float,
    deduplicated: bool = False,
    reason_code: str = "",
    approval_proposal: dict[str, Any] | None = None,
    audit_event_id: str | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> tuple[AssistantToolSseEvent, ...]:
    """Build canonical SSE events (`tool_call`, `tool_result`, optional `approval_required`)."""
    masked_args = scrub_connector_secrets(dict(request.arguments))
    events: list[AssistantToolSseEvent] = [
        AssistantToolSseEvent(
            event="tool_call",
            data={
                "turn_id": request.turn_id,
                "iteration": request.iteration,
                "tool_call_id": request.tool_call_id,
                "tool_name": request.tool_name,
                "arguments": masked_args,
                "sanitized_args": masked_args,
                "trace_id": request.trace_id,
            },
        )
    ]
    if approval_proposal is not None:
        events.append(
            AssistantToolSseEvent(
                event="approval_required",
                data={
                    **approval_proposal,
                    "proposal_id": str(
                        approval_proposal.get("proposal_id") or request.tool_call_id
                    ),
                    "action_kind": str(
                        approval_proposal.get("transition_action") or "CONTINUE_IN_PROCESS"
                    ),
                    "target_uri": str(approval_proposal.get("target_uri") or ""),
                    "workflow_ref": str(
                        approval_proposal.get("human_arbitration_uri")
                        or "orcia://system/workflows/hitl-gate"
                    ),
                    "requires_human_anchor": True,
                    "turn_id": request.turn_id,
                    "trace_id": request.trace_id,
                },
            )
        )
    mapped_status = (
        "ok"
        if verdict in ("EXECUTED", "DEDUPLICATED")
        else ("denied" if verdict in ("DENIED", "APPROVAL_REQUIRED") else "error")
    )
    events.append(
        AssistantToolSseEvent(
            event="tool_result",
            data={
                "turn_id": request.turn_id,
                "iteration": request.iteration,
                "tool_call_id": request.tool_call_id,
                "tool_name": request.tool_name,
                "verdict": verdict,
                "status": mapped_status,
                "deduplicated": deduplicated,
                "reason_code": reason_code,
                "summary": summary,
                "evidence_refs": list(evidence_refs),
                "audit_event_id": audit_event_id,
                "latency_ms": round(latency_ms, 2),
                "trace_id": request.trace_id,
            },
        )
    )
    return tuple(events)


__all__ = [
    "OutboxEnqueueCallback",
    "build_tool_sse_events",
    "enqueue_arbitration_outbox_event",
    "record_tool_audit_ledger",
]
