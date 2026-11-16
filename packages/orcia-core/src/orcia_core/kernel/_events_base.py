"""Base DomainEvent definition (`AD-12`, `AD-19`).

Pure kernel module — zero framework or business domain dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orcia_core.kernel.enums import OutboxEventStatus


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base immutable domain event stored in `domain_events_outbox` (`Q2: 2A`, `C3`)."""

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    run_id: str | None
    workspace_id: str | None
    payload: dict[str, Any]
    trace_id: str = "00000000000000000000000000000000"
    status: OutboxEventStatus = "PENDING"
    attempts: int = 0

    def to_outbox_dict(self) -> dict[str, Any]:
        """Serialize domain event to an Outbox row dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "payload_jsonb": dict(self.payload),
            "trace_id": self.trace_id,
            "status": self.status,
            "attempts": self.attempts,
        }
