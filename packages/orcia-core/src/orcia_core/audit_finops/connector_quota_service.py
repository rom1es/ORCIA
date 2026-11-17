"""Connector quota & isolated circuit breaker service (`Story 6.4`, `AD-12`, `AD-19`).

Implements `ConnectorQuotaGuardPort` backed by PostgreSQL 18 (`finops_connector_quotas`).
Opening a circuit breaker on one external connector never impacts other connectors or
internal LLM models.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal.sql_connector_quotas import (
    fetch_connector_quota_sql,
    list_connector_quotas_sql,
    record_connector_usage_sql,
    reset_connector_circuit_sql,
    trip_connector_circuit_sql,
    upsert_connector_quota_config_sql,
)
from orcia_core.audit_finops.finops_models import (
    DEFAULT_EUR_USD_RATE,
    ConnectorQuotaRecord,
    ScopeType,
)
from orcia_core.kernel._finops_audit_events import ConnectorCircuitTripped
from orcia_core.ports.finops_telemetry import (
    CircuitBreakerDecision,
    CircuitBreakerState,
    ConnectorQuotaGuardPort,
    SanitizedRemoteUsage,
    ValuationMode,
)
from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError


class SqlConnectorQuotaGuardService(ConnectorQuotaGuardPort):
    """PostgreSQL 18 isolated per-connector quota & circuit breaker guard."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None = None,
        eur_usd_rate: Decimal = DEFAULT_EUR_USD_RATE,
        anomaly_trip_threshold: int = 3,
        outbox_collector: list[Any] | None = None,
    ) -> None:
        self._engine = engine
        self._eur_usd_rate = eur_usd_rate
        self._anomaly_trip_threshold = max(1, anomaly_trip_threshold)
        self._outbox_collector: list[Any] = outbox_collector if outbox_collector is not None else []

    @property
    def collected_outbox_events(self) -> list[Any]:
        return self._outbox_collector

    async def evaluate_call_allowed(
        self,
        connector_id: str,
        scope_type: str = "GLOBAL",
        scope_id: str | None = None,
    ) -> CircuitBreakerDecision:
        if self._engine is None:
            return CircuitBreakerDecision(
                is_allowed=True,
                circuit_state="CLOSED",
                reason="Database engine unavailable; connector call permitted.",
            )
        key = connector_id.strip().lower()
        rec = await fetch_connector_quota_sql(self._engine, key)
        if rec is None:
            return CircuitBreakerDecision(
                is_allowed=True,
                circuit_state="CLOSED",
                reason="Connector has no configured quota restriction.",
            )

        remaining_usd: float | None = None
        if rec.max_monthly_cost_eur is not None:
            ceiling_usd = rec.max_monthly_cost_eur / self._eur_usd_rate
            remaining_usd = float(max(Decimal("0.000000"), ceiling_usd - rec.monthly_cost_usd))

        if rec.circuit_state == "CIRCUIT_OPEN":
            return CircuitBreakerDecision(
                is_allowed=False,
                circuit_state="CIRCUIT_OPEN",
                reason=rec.last_tripped_reason or f"Connector '{key}' circuit breaker is open.",
                remaining_budget_usd=remaining_usd,
                current_burn_usd=float(rec.monthly_cost_usd),
            )

        trip_reason: str | None = None
        if rec.max_daily_calls is not None and rec.daily_calls_count >= rec.max_daily_calls:
            trip_reason = (
                f"Daily call ceiling reached on '{key}' "
                f"({rec.daily_calls_count}/{rec.max_daily_calls})."
            )
        elif (
            rec.max_monthly_cost_eur is not None
            and rec.monthly_cost_eur >= rec.max_monthly_cost_eur
        ):
            trip_reason = (
                f"Monthly cost ceiling reached on '{key}' "
                f"({rec.monthly_cost_eur} EUR / {rec.max_monthly_cost_eur} EUR)."
            )

        if trip_reason is not None:
            evt = ConnectorCircuitTripped.create(
                connector_id=key,
                circuit_state="CIRCUIT_OPEN",
                reason=trip_reason,
                workspace_id=scope_id if scope_type == "WORKSPACE" else None,
            )
            self._outbox_collector.append(evt)
            await trip_connector_circuit_sql(
                self._engine,
                connector_key=key,
                reason=trip_reason,
                event=evt,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            return CircuitBreakerDecision(
                is_allowed=False,
                circuit_state="CIRCUIT_OPEN",
                reason=trip_reason,
                remaining_budget_usd=0.0,
                current_burn_usd=float(rec.monthly_cost_usd),
            )

        return CircuitBreakerDecision(
            is_allowed=True,
            circuit_state=rec.circuit_state,
            reason="Connector quota verified within ceilings.",
            remaining_budget_usd=remaining_usd,
            current_burn_usd=float(rec.monthly_cost_usd),
        )

    async def record_call_usage(
        self,
        connector_id: str,
        usage: SanitizedRemoteUsage,
        *,
        latency_ms: int = 0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> None:
        if self._engine is None:
            return
        key = connector_id.strip().lower()
        await record_connector_usage_sql(
            self._engine,
            connector_key=key,
            usage=usage,
            latency_ms=latency_ms,
            anomaly_trip_threshold=self._anomaly_trip_threshold,
            eur_usd_rate=self._eur_usd_rate,
            trace_id=trace_id,
        )

    async def list_remote_services(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
    ) -> list[ConnectorQuotaRecord]:
        if self._engine is None:
            return []
        return await list_connector_quotas_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
        )

    async def update_connector_quota(
        self,
        *,
        connector_key: str,
        display_name: str | None = None,
        service_kind: str | None = None,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
        valuation_mode: ValuationMode = "NATIVE_TELEMETRY",
        max_reported_cost_per_call_eur: Decimal = Decimal("5.000000"),
        fixed_cost_per_call_eur: Decimal = Decimal("0.000000"),
        unit_tariff_eur: Decimal = Decimal("0.000000"),
        default_unit_name: str | None = None,
        max_daily_calls: int | None = None,
        max_monthly_cost_eur: Decimal | None = None,
    ) -> ConnectorQuotaRecord:
        key = connector_key.strip().lower()
        if not key:
            raise ValidationDomainError(detail_override="connector_key must not be empty.")
        if self._engine is None:
            raise ValidationDomainError(
                detail_override="PostgreSQL database engine is required for connector quotas."
            )
        return await upsert_connector_quota_config_sql(
            self._engine,
            connector_key=key,
            display_name=display_name,
            service_kind=service_kind,
            scope_type=scope_type,
            scope_id=scope_id,
            valuation_mode=valuation_mode,
            max_reported_cost_per_call_eur=max_reported_cost_per_call_eur,
            fixed_cost_per_call_eur=fixed_cost_per_call_eur,
            unit_tariff_eur=unit_tariff_eur,
            default_unit_name=default_unit_name,
            max_daily_calls=max_daily_calls,
            max_monthly_cost_eur=max_monthly_cost_eur,
        )

    async def reset_circuit(
        self,
        *,
        connector_key: str,
        target_state: CircuitBreakerState = "CLOSED",
        actor_id: str = "system",
        trace_id: str = "00000000000000000000000000000000",
    ) -> ConnectorQuotaRecord:
        key = connector_key.strip().lower()
        if self._engine is None:
            raise ResourceNotFoundError(
                detail_override=f"Connecteur distant '{key}' introuvable dans le registre FinOps."
            )
        rec = await reset_connector_circuit_sql(
            self._engine,
            connector_key=key,
            target_state=target_state,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        if rec is None:
            raise ResourceNotFoundError(
                detail_override=f"Connecteur distant '{key}' introuvable dans le registre FinOps."
            )
        return rec


__all__ = [
    "SqlConnectorQuotaGuardService",
]
