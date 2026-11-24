"""Pre-loop guards & outcome builders for `ConnectorInvoker` retry loops."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from orcia_core.observability.logging import scrub_sensitive_dict
from orcia_core.permissions._connector_breaker import (
    ConnectorCircuitBreaker,
    ConnectorInvocationOutcome,
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
from orcia_kernel.ports import ConnectorInvokeResult, ConnectorPort


def outcome_on_error(
    *,
    raw_exc: Exception,
    resolved_connector: ConnectorPort,
    breaker: ConnectorCircuitBreaker,
    clock: Callable[[], float],
    audit_dedup_keys: set[str],
    norm_scheme: str,
    action: str,
    idempotency_key: str,
    attempts: int,
    max_attempts: int,
    total_wait: float,
    spent_usd: float,
    sanitized_in: dict[str, Any],
) -> tuple[ConnectorInvocationOutcome | None, float]:
    """Map an invocation exception into a terminal outcome or a backoff delay."""
    mapped: OrciaDomainError = (
        raw_exc if isinstance(raw_exc, OrciaDomainError) else resolved_connector.map_error(raw_exc)
    )
    if isinstance(mapped, (FunctionalConnectorError, PolicyDeniedError, ValidationDomainError)):
        audit_dedup_keys.add(idempotency_key)
        return (
            ConnectorInvocationOutcome(
                scheme=norm_scheme,
                action=action,
                idempotency_key=idempotency_key,
                status="WAITING_FOR_HUMAN_ARBITRATION",
                attempts_used=attempts,
                total_wait_seconds=round(total_wait, 4),
                total_cost_usd=spent_usd,
                circuit_state=breaker.current_state(clock()),
                sanitized_input=sanitized_in,
                error_code=mapped.error_code,
                error_detail=str(mapped),
            ),
            0.0,
        )
    new_state = breaker.record_failure(clock())
    if isinstance(mapped, PermanentInfraError) or new_state == "OPEN":
        audit_dedup_keys.add(idempotency_key)
        return (
            ConnectorInvocationOutcome(
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
            ),
            0.0,
        )
    if attempts >= max_attempts:
        audit_dedup_keys.add(idempotency_key)
        return (
            ConnectorInvocationOutcome(
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
            ),
            0.0,
        )
    wait_s = (
        mapped.retry_after_s
        if isinstance(mapped, (TransientInfraError, RateLimitedError, UpstreamTimeoutError))
        and mapped.retry_after_s > 0.0
        else 0.05 * (2 ** (attempts - 1))
    )
    return None, wait_s


def validate_preloop(
    *,
    breaker: ConnectorCircuitBreaker,
    clock: Callable[[], float],
    norm_scheme: str,
) -> None:
    if not breaker.allow_request(clock()):
        raise PermanentInfraError(
            detail_code="ERR_CONNECTOR_BREAKER_OPEN",
            detail_params={"scheme": norm_scheme, "failures": breaker.consecutive_failures},
        )


def check_budget_ceiling(
    *,
    accumulated_cost_usd: float,
    spent_usd: float,
    cost_per_attempt_usd: float,
    max_cost_usd: float,
    norm_scheme: str,
    action: str,
) -> None:
    next_cost = accumulated_cost_usd + spent_usd + cost_per_attempt_usd
    if next_cost > max_cost_usd:
        params = {
            "scheme": norm_scheme,
            "action": action,
            "next_cost": f"{next_cost:.2f}",
            "max_cost": f"{max_cost_usd:.2f}",
        }
        raise ValidationDomainError(
            detail_code="ERR_CONNECTOR_BUDGET_EXCEEDED", detail_params=params
        )


def build_succeeded_outcome(
    *,
    breaker: ConnectorCircuitBreaker,
    clock: Callable[[], float],
    audit_dedup_keys: set[str],
    outbox_dedup_keys: set[str],
    norm_scheme: str,
    action: str,
    idempotency_key: str,
    attempts: int,
    total_wait: float,
    spent_usd: float,
    sanitized_in: dict[str, Any],
    res: ConnectorInvokeResult,
) -> ConnectorInvocationOutcome:
    breaker.record_success()
    audit_dedup_keys.add(idempotency_key)
    outbox_dedup_keys.add(idempotency_key)
    return ConnectorInvocationOutcome(
        scheme=norm_scheme,
        action=action,
        idempotency_key=idempotency_key,
        status="SUCCEEDED",
        attempts_used=attempts,
        total_wait_seconds=round(total_wait, 4),
        total_cost_usd=spent_usd,
        circuit_state=breaker.current_state(clock()),
        sanitized_input=sanitized_in,
        sanitized_output=scrub_sensitive_dict(dict(res.output)),
    )
