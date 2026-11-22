"""Story 26.8 — Unit branch coverage for DBOS engine lifecycle & workflow defs."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from orcia_core.blackboard.models import BlackboardSnapshotEntity, StepExecutionEntity
from orcia_core.orchestration._internal import _dbos_workflow_defs as defs
from orcia_core.orchestration._internal import dbos_engine as de

_WS_ID = "0192c4e0-0000-7000-8000-000000000201"


class _DummySession:
    async def execute(self, stmt: Any, params: Any = None) -> Any:
        return SimpleNamespace(fetchone=lambda: (_WS_ID, "orcia://wf/1", "INTERACTIVE_COACHING"))


class _DummyUow:
    @asynccontextmanager
    async def session_scope(self) -> Any:
        yield _DummySession()

    async def close(self) -> None:
        return None


class _DummyRepo:
    def __init__(self) -> None:
        self.run_status = "RUNNING"
        self.snap = BlackboardSnapshotEntity(
            id="sn-1",
            snapshot_key="sk-1",
            run_id="r-1",
            step_execution_id="se-1",
            parent_snapshot_id=None,
            step_key="s1",
            branch_status="ACTIVE",
            artifact_payload={"ok": True},
            artifact_cas_key="cas/1",
            artifact_sha256="0" * 64,
        )

    async def update_run_status(self, rid: str, status: str) -> None:
        self.run_status = status

    async def get_run_status(self, rid: str) -> str:
        return self.run_status

    async def list_step_executions(self, rid: str) -> tuple[StepExecutionEntity, ...]:
        return (
            StepExecutionEntity(
                id="se-1",
                step_execution_key="sek-1",
                run_id=rid,
                step_key="s1",
                step_index=0,
                step_type="AGENT",
                execution_mode="INTERACTIVE_COACHING",
                status="PENDING",
            ),
        )

    async def list_snapshots(self, rid: str) -> tuple[BlackboardSnapshotEntity, ...]:
        return (self.snap,)

    async def append_snapshot(self, **kw: Any) -> BlackboardSnapshotEntity:
        return self.snap

    async def upsert_step_execution(self, s: Any) -> None:
        return None


def test_dbos_engine_launch_shutdown_and_dispatch_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover `launch`, `shutdown` (_SharedExecutor cleanup), `start_durable_run`, and `rewind`."""
    calls: list[str] = []

    class _FakeDbos:
        workflow_id = "wf-mock"

        def __init__(self, config: Any = None) -> None:
            calls.append("init")

        @staticmethod
        def destroy(**kw: Any) -> None:
            calls.append("destroy")

        @staticmethod
        def launch() -> None:
            calls.append("launch")

        @staticmethod
        async def start_workflow_async(*args: Any, **kwargs: Any) -> str:
            return "handle"

        @staticmethod
        async def send_async(*args: Any, **kwargs: Any) -> None:
            calls.append("send")

        @staticmethod
        async def get_workflow_status_async(wf_id: str) -> Any:
            return SimpleNamespace(status="PENDING")

        @staticmethod
        async def fork_workflow_async(wf_id: str, start_step: int) -> str:
            return "forked"

        @staticmethod
        async def recv_async(**kw: Any) -> Any:
            return {"ok": True}

    @contextmanager
    def _fake_set_wf_id(wf_id: str) -> Any:
        calls.append(f"id:{wf_id}")
        yield

    monkeypatch.setattr(de, "DBOS", _FakeDbos)
    monkeypatch.setattr(de, "SetWorkflowID", _fake_set_wf_id)
    monkeypatch.setattr(defs, "DBOS", _FakeDbos)

    async def _fake_uow_create(*args: Any, **kwargs: Any) -> _DummyUow:
        return _DummyUow()

    monkeypatch.setattr(de.DbosSqlAlchemyUnitOfWork, "create", _fake_uow_create)
    monkeypatch.setattr(de, "SqlOrchestrationRepository", lambda uow: _DummyRepo())

    eng = de.DbosDurableWorkflowEngine(
        system_database_url="postgresql://x", application_database_url="postgresql+asyncpg://x"
    )

    async def _exercise_engine() -> None:
        await eng.launch()
        assert eng.uow is not None and eng.repository is not None
        assert (
            await eng.start_durable_run(
                trigger_id="t", idempotency_key="k", run_id="r-1", steps=("s1",)
            )
            == "handle"
        )
        await eng.send_human_arbitration(workflow_id="wf", decision="GO")
        await eng.send_human_anchor_signed(workflow_id="wf", step_key="s1", signature_id="sig")
        assert await eng.get_workflow_status_name("wf") == "PENDING"
        assert (
            await eng.rewind_and_fork_from_step(
                workflow_id="wf", run_id="r-1", target_step_key="s1", start_step=0
            )
            == "forked"
        )
        loop = asyncio.get_running_loop()

        class _SharedExecutor:
            pass

        loop._default_executor = _SharedExecutor()  # type: ignore[attr-defined]
        await eng.shutdown(dispose_engine=True)
        assert getattr(loop, "_default_executor", None) is None

    asyncio.run(_exercise_engine())


