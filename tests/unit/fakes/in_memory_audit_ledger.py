"""In-memory fake for `AuditLedgerSinkPort` for unit tests (`tests/unit/fakes/`)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort, FinopsCostLedgerEntry
from orcia_kernel.ids import new_uuid7_str


class InMemoryAuditLedgerSink(AuditLedgerSinkPort):
    """Idempotent unit-test fake implementing `AuditLedgerSinkPort` (`AD-12`, `AD-19`)."""

    def __init__(self) -> None:
        self._by_source_event_id: dict[str, tuple[str, FinopsCostLedgerEntry]] = {}

    @property
    def entries(self) -> tuple[FinopsCostLedgerEntry, ...]:
        """Return recorded entries in insertion order."""
        return tuple(item[1] for item in self._by_source_event_id.values())

    async def record_entry(
        self,
        entry: FinopsCostLedgerEntry,
        *,
        conn: AsyncConnection | None = None,
    ) -> str:
        """Record an entry idempotently keyed by `source_event_id`."""
        _ = conn
        existing = self._by_source_event_id.get(entry.source_event_id)
        if existing is not None:
            return existing[0]
        entry_id = entry.id or new_uuid7_str()
        self._by_source_event_id[entry.source_event_id] = (entry_id, entry)
        return entry_id


__all__ = ["InMemoryAuditLedgerSink"]
