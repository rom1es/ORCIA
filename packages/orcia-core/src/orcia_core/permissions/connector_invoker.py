"""ConnectorInvoker — Durable Connector Execution & Circuit Breaker (`Story 3.2f`, `Story 6.4`).

Placed in `orcia_core.permissions` (Layer 4 of `AD-19 Contract 2`) and re-exported in
`orcia_core.orchestration.connector_invoker` so `orchestration`, `bootstrap` (`LiteLLMAdapter`),
and `gates` (`AgenticGateService`) can all invoke external connectors and LLM gateways
through the same governed retry, isolated FinOps quota guard, and secret-scrubbing pipeline.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from orcia_core.observability.logging import scrub_sensitive_dict
from orcia_core.permissions._connector_breaker import (
    CircuitBreakerState,
    ConnectorCircuitBreaker,
    ConnectorInvocationOutcome,
    extract_raw_usage_from_output,
)
from orcia_core.permissions._connector_invoker_loops import (
    run_async_retry_loop,
    run_sync_retry_loop,
)
from orcia_core.permissions.errors import ConnectorCircuitOpenError
from orcia_core.ports.finops_telemetry import (
    ConnectorQuotaGuardPort,
    RemoteUsageSanitizerPort,
    ValuationMode,
)
from orcia_kernel.errors import ValidationDomainError
from orcia_kernel.ports import ConnectorPort, get_registered_connector


def scrub_connector_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Scrub raw secrets/tokens and registered canaries from connector payloads (`NFR-SEC-4`)."""
    return scrub_sensitive_dict(payload)


