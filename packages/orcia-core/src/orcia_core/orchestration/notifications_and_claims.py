"""Unified Notification Inbox, Outbox Subscriber & Presence Claim Service (`Story 5.1`, `AD-4`)."""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from orcia_core.orchestration._internal.sql_task_notifications import (
    SqlTaskNotificationRepository,
    coerce_uuid,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    StepAlreadyClaimedByPeerError,
    StepClaimNotHeldError,
    ValidationDomainError,
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
    translate_outbox_event_spec,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def _second_seed_step_id(step_execution_id: str) -> str:
    if step_execution_id == "0195f000-0000-7000-8000-000000000801":
        return "0195f000-0000-7000-8000-000000000802"
    return str(coerce_uuid(f"{step_execution_id}-gate"))


class UnifiedNotificationAndClaimService:
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
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
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
        """Seed deterministic team & personal notifications if inbox is empty."""
        with self._mutex:
            if self._notifications:
                return tuple(self._notifications.values())
        n1 = self.create_notification(
            workspace_id=workspace_id,
            target_team_id=team_id,
            target_user_id=None,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            notification_type="HUMAN_ARBITRATION",
            scope_kind="TEAM",
            title="⚖️ Arbitrage IA requis — Choix de topologie d'isolation",
            summary=(
                "Deux options d'architecture présentent un score équivalent ; "
                "décision d'équipe requise."
            ),
        )
        n2 = self.create_notification(
            workspace_id=workspace_id,
            target_team_id=team_id,
            target_user_id=user_id,
            run_id=run_id,
            step_execution_id=_second_seed_step_id(step_execution_id),
            step_key="security-human-gate",
            notification_type="HUMAN_GATE",
            scope_kind="PERSONAL",
            title="🛡️ Gate Humaine Adaptative — Revue du Briefing 4 blocs",
            summary="Validation par découpage attendue sur le livrable de sécurité.",
        )
        return (n1, n2)

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
        """Seed E2E notifications into PG18 when `task_notifications` has 0 rows."""
        if not await self._pg_ready():
            return self.seed_default_notifications(
                workspace_id=workspace_id,
                team_id=team_id,
                user_id=user_id,
                run_id=run_id,
                step_execution_id=step_execution_id,
                step_key=step_key,
            )
        assert self._sql_repo is not None
        if await self._sql_repo.count_all() > 0:
            return await self._sql_repo.list_notifications(workspace_id=workspace_id)
        n1 = await self.create_notification_async(
            workspace_id=workspace_id,
            target_team_id=team_id,
            target_user_id=None,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            notification_type="HUMAN_ARBITRATION",
            scope_kind="TEAM",
            title="⚖️ Arbitrage IA requis — Choix de topologie d'isolation",
            summary=(
                "Deux options d'architecture présentent un score équivalent ; "
                "décision d'équipe requise."
            ),
            source_event_id="0195f000-0000-7000-8000-000000009101",
        )
        n2 = await self.create_notification_async(
            workspace_id=workspace_id,
            target_team_id=team_id,
            target_user_id=user_id,
            run_id=run_id,
            step_execution_id=_second_seed_step_id(step_execution_id),
            step_key="security-human-gate",
            notification_type="HUMAN_GATE",
            scope_kind="PERSONAL",
            title="🛡️ Gate Humaine Adaptative — Revue du Briefing 4 blocs",
            summary="Validation par découpage attendue sur le livrable de sécurité.",
            source_event_id="0195f000-0000-7000-8000-000000009102",
        )
        return (n1, n2)

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
        """Create a notification idempotently (deduplicated by `source_event_id` if provided)."""
        with self._mutex:
            if source_event_id and source_event_id in self._by_source_event_id:
                return self._notifications[self._by_source_event_id[source_event_id]]
            notif_id = new_uuid7_str()
            entity = TaskNotificationEntity(
                id=notif_id,
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
            self._notifications[notif_id] = entity
            self._by_step_exec_id[step_execution_id] = notif_id
            if source_event_id:
                self._by_source_event_id[source_event_id] = notif_id
        self.sse_broker.publish(
            workspace_id=workspace_id,
            event_name="task.notification.created",
            run_id=run_id,
            step_execution_id=step_execution_id,
            payload={
                "notification_id": entity.id,
                "notification_type": entity.notification_type,
                "scope_kind": entity.scope_kind,
                "title": entity.title,
            },
        )
        return entity

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
        """Create and persist a notification idempotently in PG18 + SSE broadcast."""
        if not await self._pg_ready():
            return self.create_notification(
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
        assert self._sql_repo is not None
        draft = TaskNotificationEntity(
            id=new_uuid7_str(),
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
        persisted = await self._sql_repo.insert_or_get_notification(draft)
        with self._mutex:
            self._notifications[persisted.id] = persisted
            self._by_step_exec_id[persisted.step_execution_id] = persisted.id
            if persisted.source_event_id:
                self._by_source_event_id[persisted.source_event_id] = persisted.id
        await self._publish_sse(
            workspace_id=persisted.workspace_id,
            event_name="task.notification.created",
            run_id=persisted.run_id,
            step_execution_id=persisted.step_execution_id,
            payload={
                "notification_id": persisted.id,
                "notification_type": persisted.notification_type,
                "scope_kind": persisted.scope_kind,
                "title": persisted.title,
            },
        )
        return persisted

    def consume_outbox_event(
        self,
        event: DomainEvent,
        *,
        default_team_id: str | None = None,
        default_user_id: str | None = None,
    ) -> TaskNotificationEntity | None:
        """Idempotent Outbox subscriber converting domain events into `task_notifications`."""
        spec = translate_outbox_event_spec(event.event_type, event.payload)
        if spec is None:
            return None
        ntype, title, summary = spec
        return self.create_notification(
            workspace_id=event.workspace_id or "0195f000-0000-7000-8000-000000000301",
            target_team_id=default_team_id,
            target_user_id=default_user_id,
            run_id=event.run_id or event.aggregate_id,
            step_execution_id=event.aggregate_id,
            step_key=str(event.payload.get("step_key") or "step-1"),
            notification_type=ntype,
            scope_kind="TEAM",
            title=title,
            summary=summary,
            source_event_id=event.event_id,
        )

    async def consume_outbox_event_async(
        self,
        event: DomainEvent,
        *,
        default_team_id: str | None = None,
        default_user_id: str | None = None,
    ) -> TaskNotificationEntity | None:
        """Async idempotent Outbox subscriber persisting into PG18 `task_notifications`."""
        spec = translate_outbox_event_spec(event.event_type, event.payload)
        if spec is None:
            return None
        ntype, title, summary = spec
        return await self.create_notification_async(
            workspace_id=event.workspace_id or "0195f000-0000-7000-8000-000000000301",
            target_team_id=default_team_id,
            target_user_id=default_user_id,
            run_id=event.run_id or event.aggregate_id,
            step_execution_id=event.aggregate_id,
            step_key=str(event.payload.get("step_key") or "step-1"),
            notification_type=ntype,
            scope_kind="TEAM",
            title=title,
            summary=summary,
            source_event_id=event.event_id,
        )

    def list_notifications(
        self,
        *,
        workspace_id: str | None = None,
        scope_filter: Literal["ALL", "PERSONAL", "TEAM"] = "ALL",
        notification_type: NotificationType | None = None,
        viewer_user_id: str | None = None,
    ) -> tuple[TaskNotificationEntity, ...]:
        """List notifications filtered by workspace, scope (`PERSONAL` / `TEAM`), and type."""
        with self._mutex:
            items = list(self._notifications.values())
        filtered: list[TaskNotificationEntity] = []
        for item in items:
            if workspace_id and item.workspace_id != workspace_id:
                continue
            if (
                scope_filter == "PERSONAL"
                and item.scope_kind != "PERSONAL"
                and (viewer_user_id is None or item.claimed_by_user_id != viewer_user_id)
            ):
                continue
            if scope_filter == "TEAM" and item.scope_kind != "TEAM":
                continue
            if notification_type and item.notification_type != notification_type:
                continue
            filtered.append(item)
        return tuple(filtered)

    async def list_notifications_async(
        self,
        *,
        workspace_id: str | None = None,
        scope_filter: Literal["ALL", "PERSONAL", "TEAM"] = "ALL",
        notification_type: NotificationType | None = None,
        viewer_user_id: str | None = None,
    ) -> tuple[TaskNotificationEntity, ...]:
        """List notifications from PG18 filtered by workspace, scope, and type."""
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
        """Compute the amber Sidebar badge counter for pending notifications (`UX-DR2`)."""
        with self._mutex:
            items = list(self._notifications.values())
        return sum(
            1
            for item in items
            if (workspace_id is None or item.workspace_id == workspace_id)
            and item.status in ("OPEN", "CLAIMED")
        )

    async def count_unclaimed_action_required_async(self, workspace_id: str | None = None) -> int:
        """Compute pending notifications badge counter from PG18."""
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
        """Claim a notification by `task_id` (`POST /api/v1/tasks/{task_id}/claim`, `AD-4`)."""
        self._enforce_not_observer(user, instance=instance)
        with self._mutex:
            notif = self._notifications.get(task_id)
        if notif is None:
            raise ResourceNotFoundError(
                detail_override=f"Notification '{task_id}' introuvable.", instance=instance
            )
        return self._claim_notification_entity(
            user,
            notif=notif,
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
        """Claim a notification by `task_id` in PG18 + Redis lock + SSE `< 500 ms`."""
        self._enforce_not_observer(user, instance=instance)
        if not await self._pg_ready():
            return self.claim_by_task_id(
                user,
                task_id=task_id,
                ttl_seconds=ttl_seconds,
                force=force,
                now_utc=now_utc,
                instance=instance,
            )
        assert self._sql_repo is not None
        notif = await self._sql_repo.get_notification(task_id)
        if notif is None:
            raise ResourceNotFoundError(
                detail_override=f"Notification '{task_id}' introuvable.", instance=instance
            )
        return await self._claim_notification_entity_async(
            user,
            notif=notif,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )

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
        """Claim directly by `(run_id, step_execution_id)` (`POST .../steps/{step_id}/claim`)."""
        self._enforce_not_observer(user, instance=instance)
        with self._mutex:
            notif_id = self._by_step_exec_id.get(step_execution_id)
            notif = self._notifications.get(notif_id) if notif_id else None
        if notif is None:
            notif = self.create_notification(
                workspace_id=workspace_id,
                target_team_id=user.primary_org_unit_id,
                target_user_id=None,
                run_id=run_id,
                step_execution_id=step_execution_id,
                step_key=step_key,
                notification_type="HUMAN_ARBITRATION",
                scope_kind="TEAM",
                title=f"Prise en charge directe de l'étape '{step_key}'",
                summary="Verrou de présence acquis depuis le Cockpit.",
            )
        return self._claim_notification_entity(
            user,
            notif=notif,
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
        """Claim directly by `(run_id, step_execution_id)` and persist to PG18."""
        self._enforce_not_observer(user, instance=instance)
        if not await self._pg_ready():
            return self.claim_by_step_execution(
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
        assert self._sql_repo is not None
        notif = await self._sql_repo.get_by_step_execution(step_execution_id)
        if notif is None:
            notif = await self.create_notification_async(
                workspace_id=workspace_id,
                target_team_id=user.primary_org_unit_id,
                target_user_id=None,
                run_id=run_id,
                step_execution_id=step_execution_id,
                step_key=step_key,
                notification_type="HUMAN_ARBITRATION",
                scope_kind="TEAM",
                title=f"Prise en charge directe de l'étape '{step_key}'",
                summary="Verrou de présence acquis depuis le Cockpit.",
            )
        return await self._claim_notification_entity_async(
            user,
            notif=notif,
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
        """Release or `Force Unclaim` a task notification (`UX-DR9`)."""
        self._enforce_not_observer(user, instance=instance)
        now = now_utc or datetime.now(UTC)
        with self._mutex:
            notif = self._notifications.get(task_id)
            if notif is None:
                raise ResourceNotFoundError(
                    detail_override=f"Notification '{task_id}' introuvable.", instance=instance
                )
            self._assert_release_allowed(user, notif, force=force, now=now, instance=instance)
            self.presence_lock.release(
                step_execution_id=notif.step_execution_id, user_id=user.id, force=True
            )
            updated = replace(
                notif,
                status="OPEN",
                claimed_by_user_id=None,
                claimed_by_display_name=None,
                claimed_at=None,
                lock_expires_at=None,
            )
            self._notifications[notif.id] = updated

        sse_evt = self.sse_broker.publish(
            workspace_id=updated.workspace_id,
            event_name="task.claim.released",
            run_id=updated.run_id,
            step_execution_id=updated.step_execution_id,
            payload={
                "task_id": updated.id,
                "step_execution_id": updated.step_execution_id,
                "released_by_user_id": user.id,
                "force": force,
            },
        )
        return ClaimActionOutcome(
            notification=updated,
            lock_record=None,
            sse_event=sse_evt,
            viewer_presence_state="UNCLAIMED",
            peer_presence_state="UNCLAIMED",
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
        """Release or `Force Unclaim` a task notification in PG18 + Redis + SSE."""
        self._enforce_not_observer(user, instance=instance)
        if not await self._pg_ready():
            return self.release_claim(
                user, task_id=task_id, force=force, now_utc=now_utc, instance=instance
            )
        assert self._sql_repo is not None
        now = now_utc or datetime.now(UTC)
        notif = await self._sql_repo.get_notification(task_id)
        if notif is None:
            raise ResourceNotFoundError(
                detail_override=f"Notification '{task_id}' introuvable.", instance=instance
            )
        self._assert_release_allowed(user, notif, force=force, now=now, instance=instance)
        self.presence_lock.release(
            step_execution_id=notif.step_execution_id, user_id=user.id, force=True
        )
        updated = await self._sql_repo.update_claim_state(
            task_id=notif.id,
            status="OPEN",
            claimed_by_user_id=None,
            claimed_by_display_name=None,
            claimed_at=None,
            lock_expires_at=None,
        )
        assert updated is not None
        with self._mutex:
            self._notifications[updated.id] = updated
        sse_evt = await self._publish_sse(
            workspace_id=updated.workspace_id,
            event_name="task.claim.released",
            run_id=updated.run_id,
            step_execution_id=updated.step_execution_id,
            payload={
                "task_id": updated.id,
                "step_execution_id": updated.step_execution_id,
                "released_by_user_id": user.id,
                "force": force,
            },
        )
        return ClaimActionOutcome(
            notification=updated,
            lock_record=None,
            sse_event=sse_evt,
            viewer_presence_state="UNCLAIMED",
            peer_presence_state="UNCLAIMED",
        )

    @staticmethod
    def _assert_release_allowed(
        user: UserIdentity,
        notif: TaskNotificationEntity,
        *,
        force: bool,
        now: datetime,
        instance: str | None,
    ) -> None:
        is_owner = notif.claimed_by_user_id == user.id or (
            notif.claimed_by_display_name is not None
            and notif.claimed_by_display_name == user.display_name
        )
        is_expired = notif.can_force_unclaim(now_utc=now)
        is_privileged = user.platform_role in ("PLATFORM_ADMIN", "TEAM_LEAD")
        if not is_owner and not (force and (is_expired or is_privileged)):
            raise StepClaimNotHeldError(
                detail_override=(
                    f"Impossible de relâcher le verrou sur '{notif.step_execution_id}': "
                    f"détenu par '{notif.claimed_by_display_name}' et non expiré (< 15 min)."
                ),
                instance=instance,
            )

    def verify_step_mutation_allowed(
        self,
        user: UserIdentity,
        *,
        step_execution_id: str,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> None:
        """O(1) guard checking `READ_ONLY_OBSERVER` and active peer locks (`AD-4`, `FR-3`)."""
        self._enforce_not_observer(user, instance=instance)
        active_lock = self.presence_lock.get_lock(step_execution_id, now_utc=now_utc)
        if active_lock is not None and active_lock.holder_user_id != user.id:
            raise StepAlreadyClaimedByPeerError(
                detail_override=(
                    f"Étape '{step_execution_id}' verrouillée par "
                    f"'{active_lock.holder_display_name}' (lock Redis '{active_lock.lock_key}')."
                ),
                instance=instance,
            )

    def _acquire_lock_or_raise(
        self,
        user: UserIdentity,
        *,
        notif: TaskNotificationEntity,
        ttl_seconds: int,
        force: bool,
        now: datetime,
        instance: str | None,
    ) -> StepPresenceLockRecord:
        if ttl_seconds <= 0:
            raise ValidationDomainError(
                detail_override="ttl_seconds doit être strictement positif.", instance=instance
            )
        can_force = force and (
            notif.can_force_unclaim(now_utc=now)
            or user.platform_role in ("PLATFORM_ADMIN", "TEAM_LEAD")
        )
        if (
            notif.status == "CLAIMED"
            and not can_force
            and not notif.can_force_unclaim(now_utc=now)
            and notif.claimed_by_user_id != user.id
            and notif.claimed_by_display_name != user.display_name
        ):
            raise StepAlreadyClaimedByPeerError(
                detail_override=(
                    f"La notification '{notif.id}' (step '{notif.step_execution_id}') est déjà "
                    f"prise en charge par '{notif.claimed_by_display_name}' jusqu'à "
                    f"{notif.lock_expires_at}."
                ),
                instance=instance,
            )
        acquired, lock_rec = self.presence_lock.try_acquire(
            step_execution_id=notif.step_execution_id,
            user_id=user.id,
            display_name=user.display_name,
            ttl_seconds=ttl_seconds,
            force=can_force,
            now_utc=now,
        )
        if not acquired:
            raise StepAlreadyClaimedByPeerError(
                detail_override=(
                    f"La notification '{notif.id}' (step '{notif.step_execution_id}') est déjà "
                    f"prise en charge par '{lock_rec.holder_display_name}' jusqu'à "
                    f"{lock_rec.expires_at_iso}."
                ),
                instance=instance,
            )
        return lock_rec

    def _claim_notification_entity(
        self,
        user: UserIdentity,
        *,
        notif: TaskNotificationEntity,
        ttl_seconds: int,
        force: bool,
        now_utc: datetime | None,
        instance: str | None,
    ) -> ClaimActionOutcome:
        now = now_utc or datetime.now(UTC)
        lock_rec = self._acquire_lock_or_raise(
            user, notif=notif, ttl_seconds=ttl_seconds, force=force, now=now, instance=instance
        )
        with self._mutex:
            updated = replace(
                notif,
                status="CLAIMED",
                claimed_by_user_id=user.id,
                claimed_by_display_name=user.display_name,
                claimed_at=lock_rec.acquired_at_iso,
                lock_expires_at=lock_rec.expires_at_iso,
            )
            self._notifications[notif.id] = updated
        sse_evt = self.sse_broker.publish(
            workspace_id=updated.workspace_id,
            event_name="task.claim.locked",
            run_id=updated.run_id,
            step_execution_id=updated.step_execution_id,
            payload={
                "task_id": updated.id,
                "step_execution_id": updated.step_execution_id,
                "lock_key": lock_rec.lock_key,
                "claimed_by_user_id": user.id,
                "claimed_by_display_name": user.display_name,
                "claimed_at": lock_rec.acquired_at_iso,
                "lock_expires_at": lock_rec.expires_at_iso,
                "peer_state": "CLAIMED_BY_PEER",
                "peer_opacity": 0.85,
            },
        )
        return ClaimActionOutcome(
            notification=updated,
            lock_record=lock_rec,
            sse_event=sse_evt,
            viewer_presence_state="CLAIMED_BY_ME",
            peer_presence_state="CLAIMED_BY_PEER",
        )

    async def _claim_notification_entity_async(
        self,
        user: UserIdentity,
        *,
        notif: TaskNotificationEntity,
        ttl_seconds: int,
        force: bool,
        now_utc: datetime | None,
        instance: str | None,
    ) -> ClaimActionOutcome:
        assert self._sql_repo is not None
        now = now_utc or datetime.now(UTC)
        lock_rec = self._acquire_lock_or_raise(
            user, notif=notif, ttl_seconds=ttl_seconds, force=force, now=now, instance=instance
        )
        updated = await self._sql_repo.update_claim_state(
            task_id=notif.id,
            status="CLAIMED",
            claimed_by_user_id=user.id,
            claimed_by_display_name=user.display_name,
            claimed_at=lock_rec.acquired_at_iso,
            lock_expires_at=lock_rec.expires_at_iso,
        )
        assert updated is not None
        with self._mutex:
            self._notifications[updated.id] = updated
        sse_evt = await self._publish_sse(
            workspace_id=updated.workspace_id,
            event_name="task.claim.locked",
            run_id=updated.run_id,
            step_execution_id=updated.step_execution_id,
            payload={
                "task_id": updated.id,
                "step_execution_id": updated.step_execution_id,
                "lock_key": lock_rec.lock_key,
                "claimed_by_user_id": user.id,
                "claimed_by_display_name": user.display_name,
                "claimed_at": lock_rec.acquired_at_iso,
                "lock_expires_at": lock_rec.expires_at_iso,
                "peer_state": "CLAIMED_BY_PEER",
                "peer_opacity": 0.85,
            },
        )
        return ClaimActionOutcome(
            notification=updated,
            lock_record=lock_rec,
            sse_event=sse_evt,
            viewer_presence_state="CLAIMED_BY_ME",
            peer_presence_state="CLAIMED_BY_PEER",
        )

    @staticmethod
    def _enforce_not_observer(user: UserIdentity, *, instance: str | None = None) -> None:
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=instance)


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
