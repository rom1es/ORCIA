"""Seeding, creation & outbox translation helpers for `UnifiedNotificationAndClaimService`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from orcia_core.orchestration._internal.sql_task_notifications import coerce_uuid
from orcia_core.orchestration._orchestration_cc_notif_locales import get_notif_copy
from orcia_core.orchestration.presence_and_sse import (
    NotificationScopeKind,
    NotificationType,
    TaskNotificationEntity,
    translate_outbox_event_spec,
)
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.notifications_and_claims import (
        UnifiedNotificationAndClaimService,
    )


def second_seed_step_id(step_execution_id: str) -> str:
    if step_execution_id == "0195f000-0000-7000-8000-000000000801":
        return "0195f000-0000-7000-8000-000000000802"
    return str(coerce_uuid(f"{step_execution_id}-gate"))


def format_step_claim_title(step_key: str) -> str:
    nc = get_notif_copy()
    if step_key == "inbox-review-step":
        return nc["claim_inbox"]
    readable = step_key.replace("-", " ").replace("_", " ").strip().title()
    return nc["claim_prefix"].format(readable=readable)


def seed_default_notifications_impl(
    svc: UnifiedNotificationAndClaimService,
    *,
    workspace_id: str,
    team_id: str,
    user_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
) -> tuple[TaskNotificationEntity, ...]:
    with svc._mutex:
        if svc._notifications:
            return tuple(svc._notifications.values())
    nc = get_notif_copy()
    n1 = svc.create_notification(
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
    )
    n2 = svc.create_notification(
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
    )
    return (n1, n2)


def create_notification_impl(
    svc: UnifiedNotificationAndClaimService,
    *,
    workspace_id: str,
    target_team_id: str | None,
    target_user_id: str | None,
    run_id: str,
    step_execution_id: str,
    step_key: str,
    notification_type: NotificationType,
    scope_kind: NotificationScopeKind,
    title: str,
    summary: str,
    source_event_id: str | None,
) -> TaskNotificationEntity:
    with svc._mutex:
        if source_event_id and source_event_id in svc._by_source_event_id:
            return svc._notifications[svc._by_source_event_id[source_event_id]]
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
        svc._notifications[notif_id] = entity
        svc._by_step_exec_id[step_execution_id] = notif_id
        if source_event_id:
            svc._by_source_event_id[source_event_id] = notif_id
    svc.sse_broker.publish(
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


def consume_outbox_event_impl(
    svc: UnifiedNotificationAndClaimService,
    event: DomainEvent,
    *,
    default_team_id: str | None,
    default_user_id: str | None,
) -> TaskNotificationEntity | None:
    spec = translate_outbox_event_spec(event.event_type, event.payload)
    if spec is None:
        return None
    ntype, title, summary = spec
    return svc.create_notification(
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


async def consume_outbox_event_async_impl(
    svc: UnifiedNotificationAndClaimService,
    event: DomainEvent,
    *,
    default_team_id: str | None,
    default_user_id: str | None,
) -> TaskNotificationEntity | None:
    spec = translate_outbox_event_spec(event.event_type, event.payload)
    if spec is None:
        return None
    ntype, title, summary = spec
    return await svc.create_notification_async(
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


async def create_notification_async_impl(
    svc: UnifiedNotificationAndClaimService,
    *,
    workspace_id: str,
    target_team_id: str | None,
    target_user_id: str | None,
    run_id: str,
    step_execution_id: str,
    step_key: str,
    notification_type: NotificationType,
    scope_kind: NotificationScopeKind,
    title: str,
    summary: str,
    source_event_id: str | None,
) -> TaskNotificationEntity:
    if not await svc._pg_ready():
        return svc.create_notification(
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
    assert svc._sql_repo is not None
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
    persisted = await svc._sql_repo.insert_or_get_notification(draft)
    with svc._mutex:
        svc._notifications[persisted.id] = persisted
        svc._by_step_exec_id[persisted.step_execution_id] = persisted.id
        if persisted.source_event_id:
            svc._by_source_event_id[persisted.source_event_id] = persisted.id
    await svc._publish_sse(
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


def list_notifications_impl(
    svc: UnifiedNotificationAndClaimService,
    *,
    workspace_id: str | None,
    scope_filter: str,
    notification_type: NotificationType | None,
    viewer_user_id: str | None,
) -> tuple[TaskNotificationEntity, ...]:
    with svc._mutex:
        items = list(svc._notifications.values())
    return tuple(
        item
        for item in items
        if (not workspace_id or item.workspace_id == workspace_id)
        and not (
            scope_filter == "PERSONAL"
            and item.scope_kind != "PERSONAL"
            and (viewer_user_id is None or item.claimed_by_user_id != viewer_user_id)
        )
        and not (scope_filter == "TEAM" and item.scope_kind != "TEAM")
        and (not notification_type or item.notification_type == notification_type)
    )


def count_unclaimed_action_required_impl(
    svc: UnifiedNotificationAndClaimService, workspace_id: str | None
) -> int:
    with svc._mutex:
        items = list(svc._notifications.values())
    return sum(
        1
        for item in items
        if (workspace_id is None or item.workspace_id == workspace_id)
        and item.status in ("OPEN", "CLAIMED")
    )


__all__ = [
    "consume_outbox_event_async_impl",
    "consume_outbox_event_impl",
    "count_unclaimed_action_required_impl",
    "create_notification_async_impl",
    "create_notification_impl",
    "format_step_claim_title",
    "list_notifications_impl",
    "second_seed_step_id",
    "seed_default_notifications_impl",
]
