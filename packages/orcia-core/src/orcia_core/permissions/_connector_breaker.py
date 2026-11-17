"""Connector circuit breaker state machine & invocation outcome (`Story 3.2f`, `Story 6.4`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.ports.finops_telemetry import RemoteUsageRawPayload

CircuitBreakerState = Literal["CLOSED", "OPEN", "HALF_OPEN"]


def extract_raw_usage_from_output(output: dict[str, Any]) -> RemoteUsageRawPayload:
    """Extract raw usage telemetry from `_meta.usage`, `usage`, or `X-Orcia-Usage` dict."""
    usage_dict: dict[str, Any] = {}
    meta = output.get("_meta")
    if isinstance(meta, dict) and isinstance(meta.get("usage"), dict):
        usage_dict = dict(meta["usage"])
    elif isinstance(output.get("usage"), dict):
        usage_dict = dict(output["usage"])
    elif isinstance(output.get("x_orcia_usage"), dict):
        usage_dict = dict(output["x_orcia_usage"])

    if not usage_dict:
        return RemoteUsageRawPayload()

    def _opt_int(key: str, alt: str | None = None) -> int | None:
        val = usage_dict.get(key, usage_dict.get(alt) if alt else None)
        if val is None or isinstance(val, bool):
            return None
        return int(val)

    def _opt_float(keys: tuple[str, ...]) -> float | None:
        for k in keys:
            val = usage_dict.get(k)
            if val is not None and not isinstance(val, bool):
                return float(val)
        return None

    return RemoteUsageRawPayload(
        input_tokens=_opt_int("input_tokens", "prompt_tokens"),
        output_tokens=_opt_int("output_tokens", "completion_tokens"),
        cost_amount=_opt_float(("cost_amount", "cost", "cost_eur", "cost_usd")),
        currency=str(usage_dict["currency"]) if usage_dict.get("currency") is not None else None,
        unit_count=_opt_float(("unit_count", "units")),
        unit_name=str(usage_dict["unit_name"]) if usage_dict.get("unit_name") is not None else None,
        model_name=(
            str(usage_dict["model_name"]) if usage_dict.get("model_name") is not None else None
        ),
        raw_metadata=usage_dict,
    )


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


__all__ = [
    "CircuitBreakerState",
    "ConnectorCircuitBreaker",
    "ConnectorInvocationOutcome",
    "extract_raw_usage_from_output",
]
