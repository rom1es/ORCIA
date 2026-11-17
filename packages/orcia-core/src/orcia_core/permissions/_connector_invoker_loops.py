"""Sync and async retry/circuit-breaker execution loops for `ConnectorInvoker`."""

from __future__ import annotations

import asyncio
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
    if isinstance(
        mapped,
        (FunctionalConnectorError, PolicyDeniedError, ValidationDomainError),
    ):
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


def _validate_preloop(
    *,
    breaker: ConnectorCircuitBreaker,
    clock: Callable[[], float],
    norm_scheme: str,
) -> None:
    if not breaker.allow_request(clock()):
        raise PermanentInfraError(
            detail_override=(
                f"Disjoncteur OPEN pour le connecteur '{norm_scheme}' "
                f"({breaker.consecutive_failures} échecs consécutifs)."
            )
        )


def _check_budget_ceiling(
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
        raise ValidationDomainError(
            detail_override=(
                f"Plafond budgétaire dépassé sur '{norm_scheme}.{action}': "
                f"{next_cost:.2f} USD > {max_cost_usd:.2f} USD."
            )
        )


def run_sync_retry_loop(
    *,
    breaker: ConnectorCircuitBreaker,
    clock: Callable[[], float],
    sleep_fn: Callable[[float], None],
    cost_per_attempt_usd: float,
    audit_dedup_keys: set[str],
    outbox_dedup_keys: set[str],
    norm_scheme: str,
    action: str,
    payload: dict[str, Any],
    idempotency_key: str,
    max_agent_retries: int,
    max_cost_usd: float,
    accumulated_cost_usd: float,
    resolved_connector: ConnectorPort,
) -> ConnectorInvocationOutcome:
    """Execute synchronous governed retry loop with circuit breaker & secret scrubbing."""
    sanitized_in = scrub_sensitive_dict(payload)
    _validate_preloop(breaker=breaker, clock=clock, norm_scheme=norm_scheme)
    max_attempts, attempts, total_wait, spent_usd = max(1, max_agent_retries), 0, 0.0, 0.0
    while attempts < max_attempts:
        _check_budget_ceiling(
            accumulated_cost_usd=accumulated_cost_usd,
            spent_usd=spent_usd,
            cost_per_attempt_usd=cost_per_attempt_usd,
            max_cost_usd=max_cost_usd,
            norm_scheme=norm_scheme,
            action=action,
        )
        attempts += 1
        spent_usd = round(spent_usd + cost_per_attempt_usd, 4)
        try:
            res: ConnectorInvokeResult = resolved_connector.invoke(action, payload, idempotency_key)
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
        except Exception as raw_exc:
            outcome, wait_s = outcome_on_error(
                raw_exc=raw_exc,
                resolved_connector=resolved_connector,
                breaker=breaker,
                clock=clock,
                audit_dedup_keys=audit_dedup_keys,
                norm_scheme=norm_scheme,
                action=action,
                idempotency_key=idempotency_key,
                attempts=attempts,
                max_attempts=max_attempts,
                total_wait=total_wait,
                spent_usd=spent_usd,
                sanitized_in=sanitized_in,
            )
            if outcome is not None:
                return outcome
            sleep_fn(wait_s)
            total_wait += wait_s
    raise RuntimeError("Unreachable loop exit in ConnectorInvoker.invoke")


async def run_async_retry_loop(
    *,
    breaker: ConnectorCircuitBreaker,
    clock: Callable[[], float],
    cost_per_attempt_usd: float,
    audit_dedup_keys: set[str],
    outbox_dedup_keys: set[str],
    norm_scheme: str,
    action: str,
    payload: dict[str, Any],
    idempotency_key: str,
    max_agent_retries: int,
    max_cost_usd: float,
    accumulated_cost_usd: float,
    resolved_connector: ConnectorPort,
) -> ConnectorInvocationOutcome:
    """Non-blocking async retry loop using `await asyncio.sleep(wait_s)` (`MAJOR-02`)."""
    sanitized_in = scrub_sensitive_dict(payload)
    _validate_preloop(breaker=breaker, clock=clock, norm_scheme=norm_scheme)
    max_attempts, attempts, total_wait, spent_usd = max(1, max_agent_retries), 0, 0.0, 0.0
    while attempts < max_attempts:
        _check_budget_ceiling(
            accumulated_cost_usd=accumulated_cost_usd,
            spent_usd=spent_usd,
            cost_per_attempt_usd=cost_per_attempt_usd,
            max_cost_usd=max_cost_usd,
            norm_scheme=norm_scheme,
            action=action,
        )
        attempts += 1
        spent_usd = round(spent_usd + cost_per_attempt_usd, 4)
        try:
            res: ConnectorInvokeResult = await asyncio.to_thread(
                resolved_connector.invoke, action, payload, idempotency_key
            )
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
        except Exception as raw_exc:
            outcome, wait_s = outcome_on_error(
                raw_exc=raw_exc,
                resolved_connector=resolved_connector,
                breaker=breaker,
                clock=clock,
                audit_dedup_keys=audit_dedup_keys,
                norm_scheme=norm_scheme,
                action=action,
                idempotency_key=idempotency_key,
                attempts=attempts,
                max_attempts=max_attempts,
                total_wait=total_wait,
                spent_usd=spent_usd,
                sanitized_in=sanitized_in,
            )
            if outcome is not None:
                return outcome
            await asyncio.sleep(wait_s)
            total_wait += wait_s
    raise RuntimeError("Unreachable loop exit in ConnectorInvoker.invoke_async")


__all__ = [
    "outcome_on_error",
    "run_async_retry_loop",
    "run_sync_retry_loop",
]
