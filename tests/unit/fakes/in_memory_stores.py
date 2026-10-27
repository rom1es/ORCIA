"""In-memory test fakes for unit tests (`tests/unit/fakes/`, AD-19, Story 3.2a).

Isolated from production infrastructure adapters. Implements `orcia_kernel.ports` and domain store
protocols (`CasObjectStoreProtocol`, `RevocationStoreProtocol`, `BlackboardPort`, `OutboxRelayPort`,
`ObjectStoragePort`, `SandboxPort`, `ClockPort`).
"""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime
from typing import Any

from orcia_core.catalog.cas_resolver import (
    FULL_SHA256_RE,
    InMemoryCasObjectStore,
    compute_bytes_sha256,
)
from orcia_core.catalog.models import CasObjectEntry
from orcia_core.permissions.service import InMemoryRevocationStore
from orcia_kernel.events import DomainEvent
from orcia_kernel.ports import (
    CasStoredObject,
    SandboxExecutionRequest,
    SandboxExecutionResult,
)


class InMemoryOutboxRelay:
    """In-memory transactional Outbox relay fake implementing `OutboxRelayPort` (`AD-19`, `C3`)."""

    def __init__(self) -> None:
        self._pending: list[DomainEvent] = []
        self._published: list[DomainEvent] = []

    def enqueue_in_transaction(self, event: DomainEvent) -> None:
        self._pending.append(event)

    def relay_pending_batch(self, *, batch_size: int = 100) -> int:
        batch = self._pending[:batch_size]
        self._pending = self._pending[batch_size:]
        self._published.extend(batch)
        return len(batch)

    @property
    def pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._pending)

    @property
    def published_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._published)


class InMemoryObjectStorageFake:
    """In-memory S3/CAS object storage fake implementing `ObjectStoragePort`."""

    def __init__(self) -> None:
        self._blobs: dict[str, CasStoredObject] = {}

    def put_bytes(
        self,
        *,
        cas_key: str,
        sha256: str,
        source_uri: str,
        content_bytes: bytes,
        content_type: str = "application/octet-stream",
    ) -> CasStoredObject:
        stored = CasStoredObject(
            cas_key=cas_key,
            sha256=sha256,
            source_uri=source_uri,
            content_bytes=content_bytes,
            content_type=content_type,
        )
        self._blobs[cas_key] = stored
        return stored

    def get_bytes(self, cas_key: str) -> CasStoredObject | None:
        return self._blobs.get(cas_key)


class DeterministicClockFake:
    """Deterministic monotonic UTC clock fake implementing `ClockPort`."""

    def __init__(self, initial: datetime | None = None) -> None:
        self._current = initial or datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self._current

    def advance_seconds(self, seconds: float) -> None:
        self._current = datetime.fromtimestamp(self._current.timestamp() + seconds, tz=UTC)


class InMemorySandboxFake:
    """Deterministic Wasmtime sandbox fake implementing `SandboxPort`."""

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            passed=True,
            exit_code=0,
            stdout=json.dumps(request.payload),
            stderr="",
            duration_ms=1,
        )


__all__ = [
    "Any",
    "CasObjectEntry",
    "DeterministicClockFake",
    "FULL_SHA256_RE",
    "InMemoryCasObjectStore",
    "InMemoryObjectStorageFake",
    "InMemoryOutboxRelay",
    "InMemoryRevocationStore",
    "InMemorySandboxFake",
    "compute_bytes_sha256",
    "threading",
    "time",
]
