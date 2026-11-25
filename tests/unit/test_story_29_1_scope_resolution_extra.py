"""Extra Story 29.1 unit tests: supervision engine paths & SQL query mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration._internal.sql_autonomous_supervision import (
    list_autonomous_runs_for_workspaces_sql,
    list_autonomous_runs_sql,
)
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]], scalar: Any) -> None:
        self._rows = rows
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class _FakeConnection:
    def __init__(self, engine: _FakeAsyncEngine) -> None:
        self._engine = engine

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        self._engine.executed.append((str(stmt), dict(params or {})))
        if self._engine.raise_on_execute is not None:
            raise self._engine.raise_on_execute
        return _FakeResult(self._engine.rows, self._engine.scalar)


class _FakeCtx:
    def __init__(self, conn: _FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConnection:
        return self._conn

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class _FakeAsyncEngine:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        scalar: Any = None,
        raise_on_execute: Exception | None = None,
    ) -> None:
        self.rows = rows or []
        self.scalar = scalar
        self.raise_on_execute = raise_on_execute
        self.executed: list[tuple[str, dict[str, Any]]] = []

    def connect(self) -> _FakeCtx:
        return _FakeCtx(_FakeConnection(self))

    def begin(self) -> _FakeCtx:
        return _FakeCtx(_FakeConnection(self))


def _sample_row(*, run_id: str, workspace_id: str, trigger_id: str | None = None) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "run_key": "run-key-1",
        "workspace_id": workspace_id,
        "workflow_def_id": new_uuid7_str(),
        "workflow_uri": "orcia://workflows/weekly-digest",
        "trigger_id": trigger_id,
        "trigger_label": "nightly-cron",
        "trigger_type": "CRON_AUTONOMOUS",
        "trigger_status": "ACTIVE",
        "run_status": "COMMITTED_AUTONOMOUS",
        "post_hoc_status": "PENDING_AUDIT",
        "contract_id": new_uuid7_str(),
        "cost_usd": Decimal("0.125000"),
        "help_resource_id": "help-article-1",
        "previous_version_available": True,
        "created_at": datetime(2026, 11, 25, 0, 0, 0, tzinfo=UTC),
    }


def test_autonomous_supervision_service_post_hoc_property() -> None:
    default_svc = AutonomousSupervisionService()
    assert isinstance(default_svc.post_hoc_service, PostHocAuditService)

    custom_post_hoc = PostHocAuditService()
    injected_svc = AutonomousSupervisionService(post_hoc_service=custom_post_hoc)
    assert injected_svc.post_hoc_service is custom_post_hoc


@pytest.mark.asyncio
async def test_autonomous_supervision_service_with_fake_async_engine() -> None:
    ws_a = new_uuid7_str()
    ws_b = new_uuid7_str()
    run_id = new_uuid7_str()
    trig_id = new_uuid7_str()
    sample = _sample_row(run_id=run_id, workspace_id=ws_a, trigger_id=trig_id)
    fake_engine = _FakeAsyncEngine(rows=[sample], scalar="KILL_SWITCH_STOPPED")
    svc = AutonomousSupervisionService(
        engine=cast(AsyncEngine, fake_engine),
        post_hoc_service=PostHocAuditService(),
    )

    assert await svc.is_run_stopped(run_id) is True
    fake_engine.scalar = "RUNNING"
    assert await svc.is_run_stopped(run_id) is False

    registered = await svc.register_autonomous_run(
        run_id=run_id,
        workspace_id=ws_a,
        workflow_id="orcia://workflows/weekly-digest",
        contract_id=new_uuid7_str(),
        status="RUNNING",
    )
    assert registered.run_id == run_id
    assert any("UPDATE workflow_runs" in sql for sql, _ in fake_engine.executed)

    single_ws_items = await svc.list_autonomous_runs(workspace_id=ws_a)
    assert len(single_ws_items) == 1
    assert single_ws_items[0].run_id == run_id
    assert single_ws_items[0].workflow_title == "weekly-digest"
    assert single_ws_items[0].trigger_id == trig_id
    assert single_ws_items[0].cost_usd == pytest.approx(0.125)
    assert single_ws_items[0].help_resource_id == "help-article-1"
    assert single_ws_items[0].previous_version_available is True
    assert single_ws_items[0].created_at_iso == "2026-11-25T00:00:00Z"

    assert await svc.list_autonomous_runs_for_workspaces(workspace_ids=()) == []

    multi_ws_items = await svc.list_autonomous_runs_for_workspaces(workspace_ids=(ws_a, ws_b))
    assert len(multi_ws_items) == 1
    assert multi_ws_items[0].workspace_id == ws_a


@pytest.mark.asyncio
async def test_sql_autonomous_supervision_list_queries_with_fake_engine() -> None:
    ws_a = new_uuid7_str()
    ws_b = new_uuid7_str()
    run_id = new_uuid7_str()
    sample = _sample_row(run_id=run_id, workspace_id=ws_a)
    fake_engine = _FakeAsyncEngine(rows=[sample])

    assert (
        await list_autonomous_runs_for_workspaces_sql(
            cast(AsyncEngine, fake_engine), workspace_ids=()
        )
        == []
    )
    assert (
        await list_autonomous_runs_for_workspaces_sql(
            cast(AsyncEngine, fake_engine), workspace_ids=("not-a-uuid",)
        )
        == []
    )
    assert fake_engine.executed == []

    multi_rows = await list_autonomous_runs_for_workspaces_sql(
        cast(AsyncEngine, fake_engine), workspace_ids=(ws_a, ws_b), limit=500
    )
    assert len(multi_rows) == 1
    assert multi_rows[0]["run_id"] == run_id
    assert multi_rows[0]["created_at_iso"] == "2026-11-25T00:00:00Z"
    assert fake_engine.executed[-1][1]["lim"] == 200

    single_rows = await list_autonomous_runs_sql(
        cast(AsyncEngine, fake_engine), workspace_id=ws_a, limit=10
    )
    assert len(single_rows) == 1
    assert fake_engine.executed[-1][1]["lim"] == 10

    missing_table_engine = _FakeAsyncEngine(
        raise_on_execute=RuntimeError('relation "workflow_runs" does not exist')
    )
    assert (
        await list_autonomous_runs_for_workspaces_sql(
            cast(AsyncEngine, missing_table_engine), workspace_ids=(ws_a,)
        )
        == []
    )

    unexpected_err_engine = _FakeAsyncEngine(raise_on_execute=RuntimeError("connection refused"))
    with pytest.raises(RuntimeError, match="connection refused"):
        await list_autonomous_runs_for_workspaces_sql(
            cast(AsyncEngine, unexpected_err_engine), workspace_ids=(ws_a,)
        )
