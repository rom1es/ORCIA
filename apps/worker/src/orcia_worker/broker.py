"""Dramatiq Redis broker and idempotent `system_ping_actor` (`apps/worker`).

Conventions (AGENTS.md):
- Dramatiq workers may retry on transient failures — every actor must be idempotent
  and never duplicate side-effects.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from orcia_core.observability.logging import bind_trace_context, get_logger

logger = get_logger("orcia.worker")


@dataclass(frozen=True, slots=True)
class PingExecutionResult:
    """Result of an idempotent `system_ping_actor` invocation."""

    idempotency_key: str
    trace_id: str
    already_processed: bool


class ProcessedPingRegistry:
    """Idempotency registry preventing duplicate actor side-effects across retries."""

    def __init__(self) -> None:
        self._seen_keys: set[str] = set()

    def mark_if_new(self, idempotency_key: str) -> bool:
        """Return True if `idempotency_key` is seen for the first time, False on duplicate retry."""
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        if idempotency_key in self._seen_keys:
            return False
        self._seen_keys.add(idempotency_key)
        return True

    def clear(self) -> None:
        """Clear in-memory registry (used in isolated tests)."""
        self._seen_keys.clear()


default_ping_registry = ProcessedPingRegistry()


def configure_broker(redis_url: str | None = None, *, use_stub: bool = False) -> dramatiq.Broker:
    """Configure and set the active Dramatiq broker (Redis in prod, Stub when requested)."""
    if use_stub:
        broker: dramatiq.Broker = StubBroker()
    else:
        resolved_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        broker = RedisBroker(url=resolved_url)  # type: ignore[no-untyped-call]
    dramatiq.set_broker(broker)
    return broker


_default_stub = "0" if os.getenv("REDIS_URL") else "1"
configure_broker(use_stub=os.getenv("ORCIA_WORKER_STUB_BROKER", _default_stub) == "1")


def execute_system_ping(
    idempotency_key: str,
    trace_id: str,
    *,
    registry: ProcessedPingRegistry | None = None,
) -> PingExecutionResult:
    """Execute idempotent system ping logic with W3C `trace_id` correlation."""
    ctx = bind_trace_context(trace_id)
    target_registry = registry if registry is not None else default_ping_registry
    is_first_execution = target_registry.mark_if_new(idempotency_key)
    logger.info(
        "worker.system_ping",
        idempotency_key=idempotency_key,
        already_processed=not is_first_execution,
        trace_id=ctx.trace_id,
    )
    return PingExecutionResult(
        idempotency_key=idempotency_key,
        trace_id=ctx.trace_id,
        already_processed=not is_first_execution,
    )


@dramatiq.actor(max_retries=3)
def system_ping_actor(idempotency_key: str, trace_id: str) -> None:
    """Idempotent Dramatiq actor verifying worker queue liveness."""
    execute_system_ping(idempotency_key=idempotency_key, trace_id=trace_id)
