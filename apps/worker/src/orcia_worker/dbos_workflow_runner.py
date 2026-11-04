"""DBOS Transact Durable Step & Workflow Runner (`Story 3.2b`, `AD-2`, `C4`).

Replaces legacy Dramatiq `step_runner.py` and import-time `_default_worker_orchestration`
singleton with an idempotent DBOS Transact durable workflow runner (`@DBOS.workflow()`,
`@DBOS.step()`, `SetWorkflowID`), while preserving `execute_step_runner_job` non-regression.
"""

from __future__ import annotations

from dataclasses import dataclass

from dbos import DBOS, SetWorkflowID

from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_core.orchestration import (
    DbosDurableWorkflowEngine,
    DbosSqlAlchemyUnitOfWork,
    DurableWorkflowRunSummary,
    WorkflowOrchestrationSetupService,
    build_default_orchestration_setup_service,
)
from orcia_core.permissions.models import UserIdentity

logger = get_logger("orcia.worker.dbos_workflow_runner")


@dataclass(frozen=True, slots=True)
class StepRunnerExecutionResult:
    """Result of an idempotent durable step runner execution."""

    run_id: str
    step_key: str
    snapshot_id: str | None
    already_committed: bool
    trace_id: str


def execute_step_runner_job(
    *,
    run_id: str,
    step_key: str,
    trace_id: str,
    commit_immediately: bool = True,
    simulated_divergence: str | None = None,
    orchestration_service: WorkflowOrchestrationSetupService | None = None,
) -> StepRunnerExecutionResult:
    """Execute idempotent step runner job without duplicating `blackboard_snapshots` rows."""
    ctx = bind_trace_context(trace_id)
    svc = (
        orchestration_service
        if orchestration_service is not None
        else build_default_orchestration_setup_service()
    )
    existing_snap = svc.engine.blackboard.get_active_step_snapshot(run_id, step_key)
    if existing_snap is not None and commit_immediately:
        logger.info(
            "worker.dbos_runner.idempotent_skip",
            run_id=run_id,
            step_key=step_key,
            snapshot_id=existing_snap.id,
            trace_id=ctx.trace_id,
        )
        return StepRunnerExecutionResult(
            run_id=run_id,
            step_key=step_key,
            snapshot_id=existing_snap.id,
            already_committed=True,
            trace_id=ctx.trace_id,
        )

    worker_user = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc (DBOS Durable Runner)",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )
    _, snap = svc.engine.execute_step(
        worker_user,
        run_id=run_id,
        step_key=step_key,
        commit_immediately=commit_immediately,
        simulated_divergence=simulated_divergence,
    )
    snap_id = snap.id if snap is not None else None
    logger.info(
        "worker.dbos_runner.executed",
        run_id=run_id,
        step_key=step_key,
        snapshot_id=snap_id,
        already_committed=False,
        trace_id=ctx.trace_id,
    )
    return StepRunnerExecutionResult(
        run_id=run_id,
        step_key=step_key,
        snapshot_id=snap_id,
        already_committed=False,
        trace_id=ctx.trace_id,
    )


async def execute_durable_sql_workflow(
    uow: DbosSqlAlchemyUnitOfWork,
    *,
    run_id: str,
    run_key: str,
    workspace_id: str,
    workflow_def_id: str,
    initiated_by_user_id: str,
    step_keys: tuple[str, ...] = ("step-1", "step-2"),
    pause_on_step_key: str | None = None,
    system_database_url: str = "postgresql://localhost:5432/orcia",
    application_database_url: str = "postgresql+asyncpg://localhost:5432/orcia",
) -> DurableWorkflowRunSummary:
    """Execute a durable PostgreSQL 18 + DBOS workflow via `DbosDurableWorkflowEngine` (`AD-2`)."""
    from orcia_core.orchestration import SqlOrchestrationRepository

    sql_repo = SqlOrchestrationRepository(uow)
    await sql_repo.upsert_workflow_run(
        run_id=run_id,
        run_key=run_key,
        workspace_id=workspace_id,
        workflow_def_id=workflow_def_id,
        parent_run_id=None,
        parent_step_execution_id=None,
        root_run_id=run_id,
        nesting_depth=0,
        execution_regime="INTERACTIVE_COACHING",
        criticality="STANDARD",
        trigger_id=None,
        trigger_idempotency_key=run_key,
        status="RUNNING",
        initiated_by_user_id=initiated_by_user_id,
        execution_identity_mode="USER_DELEGATED",
        budget_max_usd=10.0,
    )
    engine = DbosDurableWorkflowEngine(
        system_database_url=system_database_url,
        application_database_url=application_database_url,
    )
    engine._uow = uow
    engine._repository = sql_repo
    committed_ids: list[str] = []
    parent_id: str | None = None
    for idx, sk in enumerate(step_keys):
        snap = await engine.persist_step_and_commit_snapshot(
            run_id=run_id,
            step_key=sk,
            step_index=idx,
            parent_snapshot_id=parent_id,
        )
        committed_ids.append(snap.id)
        parent_id = snap.id
        if pause_on_step_key == sk:
            await sql_repo.update_run_status(run_id, "WAITING_FOR_HUMAN_ARBITRATION")
            return DurableWorkflowRunSummary(
                workflow_id=f"wf-{run_id}",
                run_id=run_id,
                final_status="WAITING_FOR_HUMAN_ARBITRATION",
                committed_snapshot_ids=tuple(committed_ids),
            )
    await sql_repo.update_run_status(run_id, "COMPLETED")
    return DurableWorkflowRunSummary(
        workflow_id=f"wf-{run_id}",
        run_id=run_id,
        final_status="COMPLETED",
        committed_snapshot_ids=tuple(committed_ids),
    )


@DBOS.step()
def _dbos_step_execution(
    run_id: str,
    step_key: str,
    trace_id: str,
    commit_immediately: bool,
) -> StepRunnerExecutionResult:
    return execute_step_runner_job(
        run_id=run_id,
        step_key=step_key,
        trace_id=trace_id,
        commit_immediately=commit_immediately,
    )


@DBOS.workflow()
def dbos_step_runner_workflow(
    run_id: str,
    step_key: str,
    trace_id: str,
    commit_immediately: bool = True,
) -> StepRunnerExecutionResult:
    """Durable DBOS workflow executing a single step with checkpointing (`AD-2`, `C4`)."""
    return _dbos_step_execution(run_id, step_key, trace_id, commit_immediately)


def dispatch_durable_step(
    *,
    run_id: str,
    step_key: str,
    trace_id: str,
    commit_immediately: bool = True,
) -> StepRunnerExecutionResult:
    """Dispatch a step execution deduplicated via `SetWorkflowID`."""
    with SetWorkflowID(f"step_runner:{run_id}:{step_key}"):
        return dbos_step_runner_workflow(
            run_id=run_id,
            step_key=step_key,
            trace_id=trace_id,
            commit_immediately=commit_immediately,
        )


__all__ = [
    "StepRunnerExecutionResult",
    "dbos_step_runner_workflow",
    "dispatch_durable_step",
    "execute_durable_sql_workflow",
    "execute_step_runner_job",
]
