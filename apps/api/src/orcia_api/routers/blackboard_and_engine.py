"""FastAPI Router for Story 3.2: Durable Step Execution, JIT Hydrator & Append-Only Blackboard."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_orchestration_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.blackboard import (
    BackgroundAuditReportSchemaItem,
    BackgroundAuditRunRequest,
    BackgroundAuditRunResponse,
    BlackboardSnapshotSchemaItem,
    HydratedStepContextSchemaItem,
    RunBlackboardStateResponse,
    StepExecuteRequest,
    StepExecuteResponse,
    StepExecutionSchemaItem,
    StepHumanResumeRequest,
    StepHydrateRequest,
    StepHydrateResponse,
    StepMemlogSchemaItem,
)
from orcia_core.blackboard import (
    BackgroundAuditConsolidatedReport,
    BlackboardSnapshotEntity,
    HydratedStepContext,
    StepExecutionEntity,
    StepMemlogEntry,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import JitStepHydrator

router = APIRouter(prefix="/api/v1/orchestration/runs", tags=["durable-orchestration-blackboard"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_memlog(entry: StepMemlogEntry) -> StepMemlogSchemaItem:
    return StepMemlogSchemaItem(
        entry_id=entry.entry_id,
        step_key=entry.step_key,
        marker_type=entry.marker_type,
        summary=entry.summary,
        details=entry.details,
        source_uris=list(entry.source_uris),
    )


def _serialize_snapshot(snap: BlackboardSnapshotEntity) -> BlackboardSnapshotSchemaItem:
    return BlackboardSnapshotSchemaItem(
        id=snap.id,
        snapshot_key=snap.snapshot_key,
        run_id=snap.run_id,
        step_execution_id=snap.step_execution_id,
        parent_snapshot_id=snap.parent_snapshot_id,
        step_key=snap.step_key,
        branch_status=snap.branch_status,
        artifact_payload=dict(snap.artifact_payload),
        artifact_cas_key=snap.artifact_cas_key,
        artifact_sha256=snap.artifact_sha256,
        memlog_summary=[_serialize_memlog(m) for m in snap.memlog_summary],
        superseded_snapshot_ids=list(snap.superseded_snapshot_ids),
    )


def _serialize_step_exec(step: StepExecutionEntity) -> StepExecutionSchemaItem:
    return StepExecutionSchemaItem(
        id=step.id,
        step_execution_key=step.step_execution_key,
        run_id=step.run_id,
        step_key=step.step_key,
        step_index=step.step_index,
        step_type=step.step_type,
        execution_mode=step.execution_mode,
        status=step.status,
        attempt_count=step.attempt_count,
        max_agent_retries=step.max_agent_retries,
        draft_artifact=dict(step.draft_artifact),
        draft_cas_key=step.draft_cas_key,
        step_memlog=[_serialize_memlog(m) for m in step.step_memlog],
        hydrated_input_uris=list(step.hydrated_input_uris),
        child_run_id=step.child_run_id,
        committed_snapshot_id=step.committed_snapshot_id,
        cost_usd=step.cost_usd,
    )


def _serialize_hydrated(ctx: HydratedStepContext) -> HydratedStepContextSchemaItem:
    return HydratedStepContextSchemaItem(
        run_id=ctx.run_id,
        step_key=ctx.step_key,
        step_title=ctx.step_title,
        step_type=ctx.step_type,
        execution_mode=ctx.execution_mode,
        step_directive=ctx.step_directive,
        declared_input_uris=list(ctx.declared_input_uris),
        resolved_inputs=dict(ctx.resolved_inputs),
        future_step_instructions_leaked=ctx.future_step_instructions_leaked,
        undeclared_artifacts_leaked=ctx.undeclared_artifacts_leaked,
    )


def _serialize_audit_report(
    rep: BackgroundAuditConsolidatedReport,
) -> BackgroundAuditReportSchemaItem:
    return BackgroundAuditReportSchemaItem(
        run_id=rep.run_id,
        workflow_uri=rep.workflow_uri,
        total_steps_committed=rep.total_steps_committed,
        assumptions=[_serialize_memlog(m) for m in rep.assumptions],
        suspected_code_bugs=[_serialize_memlog(m) for m in rep.suspected_code_bugs],
        suspected_obsolete_docs=[_serialize_memlog(m) for m in rep.suspected_obsolete_docs],
        sse_event_topic=rep.sse_event_topic,
        sse_latency_ms=rep.sse_latency_ms,
    )


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
    """Return durable `step_executions` and active `blackboard_snapshots` for `run_id`."""
    resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    run = svc.engine._get_run(run_id, instance=str(request.url.path))
    wf = svc.engine._get_workflow(run.workflow_uri, instance=str(request.url.path))
    svc.engine.initialize_run_steps(run, wf)
    return RunBlackboardStateResponse(
        run_id=run.id,
        root_run_id=run.root_run_id,
        run_status=run.status,
        accumulated_root_cost_usd=svc.engine.get_root_accumulated_cost(run.root_run_id),
        step_executions=[
            _serialize_step_exec(s) for s in svc.engine.blackboard.list_step_executions(run.id)
        ],
        active_snapshots=[
            _serialize_snapshot(sn) for sn in svc.engine.blackboard.get_active_snapshots(run.id)
        ],
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
    run = svc.engine._get_run(payload.run_id, instance=str(request.url.path))
    wf = svc.engine._get_workflow(run.workflow_uri, instance=str(request.url.path))
    hydrated = JitStepHydrator.hydrate_step(
        run=run,
        workflow=wf,
        step_key=payload.step_key,
        blackboard=svc.engine.blackboard,
    )
    return StepHydrateResponse(
        hydrated_context=_serialize_hydrated(hydrated),
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
    svc = get_orchestration_service(request)
    step_exec, snap = svc.engine.execute_step(
        user,
        run_id=payload.run_id,
        step_key=payload.step_key,
        commit_immediately=payload.commit_immediately,
        divergence_note=payload.divergence_note or payload.simulated_divergence,
        human_decision=payload.human_decision,
        cost_usd=payload.cost_usd,
        instance=str(request.url.path),
    )
    return StepExecuteResponse(
        step_execution=_serialize_step_exec(step_exec),
        committed_snapshot=_serialize_snapshot(snap) if snap else None,
        trace_id=_trace(request),
    )


@router.post(
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
    step_exec, snap = svc.engine.resume_human_task(
        user,
        run_id=run_id,
        step_key=step_key,
        decision=payload.decision,
        instance=str(request.url.path),
    )
    return StepExecuteResponse(
        step_execution=_serialize_step_exec(step_exec),
        committed_snapshot=_serialize_snapshot(snap) if snap else None,
        trace_id=_trace(request),
    )


@router.post(
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
    report = svc.engine.run_background_fast_path_audit(
        user,
        run_id=payload.run_id,
        divergence_note=payload.divergence_note,
        instance=str(request.url.path),
    )
    return BackgroundAuditRunResponse(
        report=_serialize_audit_report(report),
        trace_id=_trace(request),
    )
