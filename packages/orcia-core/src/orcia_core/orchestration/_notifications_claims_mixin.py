"""Notification seeding, creation & outbox consumption mixin (`Story 5.1`, `Story 27.7`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from orcia_core.orchestration._notifications_claims_async import (
    seed_default_notifications_async_impl,
)
from orcia_core.orchestration._notifications_claims_seeds import (
    consume_outbox_event_async_impl,
    consume_outbox_event_impl,
    create_notification_async_impl,
    create_notification_impl,
    seed_default_notifications_impl,
)
from orcia_core.orchestration.presence_and_sse import (
    NotificationScopeKind,
    NotificationType,
    TaskNotificationEntity,
)
from orcia_kernel.events import DomainEvent

if TYPE_CHECKING:
    from orcia_core.orchestration.notifications_and_claims import UnifiedNotificationAndClaimService


class NotificationSeedAndOutboxMixin:
    """Seeding, creation & outbox event consumption methods for notifications."""

    def seed_default_notifications(
        self,
        *,
        workspace_id: str,
        team_id: str,
        user_id: str,
        run_id: str,
        step_execution_id: str,
        step_key: str = "architecture-arbitration",
    ) -> tuple[TaskNotificationEntity, ...]:
        return seed_default_notifications_impl(
            cast("UnifiedNotificationAndClaimService", self),
            workspace_id=workspace_id,
            team_id=team_id,
            user_id=user_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
        )

    def seed_default_notifications_if_empty(
        self,
        *,
        workspace_id: str,
        team_id: str,
        user_id: str,
        run_id: str,
        step_execution_id: str,
        step_key: str = "architecture-arbitration",
    ) -> tuple[TaskNotificationEntity, ...]:
        return seed_default_notifications_impl(
            cast("UnifiedNotificationAndClaimService", self),
            workspace_id=workspace_id,
            team_id=team_id,
            user_id=user_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
        )

    async def seed_default_notifications_if_empty_async(
        self,
        *,
        workspace_id: str,
        team_id: str,
        user_id: str,
        run_id: str,
        step_execution_id: str,
        step_key: str = "architecture-arbitration",
    ) -> tuple[TaskNotificationEntity, ...]:
        return await seed_default_notifications_async_impl(
            cast("UnifiedNotificationAndClaimService", self),
            workspace_id=workspace_id,
            team_id=team_id,
            user_id=user_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
        )

    def create_notification(
        self,
        *,
        workspace_id: str,
        target_team_id: str | None,
        target_user_id: str | None,
        run_id: str,
        step_execution_id: str,
        step_key: str,
        notification_type: NotificationType,
        scope_kind: NotificationScopeKind = "TEAM",
        title: str,
        summary: str,
        source_event_id: str | None = None,
    ) -> TaskNotificationEntity:
        return create_notification_impl(
            cast("UnifiedNotificationAndClaimService", self),
            workspace_id=workspace_id,
            target_team_id=target_team_id,
            target_user_id=target_user_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            notification_type=notification_type,
            scope_kind=scope_kind,
            title=title,
            summary=summary,
            source_event_id=source_event_id,
        )

    async def create_notification_async(
        self,
        *,
        workspace_id: str,
        target_team_id: str | None,
        target_user_id: str | None,
        run_id: str,
        step_execution_id: str,
        step_key: str,
        notification_type: NotificationType,
        scope_kind: NotificationScopeKind = "TEAM",
        title: str,
        summary: str,
        source_event_id: str | None = None,
    ) -> TaskNotificationEntity:
        return await create_notification_async_impl(
            cast("UnifiedNotificationAndClaimService", self),
            workspace_id=workspace_id,
            target_team_id=target_team_id,
            target_user_id=target_user_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            notification_type=notification_type,
            scope_kind=scope_kind,
            title=title,
            summary=summary,
            source_event_id=source_event_id,
        )

    def consume_outbox_event(
        self,
        event: DomainEvent,
        *,
        default_team_id: str | None = None,
        default_user_id: str | None = None,
    ) -> TaskNotificationEntity | None:
        return consume_outbox_event_impl(
            cast("UnifiedNotificationAndClaimService", self),
            event,
            default_team_id=default_team_id,
            default_user_id=default_user_id,
        )

    async def consume_outbox_event_async(
        self,
        event: DomainEvent,
        *,
        default_team_id: str | None = None,
        default_user_id: str | None = None,
    ) -> TaskNotificationEntity | None:
        return await consume_outbox_event_async_impl(
            cast("UnifiedNotificationAndClaimService", self),
            event,
            default_team_id=default_team_id,
            default_user_id=default_user_id,
        )
