"""Async SQL repositories for FinOps budgets, baselines, and accounting queries (`Story 6.2`).

Pure SQLAlchemy asyncpg queries — zero circular dependencies, zero float operations.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops.finops_models import (
    FinopsBudgetOverride,
    FinopsScopeBudget,
    FinopsWorkflowBaseline,
    ScopeType,
)
from orcia_kernel.ids import new_uuid7_str

logger = logging.getLogger(__name__)

ZERO_UUID_STR = "00000000-0000-0000-0000-000000000000"


def _safe_uuid(val: str | None) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(val)
    except (ValueError, TypeError, AttributeError):
        return None


async def upsert_scope_budget_sql(
    engine: AsyncEngine,
    *,
    scope_type: ScopeType,
    scope_id: str | None,
    monthly_budget_usd: Decimal,
    warning_threshold_pct: int = 80,
    hard_stop_pct: int = 100,
) -> FinopsScopeBudget:
    new_id = new_uuid7_str()
    scope_uuid = UUID(scope_id) if scope_id else None
    stmt = sa.text(
        """
        INSERT INTO finops_scope_budgets (
            id, scope_type, scope_id, monthly_budget_usd,
            warning_threshold_pct, hard_stop_pct, created_at, updated_at
        ) VALUES (
            :id, :scope_type, :scope_id, :monthly_budget_usd,
            :warning_threshold_pct, :hard_stop_pct, NOW(), NOW()
        )
        ON CONFLICT (scope_type, (COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid)))
        DO UPDATE SET
            monthly_budget_usd = EXCLUDED.monthly_budget_usd,
            warning_threshold_pct = EXCLUDED.warning_threshold_pct,
            hard_stop_pct = EXCLUDED.hard_stop_pct,
            updated_at = NOW()
        RETURNING id, scope_type, scope_id, monthly_budget_usd,
                  warning_threshold_pct, hard_stop_pct, created_at, updated_at;
        """
    )
    async with engine.begin() as conn:
        res = await conn.execute(
            stmt,
            {
                "id": UUID(new_id),
                "scope_type": scope_type,
                "scope_id": scope_uuid,
                "monthly_budget_usd": monthly_budget_usd,
                "warning_threshold_pct": warning_threshold_pct,
                "hard_stop_pct": hard_stop_pct,
            },
        )
        row = res.mappings().one()
        return FinopsScopeBudget(
            id=str(row["id"]),
            scope_type=row["scope_type"],
            scope_id=str(row["scope_id"]) if row["scope_id"] else None,
            monthly_budget_usd=Decimal(str(row["monthly_budget_usd"])),
            warning_threshold_pct=row["warning_threshold_pct"],
            hard_stop_pct=row["hard_stop_pct"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


async def list_scope_budgets_sql(
    engine: AsyncEngine,
    *,
    scope_type: ScopeType | None = None,
    scope_id: str | None = None,
) -> list[FinopsScopeBudget]:
    query = "SELECT * FROM finops_scope_budgets WHERE 1=1"
    params: dict[str, Any] = {}
    if scope_type is not None:
        query += " AND scope_type = :scope_type"
        params["scope_type"] = scope_type
    uuid_val = _safe_uuid(scope_id)
    if uuid_val is not None:
        query += " AND scope_id = :scope_id"
        params["scope_id"] = uuid_val
    query += " ORDER BY scope_type, created_at ASC;"

    try:
        async with engine.connect() as conn:
            res = await conn.execute(sa.text(query), params)
            rows = res.mappings().all()
            return [
                FinopsScopeBudget(
                    id=str(r["id"]),
                    scope_type=r["scope_type"],
                    scope_id=str(r["scope_id"]) if r["scope_id"] else None,
                    monthly_budget_usd=Decimal(str(r["monthly_budget_usd"])),
                    warning_threshold_pct=r["warning_threshold_pct"],
                    hard_stop_pct=r["hard_stop_pct"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]
    except Exception as exc:
        logger.warning("FinOps list_scope_budgets query skipped: %s", exc)
        return []


async def upsert_workflow_baseline_sql(
    engine: AsyncEngine,
    *,
    workflow_definition_id: str,
    scope_id: str | None,
    manual_time_minutes: int,
    manual_cost_usd: Decimal,
    target_ttm_reduction_pct: int = 25,
) -> FinopsWorkflowBaseline:
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
    scope_id: str | None = None,
) -> list[FinopsWorkflowBaseline]:
    query = "SELECT * FROM finops_workflow_baselines WHERE 1=1"
    params: dict[str, Any] = {}
    wf_uuid = _safe_uuid(workflow_definition_id)
    if wf_uuid is not None:
        query += " AND workflow_definition_id = :wf_id"
        params["wf_id"] = wf_uuid
    scope_uuid = _safe_uuid(scope_id)
    if scope_uuid is not None:
        query += " AND scope_id = :scope_id"
        params["scope_id"] = scope_uuid
    query += " ORDER BY created_at ASC;"

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
        logger.warning("FinOps list_workflow_baselines query skipped: %s", exc)
        return []


async def insert_budget_override_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    requested_by: str,
    approved_by: str,
    override_amount_usd: Decimal,
    reason: str,
) -> FinopsBudgetOverride:
    new_id = new_uuid7_str()
    override_stmt = sa.text(
        """
        INSERT INTO finops_budget_overrides (
            id, run_id, requested_by, approved_by, override_amount_usd, reason, created_at
        ) VALUES (
            :id, :run_id, :requested_by, :approved_by, :override_amount_usd, :reason, NOW()
        )
        RETURNING id, run_id, requested_by, approved_by, override_amount_usd, reason, created_at;
        """
    )
    update_run_stmt = sa.text(
        """
        UPDATE workflow_runs
        SET budget_max_usd = budget_max_usd + :override_amount_usd,
            status = 'RUNNING'
        WHERE id = :run_id;
        """
    )
    unpause_steps_stmt = sa.text(
        """
        UPDATE step_executions
        SET status = 'PENDING'
        WHERE run_id = :run_id
          AND status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES');
        """
    )

    req_uuid = _safe_uuid(requested_by) or UUID("018d0000-0000-7000-8000-000000000001")
    appr_uuid = _safe_uuid(approved_by) or req_uuid

    async with engine.begin() as conn:
        res = await conn.execute(
            override_stmt,
            {
                "id": UUID(new_id),
                "run_id": UUID(run_id),
                "requested_by": req_uuid,
                "approved_by": appr_uuid,
                "override_amount_usd": override_amount_usd,
                "reason": reason,
            },
        )
        row = res.mappings().one()
        await conn.execute(
            update_run_stmt,
            {"run_id": UUID(run_id), "override_amount_usd": override_amount_usd},
        )
        await conn.execute(unpause_steps_stmt, {"run_id": UUID(run_id)})

        return FinopsBudgetOverride(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            requested_by=str(row["requested_by"]),
            approved_by=str(row["approved_by"]),
            override_amount_usd=Decimal(str(row["override_amount_usd"])),
            reason=row["reason"],
            created_at=row["created_at"],
        )


async def fetch_run_finops_state_sql(
    engine: AsyncEngine,
    run_id: str,
) -> dict[str, Any] | None:
    stmt = sa.text(
        """
        SELECT
            r.id,
            r.workspace_id,
            r.status,
            r.budget_max_usd,
            COALESCE(SUM(s.cost_usd), 0.000000) as total_steps_cost,
            COALESCE(SUM(l.cost_usd), 0.000000) as total_audit_cost
        FROM workflow_runs r
        LEFT JOIN step_executions s ON s.run_id = r.id
        LEFT JOIN audit_ledger l ON l.run_id = r.id
        WHERE r.id = :run_id
        GROUP BY r.id, r.workspace_id, r.status, r.budget_max_usd;
        """
    )
    async with engine.connect() as conn:
        res = await conn.execute(stmt, {"run_id": UUID(run_id)})
        row = res.mappings().first()
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "workspace_id": str(row["workspace_id"]),
            "status": row["status"],
            "budget_max_usd": Decimal(str(row["budget_max_usd"])),
            "total_steps_cost": Decimal(str(row["total_steps_cost"])),
            "total_audit_cost": Decimal(str(row["total_audit_cost"])),
        }


__all__ = [
    "fetch_run_finops_state_sql",
    "insert_budget_override_sql",
    "list_scope_budgets_sql",
    "list_workflow_baselines_sql",
    "upsert_scope_budget_sql",
    "upsert_workflow_baseline_sql",
]
