"""Autonomous Run Supervision, Emergency Stop & `@v(N-1)` Restore (`Story 7.4`, `AD-18`).

Orchestrates:
- Listing autonomous contract runs per workspace (grouped by trigger in UI).
- 1-click Emergency Stop (`KILL_SWITCH_STOPPED`) checked at `@DBOS.step` + SSE `< 500 ms`.
- 1-click Invalidate & Restore `@v(N-1)` (`HELP_ARTICLE` in `catalog_items` + Redis `< 10 ms`).
- Post-hoc quality sampling review (`VALIDATED` vs `INVALIDATED_ROLLED_BACK`).
"""

from __future__ import annotations

import inspect
import time
from dataclasses import replace
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.catalog.contextual_help import ContextualHelpResolutionService
from orcia_core.kernel.events import (
    AutonomousArtifactRolledBack,
    DomainEvent,
    KillSwitchActivated,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration._autonomous_supervision_models import (
    AutonomousRunSupervisionItem,
    EmergencyStopOutcome,
    InvalidateAndRestoreOutcome,
    build_autonomous_notification,
    make_registered_supervision_item,
    map_pg_row_to_supervision_item,
    resolve_run_context,
    restore_help_in_memory_and_flush_redis,
)
from orcia_core.orchestration._internal.sql_autonomous_supervision import (
    apply_emergency_stop_sql,
    get_autonomous_run_sql,
    is_run_kill_switch_stopped_sql,
    list_autonomous_runs_sql,
    restore_help_article_and_rollback_run_sql,
)
from orcia_core.orchestration.presence_and_sse import (
    InMemorySseBrokerAdapter,
    SseBroadcastPort,
    TaskNotificationEntity,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort


class AutonomousSupervisionService:
    """Domain service supervising autonomous runs, emergency stop & `@v(N-1)` rollback."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None = None,
        redis_client: Any | None = None,
        post_hoc_service: PostHocAuditService | None = None,
        help_service: ContextualHelpResolutionService | None = None,
        sse_broker: SseBroadcastPort | None = None,
        audit_sink: AuditLedgerSinkPort | None = None,
    ) -> None:
        self._engine = engine
        self._redis = redis_client
        self._post_hoc = post_hoc_service or PostHocAuditService(
            engine=engine, audit_sink=audit_sink
        )
        self._help_service = help_service
        self._sse = sse_broker or InMemorySseBrokerAdapter()
        self._audit_sink = audit_sink
        self._runs: dict[str, AutonomousRunSupervisionItem] = {}
        self._notifications: list[TaskNotificationEntity] = []
        self._outbox_events: list[DomainEvent] = []

    @property
    def post_hoc_service(self) -> PostHocAuditService:
        return self._post_hoc

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._outbox_events)

    @property
    def notifications(self) -> tuple[TaskNotificationEntity, ...]:
        return tuple(self._notifications)

    async def is_run_stopped(self, run_id: str) -> bool:
        """Step-boundary guard (`AD-21.5`): check if `KILL_SWITCH_STOPPED` was requested."""
        mem = self._runs.get(run_id)
        if mem is not None and mem.run_status == "KILL_SWITCH_STOPPED":
            return True
        if self._engine is not None:
            return await is_run_kill_switch_stopped_sql(self._engine, run_id=run_id)
        return False

    async def _load_run_context(
        self, run_id: str
    ) -> tuple[
        AutonomousRunSupervisionItem | None,
        dict[str, Any] | None,
        str,
        str,
        str,
        str | None,
    ]:
        mem = self._runs.get(run_id)
        pg_row = (
            await get_autonomous_run_sql(self._engine, run_id=run_id)
            if self._engine is not None
            else None
        )
        ws_id, wf_id, contract_id, trig_id = resolve_run_context(run_id, mem, pg_row)
        return mem, pg_row, ws_id, wf_id, contract_id, trig_id

    async def register_autonomous_run(
        self,
        *,
        run_id: str,
        workspace_id: str,
        workflow_id: str,
        contract_id: str,
        status: str,
        trigger_id: str | None = None,
        trigger_label: str = "Exécution sous contrat",
        trigger_type: str = "MANUAL_AUTONOMOUS",
        trigger_status: str = "ACTIVE",
        sampling_rate: Decimal | float = Decimal("0.15"),
        cost_usd: Decimal = Decimal("0.050000"),
        help_resource_id: str | None = None,
        force_post_hoc_sample: bool = False,
        trace_id: str = "00000000000000000000000000000000",
    ) -> AutonomousRunSupervisionItem:
        """Track an autonomous run, sample post-hoc (`10-20%`) on commit & emit priority alerts."""
        self._post_hoc.register_in_memory_run(
            run_id=run_id, workspace_id=workspace_id, status=status, cost_usd=cost_usd
        )
        post_hoc_status = "NONE"
        if status == "COMMITTED_AUTONOMOUS":
            sampled = await self._post_hoc.maybe_sample_committed_run(
                run_id=run_id,
                workspace_id=workspace_id,
                contract_id=contract_id,
                workflow_id=workflow_id,
                sampling_rate=sampling_rate,
                force_select=force_post_hoc_sample,
                trigger_label=trigger_label,
                trace_id=trace_id,
            )
            if sampled is not None:
                post_hoc_status = "PENDING_SAMPLE"
                self._append_notif(
                    workspace_id, run_id, workflow_id, trigger_label, "POST_HOC_AUDIT_SAMPLE"
                )
        if status == "PAUSED_AUTONOMOUS_ESCALATION":
            self._append_notif(
                workspace_id, run_id, workflow_id, trigger_label, "AUTONOMOUS_ESCALATION"
            )
        item = make_registered_supervision_item(
            run_id=run_id,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            contract_id=contract_id,
            status=status,
            trigger_id=trigger_id,
            trigger_label=trigger_label,
            trigger_type=trigger_type,
            trigger_status=trigger_status,
            post_hoc_status=post_hoc_status,
            cost_usd=cost_usd,
            help_resource_id=help_resource_id,
        )
        self._runs[run_id] = item
        return item

    def _append_notif(
        self, workspace_id: str, run_id: str, workflow_id: str, trigger_label: str, kind: str
    ) -> None:
        self._notifications.append(
            build_autonomous_notification(
                workspace_id=workspace_id,
                run_id=run_id,
                workflow_id=workflow_id,
                trigger_label=trigger_label,
                kind=kind,
            )
        )

    def _publish_sse(
        self, workspace_id: str, event_name: str, run_id: str, payload: dict[str, Any]
    ) -> float:
        return self._sse.publish(
            workspace_id=workspace_id,
            event_name=event_name,
            run_id=run_id,
            step_execution_id=run_id,
            payload=payload,
        ).dispatch_latency_ms

    async def list_autonomous_runs(
        self, *, workspace_id: str
    ) -> list[AutonomousRunSupervisionItem]:
        """List autonomous contract runs in a workspace."""
        if self._engine is not None:
            rows = await list_autonomous_runs_sql(self._engine, workspace_id=workspace_id)
            if rows:
                return [map_pg_row_to_supervision_item(r) for r in rows]
        return [r for r in self._runs.values() if r.workspace_id == workspace_id]

    async def emergency_stop(
        self,
        *,
        run_id: str,
        actor_user_id: str,
        reason: str = "",
        suspend_trigger: bool = True,
        trace_id: str = "00000000000000000000000000000000",
    ) -> EmergencyStopOutcome:
        """Trigger immediate emergency stop (`KILL_SWITCH_STOPPED`) + optional trigger pause."""
        mem, pg_row, ws_id, wf_id, _c_id, trig_id = await self._load_run_context(run_id)
        event = KillSwitchActivated.create(
            run_id=run_id,
            workspace_id=ws_id,
            workflow_id=wf_id,
            actor_user_id=actor_user_id,
            reason=reason,
            trigger_id=trig_id,
            trigger_suspended=bool(suspend_trigger and trig_id is not None),
            trace_id=trace_id,
        )
        trigger_suspended = False
        if self._engine is not None and pg_row is not None:
            res = await apply_emergency_stop_sql(
                self._engine,
                run_id=run_id,
                suspend_trigger=suspend_trigger,
                event=event,
                audit_sink=self._audit_sink,
            )
            if res is not None:
                trigger_suspended = bool(res["trigger_suspended"])
        elif suspend_trigger and trig_id is not None:
            trigger_suspended = True

        if mem is not None:
            self._runs[run_id] = replace(
                mem,
                run_status="KILL_SWITCH_STOPPED",
                trigger_status="CIRCUIT_OPEN" if trigger_suspended else mem.trigger_status,
            )
        self._post_hoc.register_in_memory_run(
            run_id=run_id, workspace_id=ws_id, status="KILL_SWITCH_STOPPED"
        )
        self._outbox_events.append(event)
        sse_ms = self._publish_sse(
            ws_id,
            "autonomous.run.killed",
            run_id,
            {
                "run_id": run_id,
                "status": "KILL_SWITCH_STOPPED",
                "trigger_suspended": trigger_suspended,
            },
        )
        return EmergencyStopOutcome(
            run_id=run_id,
            workspace_id=ws_id,
            status="KILL_SWITCH_STOPPED",
            trigger_suspended=trigger_suspended,
            sse_dispatch_latency_ms=sse_ms,
        )

    async def invalidate_and_restore(
        self,
        *,
        run_id: str,
        actor_user_id: str,
        comment: str = "",
        help_resource_id: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> InvalidateAndRestoreOutcome:
        """Invalidate an autonomous deliverable/help article and restore `@v(N-1)` + flush Redis."""
        mem, pg_row, ws_id, wf_id, contract_id, _trig_id = await self._load_run_context(run_id)
        resolved_help_id = help_resource_id or (mem.help_resource_id if mem is not None else None)
        t_cache = time.perf_counter()
        restored_ver = restore_help_in_memory_and_flush_redis(
            help_service=self._help_service,
            redis_client=self._redis,
            help_resource_id=resolved_help_id,
        )
        event = AutonomousArtifactRolledBack.create(
            run_id=run_id,
            workspace_id=ws_id,
            workflow_id=wf_id,
            actor_user_id=actor_user_id,
            restored_version=restored_ver,
            help_resource_id=resolved_help_id,
            comment=comment,
            trace_id=trace_id,
        )
        if self._engine is not None and pg_row is not None:
            res = await restore_help_article_and_rollback_run_sql(
                self._engine,
                run_id=run_id,
                reviewer_user_id=actor_user_id,
                comment=comment or None,
                help_resource_id=resolved_help_id,
                contract_id=contract_id or None,
                event=event,
                audit_sink=self._audit_sink,
            )
            if res is not None:
                restored_ver = str(res["restored_version"])
                resolved_help_id = res["help_resource_id"]
                if self._redis is not None:
                    for rkey in res["invalidated_redis_keys"]:
                        del_res = self._redis.delete(rkey)
                        if inspect.isawaitable(del_res):
                            await del_res
        else:
            await self._post_hoc.record_review(
                run_id=run_id,
                decision="INVALIDATED_ROLLED_BACK",
                reviewer_user_id=actor_user_id,
                review_comment=comment or None,
                workspace_id=ws_id,
                contract_id=contract_id or new_uuid7_str(),
            )
        redis_ms = round((time.perf_counter() - t_cache) * 1000.0, 3)
        if mem is not None:
            self._runs[run_id] = replace(
                mem,
                run_status="ROLLED_BACK",
                post_hoc_status="INVALIDATED_ROLLED_BACK",
                previous_version_available=False,
            )
        self._post_hoc.register_in_memory_run(
            run_id=run_id, workspace_id=ws_id, status="ROLLED_BACK"
        )
        self._outbox_events.append(event)
        sse_ms = self._publish_sse(
            ws_id,
            "autonomous.artifact.rolled_back",
            run_id,
            {
                "run_id": run_id,
                "status": "ROLLED_BACK",
                "restored_version": restored_ver,
                "help_resource_id": resolved_help_id,
            },
        )
        return InvalidateAndRestoreOutcome(
            run_id=run_id,
            workspace_id=ws_id,
            status="ROLLED_BACK",
            restored_version=restored_ver,
            help_resource_id=resolved_help_id,
            redis_cache_invalidated_ms=redis_ms,
            sse_dispatch_latency_ms=sse_ms,
        )

    async def review_post_hoc_sample(
        self,
        *,
        run_id: str,
        actor_user_id: str,
        decision: Literal["VALIDATED", "INVALIDATED_ROLLED_BACK"],
        comment: str = "",
        help_resource_id: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> dict[str, Any]:
        """Validate or invalidate (with `@v(N-1)` restore) a sampled autonomous run."""
        if decision == "INVALIDATED_ROLLED_BACK":
            outcome = await self.invalidate_and_restore(
                run_id=run_id,
                actor_user_id=actor_user_id,
                comment=comment,
                help_resource_id=help_resource_id,
                trace_id=trace_id,
            )
            return {
                "run_id": outcome.run_id,
                "review_status": "INVALIDATED_ROLLED_BACK",
                "run_status": outcome.status,
                "restored_version": outcome.restored_version,
            }
        mem, pg_row, ws_id, _wf_id, contract_id, _trig_id = await self._load_run_context(run_id)
        rec = await self._post_hoc.record_review(
            run_id=run_id,
            decision="VALIDATED",
            reviewer_user_id=actor_user_id,
            review_comment=comment or None,
            workspace_id=ws_id,
            contract_id=contract_id or None,
        )
        if mem is not None:
            self._runs[run_id] = replace(mem, post_hoc_status="VALIDATED")
        return {
            "run_id": run_id,
            "review_status": rec.review_status if rec else "VALIDATED",
            "run_status": mem.run_status if mem else str(pg_row["run_status"]),  # type: ignore[index]
            "restored_version": None,
        }


__all__ = [
    "AutonomousRunSupervisionItem",
    "AutonomousSupervisionService",
    "EmergencyStopOutcome",
    "InvalidateAndRestoreOutcome",
]
