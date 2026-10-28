"""SQLAlchemy 2.1 Asyncio (`asyncpg`) Repository for Orchestration & Blackboard (`Story 3.2b`).

Persists `workflow_runs`, `run_lock_manifests`, `step_executions`, and strictly
append-only `blackboard_snapshots` on PostgreSQL 18 via `DbosSqlAlchemyUnitOfWork` (`ARCH-P1`).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

import sqlalchemy as sa

from orcia_core.blackboard.models import (
    BlackboardSnapshotEntity,
    SnapshotBranchStatus,
    StepExecutionEntity,
    StepExecutionStatus,
    StepMemlogEntry,
    WorkflowExecutionRegime,
    WorkflowStepType,
)
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.orchestration.models import WorkflowRunStatus
from orcia_kernel.ids import new_uuid7_str


class SqlOrchestrationRepository:
    """Async SQLAlchemy 2.1 (`asyncpg`) repository for runs, steps, and append-only snapshots."""

    def __init__(self, uow: DbosSqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def upsert_workflow_run(
        self,
        *,
        run_id: str,
        run_key: str,
        workspace_id: str,
        workflow_def_id: str,
        parent_run_id: str | None,
        parent_step_execution_id: str | None,
        root_run_id: str,
        nesting_depth: int,
        execution_regime: WorkflowExecutionRegime,
        criticality: str,
        trigger_id: str | None,
        trigger_idempotency_key: str | None,
        status: WorkflowRunStatus,
        initiated_by_user_id: str | None,
        execution_identity_mode: str,
        budget_max_usd: float,
    ) -> None:
        """Persist or update a `workflow_runs` row inside an ACID `AsyncSession` transaction."""
        async with self._uow.session_scope() as session:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO workflow_runs (
                        id, run_key, workspace_id, workflow_def_id, parent_run_id,
                        parent_step_execution_id, root_run_id, nesting_depth,
                        execution_regime, criticality, trigger_id, trigger_idempotency_key,
                        status, initiated_by_user_id, execution_identity_mode, budget_max_usd
                    ) VALUES (
                        CAST(:id AS uuid), :run_key, CAST(:workspace_id AS uuid),
                        CAST(:workflow_def_id AS uuid), CAST(:parent_run_id AS uuid),
                        CAST(:parent_step_execution_id AS uuid), CAST(:root_run_id AS uuid),
                        :nesting_depth, :execution_regime, :criticality,
                        CAST(:trigger_id AS uuid), :trigger_idempotency_key,
                        :status, CAST(:initiated_by_user_id AS uuid),
                        :execution_identity_mode, :budget_max_usd
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        budget_max_usd = EXCLUDED.budget_max_usd;
                    """
                ),
                {
                    "id": run_id,
                    "run_key": run_key,
                    "workspace_id": workspace_id,
                    "workflow_def_id": workflow_def_id,
                    "parent_run_id": parent_run_id,
                    "parent_step_execution_id": parent_step_execution_id,
                    "root_run_id": root_run_id,
                    "nesting_depth": nesting_depth,
                    "execution_regime": execution_regime,
                    "criticality": criticality,
                    "trigger_id": trigger_id,
                    "trigger_idempotency_key": trigger_idempotency_key,
                    "status": status,
                    "initiated_by_user_id": initiated_by_user_id,
                    "execution_identity_mode": execution_identity_mode,
                    "budget_max_usd": budget_max_usd,
                },
            )

    async def update_run_status(self, run_id: str, status: WorkflowRunStatus) -> None:
        """Update `workflow_runs.status` inside an ACID transaction."""
        async with self._uow.session_scope() as session:
            await session.execute(
                sa.text(
                    """
                    UPDATE workflow_runs
                    SET status = :status
                    WHERE id = CAST(:run_id AS uuid);
                    """
                ),
                {"run_id": run_id, "status": status},
            )

    async def get_run_status(self, run_id: str) -> WorkflowRunStatus:
        """Read current `workflow_runs.status` from PostgreSQL 18."""
        async with self._uow.session_scope() as session:
            row = (
                await session.execute(
                    sa.text(
                        """
                        SELECT status FROM workflow_runs WHERE id = CAST(:run_id AS uuid);
                        """
                    ),
                    {"run_id": run_id},
                )
            ).fetchone()
            if row is None:
                raise ResourceNotFoundError(
                    detail_override=f"Workflow Run '{run_id}' introuvable en base SQL."
                )
            return cast(WorkflowRunStatus, str(row[0]))

    async def upsert_step_execution(self, step: StepExecutionEntity) -> StepExecutionEntity:
        """Insert or update a `step_executions` row (draft state separation from snapshots)."""
        async with self._uow.session_scope() as session:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO step_executions (
                        id, step_execution_key, run_id, step_key, step_index,
                        step_type, execution_mode, status, attempt_count,
                        max_agent_retries, draft_artifact_jsonb, draft_cas_key,
                        step_memlog_jsonb, hydrated_input_uris_jsonb, child_run_id,
                        committed_snapshot_id, cost_usd, updated_at
                    ) VALUES (
                        CAST(:id AS uuid), :step_execution_key, CAST(:run_id AS uuid),
                        :step_key, :step_index, :step_type, :execution_mode, :status,
                        :attempt_count, :max_agent_retries,
                        CAST(:draft_artifact_jsonb AS jsonb), :draft_cas_key,
                        CAST(:step_memlog_jsonb AS jsonb),
                        CAST(:hydrated_input_uris_jsonb AS jsonb),
                        CAST(:child_run_id AS uuid),
                        CAST(:committed_snapshot_id AS uuid), :cost_usd, NOW()
                    )
                    ON CONFLICT (step_execution_key) DO UPDATE SET
                        status = EXCLUDED.status,
                        attempt_count = EXCLUDED.attempt_count,
                        draft_artifact_jsonb = EXCLUDED.draft_artifact_jsonb,
                        draft_cas_key = EXCLUDED.draft_cas_key,
                        step_memlog_jsonb = EXCLUDED.step_memlog_jsonb,
                        hydrated_input_uris_jsonb = EXCLUDED.hydrated_input_uris_jsonb,
                        child_run_id = EXCLUDED.child_run_id,
                        committed_snapshot_id = EXCLUDED.committed_snapshot_id,
                        cost_usd = EXCLUDED.cost_usd,
                        updated_at = NOW();
                    """
                ),
                {
                    "id": step.id,
                    "step_execution_key": step.step_execution_key,
                    "run_id": step.run_id,
                    "step_key": step.step_key,
                    "step_index": step.step_index,
                    "step_type": step.step_type,
                    "execution_mode": step.execution_mode,
                    "status": step.status,
                    "attempt_count": min(step.attempt_count, 10),
                    "max_agent_retries": step.max_agent_retries,
                    "draft_artifact_jsonb": json.dumps(step.draft_artifact, sort_keys=True),
                    "draft_cas_key": step.draft_cas_key,
                    "step_memlog_jsonb": json.dumps(
                        [m.to_dict() for m in step.step_memlog], sort_keys=True
                    ),
                    "hydrated_input_uris_jsonb": json.dumps(list(step.hydrated_input_uris)),
                    "child_run_id": step.child_run_id,
                    "committed_snapshot_id": step.committed_snapshot_id,
                    "cost_usd": step.cost_usd,
                },
            )
        return step

    async def list_step_executions(self, run_id: str) -> tuple[StepExecutionEntity, ...]:
        """List all `step_executions` for `run_id` ordered by `step_index`."""
        async with self._uow.session_scope() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            """
                            SELECT
                                id::text, step_execution_key, run_id::text, step_key,
                                step_index, step_type, execution_mode, status,
                                attempt_count, max_agent_retries, draft_artifact_jsonb,
                                draft_cas_key, step_memlog_jsonb, hydrated_input_uris_jsonb,
                                child_run_id::text, committed_snapshot_id::text,
                                cost_usd::float8
                            FROM step_executions
                            WHERE run_id = CAST(:run_id AS uuid)
                            ORDER BY step_index ASC;
                            """
                        ),
                        {"run_id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            return tuple(self._row_to_step_entity(dict(r)) for r in rows)

    async def append_snapshot(
        self,
        *,
        run_id: str,
        step_execution_id: str,
        step_key: str,
        branch_status: SnapshotBranchStatus,
        artifact_payload: dict[str, Any],
        memlog_summary: tuple[StepMemlogEntry, ...] = (),
        parent_snapshot_id: str | None = None,
        superseded_snapshot_ids: tuple[str, ...] = (),
    ) -> BlackboardSnapshotEntity:
        """Append an immutable row to `blackboard_snapshots` (strictly INSERT-only)."""
        snap_id = new_uuid7_str()
        serialized = json.dumps(artifact_payload, sort_keys=True, separators=(",", ":"))
        sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        cas_key = f"cas/sha256/{sha256[:16]}/{step_key}.json"
        snap_key = f"snap-{run_id[-6:]}-{step_key}-{snap_id[-6:]}"

        async with self._uow.session_scope() as session:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO blackboard_snapshots (
                        id, snapshot_key, run_id, step_execution_id, parent_snapshot_id,
                        step_key, branch_status, artifact_payload_jsonb, artifact_cas_key,
                        artifact_sha256, memlog_summary_jsonb, superseded_snapshot_ids_jsonb
                    ) VALUES (
                        CAST(:id AS uuid), :snapshot_key, CAST(:run_id AS uuid),
                        CAST(:step_execution_id AS uuid), CAST(:parent_snapshot_id AS uuid),
                        :step_key, :branch_status, CAST(:artifact_payload_jsonb AS jsonb),
                        :artifact_cas_key, :artifact_sha256,
                        CAST(:memlog_summary_jsonb AS jsonb),
                        CAST(:superseded_snapshot_ids_jsonb AS jsonb)
                    );
                    """
                ),
                {
                    "id": snap_id,
                    "snapshot_key": snap_key,
                    "run_id": run_id,
                    "step_execution_id": step_execution_id,
                    "parent_snapshot_id": parent_snapshot_id,
                    "step_key": step_key,
                    "branch_status": branch_status,
                    "artifact_payload_jsonb": serialized,
                    "artifact_cas_key": cas_key,
                    "artifact_sha256": sha256,
                    "memlog_summary_jsonb": json.dumps(
                        [m.to_dict() for m in memlog_summary], sort_keys=True
                    ),
                    "superseded_snapshot_ids_jsonb": json.dumps(list(superseded_snapshot_ids)),
                },
            )
            if branch_status == "ACTIVE":
                await session.execute(
                    sa.text(
                        """
                        UPDATE step_executions
                        SET status = 'COMMITTED',
                            committed_snapshot_id = CAST(:snap_id AS uuid),
                            updated_at = NOW()
                        WHERE id = CAST(:step_execution_id AS uuid);
                        """
                    ),
                    {"snap_id": snap_id, "step_execution_id": step_execution_id},
                )

        return BlackboardSnapshotEntity(
            id=snap_id,
            snapshot_key=snap_key,
            run_id=run_id,
            step_execution_id=step_execution_id,
            parent_snapshot_id=parent_snapshot_id,
            step_key=step_key,
            branch_status=branch_status,
            artifact_payload=dict(artifact_payload),
            artifact_cas_key=cas_key,
            artifact_sha256=sha256,
            memlog_summary=memlog_summary,
            superseded_snapshot_ids=superseded_snapshot_ids,
        )

    async def list_snapshots(self, run_id: str) -> tuple[BlackboardSnapshotEntity, ...]:
        """List all snapshots for `run_id`, resolving effective `SUPERSEDED` lineage."""
        async with self._uow.session_scope() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            """
                            SELECT
                                id::text, snapshot_key, run_id::text, step_execution_id::text,
                                parent_snapshot_id::text, step_key, branch_status,
                                artifact_payload_jsonb, artifact_cas_key,
                                TRIM(artifact_sha256) AS artifact_sha256,
                                memlog_summary_jsonb, superseded_snapshot_ids_jsonb
                            FROM blackboard_snapshots
                            WHERE run_id = CAST(:run_id AS uuid)
                            ORDER BY created_at ASC, id ASC;
                            """
                        ),
                        {"run_id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            superseded_ids: set[str] = set()
            for r in rows:
                sup_raw = r["superseded_snapshot_ids_jsonb"]
                sup_list = json.loads(sup_raw) if isinstance(sup_raw, str) else list(sup_raw or [])
                for sid in sup_list:
                    superseded_ids.add(str(sid))

            entities: list[BlackboardSnapshotEntity] = []
            for r in rows:
                row_dict = dict(r)
                snap_id = str(row_dict["id"])
                effective_status: SnapshotBranchStatus = (
                    "SUPERSEDED"
                    if (snap_id in superseded_ids or row_dict["branch_status"] == "SUPERSEDED")
                    else "ACTIVE"
                )
                entities.append(self._row_to_snapshot_entity(row_dict, effective_status))
            return tuple(entities)

    @staticmethod
    def _row_to_step_entity(row: dict[str, Any]) -> StepExecutionEntity:
        raw_draft = row["draft_artifact_jsonb"]
        draft = json.loads(raw_draft) if isinstance(raw_draft, str) else dict(raw_draft or {})
        raw_memlog = row["step_memlog_jsonb"]
        memlog_list = (
            json.loads(raw_memlog) if isinstance(raw_memlog, str) else list(raw_memlog or [])
        )
        memlogs = tuple(
            StepMemlogEntry(
                entry_id=str(m["entry_id"]),
                step_key=str(m["step_key"]),
                marker_type=m["marker_type"],
                summary=str(m["summary"]),
                details=str(m["details"]),
                source_uris=tuple(str(u) for u in m.get("source_uris", [])),
            )
            for m in memlog_list
        )
        raw_uris = row["hydrated_input_uris_jsonb"]
        uris_list = json.loads(raw_uris) if isinstance(raw_uris, str) else list(raw_uris or [])
        return StepExecutionEntity(
            id=str(row["id"]),
            step_execution_key=str(row["step_execution_key"]),
            run_id=str(row["run_id"]),
            step_key=str(row["step_key"]),
            step_index=int(row["step_index"]),
            step_type=cast(WorkflowStepType, str(row["step_type"])),
            execution_mode=cast(WorkflowExecutionRegime, str(row["execution_mode"])),
            status=cast(StepExecutionStatus, str(row["status"])),
            attempt_count=int(row["attempt_count"]),
            max_agent_retries=int(row["max_agent_retries"]),
            draft_artifact=draft,
            draft_cas_key=str(row["draft_cas_key"]) if row["draft_cas_key"] else None,
            step_memlog=memlogs,
            hydrated_input_uris=tuple(str(u) for u in uris_list),
            child_run_id=str(row["child_run_id"]) if row["child_run_id"] else None,
            committed_snapshot_id=(
                str(row["committed_snapshot_id"]) if row["committed_snapshot_id"] else None
            ),
            cost_usd=float(row["cost_usd"]),
        )

    @staticmethod
    def _row_to_snapshot_entity(
        row: dict[str, Any], effective_status: SnapshotBranchStatus
    ) -> BlackboardSnapshotEntity:
        raw_payload = row["artifact_payload_jsonb"]
        payload = (
            json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload or {})
        )
        raw_memlog = row["memlog_summary_jsonb"]
        memlog_list = (
            json.loads(raw_memlog) if isinstance(raw_memlog, str) else list(raw_memlog or [])
        )
        memlogs = tuple(
            StepMemlogEntry(
                entry_id=str(m["entry_id"]),
                step_key=str(m["step_key"]),
                marker_type=m["marker_type"],
                summary=str(m["summary"]),
                details=str(m["details"]),
                source_uris=tuple(str(u) for u in m.get("source_uris", [])),
            )
            for m in memlog_list
        )
        raw_sup = row["superseded_snapshot_ids_jsonb"]
        sup_list = json.loads(raw_sup) if isinstance(raw_sup, str) else list(raw_sup or [])
        return BlackboardSnapshotEntity(
            id=str(row["id"]),
            snapshot_key=str(row["snapshot_key"]),
            run_id=str(row["run_id"]),
            step_execution_id=str(row["step_execution_id"]),
            parent_snapshot_id=(
                str(row["parent_snapshot_id"]) if row["parent_snapshot_id"] else None
            ),
            step_key=str(row["step_key"]),
            branch_status=effective_status,
            artifact_payload=payload,
            artifact_cas_key=str(row["artifact_cas_key"]),
            artifact_sha256=str(row["artifact_sha256"]).strip(),
            memlog_summary=memlogs,
            superseded_snapshot_ids=tuple(str(s) for s in sup_list),
        )


__all__ = ["SqlOrchestrationRepository"]
