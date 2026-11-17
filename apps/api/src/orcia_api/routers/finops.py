"""FastAPI router for Story 6.2: Complete FinOps Accounting, Baselines & Budget Overrides.

Implements (`AD-10`, `AD-12`, `AD-19`, `AD-21`, `FR-26`, `SM-1`, `Story 6.2`):
- `GET /api/v1/finops/dashboard`: Consolidated FinOps dashboard with 3-component equation
- `PUT /api/v1/finops/budgets`: Configure hierarchical scope budget limits (protected)
- `PUT /api/v1/finops/baselines`: Register pre-automation manual reference baselines (protected)
- `POST /api/v1/runs/{run_id}/budget-override`: Approve budget extension and awaken paused runs
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_finops_accounting_service,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.routers.finops_cognitive import router as cognitive_router
from orcia_api.schemas.finops import (
    BudgetOverrideRequest,
    BudgetOverrideResponse,
    FinopsBreakdownResponse,
    FinopsOverviewResponse,
    FinopsProcessItemResponse,
    FinopsTierEffortItemResponse,
    ScopeBudgetResponse,
    ScopeType,
    SetWorkflowBaselineRequest,
    UpdateScopeBudgetRequest,
    WorkflowBaselineResponse,
)
from orcia_core.audit_finops.finops_accounting_service import FinopsAccountingService
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.errors import ValidationDomainError

router = APIRouter(tags=["finops"])
router.include_router(cognitive_router)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
FinopsServiceDep = Annotated[FinopsAccountingService, Depends(get_finops_accounting_service)]


def _validate_uuid(val: str, field_name: str) -> str:
    try:
        UUID(val)
        return val
    except (ValueError, TypeError, AttributeError) as err:
        raise ValidationDomainError(
            detail_override=f"Invalid UUID format for '{field_name}': {val!r}"
        ) from err


def _enforce_finops_mutation_guard(
    request: Request,
    user: UserIdentity,
    workspace_id: str | None = None,
) -> None:
    """Enforce read-only observer protection and workspace scope access on FinOps mutations."""
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
    "/api/v1/finops/dashboard",
    response_model=FinopsBreakdownResponse,
    summary="Get consolidated FinOps dashboard metrics, processes, tiers, and baselines",
)
async def get_finops_dashboard(
    user: CurrentUserDep,
    svc: FinopsServiceDep,
    scope_type: Annotated[
        ScopeType, Query(description="Scope filter: GLOBAL, BU, TEAM, WORKSPACE")
    ] = "GLOBAL",
    scope_id: Annotated[str | None, Query(description="Target scope UUID")] = None,
) -> FinopsBreakdownResponse:
    _ = user
    if scope_id is not None:
        _validate_uuid(scope_id, "scope_id")
    data = await svc.get_breakdown(scope_type=scope_type, scope_id=scope_id)
    ov = data.overview
    return FinopsBreakdownResponse(
        overview=FinopsOverviewResponse(
            total_cost_usd=float(ov.total_cost_usd),
            total_cost_eur=float(ov.total_cost_eur),
            verified_internal_cost_usd=float(ov.verified_internal_cost_usd),
            verified_internal_cost_eur=float(ov.verified_internal_cost_eur),
            reported_external_cost_usd=float(ov.reported_external_cost_usd),
            reported_external_cost_eur=float(ov.reported_external_cost_eur),
            total_llm_tokens=ov.total_llm_tokens,
            internal_tokens=ov.internal_tokens,
            remote_tokens=ov.remote_tokens,
            total_external_calls=ov.total_external_calls,
            external_units_breakdown=ov.external_units_breakdown,
            cache_savings_usd=float(ov.cache_savings_usd),
            cache_savings_eur=float(ov.cache_savings_eur),
            active_circuit_breakers_count=ov.active_circuit_breakers_count,
            paused_runs_count=ov.paused_runs_count,
            accounted_runs_count=ov.accounted_runs_count,
        ),
        processes=[
            FinopsProcessItemResponse(
                workflow_id=p.workflow_id,
                workflow_title=p.workflow_title,
                runs_count=p.runs_count,
                amortized_setup_cost_usd=float(p.amortized_setup_cost_usd),
                amortized_setup_cost_eur=float(p.amortized_setup_cost_eur),
                run_cost_usd=float(p.run_cost_usd),
                run_cost_eur=float(p.run_cost_eur),
                human_time_cost_usd=float(p.human_time_cost_usd),
                human_time_cost_eur=float(p.human_time_cost_eur),
                total_cost_usd=float(p.total_cost_usd),
                total_cost_eur=float(p.total_cost_eur),
                baseline_manual_cost_usd=float(p.baseline_manual_cost_usd),
                baseline_manual_cost_eur=float(p.baseline_manual_cost_eur),
                ttm_reduction_pct=float(p.ttm_reduction_pct),
                active_budget_override=p.active_budget_override,
                paused_runs_count=p.paused_runs_count,
            )
            for p in data.processes
        ],
        tiers=[
            FinopsTierEffortItemResponse(
                inference_tier=t.inference_tier,
                effort=t.effort,
                invocations_count=t.invocations_count,
                input_tokens=t.input_tokens,
                output_tokens=t.output_tokens,
                total_tokens=t.total_tokens,
                cost_usd=float(t.cost_usd),
                cost_eur=float(t.cost_eur),
                escalated_from_auto_count=t.escalated_from_auto_count,
            )
            for t in data.tiers
        ],
        scope_budgets=[
            ScopeBudgetResponse(
                id=b.id,
                scope_type=b.scope_type,
                scope_id=b.scope_id,
                monthly_budget_usd=float(b.monthly_budget_usd),
                warning_threshold_pct=b.warning_threshold_pct,
                hard_stop_pct=b.hard_stop_pct,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b in data.scope_budgets
        ],
        baselines=[
            WorkflowBaselineResponse(
                id=bl.id,
                workflow_definition_id=bl.workflow_definition_id,
                scope_id=bl.scope_id,
                manual_time_minutes=bl.manual_time_minutes,
                manual_cost_usd=float(bl.manual_cost_usd),
                target_ttm_reduction_pct=bl.target_ttm_reduction_pct,
                created_at=bl.created_at,
            )
            for bl in data.baselines
        ],
    )


@router.put(
    "/api/v1/finops/budgets",
    response_model=ScopeBudgetResponse,
    summary="Configure scope budget ceiling and warning thresholds",
)
async def update_scope_budget(
    payload: UpdateScopeBudgetRequest,
    request: Request,
    user: CurrentUserDep,
    svc: FinopsServiceDep,
) -> ScopeBudgetResponse:
    if payload.scope_id is not None:
        _validate_uuid(payload.scope_id, "scope_id")
    _enforce_finops_mutation_guard(
        request, user, payload.scope_id if payload.scope_type == "WORKSPACE" else None
    )
    res = await svc.set_scope_budget(
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        monthly_budget_usd=Decimal(str(payload.monthly_budget_usd)),
        warning_threshold_pct=payload.warning_threshold_pct,
        hard_stop_pct=payload.hard_stop_pct,
    )
    return ScopeBudgetResponse(
        id=res.id,
        scope_type=res.scope_type,
        scope_id=res.scope_id,
        monthly_budget_usd=float(res.monthly_budget_usd),
        warning_threshold_pct=res.warning_threshold_pct,
        hard_stop_pct=res.hard_stop_pct,
        created_at=res.created_at,
        updated_at=res.updated_at,
    )


@router.put(
    "/api/v1/finops/baselines",
    response_model=WorkflowBaselineResponse,
    summary="Set or update pre-automation manual reference baseline",
)
async def set_workflow_baseline(
    payload: SetWorkflowBaselineRequest,
    request: Request,
    user: CurrentUserDep,
    svc: FinopsServiceDep,
) -> WorkflowBaselineResponse:
    _validate_uuid(payload.workflow_definition_id, "workflow_definition_id")
    if payload.scope_id is not None:
        _validate_uuid(payload.scope_id, "scope_id")
    _enforce_finops_mutation_guard(request, user, payload.scope_id)
    res = await svc.set_workflow_baseline(
        workflow_definition_id=payload.workflow_definition_id,
        scope_id=payload.scope_id,
        manual_time_minutes=payload.manual_time_minutes,
        manual_cost_usd=Decimal(str(payload.manual_cost_usd)),
        target_ttm_reduction_pct=payload.target_ttm_reduction_pct,
    )
    return WorkflowBaselineResponse(
        id=res.id,
        workflow_definition_id=res.workflow_definition_id,
        scope_id=res.scope_id,
        manual_time_minutes=res.manual_time_minutes,
        manual_cost_usd=float(res.manual_cost_usd),
        target_ttm_reduction_pct=res.target_ttm_reduction_pct,
        created_at=res.created_at,
    )


@router.post(
    "/api/v1/runs/{run_id}/budget-override",
    response_model=BudgetOverrideResponse,
    summary="Approve budget extension for a paused run and awaken workflow",
)
@router.post(
    "/api/v1/finops/runs/{run_id}/budget-override",
    response_model=BudgetOverrideResponse,
    summary="Approve budget extension for a paused run (alias)",
    include_in_schema=False,
)
async def approve_run_budget_override(
    payload: BudgetOverrideRequest,
    request: Request,
    user: CurrentUserDep,
    svc: FinopsServiceDep,
    run_id: Annotated[str, Path(description="Target paused workflow run UUID")],
) -> BudgetOverrideResponse:
    _validate_uuid(run_id, "run_id")
    _enforce_finops_mutation_guard(request, user, payload.workspace_id)
    override = await svc.approve_budget_override(
        run_id=run_id,
        requested_by=user.id,
        approved_by=user.id,
        override_amount_usd=Decimal(str(payload.override_amount_usd)),
        reason=payload.reason,
        workspace_id=payload.workspace_id,
        trace_id=getattr(request.state, "trace_id", "00000000000000000000000000000000"),
    )
    return BudgetOverrideResponse(
        id=override.id,
        run_id=override.run_id,
        requested_by=override.requested_by,
        approved_by=override.approved_by,
        override_amount_usd=float(override.override_amount_usd),
        reason=override.reason,
        created_at=override.created_at,
        new_run_status="RUNNING",
    )


__all__ = [
    "router",
]
