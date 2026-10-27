"""Idempotent Dramatiq actor `step_runner_actor` for Durable Step Execution (Story 3.2, AD-2).

Conventions (AGENTS.md):
- Dramatiq workers (`apps/worker`) may retry on transient failures — every actor must be
  idempotent and never duplicate `audit_ledger` or `blackboard_snapshots` rows.
"""

from __future__ import annotations

from dataclasses import dataclass

import dramatiq

from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_core.orchestration import (
    WorkflowOrchestrationSetupService,
    build_default_orchestration_setup_service,
)
from orcia_core.permissions.models import UserIdentity

logger = get_logger("orcia.worker.step_runner")


@dataclass(frozen=True, slots=True)
class StepRunnerExecutionResult:
    """Result of an idempotent `step_runner_actor` invocation."""

    run_id: str
    step_key: str
    snapshot_id: str | None
    already_committed: bool
    trace_id: str


_default_worker_orchestration = build_default_orchestration_setup_service()


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
        else _default_worker_orchestration
    )
    existing_snap = svc.engine.blackboard.get_active_step_snapshot(run_id, step_key)
    if existing_snap is not None and commit_immediately:
        logger.info(
            "worker.step_runner.idempotent_skip",
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
        display_name="Marc (Worker Step Runner)",
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
        "worker.step_runner.executed",
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


@dramatiq.actor(actor_name="step_runner", max_retries=3)
def step_runner_actor(
    run_id: str,
    step_key: str,
    trace_id: str,
    commit_immediately: bool = True,
) -> None:
    """Idempotent Dramatiq actor `step_runner` executing a single workflow step."""
    execute_step_runner_job(
        run_id=run_id,
        step_key=step_key,
        trace_id=trace_id,
        commit_immediately=commit_immediately,
    )
