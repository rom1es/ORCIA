"""Async SQL repositories for FinOps budgets, baselines, and accounting queries (`Story 6.2`).

Pure SQLAlchemy asyncpg queries — zero circular dependencies, zero float operations.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_finops_baselines import (
    list_workflow_baselines_sql,
    upsert_workflow_baseline_sql,
)
from orcia_core.audit_finops._internal._sql_scope_filter import (
    is_missing_table_error,
    safe_uuid,
)
from orcia_core.audit_finops._internal.sql_connector_quotas_helpers import (
    insert_connector_outbox_event,
)
from orcia_core.audit_finops.finops_models import (
    FinopsBudgetOverride,
    FinopsScopeBudget,
    ScopeType,
)
from orcia_core.kernel.events import DomainEvent
from orcia_core.observability.logging import get_logger
from orcia_kernel.errors import ValidationDomainError
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.audit_finops.accounting")


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
    uuid_val = safe_uuid(scope_id)
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
        if is_missing_table_error(exc):
            logger.warning("finops_list_scope_budgets_skipped", error_type=type(exc).__name__)
            return []
        logger.error(
            "finops_list_scope_budgets_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


async def insert_budget_override_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    requested_by: str,
    approved_by: str,
    override_amount_usd: Decimal,
    reason: str,
    outbox_event: DomainEvent | None = None,
) -> FinopsBudgetOverride:
    req_uuid = safe_uuid(requested_by)
    appr_uuid = safe_uuid(approved_by)
    run_uuid = safe_uuid(run_id)
    if req_uuid is None or appr_uuid is None or run_uuid is None:
        raise ValidationDomainError(
            detail_override=(
                "Valid UUID identifiers are required for run_id, requested_by, and approved_by."
            )
        )

    new_id = new_uuid7_str()
    async with engine.begin() as conn:
        req_exists = (
            await conn.execute(sa.text("SELECT id FROM users WHERE id = :uid"), {"uid": req_uuid})
        ).first()
        appr_exists = (
            await conn.execute(sa.text("SELECT id FROM users WHERE id = :uid"), {"uid": appr_uuid})
        ).first()
        if req_exists is None or appr_exists is None:
            raise ValidationDomainError(
                detail_override=(
                    "Requesting or approving user UUID does not exist in users registry."
                )
            )

        res = await conn.execute(
            sa.text(
                """
                INSERT INTO finops_budget_overrides (
                    id, run_id, requested_by, approved_by, override_amount_usd, reason, created_at
                ) VALUES (
                    :id, :run_id, :requested_by, :approved_by, :override_amount_usd, :reason, NOW()
                )
                RETURNING id, run_id, requested_by, approved_by,
                          override_amount_usd, reason, created_at;
                """
            ),
            {
                "id": UUID(new_id),
                "run_id": run_uuid,
                "requested_by": req_uuid,
                "approved_by": appr_uuid,
                "override_amount_usd": override_amount_usd,
                "reason": reason,
            },
        )
        row = res.mappings().one()
        ws_row = (
            await conn.execute(
                sa.text(
                    """
                    UPDATE workflow_runs
                    SET budget_max_usd = budget_max_usd + :override_amount_usd,
                        status = 'RUNNING'
                    WHERE id = :run_id
                    RETURNING workspace_id;
                    """
                ),
                {"run_id": run_uuid, "override_amount_usd": override_amount_usd},
            )
        ).first()
        await conn.execute(
            sa.text(
                """
                UPDATE step_executions
                SET status = 'PENDING'
                WHERE run_id = :run_id
                  AND status IN ('PAUSED_BUDGET_EXCEEDED', 'PAUSED_MAX_RETRIES');
                """
            ),
            {"run_id": run_uuid},
        )
        if outbox_event is not None:
            await insert_connector_outbox_event(conn, outbox_event)
            resolved_ws = str(ws_row[0]) if ws_row and ws_row[0] else outbox_event.workspace_id
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO audit_ledger (
                        id, source_event_id, workspace_id, scope_path, run_id,
                        actor_type, actor_id, event_type, summary,
                        cost_usd, cost_source, trace_id, metadata_jsonb
                    ) VALUES (
                        CAST(:id AS uuid), CAST(:source_event_id AS uuid),
                        CAST(:workspace_id AS uuid), :scope_path, CAST(:run_id AS uuid),
                        'USER', :actor_id, 'BudgetOverrideApproved', :summary,
                        0.000000, 'INTERNAL_VERIFIED', :trace_id, CAST(:metadata_jsonb AS jsonb)
                    )
                    ON CONFLICT (source_event_id) DO NOTHING;
                    """
                ),
                {
                    "id": new_uuid7_str(),
                    "source_event_id": outbox_event.event_id,
                    "workspace_id": resolved_ws,
                    "scope_path": f"WORKSPACE:{resolved_ws}" if resolved_ws else "GLOBAL",
                    "run_id": run_id,
                    "actor_id": str(appr_uuid),
                    "summary": (
                        "Dérogation budgétaire approuvée "
                        f"(+{float(override_amount_usd):.2f} USD) : {reason}"
                    ),
                    "trace_id": outbox_event.trace_id,
                    "metadata_jsonb": json.dumps(outbox_event.payload, sort_keys=True),
                },
            )

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


__all__ = [
    "fetch_run_finops_state_sql",
    "insert_budget_override_sql",
    "list_scope_budgets_sql",
    "list_workflow_baselines_sql",
    "upsert_scope_budget_sql",
    "upsert_workflow_baseline_sql",
]
