"""FastAPI transport Pydantic v2 schemas for Story 6.4 Remote MCP & A2A Telemetry."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ScopeType = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
ValuationModeLiteral = Literal["NATIVE_TELEMETRY", "FIXED_SCALE", "VOLUMETRIC_ONLY"]
CircuitBreakerStateLiteral = Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]


class RemoteServiceTelemetryItemResponse(BaseModel):
    """Consolidated FinOps telemetry, quota and circuit breaker state for a remote service."""

    connector_key: str = Field(..., description="Unique connector or remote service identifier")
    display_name: str = Field(..., description="Display name of the external service or agent")
    service_kind: str = Field(..., description="Service kind (MCP_SERVER, A2A_AGENT, etc.)")
    scope_type: ScopeType = Field(..., description="Configured scope level")
    scope_id: str | None = Field(default=None, description="Target scope UUID or None")
    valuation_mode: ValuationModeLiteral = Field(
        ..., description="Cost valuation mode (NATIVE_TELEMETRY, FIXED_SCALE, VOLUMETRIC_ONLY)"
    )
    max_reported_cost_per_call_eur: float = Field(
        ..., description="Safety cap per call in EUR (default 5.00)"
    )
    fixed_cost_per_call_eur: float = Field(..., description="Reference fixed cost per call in EUR")
    unit_tariff_eur: float = Field(..., description="Reference unit tariff in EUR")
    default_unit_name: str | None = Field(
        default=None, description="Business unit name (e.g. pages_ocr)"
    )
    max_daily_calls: int | None = Field(default=None, description="Maximum daily calls ceiling")
    max_monthly_cost_eur: float | None = Field(
        default=None, description="Maximum monthly cost ceiling in EUR"
    )
    daily_calls_count: int = Field(default=0, description="Number of calls recorded today")
    avg_latency_ms: int = Field(default=0, description="Latest or average latency in ms")
    total_remote_tokens: int = Field(default=0, description="Remote LLM tokens reported")
    total_business_units: float = Field(default=0.0, description="Accumulated business units")
    consolidated_cost_usd: float = Field(default=0.0, description="Consolidated cost in USD")
    consolidated_cost_eur: float = Field(default=0.0, description="Consolidated cost in EUR")
    quota_used_pct: float = Field(default=0.0, description="Percentage of configured ceiling used")
    circuit_state: CircuitBreakerStateLiteral = Field(
        default="CLOSED", description="Isolated circuit breaker state"
    )
    anomaly_count: int = Field(default=0, description="Total capped or rejected telemetry alerts")
    last_tripped_reason: str | None = Field(
        default=None, description="Latest circuit open reason if suspended"
    )
    last_invoked_at: datetime | None = Field(
        default=None, description="Timestamp of last invocation"
    )


class RemoteServicesListResponse(BaseModel):
    """Aggregated response for `/api/v1/finops/remote-services`."""

    services: list[RemoteServiceTelemetryItemResponse] = Field(
        default_factory=list, description="Registered remote MCP and A2A connectors"
    )
    total_external_calls: int = Field(default=0, description="Sum of remote service calls")
    total_remote_tokens: int = Field(default=0, description="Sum of remote LLM tokens")
    total_reported_cost_eur: float = Field(
        default=0.0, description="Consolidated external cost in EUR"
    )
    open_circuits_count: int = Field(default=0, description="Count of open connector circuits")
    units_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Totals per distinct business unit name"
    )


class UpdateConnectorQuotaRequest(BaseModel):
    """Request payload to configure quota ceilings and valuation mode for a connector."""

    display_name: str | None = Field(default=None, max_length=160)
    service_kind: str | None = Field(default=None, max_length=32)
    scope_type: ScopeType = Field(default="GLOBAL")
    scope_id: str | None = Field(default=None)
    valuation_mode: ValuationModeLiteral = Field(default="NATIVE_TELEMETRY")
    max_reported_cost_per_call_eur: float = Field(default=5.0, ge=0.0, le=100_000.0)
    fixed_cost_per_call_eur: float = Field(default=0.0, ge=0.0, le=100_000.0)
    unit_tariff_eur: float = Field(default=0.0, ge=0.0, le=100_000.0)
    default_unit_name: str | None = Field(default=None, max_length=64)
    max_daily_calls: int | None = Field(default=None, ge=0, le=10_000_000)
    max_monthly_cost_eur: float | None = Field(default=None, ge=0.0, le=1_000_000.0)


class ResetCircuitBreakerRequest(BaseModel):
    """Request payload to reset a suspended connector circuit breaker."""

    target_state: Literal["CLOSED", "HALF_OPEN"] = Field(default="CLOSED")
    scope_id: str | None = Field(default=None)


class ResetCircuitBreakerResponse(BaseModel):
    """Response returned after resetting a connector circuit breaker."""

    connector_key: str = Field(..., description="Reset connector key")
    circuit_state: CircuitBreakerStateLiteral = Field(..., description="New circuit state")
    anomaly_count: int = Field(..., description="Total historical anomaly count")
    reset_at: datetime = Field(..., description="Timestamp of reset")
    reset_by: str = Field(..., description="Actor user identifier")


__all__ = [
    "CircuitBreakerStateLiteral",
    "RemoteServiceTelemetryItemResponse",
    "RemoteServicesListResponse",
    "ResetCircuitBreakerRequest",
    "ResetCircuitBreakerResponse",
    "UpdateConnectorQuotaRequest",
    "ValuationModeLiteral",
]
