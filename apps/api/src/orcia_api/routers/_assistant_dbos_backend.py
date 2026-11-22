"""DBOS + PG18 durable backend adapter for Assistant process launch & resume (`Story 26.8`)."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import Request

from orcia_api.routers._orchestration_sql_hydration import hydrate_run_from_sql_if_missing
from orcia_api.routers.orchestration_sql_wiring import sync_instantiated_run_to_sql
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import (
    DurableOrchestrationEngine,
    WorkflowAsCodeDefinition,
    WorkflowOrchestrationSetupService,
    WorkflowRunEntity,
)
from orcia_core.orchestration.assistant_process_launcher import (
    DurableProcessBackendPort,
    DurableProcessExecutionSnapshot,
)
from orcia_core.orchestration.dbos_engine_ports import (
    DbosDurableWorkflowEngine,
    clear_run_state_waiter,
    register_run_state_waiter,
)

logger = get_logger("orcia.api.assistant_process")


class ApiDbosProcessBackendAdapter(DurableProcessBackendPort):
    """Bridges `AssistantProcessLauncherService` to `DbosDurableWorkflowEngine` + PG18."""

    def __init__(
        self,
        *,
        request: Request,
        setup_service: WorkflowOrchestrationSetupService,
        engine: DurableOrchestrationEngine,
    ) -> None:
        self._request = request
        self._setup_service = setup_service
        self._engine = engine

    def _get_launched_dbos(self) -> DbosDurableWorkflowEngine | None:
        dbos_eng: DbosDurableWorkflowEngine | None = getattr(
            self._request.app.state, "dbos_durable_engine", None
        )
        if dbos_eng is None or not getattr(dbos_eng, "_launched", False):
            return None
        return dbos_eng

    def is_available(self) -> bool:
        """Return True only when a live `DbosDurableWorkflowEngine` is launched on `app.state`."""
        return self._get_launched_dbos() is not None

    async def _start_workflow_for_run(
        self,
        *,
        dbos_eng: DbosDurableWorkflowEngine,
        trigger_id: str,
        idempotency_key: str,
        run_id: str,
        workflow: WorkflowAsCodeDefinition,
        trace_id: str,
        skip_step_keys: tuple[str, ...] = (),
        initial_parent_snapshot_id: str | None = None,
    ) -> None:
        await dbos_eng.start_durable_run(
            trigger_id=trigger_id,
            idempotency_key=idempotency_key,
            run_id=run_id,
            steps=tuple(s.step_key for s in workflow.steps),
            timeout_seconds=3600.0,
            anchored_step_keys=tuple(
                s.step_key for s in workflow.steps if s.human_authored_required
            ),
            step_types_by_key={s.step_key: str(s.step_type) for s in workflow.steps},
            emit_outbox_events=True,
            trace_id=trace_id,
            skip_step_keys=skip_step_keys,
            initial_parent_snapshot_id=initial_parent_snapshot_id,
        )

    async def _await_dbos_pause_or_finish(
        self,
        *,
        dbos_eng: DbosDurableWorkflowEngine,
        run_id: str,
        workflow_id: str,
        waiter: asyncio.Event,
        event_name: str,
    ) -> DurableProcessExecutionSnapshot:
        try:
            await asyncio.wait_for(waiter.wait(), timeout=15.0)
        except TimeoutError:
            logger.warning(event_name, run_id=run_id)
        return await self._read_pg_snapshot_and_hydrate(
            dbos_eng=dbos_eng, run_id=run_id, workflow_id=workflow_id
        )

    async def launch_durable_run_async(
        self,
        *,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        seed_inputs: dict[str, Any],
        trace_id: str,
    ) -> DurableProcessExecutionSnapshot:
        """Persist `run` + initial anchored steps to PG18 and start the DBOS workflow."""
        dbos_eng = self._get_launched_dbos()
        assert dbos_eng is not None
        initial_steps = self._engine.initialize_run_steps(
            run, workflow, initialize_anchored_as_waiting=True
        )
        await sync_instantiated_run_to_sql(self._request, run, initial_steps=initial_steps)
        workflow_id = f"assistant-process:{run.id}"

        waiter = register_run_state_waiter(run.id)
        try:
            await self._start_workflow_for_run(
                dbos_eng=dbos_eng,
                trigger_id="assistant-process",
                idempotency_key=run.id,
                run_id=run.id,
                workflow=workflow,
                trace_id=trace_id,
            )
            return await self._await_dbos_pause_or_finish(
                dbos_eng=dbos_eng,
                run_id=run.id,
                workflow_id=workflow_id,
                waiter=waiter,
                event_name="dbos_process_launch_wait_timeout",
            )
        finally:
            clear_run_state_waiter(run.id)

    async def resume_after_anchor_async(
        self,
        *,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        step_key: str,
        signature_id: str = "signed",
        trace_id: str = "0" * 32,
    ) -> DurableProcessExecutionSnapshot | None:
        """Signal a paused DBOS workflow (`send_async`) or resume via DBOS after cold restart."""
        dbos_eng = self._get_launched_dbos()
        if dbos_eng is None:
            return None
        workflow_id = f"assistant-process:{run.id}"

        waiter = register_run_state_waiter(run.id, wait_for_completion=True)
        try:
            wf_status = await dbos_eng.get_workflow_status_name(workflow_id)
            if wf_status in ("PENDING", "ENQUEUED"):
                await dbos_eng.send_human_anchor_signed(
                    workflow_id=workflow_id, step_key=step_key, signature_id=signature_id
                )
            else:
                workflow_id = f"assistant-process-resume:{run.id}:{step_key}:{signature_id}"
                committed = tuple(
                    s.step_key
                    for s in await dbos_eng.repository.list_step_executions(run.id)
                    if s.status == "COMMITTED"
                )
                snaps = await dbos_eng.repository.list_snapshots(run.id)
                await self._start_workflow_for_run(
                    dbos_eng=dbos_eng,
                    trigger_id="assistant-process-resume",
                    idempotency_key=f"{run.id}:{step_key}:{signature_id}",
                    run_id=run.id,
                    workflow=workflow,
                    trace_id=trace_id,
                    skip_step_keys=committed,
                    initial_parent_snapshot_id=snaps[-1].id if snaps else None,
                )
            return await self._await_dbos_pause_or_finish(
                dbos_eng=dbos_eng,
                run_id=run.id,
                workflow_id=workflow_id,
                waiter=waiter,
                event_name="dbos_process_resume_wait_timeout",
            )
        finally:
            clear_run_state_waiter(run.id)

    async def _read_pg_snapshot_and_hydrate(
        self,
        *,
        dbos_eng: DbosDurableWorkflowEngine,
        run_id: str,
        workflow_id: str,
    ) -> DurableProcessExecutionSnapshot:
        await hydrate_run_from_sql_if_missing(self._request, self._setup_service, run_id)
        run_status = await dbos_eng.repository.get_run_status(run_id) or "INITIALIZED"
        steps = await dbos_eng.repository.list_step_executions(run_id)
        snaps = await dbos_eng.repository.list_snapshots(run_id)
        waiting = tuple(s.step_key for s in steps if s.status.startswith("WAITING_"))
        executed = tuple(s.step_key for s in steps if s.status == "COMMITTED")
        return DurableProcessExecutionSnapshot(
            workflow_id=workflow_id,
            run_status=run_status,
            waiting_step_keys=waiting,
            executed_step_keys=executed,
            snapshot_count=len(snaps),
        )
