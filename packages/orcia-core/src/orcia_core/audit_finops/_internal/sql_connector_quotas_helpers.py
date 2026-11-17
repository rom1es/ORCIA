"""Shared SQL helpers & row mappers for `finops_connector_quotas` (`Story 6.4`)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.audit_finops.finops_models import (
    DEFAULT_EUR_USD_RATE,
    ConnectorQuotaRecord,
)
from orcia_core.kernel.events import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.finops_telemetry import SanitizedRemoteUsage


def safe_uuid(val: str | None) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(val)
    except (ValueError, TypeError, AttributeError):
        return None


def row_to_connector_quota_record(
    row: Mapping[Any, Any],
    eur_usd_rate: Decimal = DEFAULT_EUR_USD_RATE,
) -> ConnectorQuotaRecord:
    monthly_usd = Decimal(str(row["monthly_cost_usd"]))
    monthly_eur = (monthly_usd * eur_usd_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    max_monthly_eur = (
        Decimal(str(row["max_monthly_cost_eur"]))
        if row["max_monthly_cost_eur"] is not None
        else None
    )
    max_daily = int(row["max_daily_calls"]) if row["max_daily_calls"] is not None else None
    daily_calls = int(row["daily_calls_count"])

    used_pct = Decimal("0.00")
    if max_monthly_eur is not None and max_monthly_eur > Decimal("0"):
        used_pct = ((monthly_eur / max_monthly_eur) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    elif max_daily is not None and max_daily > 0:
        used_pct = ((Decimal(daily_calls) / Decimal(max_daily)) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return ConnectorQuotaRecord(
        id=str(row["id"]),
        connector_key=str(row["connector_key"]),
        display_name=str(row["display_name"] or row["connector_key"]),
        service_kind=str(row["service_kind"]),
        scope_type=row["scope_type"],
        scope_id=str(row["scope_id"]) if row["scope_id"] else None,
        valuation_mode=row["valuation_mode"],
        max_reported_cost_per_call_eur=Decimal(str(row["max_reported_cost_per_call_eur"])),
        fixed_cost_per_call_eur=Decimal(str(row["fixed_cost_per_call_eur"])),
        unit_tariff_eur=Decimal(str(row["unit_tariff_eur"])),
        default_unit_name=str(row["default_unit_name"]) if row["default_unit_name"] else None,
        max_daily_calls=max_daily,
        max_monthly_cost_eur=max_monthly_eur,
        daily_calls_count=daily_calls,
        monthly_cost_usd=monthly_usd,
        monthly_cost_eur=monthly_eur,
        total_remote_tokens=int(row["total_remote_tokens"]),
        total_business_units=Decimal(str(row["total_business_units"])),
        circuit_state=row["circuit_state"],
        anomaly_count=int(row["anomaly_count"]),
        consecutive_anomalies=int(row["consecutive_anomalies"]),
        last_latency_ms=int(row["last_latency_ms"]),
        last_tripped_reason=str(row["last_tripped_reason"]) if row["last_tripped_reason"] else None,
        last_tripped_at=row["last_tripped_at"],
        last_invoked_at=row["last_invoked_at"],
        quota_used_pct=min(Decimal("100.00"), used_pct),
    )


async def insert_connector_outbox_event(conn: AsyncConnection, event: DomainEvent) -> None:
    await conn.execute(
        sa.text(
            """
            INSERT INTO domain_events_outbox (
                event_id, event_type, aggregate_type, aggregate_id,
                run_id, workspace_id, payload_jsonb, trace_id, status, attempts
            ) VALUES (
                CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
                CAST(:payload_jsonb AS jsonb), :trace_id, :status, :attempts
            )
            ON CONFLICT (event_id) DO NOTHING;
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
            "status": event.status,
            "attempts": event.attempts,
        },
    )


async def insert_connector_ledger_row(
    conn: AsyncConnection,
    *,
    source_event_id: str,
    actor_type: str,
    actor_id: str,
    event_type: str,
    summary: str,
    scope_type: str,
    scope_id: str | None,
    cost_usd: Decimal,
    usage: SanitizedRemoteUsage | None = None,
    latency_ms: int = 0,
    trace_id: str = "00000000000000000000000000000000",
    metadata: dict[str, Any] | None = None,
) -> None:
    ws_id = scope_id if scope_type == "WORKSPACE" and safe_uuid(scope_id) else None
    await conn.execute(
        sa.text(
            """
            INSERT INTO audit_ledger (
                id, source_event_id, workspace_id, scope_path,
                actor_type, actor_id, event_type, summary,
                input_tokens, output_tokens, cost_usd, cost_source,
                native_metric_type, native_metric_value, native_currency,
                reported_by_remote, latency_ms, trace_id, metadata_jsonb
            ) VALUES (
                CAST(:id AS uuid), CAST(:source_event_id AS uuid),
                CAST(:workspace_id AS uuid), :scope_path,
                :actor_type, :actor_id, :event_type, :summary,
                :input_tokens, :output_tokens, :cost_usd, :cost_source,
                :native_metric_type, :native_metric_value, :native_currency,
                :reported_by_remote, :latency_ms, :trace_id, CAST(:metadata_jsonb AS jsonb)
            )
            ON CONFLICT (source_event_id) DO NOTHING;
            """
        ),
        {
            "id": new_uuid7_str(),
            "source_event_id": source_event_id,
            "workspace_id": ws_id,
            "scope_path": f"{scope_type}:{scope_id}" if scope_id else scope_type,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "event_type": event_type,
            "summary": summary,
            "input_tokens": usage.input_tokens if usage else 0,
            "output_tokens": usage.output_tokens if usage else 0,
            "cost_usd": cost_usd,
            "cost_source": usage.cost_source if usage else "INTERNAL_VERIFIED",
            "native_metric_type": usage.native_metric_type if usage else None,
            "native_metric_value": usage.native_metric_value if usage else None,
            "native_currency": usage.native_currency if usage else None,
            "reported_by_remote": bool(usage.reported_by_remote) if usage else False,
            "latency_ms": latency_ms,
            "trace_id": trace_id,
            "metadata_jsonb": json.dumps(metadata or {}, sort_keys=True),
        },
    )


__all__ = [
    "insert_connector_ledger_row",
    "insert_connector_outbox_event",
    "row_to_connector_quota_record",
    "safe_uuid",
]
