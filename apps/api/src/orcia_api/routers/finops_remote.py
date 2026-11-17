"""FastAPI router for Story 6.4: Remote MCP & A2A Telemetry, Quotas & Circuit Reset."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request

from orcia_api.dependencies import get_connector_quota_guard_service
from orcia_api.routers._finops_auth_guards import (
    enforce_scope_level_mutation,
    resolve_finops_read_scope,
    validate_uuid,
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
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.errors import ValidationDomainError

router = APIRouter(tags=["finops"])

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
QuotaGuardDep = Annotated[SqlConnectorQuotaGuardService, Depends(get_connector_quota_guard_service)]


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
    request: Request,
    user: CurrentUserDep,
    svc: QuotaGuardDep,
    scope_type: Annotated[
        ScopeType, Query(description="Scope filter: GLOBAL, BU, TEAM, WORKSPACE")
    ] = "GLOBAL",
    scope_id: Annotated[str | None, Query(description="Target scope UUID")] = None,
) -> RemoteServicesListResponse:
    if scope_id is not None:
        validate_uuid(scope_id, "scope_id")
    allowed_ws = await resolve_finops_read_scope(request, user, scope_type, scope_id)
    records = await svc.list_remote_services(
        scope_type=scope_type,
        scope_id=scope_id,
        allowed_workspace_ids=allowed_ws,
    )

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
        validate_uuid(payload.scope_id, "scope_id")
    await enforce_scope_level_mutation(
        request,
        user,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
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
        validate_uuid(req.scope_id, "scope_id")

    clean_key = connector_key.strip().lower()
    if not clean_key:
        raise ValidationDomainError(detail_override="connector_key must not be empty.")

    existing = await svc.get_connector_quota(clean_key)
    if existing is not None:
        await enforce_scope_level_mutation(
            request,
            user,
            scope_type=existing.scope_type,
            scope_id=existing.scope_id,
        )
    elif req.scope_id is not None:
        await enforce_scope_level_mutation(
            request,
            user,
            scope_type="WORKSPACE",
            scope_id=req.scope_id,
        )
    else:
        await enforce_scope_level_mutation(
            request,
            user,
            scope_type="GLOBAL",
            scope_id=None,
        )

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
