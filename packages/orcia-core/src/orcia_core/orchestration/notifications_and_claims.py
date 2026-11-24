"""Unified Notification Inbox, Outbox Subscriber & Presence Claim Service (`Story 5.1`, `AD-4`)."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from orcia_core.orchestration._internal.sql_task_notifications import SqlTaskNotificationRepository
from orcia_core.orchestration._notifications_claims_async import (
    claim_by_step_execution_async_impl,
    claim_by_task_id_async_impl,
    release_claim_async_impl,
)
from orcia_core.orchestration._notifications_claims_guards import NotificationClaimInternalMixin
from orcia_core.orchestration._notifications_claims_helpers import (
    claim_by_step_execution_impl,
    claim_by_task_id_impl,
    release_claim_impl,
)
from orcia_core.orchestration._notifications_claims_mixin import NotificationSeedAndOutboxMixin
from orcia_core.orchestration._notifications_claims_seeds import (
    count_unclaimed_action_required_impl,
    format_step_claim_title,
    list_notifications_impl,
)
from orcia_core.orchestration.presence_and_sse import (
    DEFAULT_CLAIM_TTL_SECONDS,
    ClaimActionOutcome,
    ClaimPresenceState,
    InMemorySseBrokerAdapter,
    InMemoryStepPresenceLockAdapter,
    NotificationScopeKind,
    NotificationStatus,
    NotificationType,
    SseBroadcastPort,
    SseEventEnvelope,
    StepPresenceLockPort,
    StepPresenceLockRecord,
    TaskNotificationEntity,
)
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


class UnifiedNotificationAndClaimService(
    NotificationSeedAndOutboxMixin, NotificationClaimInternalMixin
):
    """Unified Notification Inbox, Outbox consumer & atomic SSE Claim coordinator (`Story 5.1`)."""

    def __init__(
        self,
        *,
        presence_lock: StepPresenceLockPort | None = None,
        sse_broker: SseBroadcastPort | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        self.presence_lock = presence_lock or InMemoryStepPresenceLockAdapter()
        self.sse_broker = sse_broker or InMemorySseBrokerAdapter()
        self._engine: AsyncEngine | None = engine
        self._sql_repo: SqlTaskNotificationRepository | None = (
            SqlTaskNotificationRepository(engine) if engine is not None else None
        )
        self._mutex = threading.Lock()
        self._notifications: dict[str, TaskNotificationEntity] = {}
        self._by_step_exec_id: dict[str, str] = {}
        self._by_source_event_id: dict[str, str] = {}

    def set_engine(self, engine: AsyncEngine | None) -> None:
        self._engine = engine
        self._sql_repo = SqlTaskNotificationRepository(engine) if engine is not None else None

    async def _pg_ready(self) -> bool:
        return self._sql_repo is not None and await self._sql_repo.pg_tables_ready()

    async def _publish_sse(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, object],
    ) -> SseEventEnvelope:
        publish_async = getattr(self.sse_broker, "publish_async", None)
        if callable(publish_async):
            env: SseEventEnvelope = await publish_async(
                workspace_id=workspace_id,
                event_name=event_name,
                run_id=run_id,
                step_execution_id=step_execution_id,
                payload=dict(payload),
            )
            return env
        return self.sse_broker.publish(
            workspace_id=workspace_id,
            event_name=event_name,
            run_id=run_id,
            step_execution_id=step_execution_id,
            payload=dict(payload),
        )

    def list_notifications(
        self,
        *,
        workspace_id: str | None = None,
        scope_filter: Literal["ALL", "PERSONAL", "TEAM"] = "ALL",
        notification_type: NotificationType | None = None,
        viewer_user_id: str | None = None,
    ) -> tuple[TaskNotificationEntity, ...]:
        return list_notifications_impl(
            self,
            workspace_id=workspace_id,
            scope_filter=scope_filter,
            notification_type=notification_type,
            viewer_user_id=viewer_user_id,
        )

    async def list_notifications_async(
        self,
        *,
        workspace_id: str | None = None,
        scope_filter: Literal["ALL", "PERSONAL", "TEAM"] = "ALL",
        notification_type: NotificationType | None = None,
        viewer_user_id: str | None = None,
    ) -> tuple[TaskNotificationEntity, ...]:
        if not await self._pg_ready():
            return self.list_notifications(
                workspace_id=workspace_id,
                scope_filter=scope_filter,
                notification_type=notification_type,
                viewer_user_id=viewer_user_id,
            )
        assert self._sql_repo is not None
        return await self._sql_repo.list_notifications(
            workspace_id=workspace_id,
            scope_filter=scope_filter,
            notification_type=notification_type,
            viewer_user_id=viewer_user_id,
        )

    def count_unclaimed_action_required(self, workspace_id: str | None = None) -> int:
        return count_unclaimed_action_required_impl(self, workspace_id)

    async def count_unclaimed_action_required_async(self, workspace_id: str | None = None) -> int:
        if not await self._pg_ready():
            return self.count_unclaimed_action_required(workspace_id=workspace_id)
        assert self._sql_repo is not None
        return await self._sql_repo.count_unclaimed_action_required(workspace_id=workspace_id)

    def claim_by_task_id(
        self,
        user: UserIdentity,
        *,
        task_id: str,
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
        force: bool = False,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> ClaimActionOutcome:
        return claim_by_task_id_impl(
            self,
            user,
            task_id=task_id,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )

    async def claim_by_task_id_async(
        self,
        user: UserIdentity,
        *,
        task_id: str,
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
        force: bool = False,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> ClaimActionOutcome:
        return await claim_by_task_id_async_impl(
            self,
            user,
            task_id=task_id,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )

    @staticmethod
    def _format_step_claim_title(step_key: str) -> str:
        return format_step_claim_title(step_key)

    def claim_by_step_execution(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_execution_id: str,
        workspace_id: str = "0195f000-0000-7000-8000-000000000301",
        step_key: str = "step-1",
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
        force: bool = False,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> ClaimActionOutcome:
        return claim_by_step_execution_impl(
            self,
            user,
            run_id=run_id,
            step_execution_id=step_execution_id,
            workspace_id=workspace_id,
            step_key=step_key,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )

    async def claim_by_step_execution_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_execution_id: str,
        workspace_id: str = "0195f000-0000-7000-8000-000000000301",
        step_key: str = "step-1",
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
        force: bool = False,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> ClaimActionOutcome:
        return await claim_by_step_execution_async_impl(
            self,
            user,
            run_id=run_id,
            step_execution_id=step_execution_id,
            workspace_id=workspace_id,
            step_key=step_key,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )

    def release_claim(
        self,
        user: UserIdentity,
        *,
        task_id: str,
        force: bool = False,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> ClaimActionOutcome:
        return release_claim_impl(
            self, user, task_id=task_id, force=force, now_utc=now_utc, instance=instance
        )

    async def release_claim_async(
        self,
        user: UserIdentity,
        *,
        task_id: str,
        force: bool = False,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> ClaimActionOutcome:
        return await release_claim_async_impl(
            self, user, task_id=task_id, force=force, now_utc=now_utc, instance=instance
        )


__all__ = [
    "ClaimActionOutcome",
    "ClaimPresenceState",
    "DEFAULT_CLAIM_TTL_SECONDS",
    "InMemorySseBrokerAdapter",
    "InMemoryStepPresenceLockAdapter",
    "NotificationScopeKind",
    "NotificationStatus",
    "NotificationType",
    "SseBroadcastPort",
    "SseEventEnvelope",
    "StepPresenceLockPort",
    "StepPresenceLockRecord",
    "TaskNotificationEntity",
    "UnifiedNotificationAndClaimService",
]
