"""Async SQL aggregation queries for per-workflow FinOps breakdown (`Story 6.2`).

Extracted from `sql_finops_dashboard.py` to keep SQL modules compact and single-purpose.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_scoped_cte_with_acl,
    is_missing_table_error,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.audit_finops.dashboard.processes")


async def fetch_dashboard_processes_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate per-workflow process costs, effort, baselines & pauses cleanly."""
    if engine is None:
        return []
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return []

    uuid_val, cte_sql, params = build_scoped_cte_with_acl(
        scope_type, scope_id, allowed_workspace_ids
    )
    acl_wd_filter = (
        "OR wd.workspace_id IS NULL"
        if allowed_workspace_ids is None
        else (
            "AND (wd.workspace_id IS NULL OR wd.workspace_id IN (SELECT id FROM scoped_workspaces))"
        )
    )
    where_clause = (
        f"WHERE (wd.workspace_id IN (SELECT id FROM scoped_workspaces) {acl_wd_filter})"
        if (scope_type == "GLOBAL" and uuid_val is None and allowed_workspace_ids is None)
        else "WHERE (r.id IS NOT NULL OR wd.workspace_id IN (SELECT id FROM scoped_workspaces))"
    )

    stmt = sa.text(
        f"""
        {cte_sql},
        run_ledger AS (
            SELECT l.run_id, COALESCE(SUM(l.cost_usd), 0.000000) AS run_cost_usd
            FROM audit_ledger l
            WHERE l.run_id IS NOT NULL
            GROUP BY l.run_id
        ),
        run_overrides AS (
            SELECT ovr.run_id, COALESCE(SUM(ovr.override_amount_usd), 0.000000) AS overrides_usd
            FROM finops_budget_overrides ovr
            GROUP BY ovr.run_id
        ),
        run_human_ms AS (
            SELECT
                r.id AS run_id,
                COALESCE(ge_agg.ms, 0)
                + COALESCE(has_agg.ms, 0)
                + COALESCE(har_agg.ms, 0) AS human_ms
            FROM workflow_runs r
            LEFT JOIN (
                SELECT run_id,
                       COALESCE(SUM(CASE WHEN gate_type = 'HUMAN'
                                         THEN review_duration_ms ELSE 0 END), 0) AS ms
                FROM gate_evaluations
                GROUP BY run_id
            ) ge_agg ON ge_agg.run_id = r.id
            LEFT JOIN (
                SELECT run_id,
                       COALESCE(SUM(GREATEST(char_length * 200, 30000)), 0) AS ms
                FROM human_anchor_signatures
                GROUP BY run_id
            ) has_agg ON has_agg.run_id = r.id
            LEFT JOIN (
                SELECT run_id,
                       COALESCE(SUM(
                           CASE
                               WHEN status = 'RESOLVED_BY_HUMAN'
                                    AND resolved_at IS NOT NULL
                                    AND resolved_at >= created_at
                               THEN LEAST(
                                   GREATEST(EXTRACT(EPOCH FROM (resolved_at - created_at)) * 1000,
                                            15000),
                                   1800000
                               )
                               WHEN status = 'RESOLVED_BY_HUMAN' THEN 60000
                               ELSE 0
                           END
                       ), 0) AS ms
                FROM human_arbitration_requests
                GROUP BY run_id
            ) har_agg ON har_agg.run_id = r.id
        ),
        wf_baselines AS (
            SELECT DISTINCT ON (wb.workflow_definition_id)
                wb.workflow_definition_id,
                wb.manual_time_minutes,
                wb.manual_cost_usd,
                wb.target_ttm_reduction_pct
            FROM finops_workflow_baselines wb
            WHERE (:scope_type = 'WORKSPACE'
                   AND (wb.scope_id = CAST(:scope_id AS uuid) OR wb.scope_id IS NULL))
               OR (:scope_type <> 'WORKSPACE' AND wb.scope_id IS NULL)
            ORDER BY wb.workflow_definition_id, (wb.scope_id IS NULL) ASC, wb.updated_at DESC
        )
        SELECT
            wd.id AS workflow_id,
            COALESCE(
                NULLIF(wd.steps_schema_jsonb->>'title', ''),
                NULLIF(split_part(wd.uri, '/', -1), ''),
                wd.uri
            ) AS workflow_title,
            COUNT(DISTINCT r.id) AS runs_count,
            COALESCE(SUM(ro.overrides_usd), 0.000000) AS overrides_usd,
            COALESCE(SUM(rl.run_cost_usd), 0.000000) AS run_cost_usd,
            COALESCE(SUM(rhm.human_ms), 0) AS human_ms,
            COUNT(DISTINCT r.id) FILTER (
                WHERE r.status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES')
            ) AS paused_runs,
            MAX(r.id::text) FILTER (
                WHERE r.status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES')
            ) AS sample_paused_run_id,
            MAX(r.status) FILTER (
                WHERE r.status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES')
            ) AS sample_paused_status,
            (wb.workflow_definition_id IS NOT NULL) AS has_declared_baseline,
            wb.manual_time_minutes,
            wb.manual_cost_usd,
            wb.target_ttm_reduction_pct
        FROM workflow_definitions wd
        LEFT JOIN workflow_runs r
            ON r.workflow_def_id = wd.id
           AND r.workspace_id IN (SELECT id FROM scoped_workspaces)
        LEFT JOIN run_ledger rl ON rl.run_id = r.id
        LEFT JOIN run_overrides ro ON ro.run_id = r.id
        LEFT JOIN run_human_ms rhm ON rhm.run_id = r.id
        LEFT JOIN wf_baselines wb ON wb.workflow_definition_id = wd.id
        {where_clause}
        GROUP BY
            wd.id, wd.steps_schema_jsonb, wd.uri,
            wb.workflow_definition_id, wb.manual_time_minutes,
            wb.manual_cost_usd, wb.target_ttm_reduction_pct
        ORDER BY runs_count DESC, workflow_title ASC;
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
                    "human_ms": int(r["human_ms"]),
                    "paused_runs": int(r["paused_runs"]),
                    "sample_paused_run_id": (
                        str(r["sample_paused_run_id"])
                        if r["sample_paused_run_id"] is not None
                        else None
                    ),
                    "sample_paused_status": (
                        str(r["sample_paused_status"])
                        if r["sample_paused_status"] is not None
                        else None
                    ),
                    "has_declared_baseline": bool(r["has_declared_baseline"]),
                    "manual_time_minutes": r["manual_time_minutes"],
                    "manual_cost_usd": (
                        Decimal(str(r["manual_cost_usd"]))
                        if r["manual_cost_usd"] is not None
                        else None
                    ),
                    "target_ttm_reduction_pct": r["target_ttm_reduction_pct"],
                }
                for r in rows
            ]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning(
                "finops_dashboard_processes_skipped_missing_table",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return []
        logger.error(
            "finops_dashboard_processes_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


__all__ = ["fetch_dashboard_processes_sql"]
