"""Autonomous Run Supervision, Emergency Stop & `@v(N-1)` Restore (`Story 7.4`, `AD-18`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.catalog.contextual_help import ContextualHelpResolutionService
from orcia_core.kernel.events import DomainEvent
from orcia_core.orchestration._autonomous_supervision_executors import (
    execute_emergency_stop,
    execute_invalidate_and_restore,
)
from orcia_core.orchestration._autonomous_supervision_models import (
    AutonomousRunSupervisionItem,
    EmergencyStopOutcome,
    InvalidateAndRestoreOutcome,
    make_registered_supervision_item,
    map_pg_row_to_supervision_item,
    resolve_run_context,
)
from orcia_core.orchestration._autonomous_supervision_ops import (
    apply_trigger_status_on_register,
    execute_validated_post_hoc_review,
)
from orcia_core.orchestration._internal.sql_autonomous_supervision import (
    get_autonomous_run_sql,
    is_run_kill_switch_stopped_sql,
    list_autonomous_runs_sql,
    update_autonomous_run_status_sql,
)
from orcia_core.orchestration._orchestration_runtime_locales import (
    SUPERVISION_LOCALES,
    get_runtime_copy,
)
from orcia_core.orchestration.presence_and_sse import (
    InMemorySseBrokerAdapter,
    SseBroadcastPort,
    TaskNotificationEntity,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort

_DEFAULT_TRIGGER_LABEL = get_runtime_copy(SUPERVISION_LOCALES)["default_trigger"]


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
        if self._engine is not None:
            return await is_run_kill_switch_stopped_sql(self._engine, run_id=run_id)
        mem = self._runs.get(run_id)
        return mem is not None and mem.run_status == "KILL_SWITCH_STOPPED"

    async def _load_run_context(
        self, run_id: str
    ) -> tuple[
        AutonomousRunSupervisionItem | None, dict[str, Any] | None, str, str, str, str | None
    ]:
        pg_row = (
            await get_autonomous_run_sql(self._engine, run_id=run_id)
            if self._engine is not None
            else None
        )
        mem = None if self._engine is not None else self._runs.get(run_id)
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
        trigger_label: str = _DEFAULT_TRIGGER_LABEL,
        trigger_type: str = "MANUAL_AUTONOMOUS",
        trigger_status: str = "ACTIVE",
        sampling_rate: Decimal | float = Decimal("0.15"),
        cost_usd: Decimal = Decimal("0.050000"),
        help_resource_id: str | None = None,
        force_post_hoc_sample: bool = False,
        trace_id: str = "00000000000000000000000000000000",
    ) -> AutonomousRunSupervisionItem:
        """Track an autonomous run, sample post-hoc (`10-20%`) on commit & emit alerts."""
        if self._engine is not None:
            await update_autonomous_run_status_sql(self._engine, run_id=run_id, status=status)
        self._post_hoc.register_in_memory_run(
            run_id=run_id, workspace_id=workspace_id, status=status, cost_usd=cost_usd
        )
        sampled = (
            await self._post_hoc.maybe_sample_committed_run(
                run_id=run_id,
                workspace_id=workspace_id,
                contract_id=contract_id,
                workflow_id=workflow_id,
                sampling_rate=sampling_rate,
                force_select=force_post_hoc_sample,
                trigger_label=trigger_label,
                trace_id=trace_id,
            )
            if status == "COMMITTED_AUTONOMOUS"
            else None
        )
        post_hoc_status = apply_trigger_status_on_register(
            self._notifications,
            workspace_id=workspace_id,
            run_id=run_id,
            workflow_id=workflow_id,
            trigger_label=trigger_label,
            status=status,
            sampled=sampled,
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
        """List autonomous contract runs in a workspace (PostgreSQL authoritative)."""
        if self._engine is not None:
            rows = await list_autonomous_runs_sql(self._engine, workspace_id=workspace_id)
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
        return await execute_emergency_stop(
            self,
            run_id=run_id,
            actor_user_id=actor_user_id,
            reason=reason,
            suspend_trigger=suspend_trigger,
            trace_id=trace_id,
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
        return await execute_invalidate_and_restore(
            self,
            run_id=run_id,
            actor_user_id=actor_user_id,
            comment=comment,
            help_resource_id=help_resource_id,
            trace_id=trace_id,
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
            out = await self.invalidate_and_restore(
                run_id=run_id,
                actor_user_id=actor_user_id,
                comment=comment,
                help_resource_id=help_resource_id,
                trace_id=trace_id,
            )
            return {
                "run_id": out.run_id,
                "review_status": "INVALIDATED_ROLLED_BACK",
                "run_status": out.status,
                "restored_version": out.restored_version,
            }
        mem, pg_row, ws_id, _wf_id, contract_id, _trig_id = await self._load_run_context(run_id)
        return await execute_validated_post_hoc_review(
            post_hoc=self._post_hoc,
            runs_mem=self._runs,
            mem=mem,
            pg_row=pg_row,
            run_id=run_id,
            actor_user_id=actor_user_id,
            comment=comment,
            workspace_id=ws_id,
            contract_id=contract_id,
        )


__all__ = [
    "AutonomousRunSupervisionItem",
    "AutonomousSupervisionService",
    "EmergencyStopOutcome",
    "InvalidateAndRestoreOutcome",
]
