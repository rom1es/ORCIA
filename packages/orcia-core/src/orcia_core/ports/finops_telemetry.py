"""Hexagonal telemetry, audit and finops ports (`AD-12`, `AD-19`, `Story 6.1`, `Story 6.4`).

Pure hexagonal contracts — zero framework dependencies, zero cross-domain cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

ValuationMode = Literal["NATIVE_TELEMETRY", "FIXED_SCALE", "VOLUMETRIC_ONLY"]
CircuitBreakerState = Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]
CostSource = Literal["INTERNAL_VERIFIED", "EXTERNAL_REPORTED", "ESTIMATED_SCALE"]


@dataclass(frozen=True, slots=True)
class RemoteUsageRawPayload:
    """Raw telemetry payload extracted from MCP _meta.usage or X-Orcia-Usage header."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_amount: float | None = None
    currency: str | None = None
    unit_count: float | None = None
    unit_name: str | None = None
    model_name: str | None = None
    raw_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SanitizedRemoteUsage:
    """Sanitized, currency-normalized and bounded telemetry record."""

    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_eur: float
    cost_source: CostSource
    native_metric_type: str | None
    native_metric_value: float | None
    native_currency: str | None
    reported_by_remote: bool
    is_anomaly_capped: bool
    original_reported_cost_eur: float | None = None


@dataclass(frozen=True, slots=True)
class FinopsCostLedgerEntry:
    """Immutable accounting entry ready for audit_ledger insertion."""

    source_event_id: str
    actor_type: str
    actor_id: str
    event_type: str
    summary: str
    trace_id: str
    id: str | None = None
    workspace_id: str | None = None
    org_unit_id: str | None = None
    scope_path: str = "GLOBAL"
    run_id: str | None = None
    root_run_id: str | None = None
    step_execution_id: str | None = None
    actor_display_name: str | None = None
    actor_email: str | None = None
    model_id: str | None = None
    inference_tier: str | None = None
    effort: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_source: CostSource = "INTERNAL_VERIFIED"
    native_metric_type: str | None = None
    native_metric_value: float | None = None
    native_currency: str | None = None
    reported_by_remote: bool = False
    latency_ms: int = 0
    run_lock_sha256: str | None = None
    pre_prompt_sha256: str | None = None
    workflow_contract_sha256: str | None = None
    cas_references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class CircuitBreakerDecision:
    """Evaluation result of a connector or workflow budget circuit breaker."""

    is_allowed: bool
    circuit_state: CircuitBreakerState
    reason: str
    remaining_budget_usd: float | None = None
    current_burn_usd: float | None = None


@runtime_checkable
class RemoteUsageSanitizerPort(Protocol):
    """Port for sanitizing external MCP and A2A consumption telemetry."""

    def sanitize(
        self,
        raw: RemoteUsageRawPayload,
        *,
        valuation_mode: ValuationMode,
        fixed_cost_per_call_eur: float,
        fixed_cost_per_unit_eur: float,
        max_reported_cost_per_call_eur: float,
    ) -> SanitizedRemoteUsage: ...


@runtime_checkable
class ConnectorQuotaGuardPort(Protocol):
    """Port for checking and updating isolated connector quotas."""

    async def evaluate_call_allowed(
        self,
        connector_id: str,
        scope_type: str,
        scope_id: str | None,
    ) -> CircuitBreakerDecision: ...

    async def record_call_usage(
        self,
        connector_id: str,
        usage: SanitizedRemoteUsage,
        *,
        latency_ms: int = 0,
    ) -> None: ...


@runtime_checkable
class BudgetCircuitGuardPort(Protocol):
    """Port for evaluating hierarchical workflow run and scope budgets."""

    async def evaluate_budget_allowance(
        self,
        run_id: str,
        estimated_step_cost_usd: float,
    ) -> CircuitBreakerDecision: ...


@runtime_checkable
class AuditLedgerSinkPort(Protocol):
    """Port for recording immutable provenance entries."""

    async def record_entry(self, entry: FinopsCostLedgerEntry) -> str: ...
