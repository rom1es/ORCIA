"""DBOS workflow and step decorator definitions extracted from `dbos_engine.py`."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dbos import DBOS

from orcia_core.orchestration._internal._sql_dbos_launch_helpers import (
    enqueue_outbox_event_sql,
    ensure_step_waiting_anchor_sql,
    get_run_execution_context_sql,
    has_human_anchor_signature_sql,
)
from orcia_kernel.events import HumanArbitrationRequested, RunTerminated
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration._internal.dbos_engine import DbosDurableWorkflowEngine

ARBITRATION_TOPIC = "orcia.human.arbitration"
HUMAN_ANCHOR_TOPIC = "orcia.human.anchor"

_RUNTIME_BINDINGS: list[DbosDurableWorkflowEngine] = []
_RUN_STATE_WAITERS: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Event, bool]] = {}


def register_run_state_waiter(run_id: str, *, wait_for_completion: bool = False) -> asyncio.Event:
    """Register an `asyncio.Event` signaled when a DBOS run pauses or completes."""
    loop = asyncio.get_running_loop()
    event = asyncio.Event()
    _RUN_STATE_WAITERS[run_id] = (loop, event, wait_for_completion)
    return event


def clear_run_state_waiter(run_id: str) -> None:
    """Remove any registered state waiter for `run_id`."""
    _RUN_STATE_WAITERS.pop(run_id, None)


def signal_run_state_reached(run_id: str, *, completed: bool = False) -> None:
    """Concurrent thread and event-loop signal that `run_id` paused (`WAITING_*`) or finished."""
    entry = _RUN_STATE_WAITERS.get(run_id)
    if entry is None:
        return
    loop, event, wait_for_completion = entry
    if wait_for_completion and not completed:
        return
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None
    if current_loop is loop:
        event.set()
    else:
        loop.call_soon_threadsafe(event.set)


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
    step_type: str = "AGENT",
    emit_outbox: bool = False,
    trace_id: str = "0" * 32,
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
        step_type=step_type,
        emit_outbox=emit_outbox,
        trace_id=trace_id,
    )
    return snap.id


@DBOS.step()
async def _prepare_human_anchor_wait_step(
    run_id: str,
    step_key: str,
    emit_outbox: bool,
    trace_id: str,
) -> bool:
    """Check PG18 anchor signature inside a DBOS step so replay sees deterministic state."""
    engine = _require_bound_runtime()
    if await has_human_anchor_signature_sql(engine.uow, run_id=run_id, step_key=step_key):
        return False
    await ensure_step_waiting_anchor_sql(engine.uow, run_id=run_id, step_key=step_key)
    await engine.repository.update_run_status(run_id, "WAITING_FOR_HUMAN_ARBITRATION")
    if emit_outbox:
        ws_id, _, _ = await get_run_execution_context_sql(engine.uow, run_id)
        await enqueue_outbox_event_sql(
            engine.uow,
            HumanArbitrationRequested.create(
                arbitration_id=new_uuid7_str(),
                run_id=run_id,
                workspace_id=ws_id,
                step_key=step_key,
                options_count=1,
                trace_id=trace_id,
            ),
        )
    return True


@DBOS.step()
async def _verify_human_anchor_signed_step(run_id: str, step_key: str) -> bool:
    """Re-verify PG18 anchor signature after `DBOS.recv_async` inside a DBOS step."""
    engine = _require_bound_runtime()
    signed = await has_human_anchor_signature_sql(engine.uow, run_id=run_id, step_key=step_key)
    if signed:
        await engine.repository.update_run_status(run_id, "RUNNING")
    return signed


@DBOS.workflow()
async def _orcia_durable_run_workflow(
    run_id: str,
    steps: tuple[str, ...],
    pause_for_arbitration_after_step: str | None = None,
    timeout_seconds: float = 30.0,
    anchored_step_keys: tuple[str, ...] = (),
    step_types_by_key: dict[str, str] | None = None,
    emit_outbox_events: bool = False,
    trace_id: str = "0" * 32,
    skip_step_keys: tuple[str, ...] = (),
    initial_parent_snapshot_id: str | None = None,
) -> DurableWorkflowRunSummary:
    engine = _require_bound_runtime()
    workflow_id = DBOS.workflow_id or f"wf-{run_id}"
    if (
        not anchored_step_keys
        and await engine.repository.get_run_status(run_id) != "KILL_SWITCH_STOPPED"
    ):
        await engine.repository.update_run_status(run_id, "RUNNING")

    committed_ids: list[str] = []
    parent_snap_id: str | None = initial_parent_snapshot_id
    arbitration_decision: str | None = None
    anchored_set = set(anchored_step_keys)
    skip_set = set(skip_step_keys)

    for idx, step_key in enumerate(steps):
        if await engine.repository.get_run_status(run_id) == "KILL_SWITCH_STOPPED":
            signal_run_state_reached(run_id, completed=True)
            return DurableWorkflowRunSummary(
                workflow_id=workflow_id,
                run_id=run_id,
                final_status="KILL_SWITCH_STOPPED",
                committed_snapshot_ids=tuple(committed_ids),
                arbitration_decision=arbitration_decision,
            )
        if step_key in skip_set:
            continue

        if step_key in anchored_set:
            needs_wait = await _prepare_human_anchor_wait_step(
                run_id, step_key, emit_outbox_events, trace_id
            )
            if needs_wait:
                signal_run_state_reached(run_id)
                raw_anchor = await DBOS.recv_async(
                    topic=HUMAN_ANCHOR_TOPIC, timeout_seconds=timeout_seconds
                )
                signed_now = await _verify_human_anchor_signed_step(run_id, step_key)
                if raw_anchor is None or not signed_now:
                    signal_run_state_reached(run_id)
                    return DurableWorkflowRunSummary(
                        workflow_id=workflow_id,
                        run_id=run_id,
                        final_status="WAITING_FOR_HUMAN_ARBITRATION",
                        committed_snapshot_ids=tuple(committed_ids),
                        arbitration_decision=arbitration_decision,
                    )

        resolved_type = (step_types_by_key or {}).get(step_key, "AGENT")
        snap_id = await _execute_durable_step(
            run_id,
            step_key,
            idx,
            parent_snap_id,
            step_type=resolved_type,
            emit_outbox=emit_outbox_events,
            trace_id=trace_id,
        )
        committed_ids.append(snap_id)
        parent_snap_id = snap_id

        if pause_for_arbitration_after_step == step_key:
            await engine.repository.update_run_status(run_id, "WAITING_FOR_HUMAN_ARBITRATION")
            signal_run_state_reached(run_id)
            raw_decision = await DBOS.recv_async(
                topic=ARBITRATION_TOPIC, timeout_seconds=timeout_seconds
            )
            arbitration_decision = str(raw_decision) if raw_decision is not None else "TIMEOUT"
            await engine.repository.update_run_status(run_id, "RUNNING")

    await engine.repository.update_run_status(run_id, "COMPLETED")
    if emit_outbox_events:
        ws_id, _, _ = await get_run_execution_context_sql(engine.uow, run_id)
        await enqueue_outbox_event_sql(
            engine.uow,
            RunTerminated.create(
                run_id=run_id,
                workspace_id=ws_id,
                final_status="COMPLETED",
                total_cost_usd=round(0.25 * len(steps), 4),
                trace_id=trace_id,
            ),
        )
    signal_run_state_reached(run_id, completed=True)
    return DurableWorkflowRunSummary(
        workflow_id=workflow_id,
        run_id=run_id,
        final_status="COMPLETED",
        committed_snapshot_ids=tuple(committed_ids),
        arbitration_decision=arbitration_decision,
    )
