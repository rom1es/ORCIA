"""Unified Notification Inbox, Outbox Subscriber & Presence Claim Service (`Story 5.1`, `AD-4`)."""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal

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


class UnifiedNotificationAndClaimService:
    """Unified Notification Inbox, Outbox consumer & atomic SSE Claim coordinator (`Story 5.1`)."""

    def __init__(
        self,
        *,
        presence_lock: StepPresenceLockPort | None = None,
        sse_broker: SseBroadcastPort | None = None,
    ) -> None:
        self.presence_lock = presence_lock or InMemoryStepPresenceLockAdapter()
        self.sse_broker = sse_broker or InMemorySseBrokerAdapter()
        self._mutex = threading.Lock()
        self._notifications: dict[str, TaskNotificationEntity] = {}
        self._by_step_exec_id: dict[str, str] = {}
        self._by_source_event_id: dict[str, str] = {}

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
            step_execution_id=f"{step_execution_id}-gate",
            step_key="security-human-gate",
            notification_type="HUMAN_GATE",
            scope_kind="PERSONAL",
            title="🛡️ Gate Humaine Adaptative — Revue du Briefing 4 blocs",
            summary="Validation par découpage attendue sur le livrable de sécurité.",
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
            is_owner = notif.claimed_by_user_id == user.id
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
            self.presence_lock.release(
                step_execution_id=notif.step_execution_id,
                user_id=user.id,
                force=True,
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
        if ttl_seconds <= 0:
            raise ValidationDomainError(
                detail_override="ttl_seconds doit être strictement positif.", instance=instance
            )
        can_force = force and (
            notif.can_force_unclaim(now_utc=now)
            or user.platform_role in ("PLATFORM_ADMIN", "TEAM_LEAD")
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
