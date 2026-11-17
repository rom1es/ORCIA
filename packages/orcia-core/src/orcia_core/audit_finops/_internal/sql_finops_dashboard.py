"""Async SQL aggregation queries for FinOps dashboard and breakdowns (`Story 6.2`).

Pure SQLAlchemy asyncpg queries — zero N+1, zero Cartesian products, recursive scope filtering.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_connector_scope_clause,
    build_ledger_scope_clause,
    build_scoped_cte_with_acl,
    is_missing_table_error,
)
from orcia_core.audit_finops._internal.sql_finops_dashboard_processes import (
    fetch_dashboard_processes_sql,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.audit_finops.dashboard")


async def fetch_dashboard_overview_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Fetch consolidated KPI totals for the given hierarchical scope."""
    default_overview: dict[str, Any] = {
        "total_cost_usd": Decimal("0.000000"),
        "verified_internal_cost_usd": Decimal("0.000000"),
        "reported_external_cost_usd": Decimal("0.000000"),
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "internal_tokens": 0,
        "remote_tokens": 0,
        "total_external_calls": 0,
        "external_units_breakdown": {},
        "cache_savings_usd": Decimal("0.000000"),
        "active_circuit_breakers_count": 0,
        "accounted_runs_count": 0,
        "paused_runs_count": 0,
    }
    if engine is None:
        return default_overview
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return default_overview

    uuid_val, cte_sql, params = build_scoped_cte_with_acl(
        scope_type, scope_id, allowed_workspace_ids
    )
    ledger_where = build_ledger_scope_clause(scope_type, uuid_val, alias="l")
    if allowed_workspace_ids is not None:
        ledger_where = f"({ledger_where}) AND l.workspace_id IN (SELECT id FROM scoped_workspaces)"

    ledger_stmt = sa.text(
        f"""
        {cte_sql}
        SELECT
            COALESCE(SUM(l.cost_usd), 0.000000) AS total_cost_usd,
            COALESCE(SUM(CASE WHEN l.cost_source = 'INTERNAL_VERIFIED'
                              THEN l.cost_usd ELSE 0.000000 END),
                     0.000000) AS verified_internal_usd,
            COALESCE(SUM(CASE WHEN l.cost_source != 'INTERNAL_VERIFIED'
                              THEN l.cost_usd ELSE 0.000000 END),
                     0.000000) AS reported_external_usd,
            COALESCE(SUM(l.input_tokens), 0) AS total_input_tokens,
            COALESCE(SUM(l.output_tokens), 0) AS total_output_tokens,
            COALESCE(SUM(CASE WHEN l.reported_by_remote
                              THEN l.input_tokens + l.output_tokens ELSE 0 END),
                     0) AS remote_tokens,
            COALESCE(SUM(CASE WHEN NOT l.reported_by_remote
                              THEN l.input_tokens + l.output_tokens ELSE 0 END),
                     0) AS internal_tokens,
            COALESCE(SUM(CASE WHEN l.reported_by_remote
                              THEN 1 ELSE 0 END), 0) AS total_external_calls,
            COALESCE(SUM(
                CASE
                    WHEN (l.metadata_jsonb->>'cache_savings_usd') ~ '^[0-9]+(\\.[0-9]+)?$'
                    THEN (l.metadata_jsonb->>'cache_savings_usd')::numeric(12, 6)
                    ELSE 0.000000
                END
            ), 0.000000) AS cache_savings_usd
        FROM audit_ledger l
        WHERE {ledger_where};
        """
    )

    runs_where = (
        "TRUE"
        if (scope_type == "GLOBAL" and uuid_val is None and allowed_workspace_ids is None)
        else "r.workspace_id IN (SELECT id FROM scoped_workspaces)"
    )
    runs_stmt = sa.text(
        f"""
        {cte_sql}
        SELECT
            COUNT(*) AS accounted_runs,
            COALESCE(SUM(
                CASE WHEN r.status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES')
                     THEN 1 ELSE 0 END
            ), 0) AS paused_runs
        FROM workflow_runs r
        WHERE {runs_where};
        """
    )

    units_stmt = sa.text(
        f"""
        {cte_sql}
        SELECT l.native_metric_type, COALESCE(SUM(l.native_metric_value), 0) AS total_units
        FROM audit_ledger l
        WHERE l.reported_by_remote = TRUE
          AND l.native_metric_type IS NOT NULL
          AND l.native_metric_type NOT IN ('direct_cost', 'remote_tokens', 'calls')
          AND {ledger_where}
        GROUP BY l.native_metric_type;
        """
    )

    conn_scope_where = build_connector_scope_clause(scope_type, uuid_val)
    cb_stmt = sa.text(
        f"""
        {cte_sql}
        SELECT COUNT(*)
        FROM finops_connector_quotas
        WHERE circuit_state = 'CIRCUIT_OPEN'
          AND {conn_scope_where};
        """
    )

    try:
        async with engine.connect() as conn:
            ledger_res = (await conn.execute(ledger_stmt, params)).mappings().one()
            runs_res = (await conn.execute(runs_stmt, params)).mappings().one()
            units_rows = (await conn.execute(units_stmt, params)).mappings().all()
            units_breakdown: dict[str, float] = {
                str(r["native_metric_type"]): float(r["total_units"]) for r in units_rows
            }

            open_circuits = 0
            try:
                open_circuits = int((await conn.execute(cb_stmt, params)).scalar() or 0)
            except Exception as cb_exc:
                if is_missing_table_error(cb_exc):
                    logger.warning(
                        "finops_connector_circuit_count_table_missing",
                        error_type=type(cb_exc).__name__,
                    )
                else:
                    raise

            return {
                "total_cost_usd": Decimal(str(ledger_res["total_cost_usd"])),
                "verified_internal_cost_usd": Decimal(str(ledger_res["verified_internal_usd"])),
                "reported_external_cost_usd": Decimal(str(ledger_res["reported_external_usd"])),
                "total_input_tokens": int(ledger_res["total_input_tokens"]),
                "total_output_tokens": int(ledger_res["total_output_tokens"]),
                "internal_tokens": int(ledger_res["internal_tokens"]),
                "remote_tokens": int(ledger_res["remote_tokens"]),
                "total_external_calls": int(ledger_res["total_external_calls"]),
                "external_units_breakdown": units_breakdown,
                "cache_savings_usd": Decimal(str(ledger_res["cache_savings_usd"])),
                "active_circuit_breakers_count": open_circuits,
                "accounted_runs_count": int(runs_res["accounted_runs"]),
                "paused_runs_count": int(runs_res["paused_runs"]),
            }
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning(
                "finops_dashboard_overview_skipped_missing_table",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return default_overview
        logger.error(
            "finops_dashboard_overview_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


async def fetch_dashboard_tiers_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate inference costs and tokens by cognitive tier and effort."""
    if engine is None:
        return []
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return []

    uuid_val, cte_sql, params = build_scoped_cte_with_acl(
        scope_type, scope_id, allowed_workspace_ids
    )
    ledger_where = build_ledger_scope_clause(scope_type, uuid_val, alias="l")
    if allowed_workspace_ids is not None:
        ledger_where = f"({ledger_where}) AND l.workspace_id IN (SELECT id FROM scoped_workspaces)"

    stmt = sa.text(
        f"""
        {cte_sql}
        SELECT
            l.inference_tier,
            COALESCE(l.effort, 'default') AS effort,
            COUNT(*) AS invocations_count,
            COALESCE(SUM(l.input_tokens), 0) AS input_tokens,
            COALESCE(SUM(l.output_tokens), 0) AS output_tokens,
            COALESCE(SUM(l.cost_usd), 0.000000) AS cost_usd
        FROM audit_ledger l
        WHERE l.inference_tier IS NOT NULL
          AND {ledger_where}
        GROUP BY l.inference_tier, COALESCE(l.effort, 'default')
        ORDER BY l.inference_tier, effort;
        """
    )
    try:
        async with engine.connect() as conn:
            res = await conn.execute(stmt, params)
            rows = res.mappings().all()
            return [
                {
                    "inference_tier": str(r["inference_tier"]),
                    "effort": str(r["effort"]),
                    "invocations_count": int(r["invocations_count"]),
                    "input_tokens": int(r["input_tokens"]),
                    "output_tokens": int(r["output_tokens"]),
                    "cost_usd": Decimal(str(r["cost_usd"])),
                }
                for r in rows
            ]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning(
                "finops_dashboard_tiers_skipped_missing_table",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return []
        logger.error(
            "finops_dashboard_tiers_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


__all__ = [
    "fetch_dashboard_overview_sql",
    "fetch_dashboard_processes_sql",
    "fetch_dashboard_tiers_sql",
]
