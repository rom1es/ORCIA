"""Idempotent Workflow Triggers Dispatcher, Circuit Breaker & Opt-In Help (`Story 7.2`, `AD-18`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime
from typing import Any

from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    WorkflowTriggerRepositoryPort,
)
from orcia_core.orchestration._triggers_crud_helpers import (
    CreateTriggerCommand,
    DispatchResultKind,
    TriggerDispatchOutcome,
    UpdateTriggerCommand,
)
from orcia_core.orchestration._triggers_dispatch_helpers import (
    AutonomousTriggerExecutor,
    TriggerAutonomousExecutionContext,
)
from orcia_core.orchestration._triggers_lifecycle_ops import (
    build_circuit_opened_event_and_outcome,
    execute_create_trigger,
    execute_update_trigger,
    execute_verify_webhook_request,
    validate_create_trigger_cron,
)
from orcia_core.orchestration._triggers_pipeline import execute_full_dispatch_pipeline
from orcia_core.orchestration._triggers_runtime_ports import (
    DbosSetWorkflowIdDispatcher,
    DbosWorkflowIdDispatcherPort,
    RedisTriggerIdempotencyLockAdapter,
    TriggerIdempotencyLockPort,
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
from orcia_core.permissions.errors import (
    AutonomyContractRequiredForTriggerError,
    TriggerNotFoundError,
)
from orcia_core.ports.log_sink import LogSinkQueryPort
from orcia_kernel.events import DomainEvent


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
        autonomous_executor: AutonomousTriggerExecutor | None = None,
    ) -> None:
        self._contracts = contract_service
        self._repo = repository
        self._lock = idempotency_lock or RedisTriggerIdempotencyLockAdapter()
        self._dbos = dbos_dispatcher or DbosSetWorkflowIdDispatcher()
        self._sse = sse_broker or InMemorySseBrokerAdapter()
        self._cipher = vault_cipher or PassthroughVaultCipher("0" * 32)
        self._log_sink = log_sink
        self._autonomous_executor = autonomous_executor
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

    def set_autonomous_executor(self, executor: AutonomousTriggerExecutor | None) -> None:
        """Bind or replace the downstream autonomous execution bridge."""
        self._autonomous_executor = executor

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
        validate_create_trigger_cron(cmd)
        contract = (
            await self._require_active_contract(
                workspace_id=cmd.workspace_id, workflow_id=cmd.workflow_id
            )
            if cmd.status == "ACTIVE"
            else await self._contracts.get_active_contract(
                workspace_id=cmd.workspace_id, workflow_id=cmd.workflow_id
            )
        )
        return await execute_create_trigger(
            cmd=cmd,
            contract=contract,
            cipher=self._cipher,
            repo=self._repo,
            triggers_mem=self._triggers,
            secrets_mem=self._secrets_enc,
        )

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
        return await execute_update_trigger(
            existing=existing,
            workspace_id=workspace_id,
            trigger_id=trigger_id,
            cmd=cmd,
            next_status=next_status,
            cid=cid,
            sp_id=sp_id,
            cipher=self._cipher,
            repo=self._repo,
            triggers_mem=self._triggers,
            secrets_mem=self._secrets_enc,
        )

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
        return await execute_verify_webhook_request(
            entity=entity,
            enc_secret=enc_secret,
            trigger_id=trigger_id,
            raw_body=raw_body,
            signature_header=signature_header,
            delivery_key=delivery_key,
            cipher=self._cipher,
            repo=self._repo,
            deliveries_mem=self._deliveries,
        )

    async def record_alert_delivery_async(self, *, trigger_id: str, delivery_key: str) -> bool:
        """Persist idempotent alert delivery key in `trigger_webhook_deliveries` (or memory)."""
        if self._repo is not None:
            return await self._repo.record_webhook_delivery(
                trigger_id=trigger_id, delivery_key=delivery_key
            )
        key = (trigger_id, delivery_key)
        is_new = key not in self._deliveries
        self._deliveries.add(key)
        return is_new

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
        evt, outcome = build_circuit_opened_event_and_outcome(
            trigger=trigger, reason=reason, failures=failures, trace_id=trace_id
        )
        await self._publish_event(evt, sse_name="TriggerCircuitOpened")
        return outcome  # type: ignore[no-any-return]

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
        return await execute_full_dispatch_pipeline(  # type: ignore[no-any-return]
            self,
            trigger_id=trigger_id,
            idempotency_key=idempotency_key,
            headers=headers,
            payload=payload,
            execution_fn=execution_fn,
            estimated_cost_usd=estimated_cost_usd,
            trace_id=trace_id,
            raise_on_circuit_open=raise_on_circuit_open,
        )


__all__ = [
    "AutonomousTriggerExecutor",
    "CreateTriggerCommand",
    "DispatchResultKind",
    "TriggerAutonomousExecutionContext",
    "TriggerDispatchOutcome",
    "TriggerDispatcherService",
    "UpdateTriggerCommand",
]
