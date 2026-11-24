"""Async SQL query for single-run FinOps budget and cost state (`Story 6.2`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine


async def fetch_run_finops_state_sql(
    engine: AsyncEngine,
    run_id: str,
) -> dict[str, Any] | None:
    """Load run budget ceiling and aggregated step/audit costs from PG18."""
    stmt = sa.text(
        """
        WITH step_agg AS (
            SELECT run_id, COALESCE(SUM(cost_usd), 0.000000) AS total_steps_cost
            FROM step_executions
            WHERE run_id = :run_id
            GROUP BY run_id
        ),
        ledger_agg AS (
            SELECT run_id, COALESCE(SUM(cost_usd), 0.000000) AS total_audit_cost
            FROM audit_ledger
            WHERE run_id = :run_id
            GROUP BY run_id
        )
        SELECT
            r.id,
            r.workspace_id,
            r.status,
            r.budget_max_usd,
            COALESCE(sa_agg.total_steps_cost, 0.000000) AS total_steps_cost,
            COALESCE(la_agg.total_audit_cost, 0.000000) AS total_audit_cost
        FROM workflow_runs r
        LEFT JOIN step_agg sa_agg ON sa_agg.run_id = r.id
        LEFT JOIN ledger_agg la_agg ON la_agg.run_id = r.id
        WHERE r.id = :run_id;
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
