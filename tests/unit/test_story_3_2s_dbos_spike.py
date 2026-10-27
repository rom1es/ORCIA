"""Unit and architectural tests for Story 3.2s (`ARCH-P2-SPIKE` — DBOS Transact Spike & UoW)."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orcia_core.orchestration._internal import dbos_spike
from orcia_core.orchestration._internal.dbos_spike import (
    BlackboardSpikeResult,
    DbosSpikeRuntime,
    ForkSpikeResult,
    _arbitration_finalize_step,
    _arbitration_prepare_step,
    _dispatch_dramatiq_heavy_step,
    _fork_step_1,
    _fork_step_2,
    _fork_step_3,
    _idempotent_side_effect_step,
    _insert_blackboard_snapshot_tx,
    _record_scheduled_tick_step,
    _require_uow,
    spike_arbitration_pause_workflow,
    spike_blackboard_snapshot_workflow,
    spike_dramatiq_offload_workflow,
    spike_idempotent_trigger_workflow,
    spike_scheduled_cron_workflow,
    spike_three_step_forkable_workflow,
)
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_kernel.ids import new_uuid7


async def test_dbos_sqlalchemy_unit_of_work_delegates_to_async_datasource() -> None:
    """Verify `DbosSqlAlchemyUnitOfWork` preserves explicit engine and delegates transactions."""
    fake_session = MagicMock()
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()

    fake_ds = MagicMock()
    fake_ds.engine = fake_engine
    fake_ds.sql_session.return_value = fake_session

    async def _run_tx_step_async(
        options: dict[str, Any],
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        assert options["isolation_level"] == "SERIALIZABLE"
        assert options["name"] == "custom_tx_step"
        return await func(*args, **kwargs)

    fake_ds.run_tx_step_async = AsyncMock(side_effect=_run_tx_step_async)

    with patch(
        "orcia_core.orchestration._internal.uow.AsyncSQLAlchemyDatasource.create",
        new=AsyncMock(return_value=fake_ds),
    ) as mock_create:
        uow = await DbosSqlAlchemyUnitOfWork.create(
            "postgresql+asyncpg://localhost:5432/orcia",  # pragma: allowlist secret
            engine=fake_engine,
            schema="dbos",
            run_migrations=True,
        )
        mock_create.assert_awaited_once()
        assert uow.datasource is fake_ds
        assert uow.engine is fake_engine
        assert uow.session is fake_session

        async def _sample_repo_op(val: int) -> int:
            return val * 2

        res = await uow.run_transaction(
            _sample_repo_op,
            21,
            name="custom_tx_step",
            isolation_level="SERIALIZABLE",
        )
        assert res == 42
        await uow.close()
        fake_engine.dispose.assert_awaited_once()


async def test_require_uow_raises_when_uninitialized() -> None:
    """Verify `_require_uow()` raises `RuntimeError` when no active UoW is registered."""
    prev = dbos_spike._ACTIVE_UOW
    dbos_spike._ACTIVE_UOW = None
    try:
        with pytest.raises(RuntimeError, match="Active DbosSqlAlchemyUnitOfWork"):
            _require_uow()
    finally:
        dbos_spike._ACTIVE_UOW = prev


async def test_spike_steps_and_dramatiq_cohabitation_unit() -> None:
    """Verify individual spike steps, counters, scheduled tick, and Dramatiq StubBroker actor."""
    p = await inspect.unwrap(_arbitration_prepare_step)("unit-1")
    assert p == "prepared:unit-1"
    f = await inspect.unwrap(_arbitration_finalize_step)(p, "APPROVE")
    assert f == "completed:prepared:unit-1:decision=APPROVE"

    s1 = await inspect.unwrap(_fork_step_1)("u")
    s2 = await inspect.unwrap(_fork_step_2)(s1)
    s3 = await inspect.unwrap(_fork_step_3)(s2)
    assert "->s2:" in s2 and "->s3:" in s3

    out_tuple = await inspect.unwrap(spike_three_step_forkable_workflow)("u2")
    assert len(out_tuple) == 3

    now = datetime.now(tz=UTC)
    await inspect.unwrap(_record_scheduled_tick_step)(now.isoformat(), "ctx-unit")
    await inspect.unwrap(spike_scheduled_cron_workflow)(now, "ctx-unit-2")

    dedup = await inspect.unwrap(_idempotent_side_effect_step)("k1")
    assert dedup.startswith("executed:k1:count=")
    wf_dedup = await inspect.unwrap(spike_idempotent_trigger_workflow)("k2")
    assert wf_dedup.startswith("executed:k2:count=")

    dramatiq_res = await inspect.unwrap(_dispatch_dramatiq_heavy_step)("unit-job-1")
    assert dramatiq_res == "dramatiq_processed:unit-job-1"
    wf_dramatiq = await inspect.unwrap(spike_dramatiq_offload_workflow)("unit-job-2")
    assert wf_dramatiq == "dramatiq_processed:unit-job-2"

    with patch.object(
        dbos_spike.DBOS,
        "recv_async",
        new=AsyncMock(return_value="UNIT_DECISION"),
    ):
        pause_out = await inspect.unwrap(spike_arbitration_pause_workflow)("unit-pause", 5.0)
        assert pause_out == "completed:prepared:unit-pause:decision=UNIT_DECISION"


async def test_spike_blackboard_snapshot_tx_and_runtime_methods() -> None:
    """Verify `_insert_blackboard_snapshot_tx` and `DbosSpikeRuntime` methods in isolation."""
    fake_uow = MagicMock()
    fake_uow.session.execute = AsyncMock()
    fake_uow.close = AsyncMock()

    async def _passthrough_tx(func: Any, *args: Any, **_kwargs: Any) -> Any:
        return await func(*args)

    fake_uow.run_transaction = AsyncMock(side_effect=_passthrough_tx)

    prev = dbos_spike._ACTIVE_UOW
    dbos_spike._ACTIVE_UOW = fake_uow
    try:
        snap_id = new_uuid7()
        run_id = new_uuid7()
        out_id = await inspect.unwrap(spike_blackboard_snapshot_workflow)(
            snap_id,
            run_id,
            "step_1",
            None,
            '{"ok": true}',
        )
        assert out_id == str(snap_id)
        fake_uow.session.execute.assert_awaited_once()

        direct_id = await _insert_blackboard_snapshot_tx(
            snap_id,
            run_id,
            "step_2",
            snap_id,
            '{"ok": true}',
        )
        assert direct_id == str(snap_id)
    finally:
        dbos_spike._ACTIVE_UOW = prev

    runtime = DbosSpikeRuntime(
        system_database_url="postgresql+psycopg://localhost:5432/orcia",  # pragma: allowlist secret
        async_database_url="postgresql+asyncpg://localhost:5432/orcia",  # pragma: allowlist secret
        app_name="unit-spike",
        dbos_schema="dbos_unit",
    )
    cfg = runtime._build_config()
    assert cfg["name"] == "unit-spike"
    assert cfg["dbos_system_schema"] == "dbos_unit"
    assert cfg["run_migrations"] is True

    with (
        patch.object(dbos_spike, "DBOS") as mock_dbos,
        patch.object(
            DbosSqlAlchemyUnitOfWork,
            "create",
            new=AsyncMock(return_value=fake_uow),
        ),
    ):
        await runtime.start()
        assert runtime.uow is fake_uow
        await runtime.simulate_crash_and_relaunch()
        mock_dbos._recover_pending_workflows.assert_called_once()
        await runtime.stop()
        assert runtime.uow is None

    fork_model = ForkSpikeResult(
        original_workflow_id="wf-1",
        forked_workflow_id="wf-2",
        original_outputs=("a", "b", "c"),
        forked_outputs=("a", "b2", "c2"),
        step_execution_counts={"fork_step_1": 1, "fork_step_2": 2, "fork_step_3": 2},
    )
    assert fork_model.step_execution_counts["fork_step_1"] == 1

    bb_model = BlackboardSpikeResult(
        initial_snapshot_id=new_uuid7(),
        forked_snapshot_id=new_uuid7(),
        total_snapshots=2,
        append_only_trigger_blocked_update=True,
    )
    assert bb_model.append_only_trigger_blocked_update is True