class ConnectorInvoker:
    """Governed connector invoker enforcing retry taxonomy, circuit breaker & FinOps quota."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        cost_per_attempt_usd: float = 0.05,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
        quota_guard: ConnectorQuotaGuardPort | None = None,
        usage_sanitizer: RemoteUsageSanitizerPort | None = None,
        scope_type: str = "GLOBAL",
        scope_id: str | None = None,
        valuation_mode: ValuationMode = "NATIVE_TELEMETRY",
        fixed_cost_per_call_eur: float = 0.0,
        fixed_cost_per_unit_eur: float = 0.0,
        max_reported_cost_per_call_eur: float = 5.0,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self.cost_per_attempt_usd = max(0.0, cost_per_attempt_usd)
        self._clock = monotonic_clock
        self._sleep = sleep_fn
        self._quota_guard = quota_guard
        self._usage_sanitizer = usage_sanitizer
        self._scope_type = scope_type
        self._scope_id = scope_id
        self._valuation_mode: ValuationMode = valuation_mode
        self._fixed_cost_per_call_eur = fixed_cost_per_call_eur
        self._fixed_cost_per_unit_eur = fixed_cost_per_unit_eur
        self._max_reported_cost_per_call_eur = max_reported_cost_per_call_eur
        self._breakers: dict[str, ConnectorCircuitBreaker] = {}
        self._audit_dedup_keys: set[str] = set()
        self._outbox_dedup_keys: set[str] = set()

    def get_breaker(self, scheme: str) -> ConnectorCircuitBreaker:
        """Return or initialize the `ConnectorCircuitBreaker` for `scheme`."""
        norm = scheme.strip().lower()
        breaker = self._breakers.get(norm)
        if breaker is None:
            breaker = ConnectorCircuitBreaker(
                scheme=norm,
                failure_threshold=self.failure_threshold,
                cooldown_seconds=self.cooldown_seconds,
            )
            self._breakers[norm] = breaker
        return breaker

    @property
    def recorded_audit_keys(self) -> frozenset[str]:
        return frozenset(self._audit_dedup_keys)

    @property
    def recorded_outbox_keys(self) -> frozenset[str]:
        return frozenset(self._outbox_dedup_keys)

    def _resolve_connector(self, scheme: str, connector: ConnectorPort | None) -> ConnectorPort:
        norm_scheme = scheme.strip().lower()
        resolved = connector or get_registered_connector(norm_scheme)
        if resolved is None:
            raise ValidationDomainError(
                detail_code="ERR_CONNECTOR_NOT_REGISTERED",
                detail_params={"scheme": norm_scheme},
            )
        return resolved

    def invoke(
        self,
        *,
        scheme: str,
        action: str,
        payload: dict[str, Any],
        idempotency_key: str,
        max_agent_retries: int = 3,
        max_cost_usd: float = 10.0,
        accumulated_cost_usd: float = 0.0,
        connector: ConnectorPort | None = None,
    ) -> ConnectorInvocationOutcome:
        """Execute `connector.invoke(action, payload, idempotency_key)` synchronously."""
        norm_scheme = scheme.strip().lower()
        resolved = self._resolve_connector(norm_scheme, connector)
        return run_sync_retry_loop(
            breaker=self.get_breaker(norm_scheme),
            clock=self._clock,
            sleep_fn=self._sleep,
            cost_per_attempt_usd=self.cost_per_attempt_usd,
            audit_dedup_keys=self._audit_dedup_keys,
            outbox_dedup_keys=self._outbox_dedup_keys,
            norm_scheme=norm_scheme,
            action=action,
            payload=payload,
            idempotency_key=idempotency_key,
            max_agent_retries=max_agent_retries,
            max_cost_usd=max_cost_usd,
            accumulated_cost_usd=accumulated_cost_usd,
            resolved_connector=resolved,
        )

    async def invoke_async(
        self,
        *,
        scheme: str,
        action: str,
        payload: dict[str, Any],
        idempotency_key: str,
        max_agent_retries: int = 3,
        max_cost_usd: float = 10.0,
        accumulated_cost_usd: float = 0.0,
        connector: ConnectorPort | None = None,
        connector_key: str | None = None,
        is_internal_llm: bool = False,
    ) -> ConnectorInvocationOutcome:
        """Execute `connector.invoke(...)` guarded by isolated per-connector quota & sanitizer."""
        norm_scheme = scheme.strip().lower()
        resolved = self._resolve_connector(norm_scheme, connector)
        quota_target = (connector_key or norm_scheme).strip().lower()
        is_external = (not is_internal_llm) and norm_scheme != "litellm"

        if is_external and self._quota_guard is not None:
            decision = await self._quota_guard.evaluate_call_allowed(
                quota_target, self._scope_type, self._scope_id
            )
            if not decision.is_allowed or decision.circuit_state == "CIRCUIT_OPEN":
                raise ConnectorCircuitOpenError(detail_override=decision.reason)

        started_ms = self._clock() * 1000.0
        outcome = await run_async_retry_loop(
            breaker=self.get_breaker(norm_scheme),
            clock=self._clock,
            cost_per_attempt_usd=self.cost_per_attempt_usd,
            audit_dedup_keys=self._audit_dedup_keys,
            outbox_dedup_keys=self._outbox_dedup_keys,
            norm_scheme=norm_scheme,
            action=action,
            payload=payload,
            idempotency_key=idempotency_key,
            max_agent_retries=max_agent_retries,
            max_cost_usd=max_cost_usd,
            accumulated_cost_usd=accumulated_cost_usd,
            resolved_connector=resolved,
        )
        elapsed_ms = max(0, int(self._clock() * 1000.0 - started_ms))

        if (
            is_external
            and outcome.status == "SUCCEEDED"
            and self._quota_guard is not None
            and self._usage_sanitizer is not None
        ):
            raw_usage = extract_raw_usage_from_output(outcome.sanitized_output)
            sanitized = self._usage_sanitizer.sanitize(
                raw_usage,
                valuation_mode=self._valuation_mode,
                fixed_cost_per_call_eur=self._fixed_cost_per_call_eur,
                fixed_cost_per_unit_eur=self._fixed_cost_per_unit_eur,
                max_reported_cost_per_call_eur=self._max_reported_cost_per_call_eur,
            )
            await self._quota_guard.record_call_usage(
                quota_target,
                sanitized,
                latency_ms=elapsed_ms,
            )

        return outcome


__all__ = [
    "CircuitBreakerState",
    "ConnectorCircuitBreaker",
    "ConnectorInvocationOutcome",
    "ConnectorInvoker",
    "scrub_connector_secrets",
]
