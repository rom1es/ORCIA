"""Story 26.8 — Branch coverage for API DBOS wiring timeouts and SQL hydration fallbacks."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from orcia_api.routers._assistant_process_wiring import (
    ApiDbosProcessBackendAdapter,
    resume_assistant_process_after_anchor,
)
from orcia_api.routers._orchestration_sql_hydration import (
    hydrate_orchestration_runs_from_sql,
    hydrate_run_from_sql_if_missing,
    read_sql_blackboard_if_available,
    read_sql_run_governance_if_available,
    resolve_optional_dbos_uow,
)
from orcia_core.blackboard.models import BlackboardSnapshotEntity, StepExecutionEntity
from orcia_core.orchestration.models import WorkflowRunEntity
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service

_WS_ID = "0192c4e0-0000-7000-8000-000000000201"


def _dummy_request(app: FastAPI | None = None) -> Request:
    scope = {"type": "http", "path": "/api/v1/test", "app": app or FastAPI(), "headers": []}
    return Request(scope)


def test_api_dbos_wiring_timeouts_and_sql_hydration_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover timeout/unlaunched branches in process wiring & SQL hydration fallbacks."""
    auth = build_default_auth_and_org_service()
    marc = auth.resolve_user(persona_key="marc")
    setup_svc = build_default_orchestration_setup_service()
    wf = setup_svc._workflows_by_uri["orcia://workflows/claims-engineering-delivery"]
    run = setup_svc.instantiate_workflow_run(
        marc, workflow_uri=wf.uri, workspace_id=_WS_ID, trigger_idempotency_key="other:1"
    )
    app = FastAPI()
    req = _dummy_request(app)
    res_none = asyncio.run(
        resume_assistant_process_after_anchor(
            req,
            user=marc,
            run=run,
            step_key="frame-architecture-intent",
            signature_id="sig",
            trace_id="0" * 32,
        )
    )
    assert res_none is None

    adapter = ApiDbosProcessBackendAdapter(
        request=req, setup_service=setup_svc, engine=setup_svc.engine
    )
    assert adapter.is_available() is False
    assert (
        asyncio.run(adapter.resume_after_anchor_async(run=run, workflow=wf, step_key="s")) is None
    )

    class _StubRepo:
        async def get_run_status(self, rid: str) -> str:
            return "WAITING_FOR_HUMAN_ARBITRATION"

        async def list_step_executions(self, rid: str) -> tuple[Any, ...]:
            return ()

        async def list_snapshots(self, rid: str) -> tuple[Any, ...]:
            return ()

    class _StubDbosEng:
        _launched = True
        repository = _StubRepo()

        async def start_durable_run(self, **kw: Any) -> None:
            return None

        async def get_workflow_status_name(self, wf_id: str) -> str | None:
            return "COMPLETED"

        async def send_human_anchor_signed(self, **kw: Any) -> None:
            return None

    app.state.dbos_durable_engine = _StubDbosEng()

    async def _fast_wait_for(awaitable: Any, timeout: float = 1.0) -> Any:
        close = getattr(awaitable, "close", None)
        if callable(close):
            close()
        raise TimeoutError

    monkeypatch.setattr(
        "orcia_api.routers._assistant_dbos_backend.asyncio.wait_for", _fast_wait_for
    )
    snap1 = asyncio.run(
        adapter.launch_durable_run_async(run=run, workflow=wf, seed_inputs={}, trace_id="0" * 32)
    )
    assert snap1.run_status == "WAITING_FOR_HUMAN_ARBITRATION"
    snap2 = asyncio.run(
        adapter.resume_after_anchor_async(
            run=run, workflow=wf, step_key="frame-architecture-intent"
        )
    )
    assert snap2 is not None

    # Hydration fallbacks (`dbos_datasource`, `db_engine`, broken SQL, stale run eviction)
    app_ds = FastAPI()
    app_ds.state.dbos_datasource = SimpleNamespace(engine=object(), session_factory=lambda: None)
    assert resolve_optional_dbos_uow(_dummy_request(app_ds)) is not None

    app_eng = FastAPI()
    app_eng.state.db_engine = SimpleNamespace()
    assert resolve_optional_dbos_uow(_dummy_request(app_eng)) is not None
    req_broken = _dummy_request(app_eng)

    async def _raise_sql(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("pg down")

    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_workflow_runs_with_locks_sql",
        _raise_sql,
    )
    asyncio.run(hydrate_orchestration_runs_from_sql(req_broken, setup_svc))
    asyncio.run(hydrate_run_from_sql_if_missing(req_broken, setup_svc, "missing-run-id"))

    setup_svc._idempotency_index[("t", "k")] = "stale-run-id"
    setup_svc._runs_by_id["stale-run-id"] = WorkflowRunEntity(
        id="stale-run-id",
        run_key="rk",
        workspace_id=_WS_ID,
        workflow_def_id="wd",
        workflow_uri=wf.uri,
        parent_run_id=None,
        parent_step_execution_id=None,
        root_run_id="stale-run-id",
        nesting_depth=0,
        execution_regime="INTERACTIVE_COACHING",
        criticality="STANDARD",
        trigger_id=None,
        trigger_idempotency_key=None,
        run_lock=run.run_lock,
        status="INITIALIZED",
        initiated_by_user_id=marc.id,
        execution_identity_mode="passthrough",
        budget_max_usd=1.0,
    )

    async def _empty_runs(*args: Any, **kwargs: Any) -> tuple[Any, ...]:
        return ()

    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_workflow_runs_with_locks_sql",
        _empty_runs,
    )
    asyncio.run(hydrate_orchestration_runs_from_sql(req_broken, setup_svc))
    assert "stale-run-id" not in setup_svc._runs_by_id
    assert ("t", "k") not in setup_svc._idempotency_index

    class _BadRepo:
        async def get_run_status(self, rid: str) -> str:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.resolve_optional_sql_orchestration_repo",
        lambda r: _BadRepo(),
    )
    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.resolve_optional_sql_outbox_repo",
        lambda r: object(),
    )
    assert asyncio.run(read_sql_blackboard_if_available(req_broken, "r")) == (None, (), ())

    # Cover ApiDbosProcessBackendAdapter PENDING branch & waiter signal + full SQL hydration
    class _PendingDbosEng(_StubDbosEng):
        async def get_workflow_status_name(self, wf_id: str) -> str | None:
            return "PENDING"

    class _FullRepo(_StubRepo):
        async def list_step_executions(self, rid: str) -> tuple[Any, ...]:
            return (
                StepExecutionEntity(
                    id="se-1",
                    step_execution_key="sek-1",
                    run_id=rid,
                    step_key="frame-architecture-intent",
                    step_index=0,
                    step_type="AGENT",
                    execution_mode="INTERACTIVE_COACHING",
                    status="WAITING_FOR_HUMAN_ANCHOR",
                ),
            )

        async def list_snapshots(self, rid: str) -> tuple[Any, ...]:
            return (
                BlackboardSnapshotEntity(
                    id="sn-1",
                    snapshot_key="sk-1",
                    run_id=rid,
                    step_execution_id="se-1",
                    parent_snapshot_id=None,
                    step_key="frame-architecture-intent",
                    branch_status="ACTIVE",
                    artifact_payload={"ok": True},
                    artifact_cas_key="cas/1",
                    artifact_sha256="0" * 64,
                ),
            )

    async def _fast_ok_wait(awaitable: Any, timeout: float = 1.0) -> Any:
        close = getattr(awaitable, "close", None)
        if callable(close):
            close()
        return True

    app_full = FastAPI()
    app_full.state.dbos_durable_engine = _PendingDbosEng()
    app_full.state.dbos_durable_engine.repository = _FullRepo()
    req_full = _dummy_request(app_full)
    monkeypatch.setattr(
        "orcia_api.routers._assistant_dbos_backend.sync_instantiated_run_to_sql", _empty_runs
    )
    monkeypatch.setattr("orcia_api.routers._assistant_dbos_backend.asyncio.wait_for", _fast_ok_wait)
    ad_full = ApiDbosProcessBackendAdapter(
        request=req_full, setup_service=setup_svc, engine=setup_svc.engine
    )
    assert asyncio.run(
        ad_full.launch_durable_run_async(run=run, workflow=wf, seed_inputs={}, trace_id="0" * 32)
    ).waiting_step_keys == ("frame-architecture-intent",)
    assert (
        asyncio.run(
            ad_full.resume_after_anchor_async(
                run=run, workflow=wf, step_key="frame-architecture-intent"
            )
        )
        is not None
    )

    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.resolve_optional_sql_orchestration_repo",
        lambda r: _FullRepo(),
    )
    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.resolve_optional_sql_outbox_repo",
        lambda r: SimpleNamespace(list_events_by_run=_empty_runs),
    )
    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_workflow_runs_with_locks_sql",
        lambda uow, run_id=None: asyncio.sleep(0, result=(run,)),
    )
    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_human_arbitrations_sql",
        lambda uow, run_id=None: asyncio.sleep(
            0, result=(SimpleNamespace(id="a1", run_id=run.id, status="PENDING"),)
        ),
    )
    sig_item = SimpleNamespace(id="h1", run_id=run.id, step_key="s1", section_key="sec")
    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_human_anchor_signatures_sql",
        lambda uow, run_id=None: asyncio.sleep(0, result=(sig_item,)),
    )
    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_upstream_challenges_sql",
        lambda uow, run_id=None: asyncio.sleep(
            0, result=(SimpleNamespace(id="c1", run_id=run.id),)
        ),
    )
    app_full.state.dbos_uow = object()
    assert (
        asyncio.run(read_sql_blackboard_if_available(req_full, run.id))[0]
        == "WAITING_FOR_HUMAN_ARBITRATION"
    )
    assert (
        len(asyncio.run(read_sql_run_governance_if_available(req_full, setup_svc, run.id))[1]) == 1
    )
    setup_svc._runs_by_id.pop(run.id, None)
    asyncio.run(hydrate_run_from_sql_if_missing(req_full, setup_svc, run.id))
    assert run.id in setup_svc._runs_by_id
    asyncio.run(read_sql_run_governance_if_available(_dummy_request(FastAPI()), setup_svc, run.id))
