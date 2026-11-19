"""Supervision runtime helper functions extracted for `< 350` line modularity (`MAJOR-05`)."""

from __future__ import annotations

import inspect
from dataclasses import replace
from typing import Any

from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    build_help_redis_cache_key,
)
from orcia_core.kernel.errors import ResourceNotFoundError
from orcia_core.orchestration._autonomous_supervision_models import (
    AutonomousRunSupervisionItem,
    build_autonomous_notification,
)
from orcia_core.orchestration.presence_and_sse import TaskNotificationEntity


async def restore_help_in_memory_and_flush_redis(
    *,
    help_service: ContextualHelpResolutionService | None,
    redis_client: Any | None,
    help_resource_id: str | None,
) -> str:
    """Restore `@v(N-1)` in `ContextualHelpResolutionService` and delete Redis `help:route:*`."""
    restored_ver = "1.0.0"
    if not help_resource_id or help_service is None:
        return restored_ver
    try:
        if hasattr(help_service, "rollback_to_previous_version_async"):
            restored_art = await help_service.rollback_to_previous_version_async(help_resource_id)
        else:
            restored_art = help_service.rollback_to_previous_version(help_resource_id)
        restored_ver = restored_art.version
        if redis_client is not None:
            pack = restored_art.pack_name or "core"
            for rt in restored_art.bound_routes:
                del_res = redis_client.delete(
                    build_help_redis_cache_key(rt, pack, restored_art.lang)
                )
                if inspect.isawaitable(del_res):
                    await del_res
    except ResourceNotFoundError:
        pass
    return restored_ver


async def flush_redis_keys(redis_client: Any | None, keys: list[str]) -> None:
    """Delete Redis cache keys safely regardless of sync or async Redis client."""
    if redis_client is None or not keys:
        return
    for rkey in keys:
        del_res = redis_client.delete(rkey)
        if inspect.isawaitable(del_res):
            await del_res


def mark_mem_killed(
    runs: dict[str, AutonomousRunSupervisionItem],
    run_id: str,
    mem: AutonomousRunSupervisionItem | None,
    trigger_suspended: bool,
) -> None:
    """Update in-memory run status after an emergency stop."""
    if mem is not None:
        runs[run_id] = replace(
            mem,
            run_status="KILL_SWITCH_STOPPED",
            trigger_status="CIRCUIT_OPEN" if trigger_suspended else mem.trigger_status,
        )


def mark_mem_rolled_back(
    runs: dict[str, AutonomousRunSupervisionItem],
    run_id: str,
    mem: AutonomousRunSupervisionItem | None,
) -> None:
    """Update in-memory run status after `@v(N-1)` rollback (preserving `KILL_SWITCH_STOPPED`)."""
    if mem is not None:
        next_status = (
            "KILL_SWITCH_STOPPED" if mem.run_status == "KILL_SWITCH_STOPPED" else "ROLLED_BACK"
        )
        runs[run_id] = replace(
            mem,
            run_status=next_status,
            post_hoc_status="INVALIDATED_ROLLED_BACK",
            previous_version_available=False,
        )


def apply_trigger_status_on_register(
    notifications: list[TaskNotificationEntity],
    *,
    workspace_id: str,
    run_id: str,
    workflow_id: str,
    trigger_label: str,
    status: str,
    sampled: Any,
) -> str:
    """Record escalation or sampling notifications and return `post_hoc_status`."""
    post_hoc_status = "NONE"
    if status == "COMMITTED_AUTONOMOUS" and sampled is not None:
        post_hoc_status = "PENDING_SAMPLE"
        notifications.append(
            build_autonomous_notification(
                workspace_id=workspace_id,
                run_id=run_id,
                workflow_id=workflow_id,
                trigger_label=trigger_label,
                kind="POST_HOC_AUDIT_SAMPLE",
            )
        )
    if status == "PAUSED_AUTONOMOUS_ESCALATION":
        notifications.append(
            build_autonomous_notification(
                workspace_id=workspace_id,
                run_id=run_id,
                workflow_id=workflow_id,
                trigger_label=trigger_label,
                kind="AUTONOMOUS_ESCALATION",
            )
        )
    return post_hoc_status


