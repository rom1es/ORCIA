"""Story 26.8 — High-signal branch tests for DBOS launch helpers, wiring, and SQL hydration."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from orcia_core.blackboard.models import BlackboardSnapshotEntity, StepExecutionEntity
from orcia_core.orchestration._internal import _dbos_workflow_defs as defs
from orcia_core.orchestration._internal._sql_dbos_launch_helpers import (
    append_rewind_supersede_tombstone_sql,
    enqueue_outbox_event_sql,
    ensure_step_waiting_anchor_sql,
    get_run_execution_context_sql,
    has_human_anchor_signature_sql,
)
from orcia_core.orchestration._internal.dbos_engine import DbosDurableWorkflowEngine
from orcia_core.orchestration.assistant_process_launcher import (
    AssistantProcessLauncherService,
    DurableProcessBackendPort,
    DurableProcessExecutionSnapshot,
)
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_kernel.events import RunTerminated

_WS_ID = "0192c4e0-0000-7000-8000-000000000201"


class _FakeResult:
    def __init__(self, row: tuple[Any, ...] | None = None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class _FakeSession:
    def __init__(self, rows: list[tuple[Any, ...] | None] | None = None) -> None:
        self._rows = list(rows or [])
        self.executed: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        self.executed.append((str(stmt), dict(params or {})))
        row = self._rows.pop(0) if self._rows else None
        return _FakeResult(row)


class _FakeUow:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    @asynccontextmanager
    async def session_scope(self) -> Any:
        yield self._session


class _FakeDurableBackend(DurableProcessBackendPort):
    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.launched = False
        self.resumed = False

    def is_available(self) -> bool:
        return self._available

    async def launch_durable_run_async(
        self, *, run: Any, workflow: Any, seed_inputs: dict[str, Any], trace_id: str
    ) -> DurableProcessExecutionSnapshot:
        self.launched = True
        return DurableProcessExecutionSnapshot(
            workflow_id=f"assistant-process:{run.id}",
            run_status="WAITING_FOR_HUMAN_ARBITRATION",
            waiting_step_keys=("frame-architecture-intent",),
            executed_step_keys=(),
            snapshot_count=0,
        )

    async def resume_after_anchor_async(
        self,
        *,
        run: Any,
        workflow: Any,
        step_key: str,
        signature_id: str = "signed",
        trace_id: str = "0" * 32,
    ) -> DurableProcessExecutionSnapshot | None:
        self.resumed = True
        return DurableProcessExecutionSnapshot(
            workflow_id=f"assistant-process:{run.id}",
            run_status="COMPLETED",
            waiting_step_keys=(),
            executed_step_keys=(step_key,),
            snapshot_count=1,
        )


def _dummy_request(app: FastAPI | None = None) -> Request:
    scope = {"type": "http", "path": "/api/v1/test", "app": app or FastAPI(), "headers": []}
    return Request(scope)


def test_launcher_resolution_fallbacks_and_durable_backend_port() -> None:
    """Cover slug match, default URI removal fallback, empty registry 404, and backend port."""
    auth = build_default_auth_and_org_service()
    marc = auth.resolve_user(persona_key="marc")
    setup_svc = build_default_orchestration_setup_service()
    engine = DurableOrchestrationEngine(setup_service=setup_svc)
    backend = _FakeDurableBackend(available=True)
    launcher = AssistantProcessLauncherService(
        setup_service=setup_svc, engine=engine, durable_backend=backend
    )

    slug_wf = launcher.resolve_workflow_definition("orcia://alias/claims-engineering-delivery")
    assert slug_wf.uri == "orcia://workflows/claims-engineering-delivery"

    outcome = asyncio.run(
        launcher.launch_process_async(
            marc, workspace_id=_WS_ID, workflow_uri=None, idempotency_token="b-1"
        )
    )
    assert backend.launched is True
    assert outcome.dbos_workflow_id == f"assistant-process:{outcome.run.id}"

    resumed = asyncio.run(
        launcher.resume_after_anchor_signature_async(
            marc, run_id=outcome.run.id, step_key="frame-architecture-intent"
        )
    )
    assert backend.resumed is True
    assert resumed is not None and resumed.run_status == "COMPLETED"

    # Remove PILOT_DEFAULT_WORKFLOW_URI to cover non-default fallback and empty error
    saved = dict(setup_svc._workflows_by_uri)
    setup_svc._workflows_by_uri.pop("orcia://workflows/claims-engineering-delivery", None)
    assert launcher.resolve_workflow_definition("").uri in saved

    setup_svc._workflows_by_uri.clear()
    with pytest.raises(ResourceNotFoundError):
        launcher.resolve_workflow_definition("")


def test_dbos_launch_helpers_and_engine_unlaunched_and_mocked_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover SQL launch helpers, rewind tombstone, unlaunched guards, and waiter signaling."""
    sess = _FakeSession(
        rows=[
            (_WS_ID, "orcia://workflows/custom", "BACKGROUND_FAST_PATH"),
            None,
            (1,),
            None,
        ]
    )
    uow = _FakeUow(sess)
    assert asyncio.run(get_run_execution_context_sql(uow, "run-1")) == (  # type: ignore[arg-type]
        _WS_ID,
        "orcia://workflows/custom",
        "BACKGROUND_FAST_PATH",
    )
    assert asyncio.run(get_run_execution_context_sql(uow, "run-missing"))[0] == _WS_ID  # type: ignore[arg-type]
    assert asyncio.run(has_human_anchor_signature_sql(uow, run_id="r", step_key="s")) is True  # type: ignore[arg-type]
    assert asyncio.run(has_human_anchor_signature_sql(uow, run_id="r", step_key="s")) is False  # type: ignore[arg-type]
    asyncio.run(ensure_step_waiting_anchor_sql(uow, run_id="r", step_key="s"))  # type: ignore[arg-type]
    evt = RunTerminated.create(run_id="r", workspace_id=_WS_ID, final_status="COMPLETED")
    asyncio.run(enqueue_outbox_event_sql(uow, evt))  # type: ignore[arg-type]

    # Waiter thread signaling & unbound runtime guard
    defs.clear_run_state_waiter("missing")
    defs.signal_run_state_reached("missing")

    async def _run_waiter_flow() -> None:
        ev = defs.register_run_state_waiter("run-w")
        await asyncio.to_thread(defs.signal_run_state_reached, "run-w")
        await asyncio.wait_for(ev.wait(), timeout=2.0)
        ev2 = defs.register_run_state_waiter("run-w2")
        defs.signal_run_state_reached("run-w2")
        assert ev2.is_set()
        defs.clear_run_state_waiter("run-w")
        defs.clear_run_state_waiter("run-w2")

    asyncio.run(_run_waiter_flow())

    saved_bindings = list(defs._RUNTIME_BINDINGS)
    defs._RUNTIME_BINDINGS.clear()
    try:
        assert defs.has_active_dbos_runtime_bindings() is False
        with pytest.raises(RuntimeError):
            defs._require_bound_runtime()
        eng = DbosDurableWorkflowEngine(
            system_database_url="postgresql://x", application_database_url="postgresql+asyncpg://x"
        )
        with pytest.raises(RuntimeError):
            _ = eng.uow
        with pytest.raises(RuntimeError):
            _ = eng.repository
        eng._launched = True
        asyncio.run(eng.launch())
        eng._launched = False

        # Rewind tombstone with ACTIVE snapshots & persist_step with explicit payload
        snap = BlackboardSnapshotEntity(
            id="0192c4e0-0000-7000-8000-000000000901",
            snapshot_key="sk-1",
            run_id="r1",
            step_execution_id="se-1",
            parent_snapshot_id=None,
            step_key="s1",
            branch_status="ACTIVE",
            artifact_payload={"ok": True},
            artifact_cas_key="cas/sha256/0/s1.json",
            artifact_sha256="0" * 64,
        )
        step = StepExecutionEntity(
            id="se-1",
            step_execution_key="sek-1",
            run_id="r1",
            step_key="s1",
            step_index=0,
            step_type="AGENT",
            execution_mode="INTERACTIVE_COACHING",
            status="PENDING",
        )
        appended: list[Any] = []

        class _FakeRepo:
            async def list_snapshots(self, rid: str) -> tuple[BlackboardSnapshotEntity, ...]:
                return (snap,)

            async def list_step_executions(self, rid: str) -> tuple[StepExecutionEntity, ...]:
                return (step,)

            async def append_snapshot(self, **kw: Any) -> BlackboardSnapshotEntity:
                appended.append(kw)
                return snap

            async def get_run_status(self, rid: str) -> str:
                return "KILL_SWITCH_STOPPED"

            async def upsert_step_execution(self, s: Any) -> None:
                appended.append(s)

        asyncio.run(
            append_rewind_supersede_tombstone_sql(
                _FakeRepo(),
                run_id="r1",
                target_step_key="s1",  # type: ignore[arg-type]
            )
        )
        assert appended and appended[0]["branch_status"] == "SUPERSEDED"

        eng._uow = uow  # type: ignore[assignment]
        eng._repository = _FakeRepo()  # type: ignore[assignment]
        res = asyncio.run(
            eng.persist_step_and_commit_snapshot(
                run_id="r1",
                step_key="s1",
                step_index=0,
                artifact_payload={"custom": 1},
                emit_outbox=True,
            )
        )
        assert res.id == snap.id

        defs._RUNTIME_BINDINGS.append(eng)
        with pytest.raises(RuntimeError, match="KILL_SWITCH_STOPPED"):
            asyncio.run(defs._execute_durable_step.__wrapped__("r1", "s1", 0, None))
    finally:
        defs._RUNTIME_BINDINGS.clear()
        defs._RUNTIME_BINDINGS.extend(saved_bindings)
