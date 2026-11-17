"""Async SQL aggregation queries for FinOps dashboard and breakdowns (`Story 6.2`).

Pure SQLAlchemy asyncpg queries (< 300 lines).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops.finops_models import ScopeType

logger = logging.getLogger(__name__)


def _safe_uuid(val: str | None) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(val)
    except (ValueError, TypeError, AttributeError):
        return None


async def fetch_dashboard_overview_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
) -> dict[str, Any]:
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
        "active_circuit_breakers_count": 0,
        "accounted_runs_count": 0,
        "paused_runs_count": 0,
    }
    if engine is None:
        return default_overview

    uuid_val = _safe_uuid(scope_id)
    scope_filter = ""
    params: dict[str, Any] = {}
    if uuid_val is not None:
        scope_filter = "WHERE l.workspace_id = :scope_id"
        params["scope_id"] = uuid_val

    ledger_stmt = sa.text(
        f"""
        SELECT
            COALESCE(SUM(cost_usd), 0.000000) as total_cost_usd,
            COALESCE(SUM(CASE WHEN cost_source = 'INTERNAL_VERIFIED'
                              THEN cost_usd ELSE 0.000000 END), 0.000000) as verified_internal_usd,
            COALESCE(SUM(CASE WHEN cost_source != 'INTERNAL_VERIFIED'
                              THEN cost_usd ELSE 0.000000 END), 0.000000) as reported_external_usd,
            COALESCE(SUM(input_tokens), 0) as total_input_tokens,
            COALESCE(SUM(output_tokens), 0) as total_output_tokens,
            COALESCE(SUM(CASE WHEN reported_by_remote
                              THEN input_tokens + output_tokens ELSE 0 END), 0) as remote_tokens,
            COALESCE(SUM(CASE WHEN NOT reported_by_remote
                              THEN input_tokens + output_tokens ELSE 0 END), 0) as internal_tokens,
            COALESCE(SUM(CASE WHEN reported_by_remote
                              THEN 1 ELSE 0 END), 0) as total_external_calls
        FROM audit_ledger l
        {scope_filter};
        """
    )

    runs_filter = ""
    if uuid_val is not None:
        runs_filter = "WHERE workspace_id = :scope_id"
    runs_stmt = sa.text(
        f"""
        SELECT
            COUNT(*) as accounted_runs,
            COALESCE(SUM(
                CASE WHEN status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES')
                     THEN 1 ELSE 0 END
            ), 0) as paused_runs
        FROM workflow_runs
        {runs_filter};
        """
    )

    try:
        async with engine.connect() as conn:
            ledger_res = (await conn.execute(ledger_stmt, params)).mappings().one()
            runs_res = (await conn.execute(runs_stmt, params)).mappings().one()

            units_where = (
                "WHERE l.reported_by_remote = TRUE AND l.native_metric_type IS NOT NULL "
                "AND l.native_metric_type NOT IN ('direct_cost', 'remote_tokens', 'calls')"
            )
            if uuid_val is not None:
                units_where += " AND l.workspace_id = :scope_id"
            units_stmt = sa.text(
                f"""
                SELECT l.native_metric_type, COALESCE(SUM(l.native_metric_value), 0) as total_units
                FROM audit_ledger l
                {units_where}
                GROUP BY l.native_metric_type;
                """
            )
            units_rows = (await conn.execute(units_stmt, params)).mappings().all()
            units_breakdown: dict[str, float] = {
                str(r["native_metric_type"]): float(r["total_units"]) for r in units_rows
            }

            open_circuits = 0
            try:
                cb_stmt = sa.text(
                    "SELECT COUNT(*) FROM finops_connector_quotas "
                    "WHERE circuit_state = 'CIRCUIT_OPEN';"
                )
                open_circuits = int((await conn.execute(cb_stmt)).scalar() or 0)
            except Exception as cb_exc:
                logger.warning("FinOps connector circuit count skipped: %s", cb_exc)

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
                "active_circuit_breakers_count": open_circuits,
                "accounted_runs_count": int(runs_res["accounted_runs"]),
                "paused_runs_count": int(runs_res["paused_runs"]),
            }
    except Exception as exc:
        logger.warning(
            "FinOps dashboard overview query skipped (uninitialized DB or test fixture): %s", exc
        )
        return default_overview


async def fetch_dashboard_processes_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
) -> list[dict[str, Any]]:
    if engine is None:
        return []
    uuid_val = _safe_uuid(scope_id)
    scope_clause = ""
    params: dict[str, Any] = {}
    if uuid_val is not None:
        scope_clause = "WHERE r.workspace_id = :scope_id"
        params["scope_id"] = uuid_val

    stmt = sa.text(
        f"""
        SELECT
            wd.id as workflow_id,
            wd.title as workflow_title,
            COUNT(DISTINCT r.id) as runs_count,
            COALESCE(SUM(DISTINCT ovr.override_amount_usd), 0.000000) as overrides_usd,
            COALESCE(SUM(l.cost_usd), 0.000000) as run_cost_usd,
            COALESCE(SUM(
                CASE WHEN r.status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES')
                     THEN 1 ELSE 0 END
            ), 0) as paused_runs,
            wb.manual_time_minutes,
            wb.manual_cost_usd,
            wb.target_ttm_reduction_pct
        FROM workflow_definitions wd
        LEFT JOIN workflow_runs r ON r.workflow_def_id = wd.id
        LEFT JOIN audit_ledger l ON l.run_id = r.id
        LEFT JOIN finops_budget_overrides ovr ON ovr.run_id = r.id
        LEFT JOIN finops_workflow_baselines wb ON wb.workflow_definition_id = wd.id
        {scope_clause}
        GROUP BY
            wd.id, wd.title, wb.manual_time_minutes,
            wb.manual_cost_usd, wb.target_ttm_reduction_pct
        ORDER BY runs_count DESC, wd.title ASC;
        """
    )
    try:
        async with engine.connect() as conn:
            res = await conn.execute(stmt, params)
            rows = res.mappings().all()
            return [
                {
                    "workflow_id": str(r["workflow_id"]),
                    "workflow_title": str(r["workflow_title"]),
                    "runs_count": int(r["runs_count"]),
                    "run_cost_usd": Decimal(str(r["run_cost_usd"])),
                    "overrides_usd": Decimal(str(r["overrides_usd"])),
                    "paused_runs": int(r["paused_runs"]),
                    "manual_time_minutes": r["manual_time_minutes"],
                    "manual_cost_usd": Decimal(str(r["manual_cost_usd"]))
                    if r["manual_cost_usd"] is not None
                    else None,
                    "target_ttm_reduction_pct": r["target_ttm_reduction_pct"],
                }
                for r in rows
            ]
    except Exception as exc:
        logger.warning("FinOps dashboard processes query skipped: %s", exc)
        return []


async def fetch_dashboard_tiers_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
) -> list[dict[str, Any]]:
    if engine is None:
        return []
    uuid_val = _safe_uuid(scope_id)
    scope_clause = "WHERE l.inference_tier IS NOT NULL"
    params: dict[str, Any] = {}
    if uuid_val is not None:
        scope_clause += " AND l.workspace_id = :scope_id"
        params["scope_id"] = uuid_val

    stmt = sa.text(
        f"""
        SELECT
            l.inference_tier,
            COALESCE(l.effort, 'default') as effort,
            COUNT(*) as invocations_count,
            COALESCE(SUM(l.input_tokens), 0) as input_tokens,
            COALESCE(SUM(l.output_tokens), 0) as output_tokens,
            COALESCE(SUM(l.cost_usd), 0.000000) as cost_usd
        FROM audit_ledger l
        {scope_clause}
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
        logger.warning("FinOps dashboard tiers query skipped: %s", exc)
        return []


__all__ = [
    "fetch_dashboard_overview_sql",
    "fetch_dashboard_processes_sql",
    "fetch_dashboard_tiers_sql",
]
