"""Emergency stop & rollback execution helpers for `AutonomousSupervisionService`."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from orcia_core.orchestration._autonomous_supervision_models import (
    EmergencyStopOutcome,
    InvalidateAndRestoreOutcome,
    resolve_help_id_from_context,
)
from orcia_core.orchestration._autonomous_supervision_ops import (
    build_kill_switch_event_and_payload,
    build_rollback_event_and_payload,
    flush_redis_keys,
    make_emergency_stop_outcome,
    make_rollback_outcome,
    mark_mem_killed,
    mark_mem_rolled_back,
    restore_help_in_memory_and_flush_redis,
)
from orcia_core.orchestration._internal.sql_autonomous_supervision import (
    apply_emergency_stop_sql,
    restore_help_article_and_rollback_run_sql,
)
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService


async def execute_emergency_stop(
    svc: AutonomousSupervisionService,
    *,
    run_id: str,
    actor_user_id: str,
    reason: str,
    suspend_trigger: bool,
    trace_id: str,
) -> EmergencyStopOutcome:
    """Trigger immediate emergency stop (`KILL_SWITCH_STOPPED`) + optional trigger pause."""
    mem, pg_row, ws_id, wf_id, _c_id, trig_id = await svc._load_run_context(run_id)
    event, sse_payload = build_kill_switch_event_and_payload(
        run_id=run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        actor_user_id=actor_user_id,
        reason=reason,
        trigger_id=trig_id,
        suspend_trigger=suspend_trigger,
        trace_id=trace_id,
    )
    trigger_suspended = False
    if svc._engine is not None and pg_row is not None:
        res = await apply_emergency_stop_sql(
            svc._engine,
            run_id=run_id,
            suspend_trigger=suspend_trigger,
            event=event,
            audit_sink=svc._audit_sink,
        )
        trigger_suspended = bool(res["trigger_suspended"]) if res is not None else False
    elif suspend_trigger and trig_id is not None:
        trigger_suspended = True
    mark_mem_killed(svc._runs, run_id, mem, trigger_suspended)
    svc._post_hoc.register_in_memory_run(
        run_id=run_id, workspace_id=ws_id, status="KILL_SWITCH_STOPPED"
    )
    svc._outbox_events.append(event)
    sse_payload["trigger_suspended"] = trigger_suspended
    sse_ms = svc._publish_sse(ws_id, "autonomous.run.killed", run_id, sse_payload)
    return make_emergency_stop_outcome(  # type: ignore[no-any-return]
        run_id=run_id,
        workspace_id=ws_id,
        trigger_suspended=trigger_suspended,
        sse_ms=sse_ms,
    )


async def execute_invalidate_and_restore(
    svc: AutonomousSupervisionService,
    *,
    run_id: str,
    actor_user_id: str,
    comment: str,
    help_resource_id: str | None,
    trace_id: str,
) -> InvalidateAndRestoreOutcome:
    """Invalidate an autonomous deliverable/help article and restore `@v(N-1)` + flush Redis."""
    mem, pg_row, ws_id, wf_id, contract_id, _trig_id = await svc._load_run_context(run_id)
    resolved_help_id = resolve_help_id_from_context(help_resource_id, mem, pg_row)
    t_cache = time.perf_counter()
    restored_ver = await restore_help_in_memory_and_flush_redis(
        help_service=svc._help_service,
        redis_client=svc._redis,
        help_resource_id=resolved_help_id,
    )
    event, sse_payload = build_rollback_event_and_payload(
        run_id=run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        actor_user_id=actor_user_id,
        restored_ver=restored_ver,
        help_resource_id=resolved_help_id,
        comment=comment,
        trace_id=trace_id,
    )
    effective_status = (
        "KILL_SWITCH_STOPPED"
        if (pg_row is not None and str(pg_row.get("run_status") or "") == "KILL_SWITCH_STOPPED")
        or (mem is not None and mem.run_status == "KILL_SWITCH_STOPPED")
        else "ROLLED_BACK"
    )
    if svc._engine is not None and pg_row is not None:
        res = await restore_help_article_and_rollback_run_sql(
            svc._engine,
            run_id=run_id,
            reviewer_user_id=actor_user_id,
            comment=comment or None,
            help_resource_id=resolved_help_id,
            contract_id=contract_id or None,
            event=event,
            audit_sink=svc._audit_sink,
        )
        if res is not None:
            effective_status = str(res["status"])
            restored_ver = str(res["restored_version"])
            resolved_help_id = res["help_resource_id"]
            await flush_redis_keys(svc._redis, list(res["invalidated_redis_keys"]))
    else:
        await svc._post_hoc.record_review(
            run_id=run_id,
            decision="INVALIDATED_ROLLED_BACK",
            reviewer_user_id=actor_user_id,
            review_comment=comment or None,
            workspace_id=ws_id,
            contract_id=contract_id or new_uuid7_str(),
        )
    redis_ms = round((time.perf_counter() - t_cache) * 1000.0, 3)
    mark_mem_rolled_back(svc._runs, run_id, mem)
    svc._post_hoc.register_in_memory_run(run_id=run_id, workspace_id=ws_id, status=effective_status)
    svc._outbox_events.append(event)
    sse_payload["status"] = effective_status
    sse_payload["restored_version"] = restored_ver
    sse_payload["help_resource_id"] = resolved_help_id
    sse_ms = svc._publish_sse(ws_id, "autonomous.artifact.rolled_back", run_id, sse_payload)
    return make_rollback_outcome(  # type: ignore[no-any-return]
        run_id=run_id,
        workspace_id=ws_id,
        restored_ver=restored_ver,
        help_resource_id=resolved_help_id,
        redis_ms=redis_ms,
        sse_ms=sse_ms,
        status=effective_status,
    )


__all__ = ["execute_emergency_stop", "execute_invalidate_and_restore"]
