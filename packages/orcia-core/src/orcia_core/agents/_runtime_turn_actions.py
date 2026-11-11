"""Turn-level emission, surgical action, write-preview suspension, and completion helpers.

Extracted from `reflexive_runtime.py` (`Story 16.2`) to keep every module below 350 lines.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from orcia_core.agents._runtime_helpers import (
    assert_snapshot_not_expired,
    build_scratchpad_entry_from_observation,
    build_trace_event_from_observation,
)
from orcia_core.agents.errors import PolicyDeniedError, ReflexiveInvalidStateError
from orcia_core.agents.reflexive_schemas import (
    AgentTraceEvent,
    ReflexiveScratchpadEntry,
    ReflexiveSessionSnapshot,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
    ReflexiveWriteApprovalInput,
    TraceEventKind,
    compute_default_session_expiry_utc,
)
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveLlmPort,
    ReflexiveWriteGatePort,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalPrimitiveName,
)
from orcia_core.storage.claim_check import ClaimCheckStorageService

PublishEventFn = Callable[[ReflexiveSessionSnapshot, AgentTraceEvent], Awaitable[None]]
PersistSnapshotFn = Callable[[ReflexiveSessionSnapshot], Awaitable[None]]


async def emit_thought_and_answer_deltas(
    *,
    llm: ReflexiveLlmPort,
    snapshot: ReflexiveSessionSnapshot,
    turn_input: ReflexiveTurnInput,
    decision: ReflexiveTurnDecision,
    turn_idx: int,
    started_perf: float,
    publish_fn: PublishEventFn,
) -> None:
    """Stream real `thought_delta` and `answer_token_delta` chunks without space splitting."""
    if decision.group_title:
        await publish_fn(
            snapshot,
            AgentTraceEvent(
                execution_id=snapshot.execution_id,
                sequence_index=len(snapshot.trace_events),
                turn_index=turn_idx,
                kind=TraceEventKind.GROUP_HEADER,
                group_title=decision.group_title,
            ),
        )
    if decision.status_label:
        await publish_fn(
            snapshot,
            AgentTraceEvent(
                execution_id=snapshot.execution_id,
                sequence_index=len(snapshot.trace_events),
                turn_index=turn_idx,
                kind=TraceEventKind.STATUS_WORKING,
                status_label=decision.status_label,
            ),
        )
    emitted_thought = False
    emitted_answer = False
    async for chunk in llm.stream_turn_deltas(turn_input, decision):
        if chunk.thinking_delta:
            emitted_thought = True
            await publish_fn(
                snapshot,
                AgentTraceEvent(
                    execution_id=snapshot.execution_id,
                    sequence_index=len(snapshot.trace_events),
                    turn_index=turn_idx,
                    kind=TraceEventKind.THOUGHT_DELTA,
                    delta_text=chunk.thinking_delta,
                ),
            )
        if chunk.answer_delta:
            emitted_answer = True
            await publish_fn(
                snapshot,
                AgentTraceEvent(
                    execution_id=snapshot.execution_id,
                    sequence_index=len(snapshot.trace_events),
                    turn_index=turn_idx,
                    kind=TraceEventKind.ANSWER_TOKEN_DELTA,
                    delta_text=chunk.answer_delta,
                ),
            )
    if emitted_thought or decision.thought_text:
        elapsed_ms = max(1, int((time.perf_counter() - started_perf) * 1000))
        await publish_fn(
            snapshot,
            AgentTraceEvent(
                execution_id=snapshot.execution_id,
                sequence_index=len(snapshot.trace_events),
                turn_index=turn_idx,
                kind=TraceEventKind.THOUGHT_COMPLETED,
                thought_duration_ms=elapsed_ms,
            ),
        )
    if decision.action_kind == "final_answer" and decision.final_markdown and not emitted_answer:
        await publish_fn(
            snapshot,
            AgentTraceEvent(
                execution_id=snapshot.execution_id,
                sequence_index=len(snapshot.trace_events),
                turn_index=turn_idx,
                kind=TraceEventKind.ANSWER_TOKEN_DELTA,
                delta_text=decision.final_markdown,
            ),
        )


async def execute_surgical_turn(
    *,
    explorer: SurgicalExplorerPort,
    snapshot: ReflexiveSessionSnapshot,
    decision: ReflexiveTurnDecision,
    turn_idx: int,
    publish_fn: PublishEventFn,
) -> None:
    """Invoke `SurgicalExplorerPort` (`Story 16.1`) and record compact observation in scratchpad."""
    prim = decision.primitive or SurgicalPrimitiveName.INSPECT_RESOURCE_LINES
    obs = await explorer.execute_primitive(
        prim,
        resource_uri=decision.resource_uri,
        query=decision.query,
        start_line=decision.start_line,
        end_line=decision.end_line,
        workspace_id=snapshot.workspace_id,
        actor_id=snapshot.actor_user_id,
        has_read_source=snapshot.has_read_source,
    )
    ev = build_trace_event_from_observation(
        execution_id=snapshot.execution_id,
        sequence_index=len(snapshot.trace_events),
        turn_index=turn_idx,
        obs=obs,
    )
    await publish_fn(snapshot, ev)
    snapshot.scratchpad.append(
        build_scratchpad_entry_from_observation(turn_index=turn_idx, obs=obs)
    )


async def suspend_for_write_preview(
    *,
    write_gate: ReflexiveWriteGatePort | None,
    snapshot: ReflexiveSessionSnapshot,
    decision: ReflexiveTurnDecision,
    turn_idx: int,
    publish_fn: PublishEventFn,
    persist_fn: PersistSnapshotFn,
) -> ReflexiveSessionSnapshot:
    """Build `WritePreviewCard`, transition to `WAITING_WRITE_PREVIEW`, persist, and return."""
    if write_gate is None:
        raise PolicyDeniedError(
            detail_override="Aucun port de gouvernance d'écriture n'est configuré."
        )
    preview = await write_gate.prepare_write_preview(
        connector_type=decision.connector_type or "mcp:default",
        action=decision.write_action or "write_resource",
        target_resource_uri=decision.write_target_uri or "catalog://resource/target",
        action_summary=decision.write_summary or "Action externe soumise à approbation",
        payload=decision.write_payload,
    )
    snapshot.pending_write_preview = preview
    snapshot.status = "WAITING_WRITE_PREVIEW"
    snapshot.turns_used = turn_idx + 1
    snapshot.updated_at_utc = datetime.now(UTC).isoformat()
    snapshot.expires_at_utc = compute_default_session_expiry_utc()
    await publish_fn(
        snapshot,
        AgentTraceEvent(
            execution_id=snapshot.execution_id,
            sequence_index=len(snapshot.trace_events),
            turn_index=turn_idx,
            kind=TraceEventKind.WRITE_PREVIEW_REQUESTED,
            resource_uri=preview.target_resource_uri,
            write_preview_id=preview.preview_id,
            status_label=preview.action_summary,
            metadata=preview.model_dump(mode="json"),
        ),
    )
    await persist_fn(snapshot)
    return snapshot


async def finalize_completed_snapshot(
    *,
    claim_check: ClaimCheckStorageService,
    snapshot: ReflexiveSessionSnapshot,
    final_markdown: str,
    publish_fn: PublishEventFn,
    persist_fn: PersistSnapshotFn,
) -> ReflexiveSessionSnapshot:
    """Archive final Markdown via `ClaimCheckStorageService` and emit `loop_completed`."""
    snapshot.final_markdown = final_markdown
    snapshot.status = "COMPLETED"
    snapshot.artifact_pointer = claim_check.store_artifact(
        run_id=snapshot.execution_id,
        step_id=snapshot.actor_slug,
        iteration=max(1, snapshot.turns_used),
        content=final_markdown,
        mime_type="text/markdown",
    )
    snapshot.updated_at_utc = datetime.now(UTC).isoformat()
    await publish_fn(
        snapshot,
        AgentTraceEvent(
            execution_id=snapshot.execution_id,
            sequence_index=len(snapshot.trace_events),
            turn_index=max(0, snapshot.turns_used - 1),
            kind=TraceEventKind.LOOP_COMPLETED,
            metadata={
                "turns_used": snapshot.turns_used,
                "tokens_used": snapshot.tokens_used,
                "s3_uri": snapshot.artifact_pointer.s3_uri,
                "sha256": snapshot.artifact_pointer.sha256,
            },
        ),
    )
    await persist_fn(snapshot)
    return snapshot


async def mark_snapshot_cancelled(
    *,
    snapshot: ReflexiveSessionSnapshot,
    publish_fn: PublishEventFn,
    persist_fn: PersistSnapshotFn,
) -> ReflexiveSessionSnapshot:
    """Transition snapshot to `CANCELLED` (`0` extra LLM turns) and emit `loop_cancelled`."""
    snapshot.status = "CANCELLED"
    snapshot.updated_at_utc = datetime.now(UTC).isoformat()
    if not snapshot.trace_events or snapshot.trace_events[-1].kind != TraceEventKind.LOOP_CANCELLED:
        await publish_fn(
            snapshot,
            AgentTraceEvent(
                execution_id=snapshot.execution_id,
                sequence_index=len(snapshot.trace_events),
                turn_index=snapshot.turns_used,
                kind=TraceEventKind.LOOP_CANCELLED,
            ),
        )
    await persist_fn(snapshot)
    return snapshot


async def apply_write_gate_decision(
    *,
    write_gate: ReflexiveWriteGatePort | None,
    snapshot: ReflexiveSessionSnapshot,
    approved: bool,
    approval: ReflexiveWriteApprovalInput | None,
    rejection_reason: str,
    persist_fn: PersistSnapshotFn,
) -> None:
    """Validate `WAITING_WRITE_PREVIEW` + TTL, execute or reject write, and mark `RUNNING`."""
    if snapshot.status != "WAITING_WRITE_PREVIEW" or snapshot.pending_write_preview is None:
        raise ReflexiveInvalidStateError(
            detail_override=(
                f"ERR_REFLEXIVE_STATE_INVALID: Execution '{snapshot.execution_id}' is in status "
                f"'{snapshot.status}', expected 'WAITING_WRITE_PREVIEW'."
            )
        )
    assert_snapshot_not_expired(snapshot)
    preview = snapshot.pending_write_preview
    if approved:
        if write_gate is None or approval is None:
            raise PolicyDeniedError(
                detail_override="ERR_WRITE_PREVIEW_APPROVAL_REQUIRED: Jeton signé requis."
            )
        outcome = await write_gate.execute_approved_write(preview=preview, approval=approval)
        snapshot.scratchpad.append(
            ReflexiveScratchpadEntry(
                turn_index=snapshot.turns_used,
                action_kind="external_write_approved",
                resource_uri=preview.target_resource_uri,
                summary=(
                    f"Écriture externe approuvée et appliquée sur {preview.target_resource_uri}."
                ),
                metadata={"write_outcome": outcome, "preview_id": preview.preview_id},
            )
        )
    else:
        reason_clean = rejection_reason.strip() or "Refusé par le valideur humain."
        snapshot.scratchpad.append(
            ReflexiveScratchpadEntry(
                turn_index=snapshot.turns_used,
                action_kind="external_write_rejected",
                resource_uri=preview.target_resource_uri,
                summary=f"Écriture externe refusée par l'humain : {reason_clean}",
                metadata={"preview_id": preview.preview_id, "rejection_reason": reason_clean},
            )
        )
    snapshot.pending_write_preview = None
    snapshot.status = "RUNNING"
    snapshot.updated_at_utc = datetime.now(UTC).isoformat()
    await persist_fn(snapshot)
