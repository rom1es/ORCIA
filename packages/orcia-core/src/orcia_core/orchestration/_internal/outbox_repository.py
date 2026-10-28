"""Transactional Outbox SQLAlchemy 2.1 Repository (`domain_events_outbox`, `Story 3.2c`).

Implements engine-independent transactional Outbox persistence (`ARCH-M6`, `Q2: 2A`, `C3`)
using `SELECT ... FOR UPDATE SKIP LOCKED` batched claiming on PostgreSQL 18.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_kernel.enums import OutboxEventStatus
from orcia_kernel.events import DomainEvent

AsyncSubscriberCallback = Callable[[DomainEvent], Awaitable[None]]


class SqlDomainEventsOutboxRepository:
    """Async SQLAlchemy 2.1 (`asyncpg`) repository for `domain_events_outbox` (`C3`)."""

    def __init__(self, uow: DbosSqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @staticmethod
    async def insert_event_in_session(session: AsyncSession, event: DomainEvent) -> None:
        """Insert a `DomainEvent` inside an active `AsyncSession` transaction (`0` duplicates)."""
        await session.execute(
            sa.text(
                """
                INSERT INTO domain_events_outbox (
                    event_id, event_type, aggregate_type, aggregate_id,
                    run_id, workspace_id, payload_jsonb, trace_id, status, attempts
                ) VALUES (
                    CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                    CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
                    CAST(:payload_jsonb AS jsonb), :trace_id, :status, :attempts
                )
                ON CONFLICT (event_id) DO NOTHING;
                """
            ),
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "run_id": event.run_id,
                "workspace_id": event.workspace_id,
                "payload_jsonb": json.dumps(event.payload, sort_keys=True),
                "trace_id": event.trace_id,
                "status": event.status,
                "attempts": event.attempts,
            },
        )

    async def enqueue_event(self, event: DomainEvent) -> None:
        """Persist a `DomainEvent` in `domain_events_outbox` inside a Unit of Work transaction."""
        async with self._uow.session_scope() as session:
            await self.insert_event_in_session(session, event)

    async def claim_and_relay_pending_batch(
        self,
        *,
        batch_size: int = 100,
        subscriber_fn: AsyncSubscriberCallback | None = None,
    ) -> int:
        """Claim `PENDING` events with `FOR UPDATE SKIP LOCKED` and mark `PUBLISHED`."""
        async with self._uow.session_scope() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            """
                            SELECT
                                event_id::text, event_type, aggregate_type, aggregate_id,
                                run_id::text, workspace_id::text, payload_jsonb,
                                trace_id, status, attempts
                            FROM domain_events_outbox
                            WHERE status = 'PENDING'
                            ORDER BY created_at ASC, event_id ASC
                            LIMIT :batch_size
                            FOR UPDATE SKIP LOCKED;
                            """
                        ),
                        {"batch_size": batch_size},
                    )
                )
                .mappings()
                .all()
            )
            relayed_count = 0
            for r in rows:
                event = self._row_to_domain_event(dict(r))
                if subscriber_fn is not None:
                    await subscriber_fn(event)
                await session.execute(
                    sa.text(
                        """
                        UPDATE domain_events_outbox
                        SET status = 'PUBLISHED',
                            attempts = attempts + 1,
                            published_at = NOW()
                        WHERE event_id = CAST(:event_id AS uuid);
                        """
                    ),
                    {"event_id": event.event_id},
                )
                relayed_count += 1
            return relayed_count

    async def list_events_by_run(self, run_id: str) -> tuple[DomainEvent, ...]:
        """List all outbox events for `run_id` ordered by `created_at`."""
        async with self._uow.session_scope() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            """
                            SELECT
                                event_id::text, event_type, aggregate_type, aggregate_id,
                                run_id::text, workspace_id::text, payload_jsonb,
                                trace_id, status, attempts
                            FROM domain_events_outbox
                            WHERE run_id = CAST(:run_id AS uuid)
                            ORDER BY created_at ASC, event_id ASC;
                            """
                        ),
                        {"run_id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            return tuple(self._row_to_domain_event(dict(r)) for r in rows)

    @staticmethod
    def _row_to_domain_event(row: dict[str, Any]) -> DomainEvent:
        raw_payload = row["payload_jsonb"]
        payload = (
            json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload or {})
        )
        return DomainEvent(
            event_id=str(row["event_id"]),
            event_type=str(row["event_type"]),
            aggregate_type=str(row["aggregate_type"]),
            aggregate_id=str(row["aggregate_id"]),
            run_id=str(row["run_id"]) if row["run_id"] else None,
            workspace_id=str(row["workspace_id"]) if row["workspace_id"] else None,
            payload=payload,
            trace_id=str(row["trace_id"]),
            status=cast(OutboxEventStatus, str(row["status"])),
            attempts=int(row["attempts"]),
        )


__all__ = ["AsyncSubscriberCallback", "SqlDomainEventsOutboxRepository"]
