"""PG18 SQL Helpers for Durable DBOS Workflow Launch, Anchor Pause & Outbox (`Story 26.8`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

import sqlalchemy as sa

from orcia_core.blackboard.models import (
    StepExecutionEntity,
    StepMemlogEntry,
    WorkflowExecutionRegime,
)
from orcia_core.orchestration._internal.outbox_repository import SqlDomainEventsOutboxRepository
from orcia_core.orchestration._internal.sql_repository import SqlOrchestrationRepository
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_kernel.events import ArtifactProduced, DomainEvent, StepCompleted
from orcia_kernel.ids import new_uuid7_str


async def get_run_execution_context_sql(
    uow: DbosSqlAlchemyUnitOfWork, run_id: str
) -> tuple[str, str, str]:
    """Return `(workspace_id, workflow_uri, execution_regime)` for `run_id` from PG18."""
    async with uow.session_scope() as session:
        row = (
            await session.execute(
                sa.text(
                    """
                    SELECT
                        wr.workspace_id::text,
                        COALESCE(wd.uri, :fallback_uri) AS workflow_uri,
                        wr.execution_regime
                    FROM workflow_runs wr
                    LEFT JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
                    WHERE wr.id = CAST(:run_id AS uuid)
                    LIMIT 1;
                    """
                ),
                {"run_id": run_id, "fallback_uri": f"orcia://workflows/durable/{run_id}"},
            )
        ).fetchone()
    if row is None:
        return (
            "0192c4e0-0000-7000-8000-000000000201",
            f"orcia://workflows/durable/{run_id}",
            "INTERACTIVE_COACHING",
        )
    return str(row[0]), str(row[1]), str(row[2])


async def has_human_anchor_signature_sql(
    uow: DbosSqlAlchemyUnitOfWork, *, run_id: str, step_key: str
) -> bool:
    """Return True when a signed `human_anchor_signatures` row exists for `(run_id, step_key)`."""
    async with uow.session_scope() as session:
        row = (
            await session.execute(
                sa.text(
                    """
                    SELECT 1
                    FROM human_anchor_signatures
                    WHERE run_id = CAST(:run_id AS uuid)
                      AND step_key = :step_key
                      AND char_length >= 30
                    LIMIT 1;
                    """
                ),
                {"run_id": run_id, "step_key": step_key},
            )
        ).fetchone()
    return row is not None


async def ensure_step_waiting_anchor_sql(
    uow: DbosSqlAlchemyUnitOfWork, *, run_id: str, step_key: str
) -> None:
    """Ensure `step_executions.status` is `WAITING_FOR_HUMAN_ANCHOR` when unsigned."""
    async with uow.session_scope() as session:
        await session.execute(
            sa.text(
                """
                UPDATE step_executions
                SET status = 'WAITING_FOR_HUMAN_ANCHOR',
                    updated_at = NOW()
                WHERE run_id = CAST(:run_id AS uuid)
                  AND step_key = :step_key
                  AND status = 'PENDING';
                """
            ),
            {"run_id": run_id, "step_key": step_key},
        )


async def enqueue_outbox_event_sql(uow: DbosSqlAlchemyUnitOfWork, event: DomainEvent) -> None:
    """Persist a `DomainEvent` row inside `domain_events_outbox` idempotently."""
    outbox_repo = SqlDomainEventsOutboxRepository(uow)
    await outbox_repo.enqueue_event(event)


def build_step_execution_record(
    *,
    existing: StepExecutionEntity | None,
    step_id: str,
    run_id: str,
    step_key: str,
    step_index: int,
    resolved_type: str,
    exec_regime: str,
    resolved_payload: dict[str, Any],
    memlog_summary: str,
    memlog_details: str,
    cost_usd: float,
) -> StepExecutionEntity:
    """Build an updated `StepExecutionEntity` preserving prior attempts and memlog entries."""
    new_entry = StepMemlogEntry(
        entry_id=new_uuid7_str(),
        step_key=step_key,
        marker_type="REASONING",
        summary=memlog_summary,
        details=memlog_details,
    )
    prior_memlog = existing.step_memlog if existing is not None else ()
    return StepExecutionEntity(
        id=step_id,
        step_execution_key=(
            existing.step_execution_key
            if existing is not None
            else f"stepexec-{run_id[-6:]}-{step_key}"
        ),
        run_id=run_id,
        step_key=step_key,
        step_index=step_index,
        step_type=resolved_type,  # type: ignore[arg-type]
        execution_mode=cast(WorkflowExecutionRegime, exec_regime),
        status="EXECUTING_AGENT",
        attempt_count=(existing.attempt_count + 1) if existing else 1,
        max_agent_retries=existing.max_agent_retries if existing is not None else 3,
        draft_artifact=resolved_payload,
        step_memlog=(*prior_memlog, new_entry),
        cost_usd=cost_usd,
    )


def build_step_artifact_outbox_events(
    *,
    step_id: str,
    run_id: str,
    workspace_id: str,
    step_key: str,
    cost_usd: float,
    resolved_payload: dict[str, Any],
    trace_id: str,
) -> tuple[DomainEvent, ...]:
    """Build deterministic `StepCompleted` and `ArtifactProduced` outbox events."""
    serialized = json.dumps(resolved_payload, sort_keys=True, separators=(",", ":"))
    sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    cas_key = f"cas/sha256/{sha256[:16]}/{step_key}.json"
    return (
        StepCompleted.create(
            step_execution_id=step_id,
            run_id=run_id,
            workspace_id=workspace_id,
            step_key=step_key,
            cost_usd=cost_usd,
            trace_id=trace_id,
        ),
        ArtifactProduced.create(
            snapshot_id=new_uuid7_str(),
            run_id=run_id,
            workspace_id=workspace_id,
            artifact_cas_key=cas_key,
            artifact_sha256=sha256,
            trace_id=trace_id,
        ),
    )


async def append_rewind_supersede_tombstone_sql(
    repository: SqlOrchestrationRepository, *, run_id: str, target_step_key: str
) -> None:
    """Append a `SUPERSEDED` snapshot tombstone prior to forking a DBOS workflow."""
    snapshots = await repository.list_snapshots(run_id)
    steps = await repository.list_step_executions(run_id)
    step_index_by_key = {s.step_key: s.step_index for s in steps}
    target_idx = step_index_by_key.get(target_step_key, 0)
    to_supersede = [
        snap
        for snap in snapshots
        if snap.branch_status == "ACTIVE" and step_index_by_key.get(snap.step_key, 0) >= target_idx
    ]
    if to_supersede:
        first_sup = to_supersede[0]
        await repository.append_snapshot(
            run_id=run_id,
            step_execution_id=first_sup.step_execution_id,
            step_key=first_sup.step_key,
            branch_status="SUPERSEDED",
            artifact_payload={"rewind_target_step_key": target_step_key},
            parent_snapshot_id=first_sup.id,
            superseded_snapshot_ids=tuple(s.id for s in to_supersede),
        )


__all__ = [
    "enqueue_outbox_event_sql",
    "ensure_step_waiting_anchor_sql",
    "get_run_execution_context_sql",
    "has_human_anchor_signature_sql",
]
