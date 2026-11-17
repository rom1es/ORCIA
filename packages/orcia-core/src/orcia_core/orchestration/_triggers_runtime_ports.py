"""Redis NX lock & DBOS `SetWorkflowID` adapters for workflow triggers (`Story 7.2`, `AD-18`).

Zero SDLC vocabulary (`AD-19`, `AD-20`).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from dbos import SetWorkflowID

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.models import WorkflowTriggerEntity
from orcia_kernel.errors import (
    FunctionalConnectorError,
    PolicyDeniedError,
    TransientConnectorError,
    TransientInfraError,
    ValidationDomainError,
)

logger = get_logger("orcia.core.orchestration.triggers_runtime")


@runtime_checkable
class TriggerIdempotencyLockPort(Protocol):
    """Atomic `SET lock:trigger:{trigger_id}:{idempotency_key} 1 NX EX 86400` lock port."""

    async def try_acquire(
        self, *, trigger_id: str, idempotency_key: str, ttl_seconds: int = 86400
    ) -> bool:
        """Return `True` if the lock was acquired for the first time, else `False`."""
        ...


class RedisTriggerIdempotencyLockAdapter(TriggerIdempotencyLockPort):
    """Redis `SET NX EX 86400` lock with concurrent in-process mutex fallback."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._mutex = threading.Lock()
        self._seen: set[str] = set()

    @staticmethod
    def build_key(trigger_id: str, idempotency_key: str) -> str:
        return f"lock:trigger:{trigger_id}:{idempotency_key}"

    async def try_acquire(
        self, *, trigger_id: str, idempotency_key: str, ttl_seconds: int = 86400
    ) -> bool:
        key = self.build_key(trigger_id, idempotency_key)
        if self._redis is not None:
            result = self._redis.set(key, "1", nx=True, ex=max(60, int(ttl_seconds)))
            if asyncio.iscoroutine(result):
                result = await result
            return bool(result)
        with self._mutex:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True


@runtime_checkable
class DbosWorkflowIdDispatcherPort(Protocol):
    """Port binding canonical `SetWorkflowID("<trigger_id>:<idempotency_key>")` (`AD-18`)."""

    async def dispatch(
        self,
        *,
        dbos_workflow_id: str,
        trigger: WorkflowTriggerEntity,
        run_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        execution_fn: Callable[[], Awaitable[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Execute trigger workload idempotently under `dbos_workflow_id`."""
        ...


@dataclass
class DbosSetWorkflowIdDispatcher(DbosWorkflowIdDispatcherPort):
    """Default dispatcher wrapping execution in DBOS `SetWorkflowID` context (`AD-18`)."""

    executed_workflow_ids: list[str] = field(default_factory=list)

    async def dispatch(
        self,
        *,
        dbos_workflow_id: str,
        trigger: WorkflowTriggerEntity,
        run_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        execution_fn: Callable[[], Awaitable[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        with SetWorkflowID(dbos_workflow_id):
            self.executed_workflow_ids.append(dbos_workflow_id)
            if execution_fn is not None:
                return await execution_fn()
            return {
                "run_id": run_id,
                "trigger_id": trigger.id,
                "workflow_id": trigger.workflow_id,
                "idempotency_key": idempotency_key,
                "dbos_workflow_id": dbos_workflow_id,
                "payload_keys": sorted(payload.keys()),
            }


async def run_with_error_taxonomy(
    execution_fn: Callable[[], Awaitable[dict[str, Any]]],
    *,
    max_transient_retries: int = 2,
) -> tuple[dict[str, Any], int]:
    """Execute `execution_fn`, retrying ONLY `TransientConnectorError`/`TransientInfraError`."""
    attempts = 0
    while True:
        attempts += 1
        try:
            res = await execution_fn()
            return res, attempts
        except (FunctionalConnectorError, PolicyDeniedError, ValidationDomainError):
            raise
        except (TransientConnectorError, TransientInfraError) as exc:
            if attempts > max(0, max_transient_retries):
                raise exc
            logger.warning(
                "trigger_transient_connector_retry",
                attempt=attempts,
                error=str(exc),
            )
            await asyncio.sleep(0)


__all__ = [
    "DbosSetWorkflowIdDispatcher",
    "DbosWorkflowIdDispatcherPort",
    "RedisTriggerIdempotencyLockAdapter",
    "TriggerIdempotencyLockPort",
    "run_with_error_taxonomy",
]
