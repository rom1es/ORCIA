"""Assistant Harness Transactional Outbox Emitter (`SqlDomainEventsOutboxRepository`, `H-22`)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from orcia_core.kernel.events import (
    AssistantTurnCompleted,
    AssistantTurnFailed,
    AssistantTurnStarted,
    AssistantTurnStopped,
    DomainEvent,
    SettingsChanged,
)
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._internal.outbox_repository import SqlDomainEventsOutboxRepository
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger("orcia.assistant.outbox")


def coerce_optional_uuid(raw_id: str | None) -> str | None:
    """Return canonical UUID string when valid, or `None` for non-UUID test slugs."""
    if not raw_id:
        return None
    try:
        return str(UUID(str(raw_id).strip()))
    except (ValueError, TypeError):
        return None


class AssistantOutboxEmitter:
    """Persists real assistant harness lifecycle events into PostgreSQL `domain_events_outbox`."""

    def __init__(
        self,
        *,
        outbox_repo: SqlDomainEventsOutboxRepository | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        self._outbox_repo = outbox_repo
        self._engine = engine

    @classmethod
    def from_uow_or_engine(
        cls,
        *,
        uow: DbosSqlAlchemyUnitOfWork | None = None,
        engine: AsyncEngine | None = None,
    ) -> AssistantOutboxEmitter | None:
        """Build an `AssistantOutboxEmitter` from Composition Root `uow` or `db_engine`."""
        if uow is not None:
            return cls(outbox_repo=SqlDomainEventsOutboxRepository(uow))
        if engine is not None:
            return cls(
                outbox_repo=SqlDomainEventsOutboxRepository(
                    DbosSqlAlchemyUnitOfWork.from_engine(engine)
                ),
                engine=engine,
            )
        return None

    async def _enqueue(self, event: DomainEvent) -> str | None:
        if self._outbox_repo is None:
            return None
        try:
            await self._outbox_repo.enqueue_event(event)
            return event.event_id
        except Exception as exc:
            logger.warning(
                "assistant_outbox_enqueue_failed",
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                error_type=type(exc).__name__,
            )
            return None

    async def emit_turn_started(
        self,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        speed_mode: str,
        trace_id: str,
    ) -> str | None:
        """Persist `AssistantTurnStarted` into `domain_events_outbox`."""
        evt = AssistantTurnStarted.create(
            turn_id=turn_id,
            workspace_id=coerce_optional_uuid(workspace_id),
            user_id=user_id,
            speed_mode=speed_mode,
            trace_id=trace_id or ("0" * 32),
        )
        return await self._enqueue(evt)

    async def emit_turn_completed(
        self,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        speed_mode: str,
        input_tokens: int,
        output_tokens: int,
        trace_id: str,
    ) -> str | None:
        """Persist `AssistantTurnCompleted` into `domain_events_outbox`."""
        evt = AssistantTurnCompleted.create(
            turn_id=turn_id,
            workspace_id=coerce_optional_uuid(workspace_id),
            user_id=user_id,
            speed_mode=speed_mode,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            trace_id=trace_id or ("0" * 32),
        )
        return await self._enqueue(evt)

    async def emit_turn_stopped(
        self,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        stopped_by_user_id: str,
        trace_id: str,
    ) -> str | None:
        """Persist `AssistantTurnStopped` into `domain_events_outbox`."""
        evt = AssistantTurnStopped.create(
            turn_id=turn_id,
            workspace_id=coerce_optional_uuid(workspace_id),
            user_id=user_id,
            stopped_by_user_id=stopped_by_user_id,
            trace_id=trace_id or ("0" * 32),
        )
        return await self._enqueue(evt)

    async def emit_turn_failed(
        self,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        error_code: str,
        trace_id: str,
    ) -> str | None:
        """Persist `AssistantTurnFailed` into `domain_events_outbox`."""
        evt = AssistantTurnFailed.create(
            turn_id=turn_id,
            workspace_id=coerce_optional_uuid(workspace_id),
            user_id=user_id,
            error_code=error_code,
            trace_id=trace_id or ("0" * 32),
        )
        return await self._enqueue(evt)

    async def emit_settings_changed(
        self,
        *,
        workspace_id: str | None,
        setting_key: str,
        actor_id: str,
        trace_id: str,
        scope_level: str = "WORKSPACE",
        after_sha256: str = "",
        changed_keys: tuple[str, ...] = (),
    ) -> str | None:
        """Persist `SettingsChanged` into `domain_events_outbox`."""
        ws_uuid = coerce_optional_uuid(workspace_id)
        scope_ref = ws_uuid or (workspace_id or "scope-global")
        evt = SettingsChanged.create(
            setting_id=scope_ref,
            workspace_id=ws_uuid,
            scope_level=scope_level,
            scope_id=scope_ref,
            category="assistant",
            key=setting_key,
            version=1,
            before_sha256="",
            after_sha256=after_sha256,
            changed_keys=changed_keys or (setting_key,),
            updated_by=actor_id,
            trace_id=trace_id or ("0" * 32),
        )
        return await self._enqueue(evt)


__all__ = ["AssistantOutboxEmitter", "coerce_optional_uuid"]