def build_kill_switch_event_and_payload(
    *,
    run_id: str,
    workspace_id: str,
    workflow_id: str,
    actor_user_id: str,
    reason: str,
    trigger_id: str | None,
    suspend_trigger: bool,
    trace_id: str,
) -> tuple[Any, dict[str, Any]]:
    """Build `KillSwitchActivated` event and SSE payload metadata."""
    from orcia_core.kernel.events import KillSwitchActivated

    trig_susp = bool(suspend_trigger and trigger_id is not None)
    event = KillSwitchActivated.create(
        run_id=run_id,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        actor_user_id=actor_user_id,
        reason=reason,
        trigger_id=trigger_id,
        trigger_suspended=trig_susp,
        trace_id=trace_id,
    )
    return event, {"run_id": run_id, "status": "KILL_SWITCH_STOPPED"}


def build_rollback_event_and_payload(
    *,
    run_id: str,
    workspace_id: str,
    workflow_id: str,
    actor_user_id: str,
    restored_ver: str,
    help_resource_id: str | None,
    comment: str,
    trace_id: str,
) -> tuple[Any, dict[str, Any]]:
    """Build `AutonomousArtifactRolledBack` event and SSE payload."""
    from orcia_core.kernel.events import AutonomousArtifactRolledBack

    event = AutonomousArtifactRolledBack.create(
        run_id=run_id,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        actor_user_id=actor_user_id,
        restored_version=restored_ver,
        help_resource_id=help_resource_id,
        comment=comment,
        trace_id=trace_id,
    )
    payload = {
        "run_id": run_id,
        "status": "ROLLED_BACK",
        "restored_version": restored_ver,
        "help_resource_id": help_resource_id,
    }
    return event, payload


def make_emergency_stop_outcome(
    *,
    run_id: str,
    workspace_id: str,
    trigger_suspended: bool,
    sse_ms: float,
) -> Any:
    """Build `EmergencyStopOutcome` instance."""
    from orcia_core.orchestration._autonomous_supervision_models import EmergencyStopOutcome

    return EmergencyStopOutcome(
        run_id=run_id,
        workspace_id=workspace_id,
        status="KILL_SWITCH_STOPPED",
        trigger_suspended=trigger_suspended,
        sse_dispatch_latency_ms=sse_ms,
    )


def make_rollback_outcome(
    *,
    run_id: str,
    workspace_id: str,
    restored_ver: str,
    help_resource_id: str | None,
    redis_ms: float,
    sse_ms: float,
    status: str = "ROLLED_BACK",
) -> Any:
    """Build `InvalidateAndRestoreOutcome` instance."""
    from orcia_core.orchestration._autonomous_supervision_models import InvalidateAndRestoreOutcome

    return InvalidateAndRestoreOutcome(
        run_id=run_id,
        workspace_id=workspace_id,
        status=status,
        restored_version=restored_ver,
        help_resource_id=help_resource_id,
        redis_cache_invalidated_ms=redis_ms,
        sse_dispatch_latency_ms=sse_ms,
    )


async def execute_validated_post_hoc_review(
    *,
    post_hoc: Any,
    runs_mem: dict[str, AutonomousRunSupervisionItem],
    mem: AutonomousRunSupervisionItem | None,
    pg_row: dict[str, Any] | None,
    run_id: str,
    actor_user_id: str,
    comment: str,
    workspace_id: str,
    contract_id: str,
) -> dict[str, Any]:
    """Record a `VALIDATED` post-hoc audit review and update in-memory cache."""
    rec = await post_hoc.record_review(
        run_id=run_id,
        decision="VALIDATED",
        reviewer_user_id=actor_user_id,
        review_comment=comment or None,
        workspace_id=workspace_id,
        contract_id=contract_id or None,
    )
    if mem is not None:
        runs_mem[run_id] = replace(mem, post_hoc_status="VALIDATED")
    return {
        "run_id": run_id,
        "review_status": rec.review_status if rec else "VALIDATED",
        "run_status": mem.run_status if mem else str(pg_row["run_status"]),  # type: ignore[index]
        "restored_version": None,
    }
