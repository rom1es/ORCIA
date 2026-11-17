"""Async SQL repositories for FinOps workflow baselines (`Story 6.2`, `BLOCKING-RES-02`).

Extracted from `sql_finops_accounting.py` to keep SQL modules compact (< 350 lines)
and enforce scope + ACL workspace isolation on baseline reads.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_scoped_cte_with_acl,
    is_missing_table_error,
    safe_uuid,
)
from orcia_core.audit_finops.finops_models import FinopsWorkflowBaseline, ScopeType
from orcia_core.observability.logging import get_logger
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.audit_finops.baselines")


async def upsert_workflow_baseline_sql(
    engine: AsyncEngine,
    *,
    workflow_definition_id: str,
    scope_id: str | None,
    manual_time_minutes: int,
    manual_cost_usd: Decimal,
    target_ttm_reduction_pct: int = 25,
) -> FinopsWorkflowBaseline:
    """Insert or update a declared manual baseline for a workflow definition."""
    new_id = new_uuid7_str()
    scope_uuid = UUID(scope_id) if scope_id else None
    wf_uuid = UUID(workflow_definition_id)
    stmt = sa.text(
        """
        INSERT INTO finops_workflow_baselines (
            id, workflow_definition_id, scope_id, manual_time_minutes,
            manual_cost_usd, target_ttm_reduction_pct, created_at, updated_at
        ) VALUES (
            :id, :wf_id, :scope_id, :manual_time_minutes,
            :manual_cost_usd, :target_ttm_reduction_pct, NOW(), NOW()
        )
        ON CONFLICT (
            workflow_definition_id,
            (COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid))
        )
        DO UPDATE SET
            manual_time_minutes = EXCLUDED.manual_time_minutes,
            manual_cost_usd = EXCLUDED.manual_cost_usd,
            target_ttm_reduction_pct = EXCLUDED.target_ttm_reduction_pct,
            updated_at = NOW()
        RETURNING id, workflow_definition_id, scope_id, manual_time_minutes,
                  manual_cost_usd, target_ttm_reduction_pct, created_at, updated_at;
        """
    )
    async with engine.begin() as conn:
        res = await conn.execute(
            stmt,
            {
                "id": UUID(new_id),
                "wf_id": wf_uuid,
                "scope_id": scope_uuid,
                "manual_time_minutes": manual_time_minutes,
                "manual_cost_usd": manual_cost_usd,
                "target_ttm_reduction_pct": target_ttm_reduction_pct,
            },
        )
        row = res.mappings().one()
        return FinopsWorkflowBaseline(
            id=str(row["id"]),
            workflow_definition_id=str(row["workflow_definition_id"]),
            scope_id=str(row["scope_id"]) if row["scope_id"] else None,
            manual_time_minutes=row["manual_time_minutes"],
            manual_cost_usd=Decimal(str(row["manual_cost_usd"])),
            target_ttm_reduction_pct=row["target_ttm_reduction_pct"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


async def list_workflow_baselines_sql(
    engine: AsyncEngine,
    *,
    workflow_definition_id: str | None = None,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> list[FinopsWorkflowBaseline]:
    """List declared workflow baselines strictly filtered by requested scope & RBAC allowlist."""
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return []

    explicit_scope_uuid = safe_uuid(scope_id)
    effective_scope_type: ScopeType = (
        "WORKSPACE" if (scope_type == "GLOBAL" and explicit_scope_uuid is not None) else scope_type
    )
    uuid_val, cte_sql, params = build_scoped_cte_with_acl(
        effective_scope_type, scope_id, allowed_workspace_ids
    )
    wf_uuid = safe_uuid(workflow_definition_id)
    wf_clause = ""
    if wf_uuid is not None:
        wf_clause = " AND b.workflow_definition_id = :wf_id"
        params["wf_id"] = wf_uuid

    is_unrestricted_global = (
        effective_scope_type == "GLOBAL" and uuid_val is None and allowed_workspace_ids is None
    )
    if is_unrestricted_global:
        query = f"""
            SELECT b.*
            FROM finops_workflow_baselines b
            WHERE 1=1{wf_clause}
            ORDER BY b.created_at ASC;
        """
    else:
        global_template_clause = (
            """
                          OR (
                              wd.workspace_id IS NULL
                              AND NOT EXISTS (
                                  SELECT 1 FROM workflow_runs wr2
                                  WHERE wr2.workflow_def_id = wd.id
                              )
                          )"""
            if effective_scope_type == "GLOBAL"
            else ""
        )
        query = f"""
            {cte_sql}
            SELECT b.*
            FROM finops_workflow_baselines b
            JOIN workflow_definitions wd ON wd.id = b.workflow_definition_id
            WHERE 1=1{wf_clause}
              AND (
                  (b.scope_id IS NOT NULL AND b.scope_id IN (SELECT id FROM scoped_workspaces))
                  OR (
                      b.scope_id IS NULL
                      AND (
                          wd.workspace_id IN (SELECT id FROM scoped_workspaces)
                          OR EXISTS (
                              SELECT 1 FROM workflow_runs wr
                              WHERE wr.workflow_def_id = wd.id
                                AND wr.workspace_id IN (SELECT id FROM scoped_workspaces)
                          ){global_template_clause}
                      )
                  )
              )
            ORDER BY b.created_at ASC;
        """

    try:
        async with engine.connect() as conn:
            res = await conn.execute(sa.text(query), params)
            rows = res.mappings().all()
            return [
                FinopsWorkflowBaseline(
                    id=str(r["id"]),
                    workflow_definition_id=str(r["workflow_definition_id"]),
                    scope_id=str(r["scope_id"]) if r["scope_id"] else None,
                    manual_time_minutes=r["manual_time_minutes"],
                    manual_cost_usd=Decimal(str(r["manual_cost_usd"])),
                    target_ttm_reduction_pct=r["target_ttm_reduction_pct"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("finops_list_baselines_skipped", error_type=type(exc).__name__)
            return []
        logger.error(
            "finops_list_baselines_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


__all__ = [
    "list_workflow_baselines_sql",
    "upsert_workflow_baseline_sql",
]
