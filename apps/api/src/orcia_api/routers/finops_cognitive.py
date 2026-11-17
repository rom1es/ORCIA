"""FastAPI router for Cognitive Impact, Human Mastery & Reversibility (`Story 6.3`, `FR-27`).

Implements:
- `GET /api/v1/finops/cognitive-impact`: Consolidated metrics & gate recommendations
- `POST /api/v1/finops/gates/policy-recommendation/{recommendation_id}/apply`: Apply gate adjustment
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_cognitive_impact_service,
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
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.errors import ValidationDomainError

router = APIRouter(tags=["finops"])

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
CognitiveServiceDep = Annotated[CognitiveImpactService, Depends(get_cognitive_impact_service)]


def _validate_uuid(val: str, field_name: str) -> str:
    try:
        UUID(val)
        return val
    except (ValueError, TypeError, AttributeError) as err:
        raise ValidationDomainError(
            detail_override=f"Invalid UUID format for '{field_name}': {val!r}"
        ) from err


def _enforce_cognitive_mutation_guard(
    request: Request,
    user: UserIdentity,
    workspace_id: str | None = None,
) -> None:
    """Enforce read-only observer protection on cognitive governance mutations."""
    path = str(request.url.path)
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()

    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or active_hat in ("READ_ONLY_OBSERVER", "OBSERVER")
        or observer_hdr in ("1", "true", "yes")
        or user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER")
    ):
        raise ObserverModeReadOnlyError(instance=path)

    if workspace_id is not None:
        auth_svc = get_auth_service(request)
        ws = auth_svc.evaluator.get_workspace(workspace_id)
        if ws is not None:
            access = auth_svc.evaluator.resolve_workspace_access(user, ws.id)
            if access is None:
                raise ScopeAccessDeniedError(instance=path)
            if access.access_mode == "READ_ONLY_OBSERVER":
                raise ObserverModeReadOnlyError(instance=path)


@router.get(
    "/api/v1/finops/cognitive-impact",
    response_model=CognitiveImpactDashboardResponse,
    summary="Get executive cognitive impact and gate recommendations",
)
async def get_cognitive_impact(
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
    _ = user
    if scope_id is not None:
        _validate_uuid(scope_id, "scope_id")

    dash = await svc.get_dashboard(
        scope_type=scope_type,
        scope_id=scope_id,
        time_window=time_window,
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
    _enforce_cognitive_mutation_guard(request, user)
    applied = await svc.apply_policy_recommendation(
        recommendation_id=recommendation_id,
        applied_by=user.id,
    )
    assert applied.applied_at is not None
    return ApplyRecommendationResponse(
        recommendation_id=applied.id,
        status=applied.status,
        applied_at=applied.applied_at,
        applied_by=user.id,
        workflow_id=applied.workflow_id,
        suggested_policy=applied.suggested_policy,
    )


__all__ = ["router"]
