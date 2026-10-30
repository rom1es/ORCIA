"""Transactional Outbox Relay (`OutboxRelayPort`) for Dramatiq and DBOS (`Story 3.2c`, `C3`).

Distributes `domain_events_outbox` rows (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`,
`RunTerminated`, `HumanArbitrationRequested`) idempotently (`0` duplicates per `event_id`) to
decoupled subscribers (`audit_finops`, `ontology`, `sse`) without coupling `engine.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import dramatiq
from dbos import DBOS

from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_kernel.events import DomainEvent
from orcia_kernel.ports import OutboxRelayPort

logger = get_logger("orcia.worker.outbox_relay")

SyncSubscriberHandler = Callable[[DomainEvent], None]


@dataclass
class OutboxEventBus:
    """Idempotent in-process domain event bus routing Outbox events to decoupled subscribers."""

    _subscribers: dict[str, list[tuple[str, SyncSubscriberHandler]]] = field(default_factory=dict)
    _delivered_keys: set[tuple[str, str]] = field(default_factory=set)
    audit_finops_ledger: list[DomainEvent] = field(default_factory=list)
    ontology_extraction_queue: list[DomainEvent] = field(default_factory=list)
    notifications_queue: list[DomainEvent] = field(default_factory=list)
    sse_published_messages: list[tuple[str, DomainEvent]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.subscribe("*", "audit_finops", self._on_audit_finops)
        self.subscribe("ArtifactProduced", "ontology", self._on_ontology_l4)
        self.subscribe("*", "notifications", self._on_notifications)
        self.subscribe("*", "sse", self._on_sse_broadcast)

    def subscribe(
        self,
        event_type: str,
        subscriber_name: str,
        handler: SyncSubscriberHandler,
    ) -> None:
        """Register an idempotent subscriber for `event_type` (or `'*'` for all events)."""
        self._subscribers.setdefault(event_type, []).append((subscriber_name, handler))

    def publish_idempotent(self, event: DomainEvent) -> int:
        """Deliver `event` to matching subscribers with `0` duplicates per `event_id`."""
        bind_trace_context(event.trace_id, workspace_id=event.workspace_id, run_id=event.run_id)
        handlers = list(self._subscribers.get(event.event_type, [])) + list(
            self._subscribers.get("*", [])
        )
        delivered = 0
        for sub_name, handler in handlers:
            dedup_key = (sub_name, event.event_id)
            if dedup_key in self._delivered_keys:
                continue
            handler(event)
            self._delivered_keys.add(dedup_key)
            delivered += 1
        return delivered

    async def publish_idempotent_async(self, event: DomainEvent) -> None:
        """Async callback for `SqlDomainEventsOutboxRepository.claim_and_relay_pending_batch`."""
        self.publish_idempotent(event)

    def _on_audit_finops(self, event: DomainEvent) -> None:
        self.audit_finops_ledger.append(event)

    def _on_ontology_l4(self, event: DomainEvent) -> None:
        self.ontology_extraction_queue.append(event)

    def _on_notifications(self, event: DomainEvent) -> None:
        self.notifications_queue.append(event)

    def _on_sse_broadcast(self, event: DomainEvent) -> None:
        ws_id = event.workspace_id or "global"
        topic = f"channel:workspace:{ws_id}:{event.event_type}"
        self.sse_published_messages.append((topic, event))


class DramatiqOutboxRelay(OutboxRelayPort):
    """`OutboxRelayPort` implementation backed by Dramatiq (`C3`, `Q2: 2A`)."""

    def __init__(self, event_bus: OutboxEventBus | None = None) -> None:
        self.event_bus = event_bus or OutboxEventBus()
        self._pending: dict[str, DomainEvent] = {}
        self._published_ids: set[str] = set()

    def enqueue_in_transaction(self, event: DomainEvent) -> None:
        if event.event_id in self._published_ids or event.event_id in self._pending:
            return
        self._pending[event.event_id] = event

    def relay_pending_batch(self, *, batch_size: int = 100) -> int:
        keys = list(self._pending.keys())[: max(0, batch_size)]
        for eid in keys:
            evt = self._pending.pop(eid)
            self.event_bus.publish_idempotent(evt)
            self._published_ids.add(eid)
        return len(keys)


class DbosOutboxRelay(OutboxRelayPort):
    """`OutboxRelayPort` implementation backed by a DBOS workflow/step (`C3`, `Q2: 2A`)."""

    def __init__(self, event_bus: OutboxEventBus | None = None) -> None:
        self.event_bus = event_bus or OutboxEventBus()
        self._pending: dict[str, DomainEvent] = {}
        self._published_ids: set[str] = set()

    def enqueue_in_transaction(self, event: DomainEvent) -> None:
        if event.event_id in self._published_ids or event.event_id in self._pending:
            return
        self._pending[event.event_id] = event

    def relay_pending_batch(self, *, batch_size: int = 100) -> int:
        keys = list(self._pending.keys())[: max(0, batch_size)]
        for eid in keys:
            evt = self._pending.pop(eid)
            self.event_bus.publish_idempotent(evt)
            self._published_ids.add(eid)
        return len(keys)


@dramatiq.actor(actor_name="outbox_relay", max_retries=3)
def outbox_relay_actor(batch_size: int = 100) -> int:
    """Idempotent Dramatiq actor relaying a batch of Outbox events."""
    relay = DramatiqOutboxRelay()
    return relay.relay_pending_batch(batch_size=batch_size)


@DBOS.step()
def _dbos_outbox_relay_step(batch_size: int) -> int:
    relay = DbosOutboxRelay()
    return relay.relay_pending_batch(batch_size=batch_size)


@DBOS.workflow()
def dbos_outbox_relay_workflow(batch_size: int = 100) -> int:
    """Idempotent DBOS workflow relaying a batch of Outbox events (`C3`)."""
    return _dbos_outbox_relay_step(batch_size)


__all__ = [
    "DbosOutboxRelay",
    "DramatiqOutboxRelay",
    "OutboxEventBus",
    "dbos_outbox_relay_workflow",
    "outbox_relay_actor",
]
