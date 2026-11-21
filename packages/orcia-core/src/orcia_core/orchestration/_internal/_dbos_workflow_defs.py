"""DBOS workflow and step decorator definitions extracted from `dbos_engine.py`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dbos import DBOS

if TYPE_CHECKING:
    from orcia_core.orchestration._internal.dbos_engine import DbosDurableWorkflowEngine

ARBITRATION_TOPIC = "orcia.human.arbitration"

_RUNTIME_BINDINGS: list[DbosDurableWorkflowEngine] = []


def bind_dbos_runtime(engine: DbosDurableWorkflowEngine) -> None:
    """Register an active DBOS durable engine binding."""
    _RUNTIME_BINDINGS.append(engine)


def unbind_dbos_runtime(engine: DbosDurableWorkflowEngine) -> None:
    """Remove an active DBOS durable engine binding if present."""
    if engine in _RUNTIME_BINDINGS:
        _RUNTIME_BINDINGS.remove(engine)


def _require_bound_runtime() -> DbosDurableWorkflowEngine:
    if not _RUNTIME_BINDINGS:
        raise RuntimeError("DbosDurableWorkflowEngine is not launched.")
    return _RUNTIME_BINDINGS[-1]


def has_active_dbos_runtime_bindings() -> bool:
    """Return True when a `DbosDurableWorkflowEngine` is currently bound."""
    return bool(_RUNTIME_BINDINGS)


@dataclass(frozen=True, slots=True)
class DurableWorkflowRunSummary:
    """Result summary of a DBOS durable workflow run persisted in PostgreSQL 18."""

    workflow_id: str
    run_id: str
    final_status: str
    committed_snapshot_ids: tuple[str, ...]
    arbitration_decision: str | None = None


@DBOS.step()
async def _execute_durable_step(
    run_id: str,
    step_key: str,
    step_index: int,
    parent_snapshot_id: str | None,
) -> str:
    engine = _require_bound_runtime()
    if await engine.repository.get_run_status(run_id) == "KILL_SWITCH_STOPPED":
        raise RuntimeError(f"KILL_SWITCH_STOPPED:{run_id}")
    snap = await engine.persist_step_and_commit_snapshot(
        run_id=run_id,
        step_key=step_key,
        step_index=step_index,
        artifact_payload=None,
        parent_snapshot_id=parent_snapshot_id,
    )
    return snap.id


@DBOS.workflow()
async def _orcia_durable_run_workflow(
    run_id: str,
    steps: tuple[str, ...],
    pause_for_arbitration_after_step: str | None = None,
    timeout_seconds: float = 30.0,
) -> DurableWorkflowRunSummary:
    engine = _require_bound_runtime()
    workflow_id = DBOS.workflow_id or f"wf-{run_id}"
    await engine.repository.update_run_status(run_id, "RUNNING")
    committed_ids: list[str] = []
    parent_snap_id: str | None = None
    arbitration_decision: str | None = None

    for idx, step_key in enumerate(steps):
        current_status = await engine.repository.get_run_status(run_id)
        if current_status == "KILL_SWITCH_STOPPED":
            return DurableWorkflowRunSummary(
                workflow_id=workflow_id,
                run_id=run_id,
                final_status="KILL_SWITCH_STOPPED",
                committed_snapshot_ids=tuple(committed_ids),
                arbitration_decision=arbitration_decision,
            )

        snap_id = await _execute_durable_step(
            run_id,
            step_key,
            idx,
            parent_snap_id,
        )
        committed_ids.append(snap_id)
        parent_snap_id = snap_id

        if pause_for_arbitration_after_step == step_key:
            await engine.repository.update_run_status(run_id, "WAITING_FOR_HUMAN_ARBITRATION")
            raw_decision = await DBOS.recv_async(
                topic=ARBITRATION_TOPIC, timeout_seconds=timeout_seconds
            )
            arbitration_decision = str(raw_decision) if raw_decision is not None else "TIMEOUT"
            await engine.repository.update_run_status(run_id, "RUNNING")

    await engine.repository.update_run_status(run_id, "COMPLETED")
    return DurableWorkflowRunSummary(
        workflow_id=workflow_id,
        run_id=run_id,
        final_status="COMPLETED",
        committed_snapshot_ids=tuple(committed_ids),
        arbitration_decision=arbitration_decision,
    )
