"""FastAPI Router for Story 3.2: Durable Step Execution, JIT Hydrator & Append-Only Blackboard."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_auth_service, get_orchestration_service
from orcia_api.routers._blackboard_arbitration_routes import arbitration_router
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.routers.orchestration_sql_wiring import (
    hydrate_run_from_sql_if_missing,
    read_sql_blackboard_if_available,
    read_sql_run_governance_if_available,
    serialize_anchor,
    serialize_arbitration,
    serialize_hydrated,
    serialize_snapshot,
    serialize_step_exec,
    sync_human_anchor_to_sql,
    sync_step_execution_and_snapshot_to_sql,
)
from orcia_api.schemas.blackboard import (
    HumanAnchorSignRequest,
    HumanAnchorSignResponse,
    RunBlackboardStateResponse,
    StepExecuteRequest,
    StepExecuteResponse,
    StepHydrateRequest,
    StepHydrateResponse,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import (
    JitStepHydrator,
    WorkflowRunStatus,
)

router = APIRouter(prefix="/api/v1/orchestration/runs", tags=["durable-orchestration-blackboard"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


@router.get(
    "/{run_id}/blackboard",
    response_model=RunBlackboardStateResponse,
    summary="Get durable step executions and append-only Blackboard snapshots for a Run",
    responses=PROBLEM_RESPONSES,
)
async def get_run_blackboard_state(
    request: Request,
    run_id: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> RunBlackboardStateResponse:
    """Return durable `step_executions`, active snapshots, pending arbitrations & anchors."""
    resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    await hydrate_run_from_sql_if_missing(request, svc, run_id)
    run = svc.engine._get_run(run_id, instance=str(request.url.path))
    wf = svc.engine._get_workflow(run.workflow_uri, instance=str(request.url.path))
    svc.engine.initialize_run_steps(run, wf)
    sql_status, sql_steps, sql_snaps = await read_sql_blackboard_if_available(request, run.id)
    pending_arbs, human_anchors = await read_sql_run_governance_if_available(request, svc, run.id)
    steps = sql_steps if sql_steps else svc.engine.blackboard.list_step_executions(run.id)
    active_snaps = (
        tuple(sn for sn in sql_snaps if sn.branch_status == "ACTIVE")
        if sql_snaps
        else svc.engine.blackboard.get_active_snapshots(run.id)
    )
    effective_status = cast(WorkflowRunStatus, sql_status) if sql_status is not None else run.status
    return RunBlackboardStateResponse(
        run_id=run.id,
        root_run_id=run.root_run_id,
        run_status=effective_status,
        accumulated_root_cost_usd=svc.engine.get_root_accumulated_cost(run.root_run_id),
        step_executions=[serialize_step_exec(s) for s in steps],
        active_snapshots=[serialize_snapshot(sn) for sn in active_snaps],
        pending_arbitrations=[serialize_arbitration(a) for a in pending_arbs],
        human_anchors=[serialize_anchor(s) for s in human_anchors],
        trace_id=_trace(request),
    )


@router.post(
    "/steps/hydrate",
    response_model=StepHydrateResponse,
    summary="Hydrate Just-In-Time context for Step k (0 future step leakage, AD-13)",
    responses=PROBLEM_RESPONSES,
)
async def hydrate_step_context(
    payload: StepHydrateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StepHydrateResponse:
    """Resolve isolated `HydratedStepContext` for Step $k$ (`JitStepHydrator`, `AD-13`)."""
    resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    await hydrate_run_from_sql_if_missing(request, svc, payload.run_id)
    run = svc.engine._get_run(payload.run_id, instance=str(request.url.path))
    wf = svc.engine._get_workflow(run.workflow_uri, instance=str(request.url.path))
    hydrated = JitStepHydrator.hydrate_step(
        run=run,
        workflow=wf,
        step_key=payload.step_key,
        blackboard=svc.engine.blackboard,
    )
    return StepHydrateResponse(
        hydrated_context=serialize_hydrated(hydrated),
        trace_id=_trace(request),
    )


@router.post(
    "/steps/execute",
    response_model=StepExecuteResponse,
    summary="Execute a durable workflow step (AGENT, SKILL, SUB_WORKFLOW, HUMAN_TASK, HTTP_ACTION)",
    responses=PROBLEM_RESPONSES,
)
async def execute_workflow_step(
    payload: StepExecuteRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StepExecuteResponse:
    """Execute a step via `orcia.step_executors` and commit to `blackboard_snapshots`."""
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    await hydrate_run_from_sql_if_missing(request, svc, payload.run_id)
    trace_id = _trace(request)
    step_exec, snap = await svc.engine.execute_step_async(
        user,
        run_id=payload.run_id,
        step_key=payload.step_key,
        commit_immediately=payload.commit_immediately,
        divergence_note=payload.divergence_note or payload.simulated_divergence,
        human_decision=payload.human_decision,
        cost_usd=payload.cost_usd,
        require_human_anchor=payload.require_human_anchor,
        author_type=payload.author_type,
        instance=str(request.url.path),
    )
    run = svc.engine._get_run(payload.run_id, instance=str(request.url.path))
    await sync_step_execution_and_snapshot_to_sql(
        request,
        run=run,
        step_exec=step_exec,
        snapshot=snap,
        trace_id=trace_id,
    )
    return StepExecuteResponse(
        step_execution=serialize_step_exec(step_exec),
        committed_snapshot=serialize_snapshot(snap) if snap else None,
        trace_id=trace_id,
    )


@router.post(
    "/anchors/sign",
    response_model=HumanAnchorSignResponse,
    summary="Sign a mandatory Human-Led Anchor section (human_authored_required: true, Story 3.4)",
    responses=PROBLEM_RESPONSES,
)
async def sign_human_anchor(
    payload: HumanAnchorSignRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanAnchorSignResponse:
    """Sign a mandatory human-authored section (`>= 30` chars, rejects agent callers with 422)."""
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    await hydrate_run_from_sql_if_missing(request, svc, payload.run_id)
    sig = svc.engine.anchors_and_arbitration.sign_human_anchor(
        user,
        run_id=payload.run_id,
        step_key=payload.step_key,
        section_key=payload.section_key,
        content_text=payload.content_text,
        signature_text=payload.signature_text,
        author_type=payload.author_type,
        instance=str(request.url.path),
    )
    step_exec = svc.engine.blackboard.get_step_execution(payload.run_id, payload.step_key)
    run = svc.engine._get_run(payload.run_id, instance=str(request.url.path))
    trace_id = _trace(request)
    await sync_step_execution_and_snapshot_to_sql(
        request,
        run=run,
        step_exec=step_exec,
        snapshot=None,
        trace_id=trace_id,
    )
    await sync_human_anchor_to_sql(
        request,
        run=run,
        step_exec=step_exec,
        signature=sig,
    )
    return HumanAnchorSignResponse(
        signature=serialize_anchor(sig),
        step_execution=serialize_step_exec(step_exec),
        trace_id=trace_id,
    )


router.include_router(arbitration_router)
