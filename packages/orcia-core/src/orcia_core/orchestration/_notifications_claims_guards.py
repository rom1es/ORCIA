"""Claim/release authorization guards for `UnifiedNotificationAndClaimService`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    StepAlreadyClaimedByPeerError,
    StepClaimNotHeldError,
)
from orcia_core.orchestration.presence_and_sse import StepPresenceLockRecord, TaskNotificationEntity
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration.notifications_and_claims import (
        ClaimActionOutcome,
        UnifiedNotificationAndClaimService,
    )


def assert_release_allowed_impl(
    user: UserIdentity,
    notif: TaskNotificationEntity,
    *,
    force: bool,
    now: datetime,
    instance: str | None,
) -> None:
    """Assert that `user` is permitted to release the step claim."""
    is_owner = notif.claimed_by_user_id == user.id or (
        notif.claimed_by_display_name is not None
        and notif.claimed_by_display_name == user.display_name
    )
    is_expired = notif.can_force_unclaim(now_utc=now)
    is_privileged = user.platform_role in ("PLATFORM_ADMIN", "TEAM_LEAD")
    if not is_owner and not (force and (is_expired or is_privileged)):
        raise StepClaimNotHeldError(
            detail_code="ERR_CLAIM_RELEASE_FORBIDDEN",
            detail_params={
                "step_id": notif.step_execution_id,
                "holder": notif.claimed_by_display_name or "",
            },
            instance=instance,
        )


def verify_step_mutation_allowed_impl(
    svc: UnifiedNotificationAndClaimService,
    user: UserIdentity,
    *,
    step_execution_id: str,
    now_utc: datetime | None,
    instance: str | None,
) -> None:
    """Assert `user` holds (or is not blocked by) any active peer lock on `step_execution_id`."""
    svc._enforce_not_observer(user, instance=instance)
    active_lock = svc.presence_lock.get_lock(step_execution_id, now_utc=now_utc)
    if active_lock is not None and active_lock.holder_user_id != user.id:
        raise StepAlreadyClaimedByPeerError(
            detail_code="ERR_STEP_LOCKED_BY_PEER",
            detail_params={
                "step_id": step_execution_id,
                "holder": active_lock.holder_display_name,
                "lock_key": active_lock.lock_key,
            },
            instance=instance,
        )


class NotificationClaimInternalMixin:
    """Internal guard & lock delegation methods for `UnifiedNotificationAndClaimService`."""

    @staticmethod
    def _assert_release_allowed(
        user: UserIdentity,
        notif: TaskNotificationEntity,
        *,
        force: bool,
        now: datetime,
        instance: str | None,
    ) -> None:
        assert_release_allowed_impl(user, notif, force=force, now=now, instance=instance)

    def verify_step_mutation_allowed(
        self,
        user: UserIdentity,
        *,
        step_execution_id: str,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> None:
        verify_step_mutation_allowed_impl(
            self,  # type: ignore[arg-type]
            user,
            step_execution_id=step_execution_id,
            now_utc=now_utc,
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
        from orcia_core.orchestration._notifications_claims_helpers import (
            acquire_lock_or_raise_impl,
        )

        return acquire_lock_or_raise_impl(
            self,  # type: ignore[arg-type]
            user,
            notif=notif,
            ttl_seconds=ttl_seconds,
            force=force,
            now=now,
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
        from orcia_core.orchestration._notifications_claims_helpers import (
            claim_notification_entity_impl,
        )

        return claim_notification_entity_impl(
            self,  # type: ignore[arg-type]
            user,
            notif=notif,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
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
        from orcia_core.orchestration._notifications_claims_async import (
            claim_notification_entity_async_impl,
        )

        return await claim_notification_entity_async_impl(
            self,  # type: ignore[arg-type]
            user,
            notif=notif,
            ttl_seconds=ttl_seconds,
            force=force,
            now_utc=now_utc,
            instance=instance,
        )

    @staticmethod
    def _enforce_not_observer(user: UserIdentity, *, instance: str | None = None) -> None:
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=instance)
