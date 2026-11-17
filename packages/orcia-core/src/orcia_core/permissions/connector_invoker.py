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
from orcia_core.permissions.errors import ConnectorCircuitOpenError
from orcia_core.ports.finops_telemetry import (
    ConnectorQuotaGuardPort,
    RemoteUsageSanitizerPort,
    ValuationMode,
)
from orcia_kernel.errors import (
    FunctionalConnectorError,
    OrciaDomainError,
    PermanentInfraError,
    PolicyDeniedError,
    RateLimitedError,
    TransientInfraError,
    UpstreamTimeoutError,
    ValidationDomainError,
)
from orcia_kernel.ports import (
    ConnectorInvokeResult,
    ConnectorPort,
    get_registered_connector,
)


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

    def _run_connector_loop(
        self,
        *,
        norm_scheme: str,
        action: str,
        payload: dict[str, Any],
        idempotency_key: str,
        max_agent_retries: int,
        max_cost_usd: float,
        accumulated_cost_usd: float,
        resolved_connector: ConnectorPort,
    ) -> ConnectorInvocationOutcome:
        sanitized_in = scrub_connector_secrets(payload)
        breaker = self.get_breaker(norm_scheme)
        if not breaker.allow_request(self._clock()):
            raise PermanentInfraError(
                detail_override=(
                    f"Disjoncteur OPEN pour le connecteur '{norm_scheme}' "
                    f"({breaker.consecutive_failures} échecs consécutifs)."
                )
            )
        max_attempts, attempts, total_wait, spent_usd = max(1, max_agent_retries), 0, 0.0, 0.0
        while attempts < max_attempts:
            next_cost = accumulated_cost_usd + spent_usd + self.cost_per_attempt_usd
            if next_cost > max_cost_usd:
                raise ValidationDomainError(
                    detail_override=(
                        f"Plafond budgétaire dépassé sur '{norm_scheme}.{action}': "
                        f"{next_cost:.2f} USD > {max_cost_usd:.2f} USD."
                    )
                )
            attempts += 1
            spent_usd = round(spent_usd + self.cost_per_attempt_usd, 4)
            try:
                res: ConnectorInvokeResult = resolved_connector.invoke(
                    action, payload, idempotency_key
                )
                breaker.record_success()
                self._audit_dedup_keys.add(idempotency_key)
                self._outbox_dedup_keys.add(idempotency_key)
                return ConnectorInvocationOutcome(
                    scheme=norm_scheme,
                    action=action,
                    idempotency_key=idempotency_key,
                    status="SUCCEEDED",
                    attempts_used=attempts,
                    total_wait_seconds=round(total_wait, 4),
                    total_cost_usd=spent_usd,
                    circuit_state=breaker.current_state(self._clock()),
                    sanitized_input=sanitized_in,
                    sanitized_output=scrub_connector_secrets(dict(res.output)),
                )
            except Exception as raw_exc:
                mapped: OrciaDomainError = (
                    raw_exc
                    if isinstance(raw_exc, OrciaDomainError)
                    else resolved_connector.map_error(raw_exc)
                )
                if isinstance(
                    mapped,
                    (FunctionalConnectorError, PolicyDeniedError, ValidationDomainError),
                ):
                    self._audit_dedup_keys.add(idempotency_key)
                    return ConnectorInvocationOutcome(
                        scheme=norm_scheme,
                        action=action,
                        idempotency_key=idempotency_key,
                        status="WAITING_FOR_HUMAN_ARBITRATION",
                        attempts_used=attempts,
                        total_wait_seconds=round(total_wait, 4),
                        total_cost_usd=spent_usd,
                        circuit_state=breaker.current_state(self._clock()),
                        sanitized_input=sanitized_in,
                        error_code=mapped.error_code,
                        error_detail=str(mapped),
                    )
                new_state = breaker.record_failure(self._clock())
                if isinstance(mapped, PermanentInfraError) or new_state == "OPEN":
                    self._audit_dedup_keys.add(idempotency_key)
                    return ConnectorInvocationOutcome(
                        scheme=norm_scheme,
                        action=action,
                        idempotency_key=idempotency_key,
                        status=(
                            "PAUSED_CIRCUIT_BREAKER"
                            if new_state == "OPEN"
                            else "WAITING_FOR_HUMAN_ARBITRATION"
                        ),
                        attempts_used=attempts,
                        total_wait_seconds=round(total_wait, 4),
                        total_cost_usd=spent_usd,
                        circuit_state=new_state,
                        sanitized_input=sanitized_in,
                        error_code=mapped.error_code,
                        error_detail=str(mapped),
                    )
                if attempts >= max_attempts:
                    self._audit_dedup_keys.add(idempotency_key)
                    return ConnectorInvocationOutcome(
                        scheme=norm_scheme,
                        action=action,
                        idempotency_key=idempotency_key,
                        status="WAITING_FOR_HUMAN_ARBITRATION",
                        attempts_used=attempts,
                        total_wait_seconds=round(total_wait, 4),
                        total_cost_usd=spent_usd,
                        circuit_state=new_state,
                        sanitized_input=sanitized_in,
                        error_code=mapped.error_code,
                        error_detail=str(mapped),
                    )
                wait_s = (
                    mapped.retry_after_s
                    if isinstance(
                        mapped, (TransientInfraError, RateLimitedError, UpstreamTimeoutError)
                    )
                    and mapped.retry_after_s > 0.0
                    else 0.05 * (2 ** (attempts - 1))
                )
                self._sleep(wait_s)
                total_wait += wait_s
        raise RuntimeError("Unreachable loop exit in ConnectorInvoker.invoke")

    def _resolve_connector(self, scheme: str, connector: ConnectorPort | None) -> ConnectorPort:
        norm_scheme = scheme.strip().lower()
        resolved = connector or get_registered_connector(norm_scheme)
        if resolved is None:
            raise ValidationDomainError(
                detail_override=f"Connecteur '{norm_scheme}' non enregistré dans orcia.connectors."
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
        return self._run_connector_loop(
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
        outcome = self._run_connector_loop(
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
