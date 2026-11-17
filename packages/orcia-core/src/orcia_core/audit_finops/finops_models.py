"""Pure domain models for FinOps accounting, baselines, and budget guards (`Story 6.2`).

Strict Decimal representation for all monetary attributes (`AD-12`, `AD-19`, `AD-21`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from orcia_core.ports.finops_telemetry import CircuitBreakerState, ValuationMode

ScopeType = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
DEFAULT_HOURLY_RATE_USD = Decimal("75.000000")
DEFAULT_EUR_USD_RATE = Decimal("0.920000")
DEFAULT_AMORTIZATION_RUNS = Decimal("100")


@dataclass(frozen=True, slots=True)
class FinopsScopeBudget:
    """Configured monthly budget ceiling and thresholds for a scope (`Story 6.2`)."""

    id: str
    scope_type: ScopeType
    scope_id: str | None
    monthly_budget_usd: Decimal
    warning_threshold_pct: int = 80
    hard_stop_pct: int = 100
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FinopsWorkflowBaseline:
    """Manual baseline used to measure cost and TTM reduction (`SM-1`, `Story 6.2`)."""

    id: str
    workflow_definition_id: str
    scope_id: str | None
    manual_time_minutes: int
    manual_cost_usd: Decimal
    target_ttm_reduction_pct: int = 25
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FinopsBudgetOverride:
    """Immutable audit record of human budget extension for a paused run (`Story 6.2`)."""

    id: str
    run_id: str
    requested_by: str
    approved_by: str
    override_amount_usd: Decimal
    reason: str
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FinopsProcessItem:
    """Consolidated accounting metrics for a specific workflow definition."""

    workflow_id: str
    workflow_title: str
    runs_count: int
    amortized_setup_cost_usd: Decimal
    amortized_setup_cost_eur: Decimal
    run_cost_usd: Decimal
    run_cost_eur: Decimal
    human_time_cost_usd: Decimal
    human_time_cost_eur: Decimal
    total_cost_usd: Decimal
    total_cost_eur: Decimal
    baseline_manual_cost_usd: Decimal
    baseline_manual_cost_eur: Decimal
    ttm_reduction_pct: Decimal
    active_budget_override: bool = False
    paused_runs_count: int = 0


@dataclass(frozen=True, slots=True)
class FinopsTierEffortItem:
    """Cost and token breakdown per cognitive inference tier and effort level."""

    inference_tier: str
    effort: str
    invocations_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    cost_eur: Decimal
    escalated_from_auto_count: int = 0


@dataclass(frozen=True, slots=True)
class FinopsOverview:
    """Top-level FinOps dashboard KPI summary."""

    total_cost_usd: Decimal
    total_cost_eur: Decimal
    verified_internal_cost_usd: Decimal
    verified_internal_cost_eur: Decimal
    reported_external_cost_usd: Decimal
    reported_external_cost_eur: Decimal
    total_llm_tokens: int
    internal_tokens: int
    remote_tokens: int
    total_external_calls: int
    external_units_breakdown: dict[str, float] = field(default_factory=dict)
    cache_savings_usd: Decimal = field(default_factory=lambda: Decimal("0.000000"))
    cache_savings_eur: Decimal = field(default_factory=lambda: Decimal("0.000000"))
    active_circuit_breakers_count: int = 0
    paused_runs_count: int = 0
    accounted_runs_count: int = 0


@dataclass(frozen=True, slots=True)
class FinopsBreakdown:
    """Complete consolidated FinOps dashboard data with process and tier breakdowns."""

    overview: FinopsOverview
    processes: list[FinopsProcessItem] = field(default_factory=list)
    tiers: list[FinopsTierEffortItem] = field(default_factory=list)
    scope_budgets: list[FinopsScopeBudget] = field(default_factory=list)
    baselines: list[FinopsWorkflowBaseline] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConnectorQuotaRecord:
    """Configured quota, valuation mode, consumption & circuit state for a remote connector."""

    id: str
    connector_key: str
    display_name: str
    service_kind: str
    scope_type: ScopeType
    scope_id: str | None
    valuation_mode: ValuationMode
    max_reported_cost_per_call_eur: Decimal
    fixed_cost_per_call_eur: Decimal
    unit_tariff_eur: Decimal
    default_unit_name: str | None
    max_daily_calls: int | None
    max_monthly_cost_eur: Decimal | None
    daily_calls_count: int
    monthly_cost_usd: Decimal
    monthly_cost_eur: Decimal
    total_remote_tokens: int
    total_business_units: Decimal
    circuit_state: CircuitBreakerState
    anomaly_count: int
    consecutive_anomalies: int
    last_latency_ms: int
    last_tripped_reason: str | None = None
    last_tripped_at: datetime | None = None
    last_invoked_at: datetime | None = None
    quota_used_pct: Decimal = field(default_factory=lambda: Decimal("0.00"))


__all__ = [
    "ConnectorQuotaRecord",
    "DEFAULT_AMORTIZATION_RUNS",
    "DEFAULT_EUR_USD_RATE",
    "DEFAULT_HOURLY_RATE_USD",
    "FinopsBreakdown",
    "FinopsBudgetOverride",
    "FinopsOverview",
    "FinopsProcessItem",
    "FinopsScopeBudget",
    "FinopsTierEffortItem",
    "FinopsWorkflowBaseline",
    "ScopeType",
]
