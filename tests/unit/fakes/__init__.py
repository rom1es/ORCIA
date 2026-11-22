"""Isolated in-memory fakes package for ORCIA unit tests (`tests/unit/fakes/`, AD-19)."""

from __future__ import annotations

from tests.unit.fakes.in_memory_reindex import (
    InMemoryReindexManager,
    default_in_memory_reindex_manager,
)
from tests.unit.fakes.in_memory_stores import (
    DeterministicClockFake,
    InMemoryCasObjectStore,
    InMemoryObjectStorageFake,
    InMemoryOutboxRelay,
    InMemoryRevocationStore,
    InMemorySandboxFake,
)
from tests.unit.fakes.in_memory_thread_lock import InMemoryThreadTurnLock

__all__ = [
    "DeterministicClockFake",
    "InMemoryCasObjectStore",
    "InMemoryObjectStorageFake",
    "InMemoryOutboxRelay",
    "InMemoryReindexManager",
    "InMemoryRevocationStore",
    "InMemorySandboxFake",
    "InMemoryThreadTurnLock",
    "default_in_memory_reindex_manager",
]
