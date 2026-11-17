"""Idempotent Workflow Triggers Dispatcher, Circuit Breaker & Opt-In Help (`Story 7.2`, `AD-18`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    WorkflowTriggerRepositoryPort,
)
from orcia_core.orchestration._triggers_crud_helpers import (
    CreateTriggerCommand,
    DispatchResultKind,
    TriggerDispatchOutcome,
    UpdateTriggerCommand,
    apply_trigger_update,
    now_iso,
    prepare_webhook_secret,
)
from orcia_core.orchestration._triggers_log_cron import (
    evaluate_self_trigger_guard,
    validate_cron_expr,
)
from orcia_core.orchestration._triggers_runtime_ports import (
    DbosSetWorkflowIdDispatcher,
    DbosWorkflowIdDispatcherPort,
    RedisTriggerIdempotencyLockAdapter,
    TriggerIdempotencyLockPort,
    run_with_error_taxonomy,
)
from orcia_core.orchestration._triggers_schedulers import (
    run_cron_trigger_evaluation,
    run_log_sink_trigger_scan,
    run_workflow_published_optin_help,
)
from orcia_core.orchestration.models import WorkflowTriggerEntity, WorkflowTriggerType
from orcia_core.orchestration.presence_and_sse import InMemorySseBrokerAdapter, SseBroadcastPort
from orcia_core.permissions.autonomy_contracts import AutonomyContract, AutonomyContractService
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import unpack_encrypted_secret
from orcia_core.permissions.errors import (
    AutonomyContractRequiredForTriggerError,
    TriggerCircuitOpenError,
    TriggerDuplicateKeyError,
    TriggerNotFoundError,
    ValidationDomainError,
    WebhookSignatureInvalidError,
)
from orcia_core.permissions.webhook_security import verify_webhook_hmac_sha256
from orcia_core.ports.log_sink import LogSinkQueryPort
from orcia_kernel.events import DomainEvent, SelfTriggerBlocked, TriggerCircuitOpened, TriggerFired
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.orchestration.triggers_dispatcher")


class TriggerDispatcherService:
    """Orchestrates trigger lifecycle, triple idempotence, Self-Trigger Guard & circuit breaker."""

    def __init__(
        self,
        *,
        contract_service: AutonomyContractService,
        repository: WorkflowTriggerRepositoryPort | None = None,
        idempotency_lock: TriggerIdempotencyLockPort | None = None,
        dbos_dispatcher: DbosWorkflowIdDispatcherPort | None = None,
        sse_broker: SseBroadcastPort | None = None,
        vault_cipher: PassthroughVaultCipher | None = None,
        log_sink: LogSinkQueryPort | None = None,
    ) -> None:
        self._contracts = contract_service
        self._repo = repository
        self._lock = idempotency_lock or RedisTriggerIdempotencyLockAdapter()
        self._dbos = dbos_dispatcher or DbosSetWorkflowIdDispatcher()
        self._sse = sse_broker or InMemorySseBrokerAdapter()
        self._cipher = vault_cipher or PassthroughVaultCipher("0" * 32)
        self._log_sink = log_sink
        self._triggers: dict[str, WorkflowTriggerEntity] = {}
        self._secrets_enc: dict[str, str] = {}
        self._deliveries: set[tuple[str, str]] = set()
        self._run_keys: set[tuple[str, str]] = set()
        self._runs_by_trigger: dict[str, list[tuple[datetime, float]]] = {}
        self._outbox_events: list[DomainEvent] = []

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._outbox_events)

    @property
    def sse_broker(self) -> SseBroadcastPort:
        return self._sse

    @property
    def log_sink(self) -> LogSinkQueryPort | None:
        return self._log_sink

    async def list_active_by_type(
        self, trigger_type: WorkflowTriggerType
    ) -> list[WorkflowTriggerEntity]:
        if self._repo is not None:
            return await self._repo.list_active_triggers(trigger_type=trigger_type)
        return [
            t
            for t in self._triggers.values()
            if t.status == "ACTIVE" and t.trigger_type == trigger_type
        ]

    async def _require_active_contract(
        self, *, workspace_id: str, workflow_id: str
    ) -> AutonomyContract:
        contract = await self._contracts.get_active_contract(
            workspace_id=workspace_id, workflow_id=workflow_id
        )
        if contract is None or contract.status != "ACTIVE":
            raise AutonomyContractRequiredForTriggerError()
        return contract

    async def list_triggers(
        self, *, workspace_id: str, workflow_id: str | None = None
    ) -> list[WorkflowTriggerEntity]:
        if self._repo is not None:
            return await self._repo.list_triggers(
                workspace_id=workspace_id, workflow_id=workflow_id
            )
        return [
            t
            for t in self._triggers.values()
            if t.workspace_id == workspace_id
            and (workflow_id is None or t.workflow_id == workflow_id)
        ]

    async def scan_log_sink_triggers(
        self,
        *,
        workspace_id: str | None = None,
        now_utc: datetime | None = None,
        log_sink: LogSinkQueryPort | None = None,
    ) -> list[TriggerDispatchOutcome]:
        return await run_log_sink_trigger_scan(
            self, workspace_id=workspace_id, now_utc=now_utc, log_sink=log_sink
        )

    async def evaluate_cron_triggers(
        self, *, workspace_id: str | None = None, now_utc: datetime | None = None
    ) -> list[TriggerDispatchOutcome]:
        return await run_cron_trigger_evaluation(self, workspace_id=workspace_id, now_utc=now_utc)

    async def handle_workflow_published(
        self, event: DomainEvent, *, help_service: Any | None = None
    ) -> list[TriggerDispatchOutcome]:
        return await run_workflow_published_optin_help(self, event, help_service=help_service)

    async def get_trigger(self, trigger_id: str) -> tuple[WorkflowTriggerEntity, str | None]:
        if self._repo is not None:
            found = await self._repo.get_trigger(trigger_id)
            if found is None:
                raise TriggerNotFoundError()
            return found
        entity = self._triggers.get(trigger_id)
        if entity is None:
            raise TriggerNotFoundError()
        return entity, self._secrets_enc.get(trigger_id)

    async def create_trigger(self, cmd: CreateTriggerCommand) -> WorkflowTriggerEntity:
        if cmd.trigger_type == "CRON":
            if not (cmd.cron_expr or "").strip():
                raise ValidationDomainError(detail_override="cron_expr is required for CRON.")
            validate_cron_expr(cmd.cron_expr or "")
        contract = (
            await self._require_active_contract(
                workspace_id=cmd.workspace_id, workflow_id=cmd.workflow_id
            )
            if cmd.status == "ACTIVE"
            else await self._contracts.get_active_contract(
                workspace_id=cmd.workspace_id, workflow_id=cmd.workflow_id
            )
        )
        tid = new_uuid7_str()
        tkey = (cmd.trigger_key or "").strip() or f"trg-{cmd.trigger_type.lower()}-{tid[:8]}"
        enc, fp, hint, clear_flag, changed = prepare_webhook_secret(
            self._cipher, tid, cmd.webhook_secret
        )
        entity = WorkflowTriggerEntity(
            id=tid,
            trigger_key=tkey,
            workspace_id=cmd.workspace_id,
            workflow_def_id=tid,
            trigger_type=cmd.trigger_type,
            workflow_id=cmd.workflow_id,
            contract_id=contract.id if contract else None,
            cron_expr=cmd.cron_expr.strip() if cmd.cron_expr else None,
            cooldown_window_seconds=max(0, cmd.cooldown_window_seconds),
            service_principal_id=contract.service_principal_id if contract else None,
            max_runs_per_hour=max(1, cmd.max_runs_per_hour),
            max_daily_cost_usd=max(0.0, cmd.max_daily_cost_usd),
            max_consecutive_failures=max(1, cmd.max_consecutive_failures),
            post_hoc_sampling_rate=contract.post_hoc_sampling_rate if contract else 0.10,
            status=cmd.status,
            auto_help_on_publish=bool(cmd.auto_help_on_publish),
            webhook_secret_configured=bool(enc),
            webhook_secret_fingerprint=fp,
            webhook_secret_masked_hint=hint,
            webhook_secret_updated_at=now_iso() if changed else None,
            webhook_secret_updated_by=cmd.actor_id if changed else None,
            log_sink_service=cmd.log_sink_service,
            log_sink_query_text=cmd.log_sink_query_text,
            outbox_event_filter=cmd.outbox_event_filter,
        )
        if self._repo is not None:
            return await self._repo.save_trigger(
                entity, encrypted_secret=enc, clear_secret=clear_flag
            )
        if any(t.trigger_key == tkey for t in self._triggers.values()):
            raise TriggerDuplicateKeyError()
        self._triggers[tid] = entity
        if enc:
            self._secrets_enc[tid] = enc
        return entity

    async def update_trigger(
        self, *, workspace_id: str, trigger_id: str, cmd: UpdateTriggerCommand
    ) -> WorkflowTriggerEntity:
        existing, _ = await self.get_trigger(trigger_id)
        if existing.workspace_id != workspace_id:
            raise TriggerNotFoundError()
        next_status = cmd.status or existing.status
        cid, sp_id = existing.contract_id, existing.service_principal_id
        if next_status == "ACTIVE":
            contract = await self._require_active_contract(
                workspace_id=workspace_id, workflow_id=existing.workflow_id
            )
            cid, sp_id = contract.id, contract.service_principal_id
        next_cron = cmd.cron_expr if cmd.cron_expr is not None else existing.cron_expr
        if existing.trigger_type == "CRON" and next_cron:
            validate_cron_expr(next_cron)
        enc, fp, hint, clear_flag, changed = prepare_webhook_secret(
            self._cipher, trigger_id, cmd.webhook_secret
        )
        updated = apply_trigger_update(
            existing,
            cmd,
            next_status=next_status,
            contract_id=cid,
            sp_id=sp_id,
            next_cron=next_cron,
            enc=enc,
            fp=fp,
            hint=hint,
            clear_flag=clear_flag,
            changed=changed,
        )
        if self._repo is not None:
            return await self._repo.save_trigger(
                updated, encrypted_secret=enc, clear_secret=clear_flag
            )
        self._triggers[trigger_id] = updated
        if clear_flag:
            self._secrets_enc.pop(trigger_id, None)
        elif enc:
            self._secrets_enc[trigger_id] = enc
        return updated

    async def delete_trigger(self, *, workspace_id: str, trigger_id: str) -> None:
        if self._repo is not None:
            await self._repo.delete_trigger(workspace_id=workspace_id, trigger_id=trigger_id)
            return
        existing = self._triggers.get(trigger_id)
        if existing is None or existing.workspace_id != workspace_id:
            raise TriggerNotFoundError()
        self._triggers.pop(trigger_id, None)
        self._secrets_enc.pop(trigger_id, None)

    async def verify_webhook_request(
        self, *, trigger_id: str, raw_body: bytes, signature_header: str | None, delivery_key: str
    ) -> tuple[WorkflowTriggerEntity, bool]:
        """Verify HMAC-SHA256 using shared `webhook_security` and deduplicate delivery."""
        entity, enc_secret = await self.get_trigger(trigger_id)
        if enc_secret:
            secret = unpack_encrypted_secret(
                self._cipher,
                owner_id=trigger_id,
                packed=enc_secret,
                scheme="webhook",
                host="trigger",
            )
            if not verify_webhook_hmac_sha256(raw_body, secret, signature_header):
                raise WebhookSignatureInvalidError()
        elif signature_header:
            raise WebhookSignatureInvalidError()
        if self._repo is not None:
            is_new = await self._repo.record_webhook_delivery(
                trigger_id=trigger_id, delivery_key=delivery_key
            )
        else:
            key = (trigger_id, delivery_key)
            is_new = key not in self._deliveries
            self._deliveries.add(key)
        return entity, is_new

    async def reset_circuit(self, *, workspace_id: str, trigger_id: str) -> WorkflowTriggerEntity:
        existing, _ = await self.get_trigger(trigger_id)
        if existing.workspace_id != workspace_id:
            raise TriggerNotFoundError()
        await self._require_active_contract(
            workspace_id=workspace_id, workflow_id=existing.workflow_id
        )
        if self._repo is not None:
            return await self._repo.set_trigger_status(
                trigger_id=trigger_id, status="ACTIVE", consecutive_failures=0
            )
        updated = replace(existing, status="ACTIVE", consecutive_failures=0)
        self._triggers[trigger_id] = updated
        return updated

    async def _publish_event(self, event: DomainEvent, *, sse_name: str | None = None) -> None:
        self._outbox_events.append(event)
        if self._repo is not None:
            await self._repo.publish_outbox_event(event)
        if sse_name and event.workspace_id:
            self._sse.publish(
                workspace_id=event.workspace_id,
                event_name=sse_name,
                run_id=event.run_id or event.aggregate_id,
                step_execution_id=event.aggregate_id,
                payload=dict(event.payload),
            )

    async def _open_circuit(
        self, trigger: WorkflowTriggerEntity, *, reason: str, failures: int, trace_id: str
    ) -> TriggerDispatchOutcome:
        if self._repo is not None:
            await self._repo.set_trigger_status(
                trigger_id=trigger.id, status="CIRCUIT_OPEN", consecutive_failures=failures
            )
        else:
            self._triggers[trigger.id] = replace(
                trigger, status="CIRCUIT_OPEN", consecutive_failures=failures
            )
        evt = TriggerCircuitOpened.create(
            trigger_id=trigger.id,
            workspace_id=trigger.workspace_id,
            workflow_id=trigger.workflow_id,
            reason=reason,
            consecutive_failures=failures,
            trace_id=trace_id,
        )
        await self._publish_event(evt, sse_name="TriggerCircuitOpened")
        return TriggerDispatchOutcome(
            dispatched=False,
            outcome="CIRCUIT_OPEN",
            trigger_id=trigger.id,
            idempotency_key="",
            dbos_workflow_id="",
            reason=reason,
        )

    async def dispatch_trigger(
        self,
        *,
        trigger_id: str,
        idempotency_key: str,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        execution_fn: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        estimated_cost_usd: float = 0.05,
        trace_id: str = "00000000000000000000000000000000",
        raise_on_circuit_open: bool = True,
    ) -> TriggerDispatchOutcome:
        """Dispatch `trigger_id` with triple idempotence, Self-Trigger Guard & circuit breaker."""
        trigger, _ = await self.get_trigger(trigger_id)
        dbos_wf_id = f"{trigger.id}:{idempotency_key}"
        if trigger.status == "CIRCUIT_OPEN":
            if raise_on_circuit_open:
                raise TriggerCircuitOpenError()
            return TriggerDispatchOutcome(
                False,
                "CIRCUIT_OPEN",
                trigger.id,
                idempotency_key,
                dbos_wf_id,
                reason="Circuit open",
            )
        if trigger.status == "PAUSED":
            return TriggerDispatchOutcome(
                False, "PAUSED", trigger.id, idempotency_key, dbos_wf_id, reason="Trigger paused"
            )
        contract = await self._require_active_contract(
            workspace_id=trigger.workspace_id, workflow_id=trigger.workflow_id
        )
        guard = evaluate_self_trigger_guard(
            trigger=trigger,
            contract_service_principal_id=contract.service_principal_id,
            headers=headers,
            payload=payload,
        )
        if guard.blocked:
            evt = SelfTriggerBlocked.create(
                trigger_id=trigger.id,
                workspace_id=trigger.workspace_id,
                workflow_id=trigger.workflow_id,
                reason=guard.reason,
                origin_run_id=guard.origin_run_id,
                service_principal_id=contract.service_principal_id,
                trace_id=trace_id,
            )
            await self._publish_event(evt, sse_name="SelfTriggerBlocked")
            return TriggerDispatchOutcome(
                False,
                "SELF_TRIGGER_BLOCKED",
                trigger.id,
                idempotency_key,
                dbos_wf_id,
                reason=guard.reason,
            )
        if self._repo is not None:
            hourly = await self._repo.count_runs_last_hour(trigger_id=trigger.id)
            daily_cost = await self._repo.sum_daily_cost_usd(trigger_id=trigger.id)
        else:
            now = datetime.now(UTC)
            hist = self._runs_by_trigger.get(trigger.id, [])
            hourly = sum(1 for ts, _ in hist if (now - ts).total_seconds() <= 3600)
            daily_cost = sum(c for ts, c in hist if ts.date() == now.date())
        if hourly >= trigger.max_runs_per_hour:
            res = await self._open_circuit(
                trigger,
                reason="max_runs_per_hour exceeded",
                failures=trigger.consecutive_failures,
                trace_id=trace_id,
            )
            return replace(res, idempotency_key=idempotency_key, dbos_workflow_id=dbos_wf_id)
        if daily_cost + estimated_cost_usd > trigger.max_daily_cost_usd:
            res = await self._open_circuit(
                trigger,
                reason="max_daily_cost_usd exceeded",
                failures=trigger.consecutive_failures,
                trace_id=trace_id,
            )
            return replace(res, idempotency_key=idempotency_key, dbos_workflow_id=dbos_wf_id)
        if not await self._lock.try_acquire(trigger_id=trigger.id, idempotency_key=idempotency_key):
            return TriggerDispatchOutcome(
                False,
                "DUPLICATE_SUPPRESSED",
                trigger.id,
                idempotency_key,
                dbos_wf_id,
                reason="Duplicate suppressed by Redis NX lock",
            )
        run_id = new_uuid7_str()
        if self._repo is not None:
            inserted = await self._repo.create_idempotent_trigger_run(
                run_id=run_id,
                trigger=trigger,
                idempotency_key=idempotency_key,
                status="INITIALIZED",
                budget_max_usd=min(contract.max_cost_per_run_usd, trigger.max_daily_cost_usd),
            )
        else:
            rk = (trigger.id, idempotency_key)
            inserted = rk not in self._run_keys
            if inserted:
                self._run_keys.add(rk)
                self._runs_by_trigger.setdefault(trigger.id, []).append(
                    (datetime.now(UTC), estimated_cost_usd)
                )
        if not inserted:
            return TriggerDispatchOutcome(
                False,
                "DUPLICATE_SUPPRESSED",
                trigger.id,
                idempotency_key,
                dbos_wf_id,
                reason="Duplicate suppressed by SQL UNIQUE constraint",
            )
        attempts_used = 1
        try:
            if execution_fn is not None:
                _, attempts_used = await run_with_error_taxonomy(
                    lambda: self._dbos.dispatch(
                        dbos_workflow_id=dbos_wf_id,
                        trigger=trigger,
                        run_id=run_id,
                        idempotency_key=idempotency_key,
                        payload=dict(payload or {}),
                        execution_fn=execution_fn,
                    )
                )
            else:
                await self._dbos.dispatch(
                    dbos_workflow_id=dbos_wf_id,
                    trigger=trigger,
                    run_id=run_id,
                    idempotency_key=idempotency_key,
                    payload=dict(payload or {}),
                )
        except Exception as exc:
            logger.warning("trigger_execution_failed", trigger_id=trigger.id, error=str(exc))
            if self._repo is not None:
                fails, opened = await self._repo.record_trigger_failure(
                    trigger_id=trigger.id, max_consecutive_failures=trigger.max_consecutive_failures
                )
            else:
                fails = trigger.consecutive_failures + 1
                opened = fails >= trigger.max_consecutive_failures
                self._triggers[trigger.id] = replace(
                    trigger,
                    consecutive_failures=fails,
                    status="CIRCUIT_OPEN" if opened else trigger.status,
                )
            if opened:
                res = await self._open_circuit(
                    trigger,
                    reason=f"Consecutive failures {fails}",
                    failures=fails,
                    trace_id=trace_id,
                )
                return replace(
                    res,
                    idempotency_key=idempotency_key,
                    dbos_workflow_id=dbos_wf_id,
                    run_id=run_id,
                    attempts=attempts_used,
                    reason=str(exc),
                )
            return TriggerDispatchOutcome(
                False,
                "FAILED_FUNCTIONAL",
                trigger.id,
                idempotency_key,
                dbos_wf_id,
                run_id=run_id,
                attempts=attempts_used,
                reason=str(exc),
            )
        if self._repo is not None:
            await self._repo.mark_trigger_fired(trigger_id=trigger.id)
        else:
            self._triggers[trigger.id] = replace(
                trigger, consecutive_failures=0, last_fired_at_iso=now_iso()
            )
        fired = TriggerFired.create(
            trigger_id=trigger.id,
            workspace_id=trigger.workspace_id,
            workflow_id=trigger.workflow_id,
            trigger_type=trigger.trigger_type,
            run_id=run_id,
            idempotency_key=idempotency_key,
            service_principal_id=contract.service_principal_id,
            trace_id=trace_id,
        )
        await self._publish_event(fired, sse_name="TriggerFired")
        return TriggerDispatchOutcome(
            True,
            "DISPATCHED",
            trigger.id,
            idempotency_key,
            dbos_wf_id,
            run_id=run_id,
            attempts=attempts_used,
        )


__all__ = [
    "CreateTriggerCommand",
    "DispatchResultKind",
    "TriggerDispatchOutcome",
    "TriggerDispatcherService",
    "UpdateTriggerCommand",
]
