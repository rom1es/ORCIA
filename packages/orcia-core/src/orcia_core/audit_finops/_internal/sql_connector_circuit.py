"""Async SQL connector quota config, circuit trip & reset operations (`Story 6.4`)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._audit_finops_locales import get_audit_finops_locale_bundle
from orcia_core.audit_finops._internal._sql_scope_filter import is_missing_table_error
from orcia_core.audit_finops._internal.sql_connector_quotas_helpers import (
    insert_connector_ledger_row,
    insert_connector_outbox_event,
    row_to_connector_quota_record,
    safe_uuid,
)
from orcia_core.audit_finops.finops_models import ConnectorQuotaRecord, ScopeType
from orcia_core.kernel.events import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.ports.finops_telemetry import CircuitBreakerState, ValuationMode
from orcia_kernel.errors import ValidationDomainError

logger = get_logger("orcia.core.audit_finops.circuit")


async def upsert_connector_quota_config_sql(
    engine: AsyncEngine,
    *,
    connector_key: str,
    display_name: str | None = None,
    service_kind: str | None = None,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    valuation_mode: ValuationMode = "NATIVE_TELEMETRY",
    max_reported_cost_per_call_eur: Decimal = Decimal("5.000000"),
    fixed_cost_per_call_eur: Decimal = Decimal("0.000000"),
    unit_tariff_eur: Decimal = Decimal("0.000000"),
    default_unit_name: str | None = None,
    max_daily_calls: int | None = None,
    max_monthly_cost_eur: Decimal | None = None,
) -> ConnectorQuotaRecord:
    stmt = sa.text(
        """
        INSERT INTO finops_connector_quotas (
            id, connector_key, display_name, service_kind, scope_type, scope_id,
            valuation_mode, max_reported_cost_per_call_eur, fixed_cost_per_call_eur,
            unit_tariff_eur, default_unit_name, max_daily_calls, max_monthly_cost_eur,
            created_at, updated_at
        ) VALUES (
            :id, :connector_key, :display_name, :service_kind, :scope_type, :scope_id,
            :valuation_mode, :max_reported_cost_per_call_eur, :fixed_cost_per_call_eur,
            :unit_tariff_eur, :default_unit_name, :max_daily_calls, :max_monthly_cost_eur,
            NOW(), NOW()
        )
        ON CONFLICT (connector_key) DO UPDATE SET
            display_name = COALESCE(NULLIF(EXCLUDED.display_name, ''),
                                    finops_connector_quotas.display_name),
            service_kind = COALESCE(NULLIF(EXCLUDED.service_kind, ''),
                                    finops_connector_quotas.service_kind),
            scope_type = EXCLUDED.scope_type,
            scope_id = EXCLUDED.scope_id,
            valuation_mode = EXCLUDED.valuation_mode,
            max_reported_cost_per_call_eur = EXCLUDED.max_reported_cost_per_call_eur,
            fixed_cost_per_call_eur = EXCLUDED.fixed_cost_per_call_eur,
            unit_tariff_eur = EXCLUDED.unit_tariff_eur,
            default_unit_name = EXCLUDED.default_unit_name,
            max_daily_calls = EXCLUDED.max_daily_calls,
            max_monthly_cost_eur = EXCLUDED.max_monthly_cost_eur,
            updated_at = NOW()
        RETURNING *;
        """
    )
    try:
        async with engine.begin() as conn:
            res = await conn.execute(
                stmt,
                {
                    "id": UUID(new_uuid7_str()),
                    "connector_key": connector_key,
                    "display_name": display_name or connector_key,
                    "service_kind": service_kind or "MCP_SERVER",
                    "scope_type": scope_type,
                    "scope_id": safe_uuid(scope_id),
                    "valuation_mode": valuation_mode,
                    "max_reported_cost_per_call_eur": max_reported_cost_per_call_eur,
                    "fixed_cost_per_call_eur": fixed_cost_per_call_eur,
                    "unit_tariff_eur": unit_tariff_eur,
                    "default_unit_name": default_unit_name,
                    "max_daily_calls": max_daily_calls,
                    "max_monthly_cost_eur": max_monthly_cost_eur,
                },
            )
            return row_to_connector_quota_record(res.mappings().one())
    except ProgrammingError as exc:
        logger.warning("FinOps upsert_connector_quota_config_sql schema unavailable: %s", exc)
        raise ValidationDomainError(
            detail_override="FinOps connector quotas schema is not migrated yet."
        ) from exc


async def trip_connector_circuit_sql(
    engine: AsyncEngine,
    *,
    connector_key: str,
    reason: str,
    event: DomainEvent,
    scope_type: str = "GLOBAL",
    scope_id: str | None = None,
) -> ConnectorQuotaRecord | None:
    async with engine.begin() as conn:
        res = await conn.execute(
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
            {"key": connector_key, "reason": reason},
        )
        row = res.mappings().first()
        if row is None:
            return None
        await insert_connector_outbox_event(conn, event)
        await insert_connector_ledger_row(
            conn,
            source_event_id=event.event_id,
            actor_type="FINOPS_QUOTA_GUARD",
            actor_id=connector_key,
            event_type=event.event_type,
            summary=f"Coupe-circuit ouvert sur connecteur {connector_key} : {reason}",
            scope_type=scope_type,
            scope_id=scope_id,
            cost_usd=Decimal("0.000000"),
            trace_id=event.trace_id,
            metadata=event.payload,
        )
        return row_to_connector_quota_record(row)


async def reset_connector_circuit_sql(
    engine: AsyncEngine,
    *,
    connector_key: str,
    target_state: CircuitBreakerState,
    actor_id: str,
    trace_id: str,
) -> ConnectorQuotaRecord | None:
    try:
        async with engine.begin() as conn:
            res = await conn.execute(
                sa.text(
                    """
                    UPDATE finops_connector_quotas
                    SET circuit_state = :target_state,
                        consecutive_anomalies = 0,
                        last_tripped_reason = NULL,
                        updated_at = NOW()
                    WHERE connector_key = :key
                    RETURNING *;
                    """
                ),
                {"key": connector_key, "target_state": target_state},
            )
            row = res.mappings().first()
            if row is None:
                return None
            rec = row_to_connector_quota_record(row)
            await insert_connector_ledger_row(
                conn,
                source_event_id=new_uuid7_str(),
                actor_type="USER",
                actor_id=actor_id,
                event_type="SettingsChanged",
                summary=get_audit_finops_locale_bundle("fr").circuit_reset_tpl.format(
                    key=connector_key, state=target_state
                ),
                scope_type=rec.scope_type,
                scope_id=rec.scope_id,
                cost_usd=Decimal("0.000000"),
                trace_id=trace_id,
                metadata={
                    "category": "FINOPS_CONNECTOR_CIRCUIT_RESET",
                    "connector_key": connector_key,
                    "target_state": target_state,
                },
            )
            return rec
    except ProgrammingError as exc:
        logger.error(
            "finops_reset_connector_circuit_sql_error",
            connector_key=connector_key,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        if is_missing_table_error(exc):
            raise ValidationDomainError(
                detail_override="FinOps connector quotas schema is not migrated yet."
            ) from exc
        raise


__all__ = [
    "reset_connector_circuit_sql",
    "trip_connector_circuit_sql",
    "upsert_connector_quota_config_sql",
]
