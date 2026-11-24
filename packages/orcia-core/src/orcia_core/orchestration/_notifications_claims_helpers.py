"""Sync claim, lock & release helper operations for `UnifiedNotificationAndClaimService`."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from orcia_core.orchestration._notifications_claims_guards import (
    assert_release_allowed_impl,
    verify_step_mutation_allowed_impl,
)
from orcia_core.orchestration._notifications_claims_seeds import (
    format_step_claim_title,
)
from orcia_core.orchestration._orchestration_cc_notif_locales import get_notif_copy
from orcia_core.orchestration.errors import (
    ResourceNotFoundError,
    StepAlreadyClaimedByPeerError,
    ValidationDomainError,
)
from orcia_core.orchestration.presence_and_sse import (
    ClaimActionOutcome,
    StepPresenceLockRecord,
    TaskNotificationEntity,
)
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration.notifications_and_claims import (
        UnifiedNotificationAndClaimService,
    )


def acquire_lock_or_raise_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    notif: TaskNotificationEntity,
    ttl_seconds: int,
    force: bool,
    now: datetime,
    instance: str | None,
) -> StepPresenceLockRecord:
    if ttl_seconds <= 0:
        raise ValidationDomainError(detail_code="ERR_TTL_MUST_BE_POSITIVE", instance=instance)
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
            detail_code="ERR_NOTIFICATION_ALREADY_CLAIMED",
            detail_params={
                "notif_id": notif.id,
                "step_id": notif.step_execution_id,
                "holder": notif.claimed_by_display_name or "",
                "expires_at": notif.lock_expires_at or "",
            },
            instance=instance,
        )
    acquired, lock_rec = svc.presence_lock.try_acquire(
        step_execution_id=notif.step_execution_id,
        user_id=user.id,
        display_name=user.display_name,
        ttl_seconds=ttl_seconds,
        force=can_force,
        now_utc=now,
    )
    if not acquired:
        raise StepAlreadyClaimedByPeerError(
            detail_code="ERR_NOTIFICATION_ALREADY_CLAIMED",
            detail_params={
                "notif_id": notif.id,
                "step_id": notif.step_execution_id,
                "holder": lock_rec.holder_display_name,
                "expires_at": lock_rec.expires_at_iso,
            },
            instance=instance,
        )
    return lock_rec


def claim_notification_entity_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    notif: TaskNotificationEntity,
    ttl_seconds: int,
    force: bool,
    now_utc: datetime | None,
    instance: str | None,
) -> ClaimActionOutcome:
    now = now_utc or datetime.now(UTC)
    lock_rec = svc._acquire_lock_or_raise(
        user, notif=notif, ttl_seconds=ttl_seconds, force=force, now=now, instance=instance
    )
    with svc._mutex:
        updated = replace(
            notif,
            status="CLAIMED",
            claimed_by_user_id=user.id,
            claimed_by_display_name=user.display_name,
            claimed_at=lock_rec.acquired_at_iso,
            lock_expires_at=lock_rec.expires_at_iso,
        )
        svc._notifications[notif.id] = updated
    sse_evt = svc.sse_broker.publish(
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


def claim_by_step_execution_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    run_id: str,
    step_execution_id: str,
    workspace_id: str,
    step_key: str,
    ttl_seconds: int,
    force: bool,
    now_utc: datetime | None,
    instance: str | None,
) -> ClaimActionOutcome:
    svc._enforce_not_observer(user, instance=instance)
    with svc._mutex:
        notif_id = svc._by_step_exec_id.get(step_execution_id)
        notif = svc._notifications.get(notif_id) if notif_id else None
    if notif is None:
        notif = svc.create_notification(
            workspace_id=workspace_id,
            target_team_id=user.primary_org_unit_id,
            target_user_id=None,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            notification_type="HUMAN_ARBITRATION",
            scope_kind="TEAM",
            title=format_step_claim_title(step_key),
            summary=get_notif_copy()["lock_acquired_cockpit"],
        )
    return svc._claim_notification_entity(
        user,
        notif=notif,
        ttl_seconds=ttl_seconds,
        force=force,
        now_utc=now_utc,
        instance=instance,
    )


def release_claim_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    task_id: str,
    force: bool,
    now_utc: datetime | None,
    instance: str | None,
) -> ClaimActionOutcome:
    svc._enforce_not_observer(user, instance=instance)
    now = now_utc or datetime.now(UTC)
    with svc._mutex:
        notif = svc._notifications.get(task_id)
        if notif is None:
            raise ResourceNotFoundError(
                detail_code="ERR_NOTIFICATION_NOT_FOUND",
                detail_params={"task_id": task_id},
                instance=instance,
            )
        svc._assert_release_allowed(user, notif, force=force, now=now, instance=instance)
        svc.presence_lock.release(
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
        svc._notifications[notif.id] = updated

    sse_evt = svc.sse_broker.publish(
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


def claim_by_task_id_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    task_id: str,
    ttl_seconds: int,
    force: bool,
    now_utc: datetime | None,
    instance: str | None,
) -> ClaimActionOutcome:
    svc._enforce_not_observer(user, instance=instance)
    with svc._mutex:
        notif = svc._notifications.get(task_id)
    if notif is None:
        raise ResourceNotFoundError(
            detail_code="ERR_NOTIFICATION_NOT_FOUND",
            detail_params={"task_id": task_id},
            instance=instance,
        )
    return svc._claim_notification_entity(
        user,
        notif=notif,
        ttl_seconds=ttl_seconds,
        force=force,
        now_utc=now_utc,
        instance=instance,
    )


__all__ = [
    "acquire_lock_or_raise_impl",
    "assert_release_allowed_impl",
    "claim_by_step_execution_impl",
    "claim_by_task_id_impl",
    "claim_notification_entity_impl",
    "release_claim_impl",
    "verify_step_mutation_allowed_impl",
]
