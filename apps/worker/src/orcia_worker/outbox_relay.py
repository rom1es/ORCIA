"""Transactional Outbox Relay (`OutboxRelayPort`) for Dramatiq and DBOS (`Story 3.2c`, `C3`).

Distributes `domain_events_outbox` rows (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`,
`RunTerminated`, `HumanArbitrationRequested`) idempotently (`0` duplicates per `event_id`) to
decoupled subscribers (`audit_finops`, `ontology`, `sse`) without coupling `engine.py`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import dramatiq
from dbos import DBOS

from orcia_core.audit_finops import AuditLedgerOutboxSubscriber, SqlAuditLedgerService
from orcia_core.observability.logging import (
    bind_trace_context,
    ensure_logging_configured,
    get_logger,
)
from orcia_core.orchestration import (
    DbosSqlAlchemyUnitOfWork,
    SqlDomainEventsOutboxRepository,
    UnifiedNotificationAndClaimService,
)
from orcia_core.orchestration.presence_and_sse import SseBroadcastPort
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.events import DomainEvent
from orcia_kernel.ports import OutboxRelayPort

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

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
    workflow_published_queue: list[DomainEvent] = field(default_factory=list)
    sse_published_messages: list[tuple[str, DomainEvent]] = field(default_factory=list)
    audit_sink: AuditLedgerSinkPort | None = None
    audit_subscriber: AuditLedgerOutboxSubscriber | None = None
    notification_service: UnifiedNotificationAndClaimService | None = None
    sse_broker: SseBroadcastPort | None = None
    on_workflow_published: Callable[[DomainEvent], Awaitable[Any] | Any] | None = None

    def __post_init__(self) -> None:
        if self.audit_sink is not None and self.audit_subscriber is None:
            self.audit_subscriber = AuditLedgerOutboxSubscriber(self.audit_sink)
        self.subscribe("*", "audit_finops", self._on_audit_finops)
        self.subscribe("ArtifactProduced", "ontology", self._on_ontology_l4)
        self.subscribe("WorkflowPublished", "triggers_outbox", self._on_triggers_outbox)
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
        if self.audit_subscriber is not None:
            await self.audit_subscriber.on_domain_event(event)
        if self.notification_service is not None:
            await self.notification_service.consume_outbox_event_async(event)
        if event.event_type == "WorkflowPublished" and self.on_workflow_published is not None:
            res = self.on_workflow_published(event)
            if asyncio.iscoroutine(res):
                await res

    def _on_audit_finops(self, event: DomainEvent) -> None:
        self.audit_finops_ledger.append(event)

    def _on_ontology_l4(self, event: DomainEvent) -> None:
        self.ontology_extraction_queue.append(event)

    def _on_triggers_outbox(self, event: DomainEvent) -> None:
        self.workflow_published_queue.append(event)

    def _on_notifications(self, event: DomainEvent) -> None:
        self.notifications_queue.append(event)

    def _on_sse_broadcast(self, event: DomainEvent) -> None:
        ws_id = event.workspace_id or "global"
        topic = f"channel:workspace:{ws_id}:{event.event_type}"
        self.sse_published_messages.append((topic, event))


def build_default_outbox_event_bus(
    engine: AsyncEngine | None = None,
    *,
    sse_broker: SseBroadcastPort | None = None,
) -> OutboxEventBus:
    """Construct an `OutboxEventBus` wired to PG18 audit & notification sinks."""
    sink = SqlAuditLedgerService(engine=engine) if engine is not None else None
    notif_svc = (
        UnifiedNotificationAndClaimService(sse_broker=sse_broker, engine=engine)
        if engine is not None
        else None
    )
    return OutboxEventBus(
        audit_sink=sink,
        notification_service=notif_svc,
        sse_broker=sse_broker,
    )


class DramatiqOutboxRelay(OutboxRelayPort):
    """`OutboxRelayPort` implementation backed by Dramatiq (`C3`, `Q2: 2A`)."""

    def __init__(
        self,
        event_bus: OutboxEventBus | None = None,
        *,
        engine: AsyncEngine | None = None,
    ) -> None:
        self.event_bus = event_bus or build_default_outbox_event_bus(engine)
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

    async def relay_sql_pending_batch(
        self,
        uow: DbosSqlAlchemyUnitOfWork,
        *,
        batch_size: int = 50,
    ) -> int:
        """Claim and relay `PENDING` rows from `domain_events_outbox` (`SKIP LOCKED`)."""
        if self.event_bus.audit_subscriber is None and getattr(uow, "engine", None) is not None:
            sink = SqlAuditLedgerService(engine=uow.engine)
            self.event_bus.audit_sink = sink
            self.event_bus.audit_subscriber = AuditLedgerOutboxSubscriber(sink)
        repo = SqlDomainEventsOutboxRepository(uow)
        return await repo.claim_and_relay_pending_batch(
            batch_size=batch_size,
            subscriber_fn=self.event_bus.publish_idempotent_async,
        )


class DbosOutboxRelay(OutboxRelayPort):
    """`OutboxRelayPort` implementation backed by a DBOS workflow/step (`C3`, `Q2: 2A`)."""

    def __init__(
        self,
        event_bus: OutboxEventBus | None = None,
        *,
        engine: AsyncEngine | None = None,
    ) -> None:
        self.event_bus = event_bus or build_default_outbox_event_bus(engine)
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

    async def relay_sql_pending_batch(
        self,
        uow: DbosSqlAlchemyUnitOfWork,
        *,
        batch_size: int = 50,
    ) -> int:
        """Claim and relay `PENDING` rows from `domain_events_outbox` (`SKIP LOCKED`)."""
        if self.event_bus.audit_subscriber is None and getattr(uow, "engine", None) is not None:
            sink = SqlAuditLedgerService(engine=uow.engine)
            self.event_bus.audit_sink = sink
            self.event_bus.audit_subscriber = AuditLedgerOutboxSubscriber(sink)
        repo = SqlDomainEventsOutboxRepository(uow)
        return await repo.claim_and_relay_pending_batch(
            batch_size=batch_size,
            subscriber_fn=self.event_bus.publish_idempotent_async,
        )


async def relay_sql_outbox_with_engine(engine: AsyncEngine, *, batch_size: int = 50) -> int:
    """Relay one SQL Outbox batch into `audit_ledger` using a shared `AsyncEngine`."""
    uow = await DbosSqlAlchemyUnitOfWork.create(
        "",
        engine=engine,
        run_migrations=False,
    )
    relay = DramatiqOutboxRelay(engine=engine)
    return await relay.relay_sql_pending_batch(uow, batch_size=batch_size)


@dramatiq.actor(actor_name="sql_outbox_relay", max_retries=3)
def sql_outbox_relay_actor(batch_size: int = 50) -> int:
    """Dramatiq actor relaying pending `domain_events_outbox` rows into `audit_ledger`."""
    ensure_logging_configured(service=os.environ.get("ORCIA_WORKER_ROLE", "worker"))
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from orcia_core.config import resolve_database_url

    async def _run() -> int:
        engine = create_async_engine(resolve_database_url(), poolclass=NullPool)
        try:
            return await relay_sql_outbox_with_engine(engine, batch_size=batch_size)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


@dramatiq.actor(actor_name="outbox_relay", max_retries=3)
def outbox_relay_actor(batch_size: int = 100) -> int:
    """Idempotent Dramatiq actor relaying a batch of Outbox events."""
    ensure_logging_configured(service=os.environ.get("ORCIA_WORKER_ROLE", "worker"))
    relay = DramatiqOutboxRelay()
    return relay.relay_pending_batch(batch_size=batch_size)


@DBOS.step()
def _dbos_outbox_relay_step(batch_size: int) -> int:
    relay = DbosOutboxRelay()
    return relay.relay_pending_batch(batch_size=batch_size)


@DBOS.workflow()
def dbos_outbox_relay_workflow(batch_size: int = 100) -> int:
    """Idempotent DBOS workflow relaying a batch of Outbox events (`C3`)."""
    ensure_logging_configured(service=os.environ.get("ORCIA_WORKER_ROLE", "worker"))
    return _dbos_outbox_relay_step(batch_size)


__all__ = [
    "DbosOutboxRelay",
    "DramatiqOutboxRelay",
    "OutboxEventBus",
    "build_default_outbox_event_bus",
    "dbos_outbox_relay_workflow",
    "outbox_relay_actor",
    "relay_sql_outbox_with_engine",
    "sql_outbox_relay_actor",
]
