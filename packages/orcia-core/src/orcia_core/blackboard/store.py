"""Append-Only Blackboard Store & Step Execution Draft Manager (Story 3.2, AD-2, NFR-SEC-3).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from typing import Any

from orcia_core.blackboard.models import (
    BlackboardSnapshotEntity,
    StepExecutionEntity,
    StepExecutionStatus,
    StepMemlogEntry,
)
from orcia_core.catalog.cas_resolver import FederatedUriResolver, compute_bytes_sha256
from orcia_core.catalog.models import CasObjectEntry
from orcia_core.domain.exceptions import ResourceNotFoundError, ValidationDomainError
from orcia_core.domain.identifiers import new_uuid7_str


class AppendOnlyBlackboardStore:
    """Append-only Blackboard store enforcing draft/snapshot separation & lexical run isolation."""

    def __init__(self, *, resolver: FederatedUriResolver | None = None) -> None:
        self.resolver = resolver or FederatedUriResolver()
        self._step_executions_by_id: dict[str, StepExecutionEntity] = {}
        self._step_exec_by_run_and_key: dict[tuple[str, str], str] = {}
        self._snapshots_by_id: dict[str, BlackboardSnapshotEntity] = {}
        self._snapshots_by_run: dict[str, list[str]] = {}
        self._superseded_ids: set[str] = set()

    def register_step_execution(self, step_exec: StepExecutionEntity) -> StepExecutionEntity:
        """Register or replace a mutable `StepExecutionEntity` (draft table)."""
        self._step_executions_by_id[step_exec.id] = step_exec
        self._step_exec_by_run_and_key[(step_exec.run_id, step_exec.step_key)] = step_exec.id
        return step_exec

    def get_step_execution(self, run_id: str, step_key: str) -> StepExecutionEntity:
        """Retrieve a `StepExecutionEntity` for `(run_id, step_key)` or raise 404."""
        exec_id = self._step_exec_by_run_and_key.get((run_id, step_key))
        if exec_id is None or exec_id not in self._step_executions_by_id:
            raise ResourceNotFoundError(
                detail_override=f"Step execution '{step_key}' introuvable pour le run '{run_id}'."
            )
        return self._step_executions_by_id[exec_id]

    def list_step_executions(self, run_id: str) -> tuple[StepExecutionEntity, ...]:
        """Return all `StepExecutionEntity` rows for `run_id` ordered by `step_index`."""
        items = [s for s in self._step_executions_by_id.values() if s.run_id == run_id]
        return tuple(sorted(items, key=lambda s: s.step_index))

    def save_step_draft(
        self,
        run_id: str,
        step_key: str,
        *,
        status: StepExecutionStatus,
        draft_artifact: dict[str, Any],
        memlog_entries: tuple[StepMemlogEntry, ...] = (),
        hydrated_input_uris: tuple[str, ...] | None = None,
        child_run_id: str | None = None,
        added_cost_usd: float = 0.0,
    ) -> StepExecutionEntity:
        """Update `draft_artifact_jsonb` and `step_memlog_jsonb` without creating a snapshot."""
        current = self.get_step_execution(run_id, step_key)
        if status == "COMMITTED":
            raise ValidationDomainError(
                detail_override="Utilisez commit_step_snapshot() pour passer une étape à COMMITTED."
            )
        raw_bytes = json.dumps(draft_artifact, sort_keys=True).encode("utf-8")
        sha = compute_bytes_sha256(raw_bytes)
        draft_cas_key = f"cas/{sha}"
        self.resolver.cas_store.put_object(
            CasObjectEntry(
                cas_key=draft_cas_key,
                sha256=sha,
                source_uri=f"orcia://runs/{run_id}/steps/{step_key}/draft",
                content_bytes=raw_bytes,
                content_type="application/json",
            )
        )
        updated = replace(
            current,
            status=status,
            draft_artifact=copy.deepcopy(draft_artifact),
            draft_cas_key=draft_cas_key,
            step_memlog=(*current.step_memlog, *memlog_entries),
            hydrated_input_uris=(
                hydrated_input_uris
                if hydrated_input_uris is not None
                else current.hydrated_input_uris
            ),
            child_run_id=child_run_id if child_run_id is not None else current.child_run_id,
            cost_usd=round(current.cost_usd + added_cost_usd, 4),
        )
        return self.register_step_execution(updated)

    def record_bounded_retry(
        self,
        run_id: str,
        step_key: str,
        *,
        feedback_reason: str,
    ) -> StepExecutionEntity:
        """Increment `attempt_count` up to `max_agent_retries` (`AD-12`)."""
        current = self.get_step_execution(run_id, step_key)
        next_attempt = current.attempt_count + 1
        retry_entry = StepMemlogEntry(
            entry_id=new_uuid7_str(),
            step_key=step_key,
            marker_type="FEEDBACK_RETRY",
            summary=f"Tentative {next_attempt}/{current.max_agent_retries}",
            details=feedback_reason,
        )
        if next_attempt > current.max_agent_retries:
            exhausted = replace(
                current,
                attempt_count=current.max_agent_retries,
                status="WAITING_FOR_HUMAN_ARBITRATION",
                step_memlog=(*current.step_memlog, retry_entry),
            )
            self.register_step_execution(exhausted)
            raise ValidationDomainError(
                detail_override=(
                    f"Plafond de boucles de rétroaction atteint ({current.max_agent_retries}) "
                    f"sur l'étape '{step_key}' — escalade vers arbitrage humain."
                )
            )
        updated = replace(
            current,
            attempt_count=next_attempt,
            status="EXECUTING_AGENT",
            step_memlog=(*current.step_memlog, retry_entry),
        )
        return self.register_step_execution(updated)

    def commit_step_snapshot(
        self,
        run_id: str,
        step_key: str,
        *,
        parent_snapshot_id: str | None = None,
        superseded_snapshot_ids: tuple[str, ...] = (),
    ) -> BlackboardSnapshotEntity:
        """Commit a `StepExecutionEntity` into an immutable `BlackboardSnapshotEntity` (`AD-2`)."""
        current = self.get_step_execution(run_id, step_key)
        # Idempotency guard: if already COMMITTED with an active snapshot, return it
        if (
            current.status == "COMMITTED"
            and current.committed_snapshot_id
            and current.committed_snapshot_id in self._snapshots_by_id
            and not superseded_snapshot_ids
        ):
            return self._snapshots_by_id[current.committed_snapshot_id]

        raw_bytes = json.dumps(current.draft_artifact, sort_keys=True).encode("utf-8")
        sha = compute_bytes_sha256(raw_bytes)
        cas_key = f"cas/{sha}"
        self.resolver.cas_store.put_object(
            CasObjectEntry(
                cas_key=cas_key,
                sha256=sha,
                source_uri=f"orcia://runs/{run_id}/steps/{step_key}/artifacts/main",
                content_bytes=raw_bytes,
                content_type="application/json",
            )
        )
        existing_for_step = [
            s.id for s in self.get_active_snapshots(run_id) if s.step_key == step_key
        ]
        all_superseded = tuple(dict.fromkeys((*superseded_snapshot_ids, *existing_for_step)))

        snap_id = new_uuid7_str()
        snapshot = BlackboardSnapshotEntity(
            id=snap_id,
            snapshot_key=f"snap-{run_id[-6:]}-{step_key}-{snap_id[-6:]}",
            run_id=run_id,
            step_execution_id=current.id,
            parent_snapshot_id=parent_snapshot_id,
            step_key=step_key,
            branch_status="ACTIVE",
            artifact_payload=copy.deepcopy(current.draft_artifact),
            artifact_cas_key=cas_key,
            artifact_sha256=sha,
            memlog_summary=current.step_memlog,
            superseded_snapshot_ids=all_superseded,
        )
        self._snapshots_by_id[snap_id] = snapshot
        self._snapshots_by_run.setdefault(run_id, []).append(snap_id)
        for sup_id in all_superseded:
            self._superseded_ids.add(sup_id)

        committed_step = replace(
            current,
            status="COMMITTED",
            committed_snapshot_id=snap_id,
        )
        self.register_step_execution(committed_step)
        return snapshot

    def mutate_or_delete_snapshot(self, snapshot_id: str) -> None:
        """Always reject any mutation or deletion of an existing snapshot (`NFR-SEC-3`)."""
        raise ValidationDomainError(
            detail_override=(
                f"ERR_BLACKBOARD_APPEND_ONLY_VIOLATION: blackboard_snapshots is strictly "
                f"append-only (mutation/delete forbidden on snapshot id={snapshot_id})."
            )
        )

    def get_active_snapshots(self, run_id: str) -> tuple[BlackboardSnapshotEntity, ...]:
        """Return active snapshots for `run_id` ONLY (strict lexical isolation between runs)."""
        snap_ids = self._snapshots_by_run.get(run_id, [])
        result: list[BlackboardSnapshotEntity] = []
        for sid in snap_ids:
            snap = self._snapshots_by_id[sid]
            if sid not in self._superseded_ids and snap.branch_status == "ACTIVE":
                result.append(snap)
        return tuple(result)

    def get_active_step_snapshot(
        self, run_id: str, step_key: str
    ) -> BlackboardSnapshotEntity | None:
        """Return the latest active snapshot for `(run_id, step_key)` within `run_id`."""
        active = [s for s in self.get_active_snapshots(run_id) if s.step_key == step_key]
        return active[-1] if active else None
