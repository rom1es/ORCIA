"""Story 3.2s (`ARCH-P2-SPIKE`) — DBOS Transact spike harness on PostgreSQL 18.

Validates the 8 Go/No-Go exit criteria for DBOS Transact and verifies `DbosSqlAlchemyUnitOfWork`.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import dramatiq
import sqlalchemy as sa
from dbos import DBOS, DBOSConfig, ScheduleInput, SetWorkflowID, WorkflowHandleAsync
from dramatiq.brokers.stub import StubBroker

from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_kernel.ids import new_uuid7

ARBITRATION_TOPIC = "orcia_human_arbitration"


@dataclass(frozen=True, slots=True)
class ForkSpikeResult:
    original_workflow_id: str
    forked_workflow_id: str
    original_outputs: tuple[str, str, str]
    forked_outputs: tuple[str, str, str]
    step_execution_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class BlackboardSpikeResult:
    initial_snapshot_id: UUID
    forked_snapshot_id: UUID
    total_snapshots: int
    append_only_trigger_blocked_update: bool


_STEP_COUNTERS: Counter[str] = Counter()
_SCHEDULE_INVOCATIONS: list[tuple[str, str]] = []
_DRAMATIQ_RESULTS: list[str] = []
_ACTIVE_UOW: DbosSqlAlchemyUnitOfWork | None = None

_SPIKE_STUB_BROKER = StubBroker()
_SPIKE_STUB_BROKER.emit_after("process_boot")


@dramatiq.actor(broker=_SPIKE_STUB_BROKER, queue_name="orcia_heavy_io_spike")
def _spike_heavy_dramatiq_actor(payload: str) -> None:
    _DRAMATIQ_RESULTS.append(f"dramatiq_processed:{payload}")


def _require_uow() -> DbosSqlAlchemyUnitOfWork:
    if _ACTIVE_UOW is None:
        msg = "Active DbosSqlAlchemyUnitOfWork is not initialized in DbosSpikeRuntime"
        raise RuntimeError(msg)
    return _ACTIVE_UOW


@DBOS.step()
async def _arbitration_prepare_step(run_key: str) -> str:
    _STEP_COUNTERS[f"prepare:{run_key}"] += 1
    return f"prepared:{run_key}"


@DBOS.step()
async def _arbitration_finalize_step(run_key: str, decision: str) -> str:
    _STEP_COUNTERS[f"finalize:{run_key}"] += 1
    return f"completed:{run_key}:decision={decision}"


@DBOS.workflow()
async def spike_arbitration_pause_workflow(run_key: str, timeout_seconds: float = 30.0) -> str:
    """Criterion 1: Pauses on `DBOS.recv_async` (`WAITING_FOR_HUMAN_ARBITRATION`) and resumes."""
    prepared = await _arbitration_prepare_step(run_key)
    decision_raw = await DBOS.recv_async(topic=ARBITRATION_TOPIC, timeout_seconds=timeout_seconds)
    decision = str(decision_raw) if decision_raw is not None else "TIMEOUT"
    return await _arbitration_finalize_step(prepared, decision)


@DBOS.step()
async def _fork_step_1(tag: str) -> str:
    _STEP_COUNTERS["fork_step_1"] += 1
    return f"s1:{tag}:{_STEP_COUNTERS['fork_step_1']}"


@DBOS.step()
async def _fork_step_2(prev: str) -> str:
    _STEP_COUNTERS["fork_step_2"] += 1
    return f"{prev}->s2:{_STEP_COUNTERS['fork_step_2']}"


@DBOS.step()
async def _fork_step_3(prev: str) -> str:
    _STEP_COUNTERS["fork_step_3"] += 1
    return f"{prev}->s3:{_STEP_COUNTERS['fork_step_3']}"


@DBOS.workflow()
async def spike_three_step_forkable_workflow(tag: str) -> tuple[str, str, str]:
    """Criterion 2: 3-step workflow used to test `DBOS.fork_workflow_async(wf_id, start_step=2)`."""
    out1 = await _fork_step_1(tag)
    out2 = await _fork_step_2(out1)
    out3 = await _fork_step_3(out2)
    return (out1, out2, out3)


@DBOS.step()
async def _record_scheduled_tick_step(scheduled_iso: str, context_tag: str) -> None:
    _SCHEDULE_INVOCATIONS.append((scheduled_iso, context_tag))


@DBOS.workflow()
async def spike_scheduled_cron_workflow(scheduled_at: datetime, context: Any) -> None:
    """Criterion 3: Declarative cron workflow invoked by `DBOS.apply_schedules`."""
    await _record_scheduled_tick_step(scheduled_at.isoformat(), str(context))


@DBOS.step()
async def _idempotent_side_effect_step(dedup_key: str) -> str:
    _STEP_COUNTERS[f"idempotent:{dedup_key}"] += 1
    return f"executed:{dedup_key}:count={_STEP_COUNTERS[f'idempotent:{dedup_key}']}"


@DBOS.workflow()
async def spike_idempotent_trigger_workflow(dedup_key: str) -> str:
    """Criterion 4: Deduplicated workflow launched inside `with SetWorkflowID(...)`."""
    return await _idempotent_side_effect_step(dedup_key)


async def _insert_blackboard_snapshot_tx(
    snapshot_id: UUID,
    run_id: UUID,
    step_id: str,
    parent_snapshot_id: UUID | None,
    payload_json: str,
) -> str:
    uow = _require_uow()
    await uow.session.execute(
        sa.text(
            """
            INSERT INTO spike_blackboard_snapshots (
                snapshot_id, run_id, step_id, parent_snapshot_id, state_status, payload_jsonb
            ) VALUES (
                :snapshot_id, :run_id, :step_id, :parent_snapshot_id,
                'ACTIVE', CAST(:payload_json AS jsonb)
            )
            """
        ),
        {
            "snapshot_id": snapshot_id,
            "run_id": run_id,
            "step_id": step_id,
            "parent_snapshot_id": parent_snapshot_id,
            "payload_json": payload_json,
        },
    )
    return str(snapshot_id)


@DBOS.workflow()
async def spike_blackboard_snapshot_workflow(
    snapshot_id: UUID,
    run_id: UUID,
    step_id: str,
    parent_snapshot_id: UUID | None,
    payload_json: str,
) -> str:
    """Criteria 5 & 7: Writes an immutable snapshot via `DbosSqlAlchemyUnitOfWork`."""
    uow = _require_uow()
    return await uow.run_transaction(
        _insert_blackboard_snapshot_tx,
        snapshot_id,
        run_id,
        step_id,
        parent_snapshot_id,
        payload_json,
        name="insert_blackboard_snapshot_tx",
    )


@DBOS.step()
async def _dispatch_dramatiq_heavy_step(task_key: str) -> str:
    _spike_heavy_dramatiq_actor.send(task_key)
    worker = dramatiq.Worker(_SPIKE_STUB_BROKER, worker_threads=1)
    worker.start()
    try:
        _SPIKE_STUB_BROKER.join("orcia_heavy_io_spike", fail_fast=True, timeout=5000)
        worker.join()
    finally:
        worker.stop()
    return _DRAMATIQ_RESULTS[-1]


@DBOS.workflow()
async def spike_dramatiq_offload_workflow(task_key: str) -> str:
    """Criterion 6: Offloads heavy CPU/I/O work from a DBOS step to a Dramatiq actor."""
    return await _dispatch_dramatiq_heavy_step(task_key)


class DbosSpikeRuntime:
    """Lifecycle and verification harness for Story 3.2s on PostgreSQL 18."""

    def __init__(
        self,
        *,
        system_database_url: str,
        async_database_url: str,
        app_name: str = "orcia-dbos-spike",
        dbos_schema: str = "dbos",
    ) -> None:
        self.system_database_url = system_database_url
        self.async_database_url = async_database_url
        self.app_name = app_name
        self.dbos_schema = dbos_schema
        self.uow: DbosSqlAlchemyUnitOfWork | None = None

    def _build_config(self) -> DBOSConfig:
        return {
            "name": self.app_name,
            "system_database_url": self.system_database_url,
            "dbos_system_schema": self.dbos_schema,
            "run_migrations": True,
            "notification_listener_polling_interval_sec": 0.05,
            "notification_coalesce_sec": 0.005,
            "scheduler_polling_interval_sec": 0.1,
            "enable_otlp": False,
        }

    async def start(self) -> None:
        global _ACTIVE_UOW
        DBOS.destroy(destroy_registry=False)
        DBOS(config=self._build_config())
        self.uow = await DbosSqlAlchemyUnitOfWork.create(
            self.async_database_url,
            schema=self.dbos_schema,
            run_migrations=True,
        )
        _ACTIVE_UOW = self.uow
        DBOS.launch()
        await self._ensure_spike_tables()

    async def crash_and_relaunch(self) -> None:
        """Stop runtime (`SIGKILL`) and relaunch pending workflows via `DBOS.launch()`."""
        global _ACTIVE_UOW
        if self.uow is not None:
            await self.uow.close()
        DBOS.destroy(destroy_registry=False)
        DBOS(config=self._build_config())
        self.uow = await DbosSqlAlchemyUnitOfWork.create(
            self.async_database_url,
            schema=self.dbos_schema,
            run_migrations=True,
        )
        _ACTIVE_UOW = self.uow
        DBOS.launch()

    async def stop(self) -> None:
        global _ACTIVE_UOW
        if self.uow is not None:
            await self.uow.close()
            self.uow = None
        _ACTIVE_UOW = None
        DBOS.destroy(destroy_registry=False)

    async def _ensure_spike_tables(self) -> None:
        assert self.uow is not None

        async def _ddl_tx() -> None:
            session = _require_uow().session
            await session.execute(
                sa.text(
                    """
                    CREATE TABLE IF NOT EXISTS spike_blackboard_snapshots (
                        snapshot_id UUID PRIMARY KEY,
                        run_id UUID NOT NULL,
                        step_id VARCHAR(128) NOT NULL,
                        parent_snapshot_id UUID NULL,
                        state_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                        payload_jsonb JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            await session.execute(
                sa.text(
                    """
                    CREATE OR REPLACE FUNCTION forbid_spike_blackboard_mutation()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        RAISE EXCEPTION
                            'ERR_BLACKBOARD_APPEND_ONLY_VIOLATION: append-only table';
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                )
            )
            await session.execute(
                sa.text(
                    "DROP TRIGGER IF EXISTS trg_spike_blackboard_append_only "
                    "ON spike_blackboard_snapshots"
                )
            )
            await session.execute(
                sa.text(
                    """
                    CREATE TRIGGER trg_spike_blackboard_append_only
                    BEFORE UPDATE OR DELETE ON spike_blackboard_snapshots
                    FOR EACH ROW EXECUTE FUNCTION forbid_spike_blackboard_mutation()
                    """
                )
            )

        await self.uow.run_transaction(_ddl_tx, name="ensure_spike_tables")

    async def verify_pause_and_crash_recovery(self, run_key: str, decision: str) -> str:
        """Criterion 1: Start workflow, verify PENDING on `recv_async`, crash, then `send_async`."""
        wf_id = f"wf-pause-{run_key}-{new_uuid7()}"
        with SetWorkflowID(wf_id):
            handle = await DBOS.start_workflow_async(
                spike_arbitration_pause_workflow, run_key, 30.0
            )
        await asyncio.sleep(0.15)
        status_before = await handle.get_status()
        assert status_before.status == "PENDING"

        await self.crash_and_relaunch()
        recovered_handle: WorkflowHandleAsync[str] = await DBOS.retrieve_workflow_async(wf_id)
        await DBOS.send_async(destination_id=wf_id, message=decision, topic=ARBITRATION_TOPIC)
        result: str = await recovered_handle.get_result()
        return result

    async def verify_fork_workflow_from_step(self, tag: str) -> ForkSpikeResult:
        """Criterion 2: Run 3-step workflow, then fork from step 2 without re-running step 1."""
        _STEP_COUNTERS.pop("fork_step_1", None)
        _STEP_COUNTERS.pop("fork_step_2", None)
        _STEP_COUNTERS.pop("fork_step_3", None)

        orig_id = f"wf-fork-orig-{tag}-{new_uuid7()}"
        with SetWorkflowID(orig_id):
            orig_handle = await DBOS.start_workflow_async(spike_three_step_forkable_workflow, tag)
        orig_outputs = await orig_handle.get_result()

        fork_handle = await DBOS.fork_workflow_async(orig_id, start_step=2)
        fork_outputs = await fork_handle.get_result()
        return ForkSpikeResult(
            original_workflow_id=orig_id,
            forked_workflow_id=fork_handle.workflow_id,
            original_outputs=orig_outputs,
            forked_outputs=fork_outputs,
            step_execution_counts={
                "fork_step_1": _STEP_COUNTERS["fork_step_1"],
                "fork_step_2": _STEP_COUNTERS["fork_step_2"],
                "fork_step_3": _STEP_COUNTERS["fork_step_3"],
            },
        )

    async def verify_declarative_schedule(self, schedule_name: str, context_tag: str) -> str:
        """Criterion 3: Apply declarative cron schedule and trigger an execution."""
        _SCHEDULE_INVOCATIONS.clear()
        schedule_input: ScheduleInput = {
            "schedule_name": schedule_name,
            "workflow_fn": spike_scheduled_cron_workflow,
            "schedule": "*/5 * * * * *",
            "context": context_tag,
        }
        DBOS.apply_schedules([schedule_input])
        schedules = DBOS.list_schedules(schedule_name_prefix=schedule_name)
        assert len(schedules) == 1
        assert schedules[0]["schedule_name"] == schedule_name

        handle = DBOS.trigger_schedule(schedule_name)
        await asyncio.to_thread(handle.get_result)
        assert len(_SCHEDULE_INVOCATIONS) >= 1
        scheduled_iso, recorded_tag = _SCHEDULE_INVOCATIONS[-1]
        return f"tick:{recorded_tag}:{scheduled_iso}"

    async def verify_idempotency_set_workflow_id(
        self,
        trigger_id: str,
        idempotency_key: str,
        concurrency: int = 5,
    ) -> tuple[list[str], int]:
        """Criterion 4: Concurrent launches with identical `SetWorkflowID` run once."""
        dedup_key = f"{trigger_id}:{idempotency_key}"
        _STEP_COUNTERS.pop(f"idempotent:{dedup_key}", None)

        async def _launch_once() -> str:
            with SetWorkflowID(dedup_key):
                handle = await DBOS.start_workflow_async(
                    spike_idempotent_trigger_workflow,
                    dedup_key,
                )
            return await handle.get_result()

        results = await asyncio.gather(*(_launch_once() for _ in range(concurrency)))
        return list(results), _STEP_COUNTERS[f"idempotent:{dedup_key}"]

    async def verify_append_only_blackboard_and_uow(self) -> BlackboardSpikeResult:
        """Criteria 5 & 7: Append-only Blackboard trigger & UoW atomic commit/rollback."""
        assert self.uow is not None
        run_id = new_uuid7()
        snap_1 = new_uuid7()
        snap_2 = new_uuid7()

        await spike_blackboard_snapshot_workflow(
            snap_1,
            run_id,
            "step_analyze",
            None,
            '{"version": 1, "branch": "main"}',
        )

        trigger_blocked = False

        async def _illegal_update_tx() -> None:
            await _require_uow().session.execute(
                sa.text(
                    "UPDATE spike_blackboard_snapshots SET state_status = 'SUPERSEDED' "
                    "WHERE snapshot_id = :snapshot_id"
                ),
                {"snapshot_id": snap_1},
            )

        try:
            await self.uow.run_transaction(_illegal_update_tx, name="illegal_update_tx")
        except Exception as exc:
            if "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION" in str(exc):
                trigger_blocked = True
            else:
                raise

        await spike_blackboard_snapshot_workflow(
            snap_2,
            run_id,
            "step_analyze_forked",
            snap_1,
            '{"version": 2, "branch": "fork-1"}',
        )

        async def _count_snapshots_tx() -> int:
            res = await _require_uow().session.execute(
                sa.text("SELECT COUNT(*) FROM spike_blackboard_snapshots WHERE run_id = :run_id"),
                {"run_id": run_id},
            )
            return int(res.scalar_one())

        total = await self.uow.run_transaction(_count_snapshots_tx, name="count_snapshots_tx")
        return BlackboardSpikeResult(
            initial_snapshot_id=snap_1,
            forked_snapshot_id=snap_2,
            total_snapshots=total,
            append_only_trigger_blocked_update=trigger_blocked,
        )

    async def verify_dramatiq_cohabitation(self, task_key: str) -> str:
        """Criterion 6: Execute Dramatiq actor from inside a DBOS workflow step."""
        return await spike_dramatiq_offload_workflow(task_key)
