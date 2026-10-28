"""ConnectorInvoker — Durable Connector Execution, Error Taxonomy & Circuit Breaker (`Story 3.2f`).

Implements `AC-F3` & `AC-F4`:
- Error classification (`TransientInfraError` / `RateLimitedError` / `UpstreamTimeoutError`
  vs non-retryable `FunctionalConnectorError` / `PolicyDeniedError` / `PermanentInfraError`).
- Respect of `retry_after_s` (`HTTP 429 Retry-After`) via injectable sleep / clock.
- Per-connector circuit breaker (`CLOSED` -> `OPEN` after `failure_threshold` -> `HALF_OPEN`
  after `cooldown_seconds` -> `CLOSED` on probe success).
- Identical `idempotency_key` forwarded on every retry (`0` duplicate external effects,
  `0` duplicate `audit_ledger` or `domain_events_outbox` records).
- Each retry attempt counted against `max_agent_retries` and `max_cost_usd` (`AD-12`).
- Secret scrubbing on inputs and outputs (`NFR-SEC-4`: zero raw credentials serialized).
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.orchestration.errors import ValidationDomainError
from orcia_kernel.errors import (
    FunctionalConnectorError,
    OrciaDomainError,
    PermanentInfraError,
    PolicyDeniedError,
    RateLimitedError,
    TransientInfraError,
    UpstreamTimeoutError,
)
from orcia_kernel.ports import (
    ConnectorInvokeResult,
    ConnectorPort,
    get_registered_connector,
)

CircuitBreakerState = Literal["CLOSED", "OPEN", "HALF_OPEN"]

_SECRET_KEY_PATTERN = re.compile(
    r"(secret|token|password|api_key|apikey|authorization|bearer|private_key|vault_ref)",
    re.IGNORECASE,
)
_BEARER_VALUE_PATTERN = re.compile(r"(Bearer\s+[A-Za-z0-9._\-]+|sk-[A-Za-z0-9_\-]{6,})")


def scrub_connector_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Scrub raw secrets/tokens from connector inputs/outputs before persistence (`NFR-SEC-4`)."""
    scrubbed: dict[str, Any] = {}
    for key, val in payload.items():
        if _SECRET_KEY_PATTERN.search(str(key)):
            scrubbed[key] = "[REDACTED_SECRET]"
        elif isinstance(val, dict):
            scrubbed[key] = scrub_connector_secrets(val)
        elif isinstance(val, str) and _BEARER_VALUE_PATTERN.search(val):
            scrubbed[key] = _BEARER_VALUE_PATTERN.sub("[REDACTED_SECRET]", val)
        else:
            scrubbed[key] = val
    return scrubbed


@dataclass(slots=True)
class ConnectorCircuitBreaker:
    """Per-connector state machine (`CLOSED` -> `OPEN` -> `HALF_OPEN`, `AC-F3`, `AC-F4`)."""

    scheme: str
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    _state: CircuitBreakerState = "CLOSED"
    _consecutive_failures: int = 0
    _opened_at_monotonic: float | None = None

    def current_state(self, now_monotonic: float) -> CircuitBreakerState:
        """Evaluate current state, transitioning `OPEN` -> `HALF_OPEN` after cooldown."""
        if (
            self._state == "OPEN"
            and self._opened_at_monotonic is not None
            and (now_monotonic - self._opened_at_monotonic) >= self.cooldown_seconds
        ):
            self._state = "HALF_OPEN"
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def allow_request(self, now_monotonic: float) -> bool:
        """Return True if a call is permitted (`CLOSED` or `HALF_OPEN` probe)."""
        state = self.current_state(now_monotonic)
        return state in ("CLOSED", "HALF_OPEN")

    def record_success(self) -> None:
        """Reset failure counter and close the circuit breaker."""
        self._consecutive_failures = 0
        self._state = "CLOSED"
        self._opened_at_monotonic = None

    def record_failure(self, now_monotonic: float) -> CircuitBreakerState:
        """Increment failure count and trip to `OPEN` when threshold is reached."""
        self._consecutive_failures += 1
        if self._state == "HALF_OPEN" or self._consecutive_failures >= self.failure_threshold:
            self._state = "OPEN"
            self._opened_at_monotonic = now_monotonic
        return self._state


@dataclass(frozen=True, slots=True)
class ConnectorInvocationOutcome:
    """Outcome of a governed `ConnectorInvoker.invoke(...)` execution (`AC-F3`, `AC-F4`)."""

    scheme: str
    action: str
    idempotency_key: str
    status: Literal[
        "SUCCEEDED",
        "WAITING_FOR_HUMAN_ARBITRATION",
        "PAUSED_CIRCUIT_BREAKER",
        "FAILED",
    ]
    attempts_used: int
    total_wait_seconds: float
    total_cost_usd: float
    circuit_state: CircuitBreakerState
    sanitized_input: dict[str, Any]
    sanitized_output: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_detail: str | None = None


class ConnectorInvoker:
    """Governed connector invoker enforcing retry taxonomy, circuit breaker & idempotency."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        cost_per_attempt_usd: float = 0.05,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self.cost_per_attempt_usd = max(0.0, cost_per_attempt_usd)
        self._clock = monotonic_clock
        self._sleep = sleep_fn
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
        """Return deduplicated `idempotency_key` set recorded for audit ledger."""
        return frozenset(self._audit_dedup_keys)

    @property
    def recorded_outbox_keys(self) -> frozenset[str]:
        """Return deduplicated `idempotency_key` set recorded for domain events outbox."""
        return frozenset(self._outbox_dedup_keys)

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
        """Execute `connector.invoke(action, payload, idempotency_key)` with governed retries."""
        norm_scheme = scheme.strip().lower()
        resolved_connector = connector or get_registered_connector(norm_scheme)
        if resolved_connector is None:
            raise ValidationDomainError(
                detail_override=f"Connecteur '{norm_scheme}' non enregistré dans orcia.connectors."
            )

        sanitized_in = scrub_connector_secrets(payload)
        breaker = self.get_breaker(norm_scheme)
        now = self._clock()
        if not breaker.allow_request(now):
            raise PermanentInfraError(
                detail_override=(
                    f"Disjoncteur OPEN pour le connecteur '{norm_scheme}' "
                    f"({breaker.consecutive_failures} échecs consécutifs)."
                )
            )

        max_attempts = max(1, max_agent_retries)
        attempts = 0
        total_wait = 0.0
        spent_usd = 0.0

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

                # Non-retryable functional or policy errors -> 0 retry, escalate to human
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

                # Permanent infrastructure failure -> record breaker failure, 0 retry
                if isinstance(mapped, PermanentInfraError):
                    new_state = breaker.record_failure(self._clock())
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

                # Transient infrastructure / 429 RateLimited / 504 Timeout
                new_state = breaker.record_failure(self._clock())
                if new_state == "OPEN":
                    self._audit_dedup_keys.add(idempotency_key)
                    return ConnectorInvocationOutcome(
                        scheme=norm_scheme,
                        action=action,
                        idempotency_key=idempotency_key,
                        status="PAUSED_CIRCUIT_BREAKER",
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


__all__ = [
    "CircuitBreakerState",
    "ConnectorCircuitBreaker",
    "ConnectorInvocationOutcome",
    "ConnectorInvoker",
    "scrub_connector_secrets",
]
