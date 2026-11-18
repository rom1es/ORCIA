"""FastAPI router for Autonomous Run Supervision, Emergency Stop & Rollback (`Story 7.4`)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request

from orcia_api.dependencies import get_autonomous_supervision_service
from orcia_api.routers._finops_auth_guards import (
    enforce_workspace_governed_mutation,
    resolve_finops_read_scope,
    resolve_run_workspace_server_side,
    validate_uuid,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.autonomous_supervision import (
    AutonomousRunsListResponse,
    AutonomousRunSupervisionItemSchema,
    EmergencyStopRequest,
    EmergencyStopResponse,
    InvalidateAndRestoreRequest,
    InvalidateAndRestoreResponse,
    PostHocReviewRequest,
    PostHocReviewResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity

PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(tags=["autonomous-supervision"], responses=PROBLEM_RESPONSES)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
SupervisionDep = Annotated[
    AutonomousSupervisionService, Depends(get_autonomous_supervision_service)
]


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


async def _enforce_run_mutation_guard(
    request: Request,
    user: UserIdentity,
    svc: AutonomousSupervisionService,
    run_id: str,
    requested_workspace_id: str | None = None,
) -> None:
    path = str(request.url.path)
    pg_ws_id = await resolve_run_workspace_server_side(request, run_id)
    if svc._engine is not None:
        resolved_ws_id = pg_ws_id
    else:
        mem_run = svc._runs.get(run_id)
        resolved_ws_id = mem_run.workspace_id if mem_run is not None else pg_ws_id

    if resolved_ws_id is None:
        raise ResourceNotFoundError(instance=path)

    if requested_workspace_id is not None and requested_workspace_id != resolved_ws_id:
        raise ScopeAccessDeniedError(instance=path)

    await enforce_workspace_governed_mutation(request, user, resolved_ws_id)


@router.get(
    "/api/v1/workspaces/{workspace_id}/autonomous-runs",
    response_model=AutonomousRunsListResponse,
    summary="List supervised autonomous contract runs in a workspace (`Story 7.4`)",
)
async def list_workspace_autonomous_runs(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    user: CurrentUserDep,
    svc: SupervisionDep,
) -> AutonomousRunsListResponse:
    resolved_ws_id = validate_uuid(workspace_id, "workspace_id")
    await resolve_finops_read_scope(request, user, "WORKSPACE", resolved_ws_id)
    runs = await svc.list_autonomous_runs(workspace_id=resolved_ws_id)
    return AutonomousRunsListResponse(
        workspace_id=resolved_ws_id,
        runs=[
            AutonomousRunSupervisionItemSchema(
                run_id=r.run_id,
                workspace_id=r.workspace_id,
                workflow_id=r.workflow_id,
                workflow_title=r.workflow_title,
                trigger_id=r.trigger_id,
                trigger_label=r.trigger_label,
                trigger_type=r.trigger_type,
                trigger_status=r.trigger_status,
                run_status=r.run_status,
                post_hoc_status=r.post_hoc_status,
                contract_id=r.contract_id,
                cost_usd=r.cost_usd,
                created_at_iso=r.created_at_iso,
                help_resource_id=r.help_resource_id,
                previous_version_available=r.previous_version_available,
            )
            for r in runs
        ],
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/runs/{run_id}/emergency-stop",
    response_model=EmergencyStopResponse,
    summary="Trigger immediate emergency stop (`KILL_SWITCH_STOPPED`, `Story 7.4`)",
)
async def emergency_stop_autonomous_run(
    request: Request,
    run_id: Annotated[str, Path(min_length=1)],
    user: CurrentUserDep,
    svc: SupervisionDep,
    body: EmergencyStopRequest | None = None,
) -> EmergencyStopResponse:
    validate_uuid(run_id, "run_id")
    req_body = body or EmergencyStopRequest()
    req_ws_id = (
        validate_uuid(req_body.workspace_id, "workspace_id")
        if req_body.workspace_id is not None
        else None
    )
    await _enforce_run_mutation_guard(request, user, svc, run_id, requested_workspace_id=req_ws_id)
    outcome = await svc.emergency_stop(
        run_id=run_id,
        actor_user_id=user.id,
        reason=req_body.reason,
        suspend_trigger=req_body.suspend_trigger,
        trace_id=_trace(request),
    )
    return EmergencyStopResponse(
        run_id=outcome.run_id,
        workspace_id=outcome.workspace_id,
        status=outcome.status,
        trigger_suspended=outcome.trigger_suspended,
        sse_dispatch_latency_ms=outcome.sse_dispatch_latency_ms,
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/runs/{run_id}/invalidate-and-restore",
    response_model=InvalidateAndRestoreResponse,
    summary="Invalidate autonomous artifact/help article and restore `@v(N-1)` (`Story 7.4`)",
)
async def invalidate_and_restore_autonomous_run(
    request: Request,
    run_id: Annotated[str, Path(min_length=1)],
    user: CurrentUserDep,
    svc: SupervisionDep,
    body: InvalidateAndRestoreRequest | None = None,
) -> InvalidateAndRestoreResponse:
    validate_uuid(run_id, "run_id")
    req_body = body or InvalidateAndRestoreRequest()
    req_ws_id = (
        validate_uuid(req_body.workspace_id, "workspace_id")
        if req_body.workspace_id is not None
        else None
    )
    await _enforce_run_mutation_guard(request, user, svc, run_id, requested_workspace_id=req_ws_id)
    outcome = await svc.invalidate_and_restore(
        run_id=run_id,
        actor_user_id=user.id,
        comment=req_body.comment,
        help_resource_id=req_body.help_resource_id,
        trace_id=_trace(request),
    )
    return InvalidateAndRestoreResponse(
        run_id=outcome.run_id,
        workspace_id=outcome.workspace_id,
        status=outcome.status,
        restored_version=outcome.restored_version,
        help_resource_id=outcome.help_resource_id,
        redis_cache_invalidated_ms=outcome.redis_cache_invalidated_ms,
        sse_dispatch_latency_ms=outcome.sse_dispatch_latency_ms,
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/runs/{run_id}/post-hoc-review",
    response_model=PostHocReviewResponse,
    summary="Validate or invalidate a sampled autonomous execution (`Story 7.4`)",
)
async def review_post_hoc_autonomous_run(
    request: Request,
    run_id: Annotated[str, Path(min_length=1)],
    body: PostHocReviewRequest,
    user: CurrentUserDep,
    svc: SupervisionDep,
) -> PostHocReviewResponse:
    validate_uuid(run_id, "run_id")
    req_ws_id = (
        validate_uuid(body.workspace_id, "workspace_id") if body.workspace_id is not None else None
    )
    await _enforce_run_mutation_guard(request, user, svc, run_id, requested_workspace_id=req_ws_id)
    res = await svc.review_post_hoc_sample(
        run_id=run_id,
        actor_user_id=user.id,
        decision=body.decision,
        comment=body.comment,
        help_resource_id=body.help_resource_id,
        trace_id=_trace(request),
    )
    return PostHocReviewResponse(
        run_id=str(res["run_id"]),
        review_status=res["review_status"],
        run_status=str(res["run_status"]),
        restored_version=res["restored_version"],
        trace_id=_trace(request),
    )


__all__ = ["router"]
