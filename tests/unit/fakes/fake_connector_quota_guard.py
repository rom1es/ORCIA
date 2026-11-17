"""In-memory fake `ConnectorQuotaGuardPort` strictly confined to unit tests (`AD-19`)."""

from __future__ import annotations

from dataclasses import dataclass, field

from orcia_core.ports.finops_telemetry import (
    CircuitBreakerDecision,
    CircuitBreakerState,
    ConnectorQuotaGuardPort,
    SanitizedRemoteUsage,
)


@dataclass
class FakeQuotaState:
    max_daily_calls: int | None = None
    max_monthly_cost_eur: float | None = None
    daily_calls_count: int = 0
    monthly_cost_eur: float = 0.0
    circuit_state: CircuitBreakerState = "CLOSED"
    recorded_usages: list[SanitizedRemoteUsage] = field(default_factory=list)


class FakeConnectorQuotaGuard(ConnectorQuotaGuardPort):
    """Test-only fake implementing `ConnectorQuotaGuardPort` for isolation unit tests."""

    def __init__(self) -> None:
        self.states: dict[str, FakeQuotaState] = {}

    def configure(
        self,
        connector_id: str,
        *,
        max_daily_calls: int | None = None,
        max_monthly_cost_eur: float | None = None,
        circuit_state: CircuitBreakerState = "CLOSED",
    ) -> None:
        self.states[connector_id.strip().lower()] = FakeQuotaState(
            max_daily_calls=max_daily_calls,
            max_monthly_cost_eur=max_monthly_cost_eur,
            circuit_state=circuit_state,
        )

    async def evaluate_call_allowed(
        self,
        connector_id: str,
        scope_type: str = "GLOBAL",
        scope_id: str | None = None,
    ) -> CircuitBreakerDecision:
        _ = (scope_type, scope_id)
        key = connector_id.strip().lower()
        st = self.states.get(key)
        if st is None:
            return CircuitBreakerDecision(
                is_allowed=True,
                circuit_state="CLOSED",
                reason="No configured quota limit.",
            )
        if st.circuit_state == "CIRCUIT_OPEN":
            return CircuitBreakerDecision(
                is_allowed=False,
                circuit_state="CIRCUIT_OPEN",
                reason=f"Circuit open for connector '{key}'.",
            )
        if st.max_daily_calls is not None and st.daily_calls_count >= st.max_daily_calls:
            st.circuit_state = "CIRCUIT_OPEN"
            return CircuitBreakerDecision(
                is_allowed=False,
                circuit_state="CIRCUIT_OPEN",
                reason=f"Daily call quota reached for '{key}'.",
            )
        if st.max_monthly_cost_eur is not None and st.monthly_cost_eur >= st.max_monthly_cost_eur:
            st.circuit_state = "CIRCUIT_OPEN"
            return CircuitBreakerDecision(
                is_allowed=False,
                circuit_state="CIRCUIT_OPEN",
                reason=f"Monthly cost quota reached for '{key}'.",
            )
        return CircuitBreakerDecision(
            is_allowed=True,
            circuit_state=st.circuit_state,
            reason="Within connector quota.",
        )

    async def record_call_usage(
        self,
        connector_id: str,
        usage: SanitizedRemoteUsage,
        *,
        latency_ms: int = 0,
    ) -> None:
        _ = latency_ms
        key = connector_id.strip().lower()
        st = self.states.setdefault(key, FakeQuotaState())
        st.daily_calls_count += 1
        st.monthly_cost_eur += usage.cost_eur
        st.recorded_usages.append(usage)
        if st.max_daily_calls is not None and st.daily_calls_count >= st.max_daily_calls:
            st.circuit_state = "CIRCUIT_OPEN"
        if st.max_monthly_cost_eur is not None and st.monthly_cost_eur >= st.max_monthly_cost_eur:
            st.circuit_state = "CIRCUIT_OPEN"
