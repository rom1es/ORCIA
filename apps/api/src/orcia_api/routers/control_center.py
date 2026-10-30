"""FastAPI Router for Story 5.2: Unified Workspace Control Center, `RunAccessGuard` & `⌘K`."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_control_center_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.control_center import (
    CommandPaletteEntryResponse,
    CommandPaletteSearchResponse,
    ControlCenterOverviewResponse,
    DeclarativeOverrideLayerResponse,
    GuidanceStepItemResponse,
    OrgUnitSummaryResponse,
    RunMutationGuardCheckRequest,
    RunMutationGuardCheckResponse,
    SupervisedDatasourceItemResponse,
    SupervisedRunItemResponse,
    UpdateWorkspaceLifecycleRequest,
    WorkspaceGovernanceItemResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(prefix="/api/v1/control-center", tags=["control-center"])

_ERR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}


@router.get(
    "/overview",
    response_model=ControlCenterOverviewResponse,
    summary="Consolidated 4-tab fractal Workspace Control Center overview (`Story 5.2`, `AD-14`)",
    responses=_ERR_RESPONSES,
)
async def get_control_center_overview(
    request: Request,
    scope_type: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"] = Query(default="GLOBAL"),
    scope_id: str = Query(
        default="0192c4e0-0000-7000-8000-000000000101", min_length=1, max_length=64
    ),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> ControlCenterOverviewResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_control_center_service(request)
    ov = svc.build_overview(
        user,
        scope_type=scope_type,
        scope_id=scope_id,
        instance=str(request.url.path),
    )
    return ControlCenterOverviewResponse(
        scope_type=ov.scope_type,
        scope_id=ov.scope_id,
        scope_label=ov.scope_label,
        viewer_access_mode=ov.viewer_access_mode,
        observer_banner_fr=ov.observer_banner_fr,
        consolidated_finops_usd=ov.consolidated_finops_usd,
        contributor_runs=[
            SupervisedRunItemResponse(
                run_id=r.run_id,
                workspace_id=r.workspace_id,
                workspace_name=r.workspace_name,
                workflow_key=r.workflow_key,
                title=r.title,
                status=r.status,
                current_step_id=r.current_step_id,
                current_step_key=r.current_step_key,
                execution_mode=r.execution_mode,
                access_mode=r.access_mode,
                claimed_by_user_id=r.claimed_by_user_id,
                claimed_by_display_name=r.claimed_by_display_name,
                budget_consumed_usd=r.budget_consumed_usd,
                blackboard_summary=r.blackboard_summary,
                blackboard_payload_masked=r.blackboard_payload_masked,
            )
            for r in ov.contributor_runs
        ],
        observer_runs=[
            SupervisedRunItemResponse(
                run_id=r.run_id,
                workspace_id=r.workspace_id,
                workspace_name=r.workspace_name,
                workflow_key=r.workflow_key,
                title=r.title,
                status=r.status,
                current_step_id=r.current_step_id,
                current_step_key=r.current_step_key,
                execution_mode=r.execution_mode,
                access_mode=r.access_mode,
                claimed_by_user_id=r.claimed_by_user_id,
                claimed_by_display_name=r.claimed_by_display_name,
                budget_consumed_usd=r.budget_consumed_usd,
                blackboard_summary=r.blackboard_summary,
                blackboard_payload_masked=r.blackboard_payload_masked,
            )
            for r in ov.observer_runs
        ],
        datasources=[
            SupervisedDatasourceItemResponse(
                id=d.id,
                workspace_id=d.workspace_id,
                workspace_name=d.workspace_name,
                alias=d.alias,
                scheme=d.scheme,
                uri=d.uri,
                role=d.role,
                execution_identity=d.execution_identity,
                freshness_ttl_days=d.freshness_ttl_days,
                tripartite_status=d.tripartite_status,
            )
            for d in ov.datasources
        ],
        guidance_steps=[
            GuidanceStepItemResponse(
                step_number=s.step_number,
                title_fr=s.title_fr,
                description_fr=s.description_fr,
                action_command=s.action_command,
            )
            for s in ov.guidance_steps
        ],
        workflow_overrides=[
            DeclarativeOverrideLayerResponse(
                workflow_key=w.workflow_key,
                title=w.title,
                base_layer=w.base_layer,
                team_override=w.team_override,
                workspace_override=w.workspace_override,
                user_override=w.user_override,
                spine_contract_ref=w.spine_contract_ref,
            )
            for w in ov.workflow_overrides
        ],
        org_units=[
            OrgUnitSummaryResponse(
                id=u.id,
                slug=u.slug,
                name=u.name,
                unit_type=u.unit_type,
                parent_id=u.parent_id,
            )
            for u in ov.org_units
        ],
        workspaces_governance=[
            WorkspaceGovernanceItemResponse(
                workspace_id=g.workspace_id,
                slug=g.slug,
                name=g.name,
                owner_org_unit_id=g.owner_org_unit_id,
                visibility_mode=g.visibility_mode,
                lifecycle_phase=g.lifecycle_phase,
                suggested_workflows=list(g.suggested_workflows),
                access_mode=g.access_mode,
                finops_cost_usd=g.finops_cost_usd,
                blackboard_payload_masked=g.blackboard_payload_masked,
            )
            for g in ov.workspaces_governance
        ],
        trace_id=trace_id,
    )


@router.patch(
    "/workspaces/{workspace_id}/lifecycle",
    response_model=WorkspaceGovernanceItemResponse,
    summary="Update product lifecycle phase (`RUN | BUILD | MIGRATION`) on a Workspace",
    responses=_ERR_RESPONSES,
)
async def update_workspace_lifecycle(
    workspace_id: str,
    payload: UpdateWorkspaceLifecycleRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> WorkspaceGovernanceItemResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_control_center_service(request)
    gov = svc.set_workspace_lifecycle_phase(
        user,
        workspace_id=workspace_id,
        lifecycle_phase=payload.lifecycle_phase,
        instance=str(request.url.path),
    )
    return WorkspaceGovernanceItemResponse(
        workspace_id=gov.workspace_id,
        slug=gov.slug,
        name=gov.name,
        owner_org_unit_id=gov.owner_org_unit_id,
        visibility_mode=gov.visibility_mode,
        lifecycle_phase=gov.lifecycle_phase,
        suggested_workflows=list(gov.suggested_workflows),
        access_mode=gov.access_mode,
        finops_cost_usd=gov.finops_cost_usd,
        blackboard_payload_masked=gov.blackboard_payload_masked,
    )


@router.post(
    "/runs/{run_id}/steps/{step_id}/mutate-check",
    response_model=RunMutationGuardCheckResponse,
    summary="Enforce `RunAccessGuard` ($O(1)$ observer `403` + peer claim `409`) on step mutation",
    responses=_ERR_RESPONSES,
)
async def check_run_step_mutation_guard(
    run_id: str,
    step_id: str,
    _payload: RunMutationGuardCheckRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> RunMutationGuardCheckResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_control_center_service(request)
    run = svc.enforce_run_mutation_guard(
        user,
        run_id=run_id,
        step_execution_id=step_id,
        instance=str(request.url.path),
    )
    return RunMutationGuardCheckResponse(
        run_id=run.run_id,
        step_execution_id=step_id,
        allowed=True,
        access_mode=run.access_mode,
        trace_id=trace_id,
    )


@router.get(
    "/command-palette",
    response_model=CommandPaletteSearchResponse,
    summary="Universal `⌘K` Command Palette search across Runs, Workspaces & shortcuts (`< 1 s`)",
    responses=_ERR_RESPONSES,
)
async def search_command_palette(
    request: Request,
    q: str = Query(default="", max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CommandPaletteSearchResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_control_center_service(request)
    entries = svc.search_command_palette(user, query=q)
    return CommandPaletteSearchResponse(
        query=q,
        items=[
            CommandPaletteEntryResponse(
                entry_id=e.entry_id,
                category=e.category,
                label_fr=e.label_fr,
                subtitle_fr=e.subtitle_fr,
                shortcut=e.shortcut,
                target_route=e.target_route,
                access_mode=e.access_mode,
            )
            for e in entries
        ],
        trace_id=trace_id,
    )