def test_dbos_workflow_defs_step_and_workflow_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover `_prepare_human_anchor_wait_step`, `_verify_human_anchor_signed_step`, & workflow."""
    repo = _DummyRepo()
    eng = SimpleNamespace(uow=_DummyUow(), repository=repo)
    saved = list(defs._RUNTIME_BINDINGS)
    defs._RUNTIME_BINDINGS.clear()
    defs._RUNTIME_BINDINGS.append(eng)  # type: ignore[arg-type]

    class _FakeDbosWf:
        workflow_id = "wf-unit"
        recv_values: list[Any] = [None, {"signed": True}, "APPROVED"]

        @staticmethod
        async def recv_async(**kw: Any) -> Any:
            return _FakeDbosWf.recv_values.pop(0) if _FakeDbosWf.recv_values else "OK"

    monkeypatch.setattr(defs, "DBOS", _FakeDbosWf)
    monkeypatch.setattr(
        defs,
        "get_run_execution_context_sql",
        lambda u, r: asyncio.sleep(0, result=(_WS_ID, "u", "INTERACTIVE_COACHING")),
    )
    monkeypatch.setattr(defs, "enqueue_outbox_event_sql", lambda u, e: asyncio.sleep(0))
    monkeypatch.setattr(defs, "ensure_step_waiting_anchor_sql", lambda u, **kw: asyncio.sleep(0))

    signed_flag = {"val": False}
    monkeypatch.setattr(
        defs,
        "has_human_anchor_signature_sql",
        lambda u, **kw: asyncio.sleep(0, result=signed_flag["val"]),
    )

    try:
        # Step helpers: unsigned then signed
        assert (
            asyncio.run(
                defs._prepare_human_anchor_wait_step.__wrapped__("r-1", "s1", True, "0" * 32)
            )
            is True
        )
        assert asyncio.run(defs._verify_human_anchor_signed_step.__wrapped__("r-1", "s1")) is False
        signed_flag["val"] = True
        assert (
            asyncio.run(
                defs._prepare_human_anchor_wait_step.__wrapped__("r-1", "s1", True, "0" * 32)
            )
            is False
        )
        assert asyncio.run(defs._verify_human_anchor_signed_step.__wrapped__("r-1", "s1")) is True

        # Execute step normal path (non-killed)
        async def _fake_persist(**kw: Any) -> Any:
            return repo.snap

        eng.persist_step_and_commit_snapshot = _fake_persist
        assert asyncio.run(defs._execute_durable_step.__wrapped__("r-1", "s1", 0, None)) == "sn-1"

        # Workflow timeout when raw_anchor is None
        monkeypatch.setattr(
            defs, "_prepare_human_anchor_wait_step", lambda *a: asyncio.sleep(0, result=True)
        )
        monkeypatch.setattr(
            defs, "_verify_human_anchor_signed_step", lambda *a: asyncio.sleep(0, result=True)
        )
        monkeypatch.setattr(
            defs, "_execute_durable_step", lambda *a, **kw: asyncio.sleep(0, result="sn-1")
        )
        wf_fn = defs._orcia_durable_run_workflow
        while hasattr(wf_fn, "__wrapped__"):
            wf_fn = wf_fn.__wrapped__
        res_wait = asyncio.run(
            wf_fn("r-1", ("s0", "s1"), anchored_step_keys=("s1",), skip_step_keys=("s0",))
        )
        assert res_wait.final_status == "WAITING_FOR_HUMAN_ARBITRATION"

        # Workflow full completion with arbitration + RunTerminated outbox
        res_done = asyncio.run(
            wf_fn(
                "r-1",
                ("s1", "s2"),
                pause_for_arbitration_after_step="s1",
                anchored_step_keys=("s1",),
                emit_outbox_events=True,
            )
        )
        assert res_done.final_status == "COMPLETED"
        assert res_done.arbitration_decision == "APPROVED"

        # Kill switch early exit
        repo.run_status = "KILL_SWITCH_STOPPED"
        res_kill = asyncio.run(wf_fn("r-1", ("s1",)))
        assert res_kill.final_status == "KILL_SWITCH_STOPPED"
    finally:
        defs._RUNTIME_BINDINGS.clear()
        defs._RUNTIME_BINDINGS.extend(saved)


def test_in_process_launcher_committed_and_pending_transitions() -> None:
    """Cover COMMITTED skip & PENDING->WAITING_FOR_HUMAN_ANCHOR transition in launcher."""
    from dataclasses import replace

    from orcia_core.orchestration.assistant_process_launcher import AssistantProcessLauncherService
    from orcia_core.orchestration.engine import DurableOrchestrationEngine
    from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
    from orcia_core.permissions import build_default_auth_and_org_service

    marc = build_default_auth_and_org_service().resolve_user(persona_key="marc")
    setup2 = build_default_orchestration_setup_service()
    leaf_wf = setup2._workflows_by_uri["orcia://workflows/sub-verify-regression-suite"]
    run2 = setup2.instantiate_workflow_run(marc, workflow_uri=leaf_wf.uri, workspace_id=_WS_ID)
    eng2 = DurableOrchestrationEngine(setup_service=setup2)
    s2 = eng2.initialize_run_steps(run2, leaf_wf, initialize_anchored_as_waiting=False)
    c0 = replace(s2[0], status="COMMITTED")
    eng2.blackboard.register_step_execution(c0)
    launcher2 = AssistantProcessLauncherService(setup_service=setup2, engine=eng2)
    args2 = {"user": marc, "run": run2, "wf": leaf_wf, "steps": (c0,), "instance": None}
    exec_k, wait_k, st = asyncio.run(launcher2._execute_in_process_until_wait_async(**args2))  # type: ignore[arg-type]
    assert exec_k == (s2[0].step_key,) and wait_k == () and st == "COMPLETED"

    wf2 = setup2._workflows_by_uri["orcia://workflows/claims-engineering-delivery"]
    run3 = setup2.instantiate_workflow_run(marc, workflow_uri=wf2.uri, workspace_id=_WS_ID)
    s3 = eng2.initialize_run_steps(run3, wf2, initialize_anchored_as_waiting=False)
    args3 = {"user": marc, "run": run3, "wf": wf2, "steps": s3, "instance": None}
    _, wait3, st3 = asyncio.run(launcher2._execute_in_process_until_wait_async(**args3))  # type: ignore[arg-type]
    assert wait3 == (s3[0].step_key,) and st3 == "WAITING_FOR_HUMAN_ARBITRATION"
