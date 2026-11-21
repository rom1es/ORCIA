"""Arbitration, Resume & Fast-Path Audit Sub-Router for Durable Blackboard (`Story 3.2`/`3.4`)."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_auth_service, get_orchestration_service
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.routers.orchestration_sql_wiring import (
    hydrate_run_from_sql_if_missing,
    serialize_arbitration,
    serialize_audit_report,
    serialize_snapshot,
    serialize_step_exec,
    sync_arbitration_request_to_sql,
    sync_arbitration_resolution_to_sql,
    sync_step_execution_and_snapshot_to_sql,
)
from orcia_api.schemas.blackboard import (
    BackgroundAuditRunRequest,
    BackgroundAuditRunResponse,
    HumanArbitrationCreateRequest,
    HumanArbitrationCreateResponse,
    HumanArbitrationResolveRequest,
    HumanArbitrationResolveResponse,
    StepExecuteResponse,
    StepHumanResumeRequest,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import ArbitrationOptionItem

arbitration_router = APIRouter()


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


@arbitration_router.post(
    "/{run_id}/steps/{step_key}/arbitration",
    response_model=HumanArbitrationCreateResponse,
    summary="Invoke request_human_arbitration(options_matrix) with tie_break_policy (Story 3.4)",
    responses=PROBLEM_RESPONSES,
)
async def request_human_arbitration(
    payload: HumanArbitrationCreateRequest,
    request: Request,
    run_id: str = Path(..., min_length=1, max_length=128),
    step_key: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanArbitrationCreateResponse:
    """Evaluate `options_matrix` against `tie_break_policy` (`AD-3`, `AD-18`, `UX-DR6`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    await hydrate_run_from_sql_if_missing(request, svc, run_id)
    trace_id = _trace(request)
    arb, step_exec = svc.engine.anchors_and_arbitration.request_human_arbitration(
        user,
        run_id=run_id,
        step_key=step_key,
        question_title=payload.question_title,
        context_summary=payload.context_summary,
        options_matrix=tuple(
            ArbitrationOptionItem(
                option_key=o.option_key,
                title=o.title,
                pros=tuple(o.pros),
                cons=tuple(o.cons),
                si_impact=o.si_impact,
                finops_impact=o.finops_impact,
                recommended=o.recommended,
                ontology_concept_key=o.ontology_concept_key,
            )
            for o in payload.options_matrix
        ),
        tie_break_policy=payload.tie_break_policy,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    run = svc.engine._get_run(run_id, instance=str(request.url.path))
    await sync_arbitration_request_to_sql(
        request,
        run=run,
        arb=arb,
        step_exec=step_exec,
        trace_id=trace_id,
    )
    return HumanArbitrationCreateResponse(
        arbitration=serialize_arbitration(arb),
        step_execution=serialize_step_exec(step_exec),
        trace_id=trace_id,
    )


@arbitration_router.post(
    "/{run_id}/steps/{step_key}/arbitration/resolve",
    response_model=HumanArbitrationResolveResponse,
    summary="Resolve a pending human arbitration decision and resume step execution (Story 3.4)",
    responses=PROBLEM_RESPONSES,
)
async def resolve_human_arbitration(
    payload: HumanArbitrationResolveRequest,
    request: Request,
    run_id: str = Path(..., min_length=1, max_length=128),
    step_key: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanArbitrationResolveResponse:
    """Record human option selection in Blackboard and immediately resume the paused step."""
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    await hydrate_run_from_sql_if_missing(request, svc, run_id)
    trace_id = _trace(request)
    arb, step_exec, snap = await svc.engine.anchors_and_arbitration.resolve_human_arbitration_async(
        user,
        run_id=run_id,
        step_key=step_key,
        arbitration_id=payload.arbitration_id,
        selected_option_key=payload.selected_option_key,
        human_justification=payload.human_justification,
        instance=str(request.url.path),
    )
    run = svc.engine._get_run(run_id, instance=str(request.url.path))
    await sync_step_execution_and_snapshot_to_sql(
        request,
        run=run,
        step_exec=step_exec,
        snapshot=snap,
        trace_id=trace_id,
    )
    await sync_arbitration_resolution_to_sql(request, run=run, arb=arb)
    return HumanArbitrationResolveResponse(
        arbitration=serialize_arbitration(arb),
        step_execution=serialize_step_exec(step_exec),
        committed_snapshot=serialize_snapshot(snap) if snap else None,
        trace_id=trace_id,
    )


@arbitration_router.post(
    "/{run_id}/steps/{step_key}/resume",
    response_model=StepExecuteResponse,
    summary="Resume a paused HUMAN_TASK or WAITING_FOR_HUMAN_ARBITRATION step (Story 3.2f, AC-F1)",
    responses=PROBLEM_RESPONSES,
)
async def resume_human_workflow_step(
    payload: StepHumanResumeRequest,
    request: Request,
    run_id: str = Path(..., min_length=1, max_length=128),
    step_key: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StepExecuteResponse:
    """Resume a paused `HUMAN_TASK` step with an explicit human arbitration decision."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    await hydrate_run_from_sql_if_missing(request, svc, run_id)
    trace_id = _trace(request)
    step_exec, snap = await svc.engine.resume_human_task_async(
        user,
        run_id=run_id,
        step_key=step_key,
        decision=payload.decision,
        instance=str(request.url.path),
    )
    run = svc.engine._get_run(run_id, instance=str(request.url.path))
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


@arbitration_router.post(
    "/fast-path-audit",
    response_model=BackgroundAuditRunResponse,
    summary="Execute a non-blocking BACKGROUND_FAST_PATH audit with structured markers (UJ-10)",
    responses=PROBLEM_RESPONSES,
)
async def execute_background_fast_path_audit(
    payload: BackgroundAuditRunRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> BackgroundAuditRunResponse:
    """Run all steps in `BACKGROUND_FAST_PATH` mode, recording assumptions and divergences."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    await hydrate_run_from_sql_if_missing(request, svc, payload.run_id)
    trace_id = _trace(request)
    report = await svc.engine.run_background_fast_path_audit_async(
        user,
        run_id=payload.run_id,
        divergence_note=payload.divergence_note,
        instance=str(request.url.path),
    )
    run = svc.engine._get_run(payload.run_id, instance=str(request.url.path))
    active_by_step = {sn.step_key: sn for sn in svc.engine.blackboard.get_active_snapshots(run.id)}
    for s_exec in svc.engine.blackboard.list_step_executions(run.id):
        await sync_step_execution_and_snapshot_to_sql(
            request,
            run=run,
            step_exec=s_exec,
            snapshot=active_by_step.get(s_exec.step_key),
            trace_id=trace_id,
        )
    return BackgroundAuditRunResponse(
        report=serialize_audit_report(report),
        trace_id=trace_id,
    )
