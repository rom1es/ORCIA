"""DBOS Transact Durable Workflow Engine (`Story 3.2b`, `Story 3.2f`, `Story 26.8`).

Implements durable step execution (`@DBOS.step()`) dispatching real `StepExecutorPort` plugins
(`orcia.step_executors`, `AC-F1`, `AC-F2`), zero-thread human arbitration & anchor pause/resume
(`DBOS.recv_async` / `DBOS.send_async`), targeted rewind (`DBOS.fork_workflow_async`), and
transactional idempotency (`SetWorkflowID("<trigger_id>:<idempotency_key>")`) on PostgreSQL 18.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from dbos import DBOS, DBOSConfig, SetWorkflowID, WorkflowHandleAsync
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.blackboard.models import (
    BlackboardSnapshotEntity,
    WorkflowExecutionRegime,
)
from orcia_core.orchestration._internal._dbos_workflow_defs import (
    ARBITRATION_TOPIC,
    HUMAN_ANCHOR_TOPIC,
    DurableWorkflowRunSummary,
    _execute_durable_step,
    _orcia_durable_run_workflow,
    _require_bound_runtime,
    bind_dbos_runtime,
    clear_run_state_waiter,
    has_active_dbos_runtime_bindings,
    register_run_state_waiter,
    unbind_dbos_runtime,
)
from orcia_core.orchestration._internal._sql_dbos_launch_helpers import (
    append_rewind_supersede_tombstone_sql,
    build_step_artifact_outbox_events,
    build_step_execution_record,
    get_run_execution_context_sql,
)
from orcia_core.orchestration._internal.sql_repository import SqlOrchestrationRepository
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_core.orchestration.step_executors import (
    execute_step_port_async,
    register_default_step_executors,
)
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import StepExecutorContext, get_registered_step_executor


class DbosDurableWorkflowEngine:
    """Production DBOS Transact durable workflow engine backed by `SqlOrchestrationRepository`."""

    def __init__(
        self,
        *,
        system_database_url: str,
        application_database_url: str,
        app_name: str = "orcia-durable-engine",
    ) -> None:
        self._system_database_url = system_database_url
        self._application_database_url = application_database_url
        self._app_name = app_name
        self._uow: DbosSqlAlchemyUnitOfWork | None = None
        self._repository: SqlOrchestrationRepository | None = None
        self._launched: bool = False
        register_default_step_executors()

    @property
    def uow(self) -> DbosSqlAlchemyUnitOfWork:
        """Return the initialized `DbosSqlAlchemyUnitOfWork`."""
        if self._uow is None:
            raise RuntimeError("DbosDurableWorkflowEngine must be launched before accessing uow.")
        return self._uow

    @property
    def repository(self) -> SqlOrchestrationRepository:
        """Return the initialized `SqlOrchestrationRepository`."""
        if self._repository is None:
            raise RuntimeError(
                "DbosDurableWorkflowEngine must be launched before accessing repository."
            )
        return self._repository

    async def launch(self, *, existing_engine: AsyncEngine | None = None) -> None:
        """Configure and launch the DBOS Transact runtime + SQLAlchemy 2.1 Asyncio UoW."""
        if self._launched:
            return
        DBOS.destroy(destroy_registry=False)
        config: DBOSConfig = {
            "name": self._app_name,
            "system_database_url": self._system_database_url,
            "dbos_system_schema": "dbos",
            "run_migrations": True,
            "notification_listener_polling_interval_sec": 0.05,
            "notification_coalesce_sec": 0.005,
            "scheduler_polling_interval_sec": 0.1,
            "enable_otlp": False,
        }
        DBOS(config=config)
        self._uow = await DbosSqlAlchemyUnitOfWork.create(
            self._application_database_url,
            engine=existing_engine,
            schema="dbos",
            run_migrations=True,
        )
        self._repository = SqlOrchestrationRepository(self._uow)
        bind_dbos_runtime(self)
        DBOS.launch()
        self._launched = True

    async def shutdown(self, *, dispose_engine: bool = True) -> None:
        """Destroy DBOS runtime and optionally dispose the SQLAlchemy `AsyncEngine` pool."""
        if self._uow is not None:
            if dispose_engine:
                await self._uow.close()
            self._uow = None
            self._repository = None
        unbind_dbos_runtime(self)
        if self._launched:
            DBOS.destroy(destroy_registry=False)
            self._launched = False
            loop = asyncio.get_running_loop()
            default_exec = getattr(loop, "_default_executor", None)
            if default_exec is not None and type(default_exec).__name__ == "_SharedExecutor":
                loop._default_executor = None  # type: ignore[attr-defined]

    async def persist_step_and_commit_snapshot(
        self,
        *,
        run_id: str,
        step_key: str,
        step_index: int,
        artifact_payload: dict[str, Any] | None = None,
        parent_snapshot_id: str | None = None,
        step_type: str = "AGENT",
        directive: str | None = None,
        emit_outbox: bool = False,
        trace_id: str = "0" * 32,
    ) -> BlackboardSnapshotEntity:
        """Execute step via `StepExecutorPort`, persist `step_executions` and append snapshot."""
        existing_steps = await self.repository.list_step_executions(run_id)
        existing = next((s for s in existing_steps if s.step_key == step_key), None)
        step_id = existing.id if existing is not None else new_uuid7_str()
        ws_id, wf_uri, exec_regime = await get_run_execution_context_sql(self.uow, run_id)
        resolved_type = existing.step_type if existing is not None else step_type

        if artifact_payload is None:
            executor = get_registered_step_executor(resolved_type)
            assert executor is not None
            ctx = StepExecutorContext(
                run_id=run_id,
                root_run_id=run_id,
                workspace_id=ws_id,
                workflow_uri=wf_uri,
                step_key=step_key,
                step_title=step_key,
                step_type=resolved_type,
                execution_regime=cast(WorkflowExecutionRegime, exec_regime),
                directive=directive or f"Execute durable step {step_key}",
                declared_input_uris=(),
                resolved_inputs={"step_index": step_index},
            )
            exec_res = await execute_step_port_async(executor, ctx)
            resolved_payload = {
                **(existing.draft_artifact if existing is not None else {}),
                **exec_res.artifact_payload,
            }
            memlog_summary = exec_res.summary
            memlog_details = exec_res.details
            cost_usd = exec_res.cost_usd if exec_res.cost_usd > 0.0 else 0.25
        else:
            resolved_payload = {
                **(existing.draft_artifact if existing is not None else {}),
                **artifact_payload,
            }
            memlog_summary = f"DBOS durable step '{step_key}' executed"
            memlog_details = f"Persisted in PostgreSQL 18 for run {run_id}"
            cost_usd = 0.25

        step_exec = build_step_execution_record(
            existing=existing,
            step_id=step_id,
            run_id=run_id,
            step_key=step_key,
            step_index=step_index,
            resolved_type=resolved_type,
            exec_regime=exec_regime,
            resolved_payload=resolved_payload,
            memlog_summary=memlog_summary,
            memlog_details=memlog_details,
            cost_usd=cost_usd,
        )
        await self.repository.upsert_step_execution(step_exec)

        outbox_events: tuple[DomainEvent, ...] = (
            build_step_artifact_outbox_events(
                step_id=step_id,
                run_id=run_id,
                workspace_id=ws_id,
                step_key=step_key,
                cost_usd=cost_usd,
                resolved_payload=resolved_payload,
                trace_id=trace_id,
            )
            if emit_outbox
            else ()
        )
        return await self.repository.append_snapshot(
            run_id=run_id,
            step_execution_id=step_id,
            step_key=step_key,
            branch_status="ACTIVE",
            artifact_payload=resolved_payload,
            memlog_summary=step_exec.step_memlog,
            parent_snapshot_id=parent_snapshot_id,
            outbox_events=outbox_events,
        )

    async def start_durable_run(
        self,
        *,
        trigger_id: str,
        idempotency_key: str,
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
    ) -> WorkflowHandleAsync[DurableWorkflowRunSummary]:
        """Start a durable DBOS workflow deduplicated by `SetWorkflowID`."""
        workflow_id = f"{trigger_id}:{idempotency_key}"
        with SetWorkflowID(workflow_id):
            return await DBOS.start_workflow_async(
                _orcia_durable_run_workflow,
                run_id,
                steps,
                pause_for_arbitration_after_step,
                timeout_seconds,
                anchored_step_keys,
                step_types_by_key,
                emit_outbox_events,
                trace_id,
                skip_step_keys,
                initial_parent_snapshot_id,
            )

    async def send_human_arbitration(self, *, workflow_id: str, decision: str) -> None:
        """Resume a paused DBOS workflow awaiting human arbitration via `DBOS.send_async`."""
        await DBOS.send_async(workflow_id, decision, topic=ARBITRATION_TOPIC)

    async def send_human_anchor_signed(
        self, *, workflow_id: str, step_key: str, signature_id: str
    ) -> None:
        """Resume a paused DBOS workflow awaiting a `WAITING_FOR_HUMAN_ANCHOR` signature."""
        await DBOS.send_async(
            workflow_id,
            {"step_key": step_key, "signature_id": signature_id},
            topic=HUMAN_ANCHOR_TOPIC,
        )

    async def get_workflow_status_name(self, workflow_id: str) -> str | None:
        """Return DBOS workflow status (`PENDING`/`ENQUEUED`/`SUCCESS`) or None."""
        status = await DBOS.get_workflow_status_async(workflow_id)
        return None if status is None else str(status.status)

    async def rewind_and_fork_from_step(
        self,
        *,
        workflow_id: str,
        run_id: str,
        target_step_key: str,
        start_step: int,
    ) -> WorkflowHandleAsync[DurableWorkflowRunSummary]:
        """Append a `SUPERSEDED` snapshot tombstone and fork the DBOS workflow from `start_step`."""
        await append_rewind_supersede_tombstone_sql(
            self.repository, run_id=run_id, target_step_key=target_step_key
        )
        return await DBOS.fork_workflow_async(workflow_id, start_step)


__all__ = [
    "ARBITRATION_TOPIC",
    "HUMAN_ANCHOR_TOPIC",
    "DbosDurableWorkflowEngine",
    "DurableWorkflowRunSummary",
    "_execute_durable_step",
    "_orcia_durable_run_workflow",
    "_require_bound_runtime",
    "clear_run_state_waiter",
    "has_active_dbos_runtime_bindings",
    "register_run_state_waiter",
]
