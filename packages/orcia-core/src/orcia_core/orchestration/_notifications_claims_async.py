"""Async PG18 seed, claim, and release helpers for `UnifiedNotificationAndClaimService`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from orcia_core.orchestration._notifications_claims_seeds import second_seed_step_id
from orcia_core.orchestration._orchestration_cc_notif_locales import get_notif_copy
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.orchestration.presence_and_sse import (
    ClaimActionOutcome,
    TaskNotificationEntity,
)
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration.notifications_and_claims import (
        UnifiedNotificationAndClaimService,
    )


async def seed_default_notifications_async_impl(
    svc: UnifiedNotificationAndClaimService,
    *,
    workspace_id: str,
    team_id: str,
    user_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
) -> tuple[TaskNotificationEntity, ...]:
    if not await svc._pg_ready():
        return svc.seed_default_notifications(
            workspace_id=workspace_id,
            team_id=team_id,
            user_id=user_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
        )
    assert svc._sql_repo is not None
    if await svc._sql_repo.count_all() > 0:
        return await svc._sql_repo.list_notifications(workspace_id=workspace_id)
    nc = get_notif_copy()
    n1 = await svc.create_notification_async(
        workspace_id=workspace_id,
        target_team_id=team_id,
        target_user_id=None,
        run_id=run_id,
        step_execution_id=step_execution_id,
        step_key=step_key,
        notification_type="HUMAN_ARBITRATION",
        scope_kind="TEAM",
        title=nc["arb_title"],
        summary=nc["arb_summary"],
        source_event_id="0195f000-0000-7000-8000-000000009101",
    )
    n2 = await svc.create_notification_async(
        workspace_id=workspace_id,
        target_team_id=team_id,
        target_user_id=user_id,
        run_id=run_id,
        step_execution_id=second_seed_step_id(step_execution_id),
        step_key="security-human-gate",
        notification_type="HUMAN_GATE",
        scope_kind="PERSONAL",
        title=nc["gate_title"],
        summary=nc["gate_summary"],
        source_event_id="0195f000-0000-7000-8000-000000009102",
    )
    return (n1, n2)


async def claim_notification_entity_async_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    notif: TaskNotificationEntity,
    ttl_seconds: int,
    force: bool,
    now_utc: datetime | None,
    instance: str | None,
) -> ClaimActionOutcome:
    assert svc._sql_repo is not None
    now = now_utc or datetime.now(UTC)
    lock_rec = svc._acquire_lock_or_raise(
        user, notif=notif, ttl_seconds=ttl_seconds, force=force, now=now, instance=instance
    )
    updated = await svc._sql_repo.update_claim_state(
        task_id=notif.id,
        status="CLAIMED",
        claimed_by_user_id=user.id,
        claimed_by_display_name=user.display_name,
        claimed_at=lock_rec.acquired_at_iso,
        lock_expires_at=lock_rec.expires_at_iso,
    )
    assert updated is not None
    with svc._mutex:
        svc._notifications[updated.id] = updated
    sse_evt = await svc._publish_sse(
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


async def release_claim_async_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    task_id: str,
    force: bool,
    now_utc: datetime | None,
    instance: str | None,
) -> ClaimActionOutcome:
    svc._enforce_not_observer(user, instance=instance)
    if not await svc._pg_ready():
        return svc.release_claim(
            user, task_id=task_id, force=force, now_utc=now_utc, instance=instance
        )
    assert svc._sql_repo is not None
    now = now_utc or datetime.now(UTC)
    notif = await svc._sql_repo.get_notification(task_id)
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
    updated = await svc._sql_repo.update_claim_state(
        task_id=notif.id,
        status="OPEN",
        claimed_by_user_id=None,
        claimed_by_display_name=None,
        claimed_at=None,
        lock_expires_at=None,
    )
    assert updated is not None
    with svc._mutex:
        svc._notifications[updated.id] = updated
    sse_evt = await svc._publish_sse(
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


async def claim_by_task_id_async_impl(
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
    if not await svc._pg_ready():
        return svc.claim_by_task_id(
            user,
            task_id=task_id,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )
    assert svc._sql_repo is not None
    notif = await svc._sql_repo.get_notification(task_id)
    if notif is None:
        raise ResourceNotFoundError(
            detail_code="ERR_NOTIFICATION_NOT_FOUND",
            detail_params={"task_id": task_id},
            instance=instance,
        )
    return await svc._claim_notification_entity_async(
        user,
        notif=notif,
        ttl_seconds=ttl_seconds,
        force=force,
        now_utc=now_utc,
        instance=instance,
    )


async def claim_by_step_execution_async_impl(
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
    if not await svc._pg_ready():
        return svc.claim_by_step_execution(
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
    assert svc._sql_repo is not None
    notif = await svc._sql_repo.get_by_step_execution(step_execution_id)
    if notif is None:
        notif = await svc.create_notification_async(
            workspace_id=workspace_id,
            target_team_id=user.primary_org_unit_id,
            target_user_id=None,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            notification_type="HUMAN_ARBITRATION",
            scope_kind="TEAM",
            title=svc._format_step_claim_title(step_key),
            summary=get_notif_copy()["lock_acquired_cockpit"],
        )
    return await svc._claim_notification_entity_async(
        user,
        notif=notif,
        ttl_seconds=ttl_seconds,
        force=force,
        now_utc=now_utc,
        instance=instance,
    )


__all__ = [
    "claim_by_step_execution_async_impl",
    "claim_by_task_id_async_impl",
    "claim_notification_entity_async_impl",
    "release_claim_async_impl",
    "seed_default_notifications_async_impl",
]
