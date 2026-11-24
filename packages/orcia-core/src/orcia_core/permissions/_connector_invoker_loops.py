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
from orcia_core.permissions._connector_invoker_outcomes import (
    build_succeeded_outcome,
    check_budget_ceiling,
    outcome_on_error,
    validate_preloop,
)
from orcia_kernel.ports import ConnectorInvokeResult, ConnectorPort


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
    validate_preloop(breaker=breaker, clock=clock, norm_scheme=norm_scheme)
    max_attempts, attempts, total_wait, spent_usd = max(1, max_agent_retries), 0, 0.0, 0.0
    while attempts < max_attempts:
        check_budget_ceiling(
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
            return build_succeeded_outcome(
                breaker=breaker,
                clock=clock,
                audit_dedup_keys=audit_dedup_keys,
                outbox_dedup_keys=outbox_dedup_keys,
                norm_scheme=norm_scheme,
                action=action,
                idempotency_key=idempotency_key,
                attempts=attempts,
                total_wait=total_wait,
                spent_usd=spent_usd,
                sanitized_in=sanitized_in,
                res=res,
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
    validate_preloop(breaker=breaker, clock=clock, norm_scheme=norm_scheme)
    max_attempts, attempts, total_wait, spent_usd = max(1, max_agent_retries), 0, 0.0, 0.0
    while attempts < max_attempts:
        check_budget_ceiling(
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
            return build_succeeded_outcome(
                breaker=breaker,
                clock=clock,
                audit_dedup_keys=audit_dedup_keys,
                outbox_dedup_keys=outbox_dedup_keys,
                norm_scheme=norm_scheme,
                action=action,
                idempotency_key=idempotency_key,
                attempts=attempts,
                total_wait=total_wait,
                spent_usd=spent_usd,
                sanitized_in=sanitized_in,
                res=res,
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
