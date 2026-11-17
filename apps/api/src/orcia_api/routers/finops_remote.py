"""FastAPI router for Story 6.4: Remote MCP & A2A Telemetry, Quotas & Circuit Reset.

Implements (`AD-12`, `AD-19`, `AD-21`, `Principe M.3`, `Story 6.4`):
- `GET /api/v1/finops/remote-services`: List external services telemetry & circuit states
- `PUT /api/v1/finops/connectors/{connector_key}/quota`: Configure quotas & valuation mode
- `POST /api/v1/finops/connectors/{connector_key}/reset-circuit`: Reset suspended circuit breaker
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_connector_quota_guard_service,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.finops_remote import (
    RemoteServicesListResponse,
    RemoteServiceTelemetryItemResponse,
    ResetCircuitBreakerRequest,
    ResetCircuitBreakerResponse,
    ScopeType,
    UpdateConnectorQuotaRequest,
)
from orcia_core.audit_finops.connector_quota_service import SqlConnectorQuotaGuardService
from orcia_core.audit_finops.finops_models import ConnectorQuotaRecord
from orcia_core.permissions.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.errors import ValidationDomainError

router = APIRouter(tags=["finops"])

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
QuotaGuardDep = Annotated[SqlConnectorQuotaGuardService, Depends(get_connector_quota_guard_service)]


def _validate_uuid(val: str, field_name: str) -> str:
    try:
        UUID(val)
        return val
    except (ValueError, TypeError, AttributeError) as err:
        raise ValidationDomainError(
            detail_override=f"Invalid UUID format for '{field_name}': {val!r}"
        ) from err


def _enforce_remote_finops_mutation_guard(
    request: Request,
    user: UserIdentity,
    workspace_id: str | None = None,
) -> None:
    """Enforce read-only observer protection (`403 ERR_OBSERVER_MODE_READ_ONLY`) & scope guard."""
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

    auth_svc = get_auth_service(request)
    if workspace_id is not None:
        ws = auth_svc.evaluator.get_workspace(workspace_id)
        if ws is not None:
            auth_svc.evaluator.enforce_scope_mutation_guard(user, ws.id, instance=path)
    elif user.platform_role == "BU_DIRECTOR":
        accessible = auth_svc.evaluator.resolve_accessible_workspaces(user)
        if accessible and all(w.access_mode == "READ_ONLY_OBSERVER" for w in accessible):
            raise ObserverModeReadOnlyError(instance=path)


def _to_item_response(rec: ConnectorQuotaRecord) -> RemoteServiceTelemetryItemResponse:
    return RemoteServiceTelemetryItemResponse(
        connector_key=rec.connector_key,
        display_name=rec.display_name,
        service_kind=rec.service_kind,
        scope_type=rec.scope_type,
        scope_id=rec.scope_id,
        valuation_mode=rec.valuation_mode,
        max_reported_cost_per_call_eur=float(rec.max_reported_cost_per_call_eur),
        fixed_cost_per_call_eur=float(rec.fixed_cost_per_call_eur),
        unit_tariff_eur=float(rec.unit_tariff_eur),
        default_unit_name=rec.default_unit_name,
        max_daily_calls=rec.max_daily_calls,
        max_monthly_cost_eur=(
            float(rec.max_monthly_cost_eur) if rec.max_monthly_cost_eur is not None else None
        ),
        daily_calls_count=rec.daily_calls_count,
        avg_latency_ms=rec.last_latency_ms,
        total_remote_tokens=rec.total_remote_tokens,
        total_business_units=float(rec.total_business_units),
        consolidated_cost_usd=float(rec.monthly_cost_usd),
        consolidated_cost_eur=float(rec.monthly_cost_eur),
        quota_used_pct=float(rec.quota_used_pct),
        circuit_state=rec.circuit_state,
        anomaly_count=rec.anomaly_count,
        last_tripped_reason=rec.last_tripped_reason,
        last_invoked_at=rec.last_invoked_at,
    )


@router.get(
    "/api/v1/finops/remote-services",
    response_model=RemoteServicesListResponse,
    summary="List remote MCP and A2A services FinOps telemetry and circuit breaker states",
)
async def list_remote_services_telemetry(
    user: CurrentUserDep,
    svc: QuotaGuardDep,
    scope_type: Annotated[
        ScopeType, Query(description="Scope filter: GLOBAL, BU, TEAM, WORKSPACE")
    ] = "GLOBAL",
    scope_id: Annotated[str | None, Query(description="Target scope UUID")] = None,
) -> RemoteServicesListResponse:
    _ = user
    if scope_id is not None:
        _validate_uuid(scope_id, "scope_id")
    records = await svc.list_remote_services(scope_type=scope_type, scope_id=scope_id)

    items = [_to_item_response(r) for r in records]
    units_breakdown: dict[str, float] = {}
    for r in records:
        if r.total_business_units > Decimal("0") and r.default_unit_name:
            units_breakdown[r.default_unit_name] = units_breakdown.get(
                r.default_unit_name, 0.0
            ) + float(r.total_business_units)

    return RemoteServicesListResponse(
        services=items,
        total_external_calls=sum(r.daily_calls_count for r in records),
        total_remote_tokens=sum(r.total_remote_tokens for r in records),
        total_reported_cost_eur=round(sum(float(r.monthly_cost_eur) for r in records), 2),
        open_circuits_count=sum(1 for r in records if r.circuit_state == "CIRCUIT_OPEN"),
        units_breakdown=units_breakdown,
    )


@router.put(
    "/api/v1/finops/connectors/{connector_key}/quota",
    response_model=RemoteServiceTelemetryItemResponse,
    summary="Configure valuation mode, safety cap and quota ceilings for a remote connector",
)
async def update_connector_quota(
    payload: UpdateConnectorQuotaRequest,
    request: Request,
    user: CurrentUserDep,
    svc: QuotaGuardDep,
    connector_key: Annotated[str, Path(min_length=1, max_length=128)],
) -> RemoteServiceTelemetryItemResponse:
    if payload.scope_id is not None:
        _validate_uuid(payload.scope_id, "scope_id")
    _enforce_remote_finops_mutation_guard(
        request,
        user,
        payload.scope_id if payload.scope_type == "WORKSPACE" else None,
    )
    clean_key = connector_key.strip().lower()
    if not clean_key:
        raise ValidationDomainError(detail_override="connector_key must not be empty.")

    rec = await svc.update_connector_quota(
        connector_key=clean_key,
        display_name=payload.display_name,
        service_kind=payload.service_kind,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        valuation_mode=payload.valuation_mode,
        max_reported_cost_per_call_eur=Decimal(str(payload.max_reported_cost_per_call_eur)),
        fixed_cost_per_call_eur=Decimal(str(payload.fixed_cost_per_call_eur)),
        unit_tariff_eur=Decimal(str(payload.unit_tariff_eur)),
        default_unit_name=payload.default_unit_name,
        max_daily_calls=payload.max_daily_calls,
        max_monthly_cost_eur=(
            Decimal(str(payload.max_monthly_cost_eur))
            if payload.max_monthly_cost_eur is not None
            else None
        ),
    )
    return _to_item_response(rec)


@router.post(
    "/api/v1/finops/connectors/{connector_key}/reset-circuit",
    response_model=ResetCircuitBreakerResponse,
    summary="Manually reset a suspended external connector circuit breaker",
)
async def reset_connector_circuit(
    request: Request,
    user: CurrentUserDep,
    svc: QuotaGuardDep,
    connector_key: Annotated[str, Path(min_length=1, max_length=128)],
    payload: Annotated[ResetCircuitBreakerRequest | None, Body()] = None,
) -> ResetCircuitBreakerResponse:
    req = payload or ResetCircuitBreakerRequest()
    if req.scope_id is not None:
        _validate_uuid(req.scope_id, "scope_id")
    _enforce_remote_finops_mutation_guard(request, user, req.scope_id)

    clean_key = connector_key.strip().lower()
    if not clean_key:
        raise ValidationDomainError(detail_override="connector_key must not be empty.")

    trace_id = getattr(request.state, "trace_id", "00000000000000000000000000000000")
    rec = await svc.reset_circuit(
        connector_key=clean_key,
        target_state=req.target_state,
        actor_id=user.id,
        trace_id=trace_id,
    )
    return ResetCircuitBreakerResponse(
        connector_key=rec.connector_key,
        circuit_state=rec.circuit_state,
        anomaly_count=rec.anomaly_count,
        reset_at=datetime.now(UTC),
        reset_by=user.id,
    )


__all__ = ["router"]
