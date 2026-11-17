"""Async SQL repository for remote connector quotas, telemetry & circuit state (`Story 6.4`).

Pure SQLAlchemy asyncpg queries — zero circular dependencies, zero float drift.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_connector_scope_clause,
    build_scoped_workspaces_cte,
    is_missing_table_error,
)
from orcia_core.audit_finops._internal.sql_connector_circuit import (
    reset_connector_circuit_sql,
    trip_connector_circuit_sql,
    upsert_connector_quota_config_sql,
)
from orcia_core.audit_finops._internal.sql_connector_quotas_helpers import (
    insert_connector_ledger_row,
    insert_connector_outbox_event,
    row_to_connector_quota_record,
    safe_uuid,
)
from orcia_core.audit_finops.finops_models import (
    DEFAULT_EUR_USD_RATE,
    ConnectorQuotaRecord,
    ScopeType,
)
from orcia_core.kernel._finops_audit_events import (
    ConnectorCircuitTripped,
    RemoteUsageAnomalyCapped,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.ports.finops_telemetry import SanitizedRemoteUsage

logger = get_logger("orcia.core.audit_finops.connectors")


async def fetch_connector_quota_sql(
    engine: AsyncEngine,
    connector_key: str,
) -> ConnectorQuotaRecord | None:
    try:
        async with engine.connect() as conn:
            res = await conn.execute(
                sa.text("SELECT * FROM finops_connector_quotas WHERE connector_key = :key"),
                {"key": connector_key},
            )
            row = res.mappings().first()
            return row_to_connector_quota_record(row) if row is not None else None
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("finops_fetch_connector_quota_skipped", error_type=type(exc).__name__)
            return None
        logger.error(
            "finops_fetch_connector_quota_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


async def list_connector_quotas_sql(
    engine: AsyncEngine,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> list[ConnectorQuotaRecord]:
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return []
    uuid_val = safe_uuid(scope_id)
    cte_sql, params = build_scoped_workspaces_cte(scope_type, uuid_val)
    scope_where = build_connector_scope_clause(scope_type, uuid_val)
    if allowed_workspace_ids is not None:
        uuids = [u for raw in allowed_workspace_ids if (u := safe_uuid(raw)) is not None]
        if not uuids:
            return []
        params["allowed_ws_ids"] = uuids
        scope_where = (
            f"({scope_where}) AND ("
            "scope_type = 'GLOBAL' "
            "OR (scope_type = 'WORKSPACE' AND scope_id = ANY(:allowed_ws_ids)) "
            "OR (scope_type IN ('BU', 'TEAM') AND scope_id IN ("
            "    SELECT w.owner_org_unit_id FROM workspaces w WHERE w.id = ANY(:allowed_ws_ids)"
            "))"
            ")"
        )
    stmt = sa.text(
        f"""
        {cte_sql}
        SELECT *
        FROM finops_connector_quotas
        WHERE {scope_where}
        ORDER BY connector_key ASC;
        """
    )
    try:
        async with engine.connect() as conn:
            res = await conn.execute(stmt, params)
            return [row_to_connector_quota_record(r) for r in res.mappings().all()]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("finops_list_connector_quotas_skipped", error_type=type(exc).__name__)
            return []
        logger.error(
            "finops_list_connector_quotas_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


async def record_connector_usage_sql(
    engine: AsyncEngine,
    *,
    connector_key: str,
    usage: SanitizedRemoteUsage,
    latency_ms: int = 0,
    anomaly_trip_threshold: int = 3,
    eur_usd_rate: Decimal = DEFAULT_EUR_USD_RATE,
    trace_id: str = "00000000000000000000000000000000",
) -> ConnectorQuotaRecord:
    cost_usd_dec = Decimal(str(round(usage.cost_usd, 6))).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    tokens_delta = int(usage.input_tokens) + int(usage.output_tokens)
    business_units_delta = (
        Decimal(str(usage.native_metric_value))
        if (
            usage.native_metric_value is not None
            and usage.native_metric_type not in (None, "direct_cost", "remote_tokens", "calls")
        )
        else Decimal("0.000000")
    )
    anomaly_inc = 1 if usage.is_anomaly_capped else 0

    async with engine.begin() as conn:
        res = await conn.execute(
            sa.text(
                """
                INSERT INTO finops_connector_quotas (
                    id, connector_key, display_name, service_kind,
                    daily_calls_count, daily_calls_window_date,
                    monthly_cost_usd, total_remote_tokens, total_business_units,
                    anomaly_count, consecutive_anomalies, last_latency_ms,
                    last_invoked_at, created_at, updated_at
                ) VALUES (
                    :id, :connector_key, :display_name, 'MCP_SERVER',
                    1, CURRENT_DATE,
                    :cost_usd, :tokens_delta, :units_delta,
                    :anomaly_inc, :anomaly_inc, :latency_ms,
                    NOW(), NOW(), NOW()
                )
                ON CONFLICT (connector_key) DO UPDATE SET
                    daily_calls_count = CASE
                        WHEN finops_connector_quotas.daily_calls_window_date = CURRENT_DATE
                        THEN finops_connector_quotas.daily_calls_count + 1
                        ELSE 1
                    END,
                    daily_calls_window_date = CURRENT_DATE,
                    monthly_cost_usd = (
                        finops_connector_quotas.monthly_cost_usd + EXCLUDED.monthly_cost_usd
                    ),
                    total_remote_tokens = (
                        finops_connector_quotas.total_remote_tokens + EXCLUDED.total_remote_tokens
                    ),
                    total_business_units = (
                        finops_connector_quotas.total_business_units + EXCLUDED.total_business_units
                    ),
                    anomaly_count = finops_connector_quotas.anomaly_count + EXCLUDED.anomaly_count,
                    consecutive_anomalies = CASE
                        WHEN EXCLUDED.anomaly_count > 0
                        THEN finops_connector_quotas.consecutive_anomalies + 1
                        ELSE 0
                    END,
                    circuit_state = CASE
                        WHEN finops_connector_quotas.circuit_state = 'HALF_OPEN'
                             AND EXCLUDED.anomaly_count = 0
                        THEN 'CLOSED'
                        ELSE finops_connector_quotas.circuit_state
                    END,
                    last_latency_ms = EXCLUDED.last_latency_ms,
                    last_invoked_at = NOW(),
                    updated_at = NOW()
                RETURNING *;
                """
            ),
            {
                "id": UUID(new_uuid7_str()),
                "connector_key": connector_key,
                "display_name": connector_key,
                "cost_usd": cost_usd_dec,
                "tokens_delta": tokens_delta,
                "units_delta": business_units_delta,
                "anomaly_inc": anomaly_inc,
                "latency_ms": max(0, latency_ms),
            },
        )
        row = res.mappings().one()
        rec = row_to_connector_quota_record(row, eur_usd_rate=eur_usd_rate)

        call_evt_id = new_uuid7_str()
        await insert_connector_ledger_row(
            conn,
            source_event_id=call_evt_id,
            actor_type="REMOTE_CONNECTOR",
            actor_id=connector_key,
            event_type="StepCompleted",
            summary=f"Invocation service externe {connector_key}",
            scope_type=rec.scope_type,
            scope_id=rec.scope_id,
            cost_usd=cost_usd_dec,
            usage=usage,
            latency_ms=max(0, latency_ms),
            trace_id=trace_id,
            metadata={
                "connector_key": connector_key,
                "is_anomaly_capped": usage.is_anomaly_capped,
            },
        )

        if usage.is_anomaly_capped:
            anomaly_evt = RemoteUsageAnomalyCapped.create(
                connector_id=connector_key,
                reported_cost_eur=usage.original_reported_cost_eur or usage.cost_eur,
                capped_cost_eur=usage.cost_eur,
                workspace_id=rec.scope_id if rec.scope_type == "WORKSPACE" else None,
                trace_id=trace_id,
            )
            await insert_connector_outbox_event(conn, anomaly_evt)

        trip_reason: str | None = None
        if rec.max_daily_calls is not None and rec.daily_calls_count >= rec.max_daily_calls:
            trip_reason = (
                f"Daily calls limit reached ({rec.daily_calls_count}/{rec.max_daily_calls})"
            )
        elif (
            rec.max_monthly_cost_eur is not None
            and rec.monthly_cost_eur >= rec.max_monthly_cost_eur
        ):
            trip_reason = (
                f"Monthly cost limit reached ({rec.monthly_cost_eur} EUR / "
                f"{rec.max_monthly_cost_eur} EUR)"
            )
        elif rec.consecutive_anomalies >= anomaly_trip_threshold:
            trip_reason = f"Consecutive telemetry anomalies ({rec.consecutive_anomalies})"

        if trip_reason is not None and rec.circuit_state != "CIRCUIT_OPEN":
            tripped_res = await conn.execute(
                sa.text(
                    """
                    UPDATE finops_connector_quotas
                    SET circuit_state = 'CIRCUIT_OPEN',
                        last_tripped_reason = :reason,
                        last_tripped_at = NOW(),
                        updated_at = NOW()
                    WHERE connector_key = :key
                    RETURNING *;
                    """
                ),
                {"key": connector_key, "reason": trip_reason},
            )
            rec = row_to_connector_quota_record(
                tripped_res.mappings().one(), eur_usd_rate=eur_usd_rate
            )
            trip_evt = ConnectorCircuitTripped.create(
                connector_id=connector_key,
                circuit_state="CIRCUIT_OPEN",
                reason=trip_reason,
                workspace_id=rec.scope_id if rec.scope_type == "WORKSPACE" else None,
                trace_id=trace_id,
            )
            await insert_connector_outbox_event(conn, trip_evt)

        return rec


__all__ = [
    "fetch_connector_quota_sql",
    "list_connector_quotas_sql",
    "record_connector_usage_sql",
    "reset_connector_circuit_sql",
    "trip_connector_circuit_sql",
    "upsert_connector_quota_config_sql",
]
