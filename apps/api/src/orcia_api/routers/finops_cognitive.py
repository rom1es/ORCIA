"""FastAPI router for Cognitive Impact, Human Mastery & Reversibility (`Story 6.3`, `FR-27`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import get_cognitive_impact_service
from orcia_api.routers._finops_auth_guards import (
    enforce_scope_level_mutation,
    resolve_finops_read_scope,
    validate_uuid,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.finops import (
    ApplyRecommendationResponse,
    CognitiveImpactDashboardResponse,
    GatePolicyRecommendationSchema,
    ScopeType,
    WorkflowCognitiveMetricsSchema,
)
from orcia_core.audit_finops.cognitive_impact_service import CognitiveImpactService
from orcia_core.permissions.models import UserIdentity

router = APIRouter(tags=["finops"])

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
CognitiveServiceDep = Annotated[CognitiveImpactService, Depends(get_cognitive_impact_service)]


@router.get(
    "/api/v1/finops/cognitive-impact",
    response_model=CognitiveImpactDashboardResponse,
    summary="Get executive cognitive impact and gate recommendations",
)
async def get_cognitive_impact(
    request: Request,
    user: CurrentUserDep,
    svc: CognitiveServiceDep,
    scope_type: Annotated[
        ScopeType, Query(description="Scope filter: GLOBAL, BU, TEAM, WORKSPACE")
    ] = "GLOBAL",
    scope_id: Annotated[str | None, Query(description="Target scope UUID")] = None,
    time_window: Annotated[
        str, Query(description="Time window for aggregation: 7D, 30D, 90D, ALL")
    ] = "30D",
) -> CognitiveImpactDashboardResponse:
    if scope_id is not None:
        validate_uuid(scope_id, "scope_id")
    allowed_ws = await resolve_finops_read_scope(request, user, scope_type, scope_id)

    dash = await svc.get_dashboard(
        scope_type=scope_type,
        scope_id=scope_id,
        time_window=time_window,
        allowed_workspace_ids=allowed_ws,
    )

    return CognitiveImpactDashboardResponse(
        active_framing_ratio=dash.active_framing_ratio,
        active_framing_target=dash.active_framing_target,
        active_framing_alert=dash.active_framing_alert,
        quick_pass_rate=dash.quick_pass_rate,
        quick_pass_threshold=dash.quick_pass_threshold,
        quick_pass_alert=dash.quick_pass_alert,
        rubber_stamping_rate=dash.rubber_stamping_rate,
        rubber_stamping_alert=dash.rubber_stamping_alert,
        architecture_deviation_index=dash.architecture_deviation_index,
        architecture_deviation_target=dash.architecture_deviation_target,
        architecture_deviation_alert=dash.architecture_deviation_alert,
        pattern_drift_index=dash.pattern_drift_index,
        pattern_drift_alert=dash.pattern_drift_alert,
        total_human_hours=dash.total_human_hours,
        active_framing_hours=dash.active_framing_hours,
        review_hours=dash.review_hours,
        uncovered_deviations_count=dash.uncovered_deviations_count,
        workflow_breakdowns=[
            WorkflowCognitiveMetricsSchema(
                workflow_id=w.workflow_id,
                workflow_title=w.workflow_title,
                criticality=w.criticality,
                human_gates_count=w.human_gates_count,
                human_passes_count=w.human_passes_count,
                quick_passes_count=w.quick_passes_count,
                quick_pass_rate=w.quick_pass_rate,
                median_review_duration_ms=w.median_review_duration_ms,
                uncovered_drift_count=w.uncovered_drift_count,
                has_alert=w.has_alert,
            )
            for w in dash.workflow_breakdowns
        ],
        recommendations=[
            GatePolicyRecommendationSchema(
                id=r.id,
                workflow_id=r.workflow_id,
                workflow_title=r.workflow_title,
                recommendation_type=r.recommendation_type,
                title=r.title,
                description=r.description,
                action_label=r.action_label,
                suggested_policy=r.suggested_policy,
                status=r.status,
                applied_at=r.applied_at,
                applied_by=r.applied_by,
            )
            for r in dash.recommendations
        ],
    )


@router.post(
    "/api/v1/finops/gates/policy-recommendation/{recommendation_id}/apply",
    response_model=ApplyRecommendationResponse,
    summary="Apply actionable gate policy adjustment under scope guard protection",
)
async def apply_gate_policy_recommendation(
    request: Request,
    user: CurrentUserDep,
    svc: CognitiveServiceDep,
    recommendation_id: Annotated[str, Path(description="Target recommendation ID to apply")],
) -> ApplyRecommendationResponse:
    ws_id = await svc.resolve_recommendation_workspace_id(recommendation_id)
    await enforce_scope_level_mutation(
        request,
        user,
        scope_type="WORKSPACE" if ws_id is not None else "GLOBAL",
        scope_id=ws_id,
    )
    allowed_ws = (ws_id,) if ws_id is not None else None
    applied = await svc.apply_policy_recommendation(
        recommendation_id=recommendation_id,
        applied_by=user.id,
        allowed_workspace_ids=allowed_ws,
    )
    applied_at = applied.applied_at or datetime.now(UTC)
    return ApplyRecommendationResponse(
        recommendation_id=applied.id,
        status=applied.status,
        applied_at=applied_at,
        applied_by=user.id,
        workflow_id=applied.workflow_id,
        suggested_policy=applied.suggested_policy,
    )


__all__ = ["router"]
