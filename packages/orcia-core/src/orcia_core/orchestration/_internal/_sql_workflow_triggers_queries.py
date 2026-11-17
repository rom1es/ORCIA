"""SQL queries, row mapping & Outbox helper for `workflow_triggers` (`Story 7.2`)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol, cast, runtime_checkable

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.audit_finops.outbox_subscriber import map_domain_event_to_ledger_entry
from orcia_core.orchestration.models import (
    WorkflowTriggerEntity,
    WorkflowTriggerStatus,
    WorkflowTriggerType,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.events import DomainEvent


def fmt_ts(val: object) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat().replace("+00:00", "Z")
    text = str(val).strip()
    return text or None


SELECT_TRIGGER_COLS = """
    id::text, trigger_key, workspace_id::text, workflow_def_id::text, trigger_type,
    workflow_id, contract_id::text, cron_expr, webhook_secret_vault_ref,
    cooldown_window_seconds, service_principal_id, max_runs_per_hour,
    max_daily_cost_usd, max_consecutive_failures, post_hoc_sampling_rate,
    contract_signature_id::text, status, auto_help_on_publish, consecutive_failures,
    last_fired_at, webhook_secret_encrypted, webhook_secret_fingerprint,
    webhook_secret_masked_hint, webhook_secret_updated_at, webhook_secret_updated_by,
    log_sink_service, log_sink_query_text, outbox_event_filter
"""


def row_to_trigger(row: Any) -> tuple[WorkflowTriggerEntity, str | None]:
    encrypted = str(row[20]) if row[20] is not None else None
    entity = WorkflowTriggerEntity(
        id=str(row[0]),
        trigger_key=str(row[1]),
        workspace_id=str(row[2]),
        workflow_def_id=str(row[3]),
        trigger_type=cast(WorkflowTriggerType, str(row[4])),
        workflow_id=str(row[5] or ""),
        contract_id=str(row[6]) if row[6] is not None else None,
        cron_expr=str(row[7]) if row[7] is not None else None,
        webhook_secret_vault_ref=str(row[8]) if row[8] is not None else None,
        cooldown_window_seconds=int(row[9]),
        service_principal_id=str(row[10]) if row[10] is not None else None,
        max_runs_per_hour=int(row[11]),
        max_daily_cost_usd=float(row[12]),
        max_consecutive_failures=int(row[13]),
        post_hoc_sampling_rate=float(row[14]),
        contract_signature_id=str(row[15]) if row[15] is not None else None,
        status=cast(WorkflowTriggerStatus, str(row[16])),
        auto_help_on_publish=bool(row[17]),
        consecutive_failures=int(row[18]),
        last_fired_at_iso=fmt_ts(row[19]),
        webhook_secret_configured=bool(encrypted),
        webhook_secret_fingerprint=str(row[21]) if row[21] is not None else None,
        webhook_secret_masked_hint=str(row[22]) if row[22] is not None else None,
        webhook_secret_updated_at=fmt_ts(row[23]),
        webhook_secret_updated_by=str(row[24]) if row[24] is not None else None,
        log_sink_service=str(row[25]) if row[25] is not None else None,
        log_sink_query_text=str(row[26]) if row[26] is not None else None,
        outbox_event_filter=str(row[27]) if row[27] is not None else None,
    )
    return entity, encrypted


async def insert_outbox_and_audit(
    conn: AsyncConnection,
    event: DomainEvent,
    audit_sink: AuditLedgerSinkPort | None,
) -> None:
    outbox_reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.domain_events_outbox')"))
    ).scalar()
    if outbox_reg is not None:
        await conn.execute(
            sa.text(
                """
                INSERT INTO domain_events_outbox (
                    event_id, event_type, aggregate_type, aggregate_id,
                    run_id, workspace_id, payload_jsonb, trace_id, status, attempts
                ) VALUES (
                    CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                    CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
                    CAST(:payload_jsonb AS jsonb), :trace_id, 'PUBLISHED', 1
                )
                ON CONFLICT (event_id) DO NOTHING
                """
            ),
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "run_id": event.run_id,
                "workspace_id": event.workspace_id,
                "payload_jsonb": json.dumps(event.payload, sort_keys=True),
                "trace_id": event.trace_id,
            },
        )
    if audit_sink is not None:
        ledger_reg = (
            await conn.execute(sa.text("SELECT to_regclass('public.audit_ledger')"))
        ).scalar()
        if ledger_reg is not None:
            entry = map_domain_event_to_ledger_entry(event)
            await audit_sink.record_entry(entry, conn=conn)  # type: ignore[call-arg]


@runtime_checkable
class WorkflowTriggerRepositoryPort(Protocol):
    """Hexagonal persistence port for workflow triggers, deliveries & idempotent runs."""

    async def list_triggers(
        self, *, workspace_id: str, workflow_id: str | None = None
    ) -> list[WorkflowTriggerEntity]: ...

    async def list_active_triggers(
        self, *, trigger_type: WorkflowTriggerType | None = None
    ) -> list[WorkflowTriggerEntity]: ...

    async def get_trigger(
        self, trigger_id: str
    ) -> tuple[WorkflowTriggerEntity, str | None] | None: ...

    async def save_trigger(
        self,
        trigger: WorkflowTriggerEntity,
        *,
        encrypted_secret: str | None = None,
        clear_secret: bool = False,
    ) -> WorkflowTriggerEntity: ...

    async def delete_trigger(self, *, workspace_id: str, trigger_id: str) -> None: ...

    async def record_webhook_delivery(self, *, trigger_id: str, delivery_key: str) -> bool: ...

    async def count_runs_last_hour(self, *, trigger_id: str) -> int: ...

    async def sum_daily_cost_usd(self, *, trigger_id: str) -> float: ...

    async def create_idempotent_trigger_run(
        self,
        *,
        run_id: str,
        trigger: WorkflowTriggerEntity,
        idempotency_key: str,
        status: str,
        budget_max_usd: float,
    ) -> bool: ...

    async def mark_trigger_fired(self, *, trigger_id: str) -> WorkflowTriggerEntity | None: ...

    async def record_trigger_failure(
        self, *, trigger_id: str, max_consecutive_failures: int
    ) -> tuple[int, bool]: ...

    async def set_trigger_status(
        self,
        *,
        trigger_id: str,
        status: WorkflowTriggerStatus,
        consecutive_failures: int | None = None,
    ) -> WorkflowTriggerEntity: ...

    async def publish_outbox_event(self, event: DomainEvent) -> None: ...
