"""Async SQL queries for Autonomous Metrics (`SM-A1..A3`) & Post-Hoc Audits (`Story 7.4`).

Strict Hexagonal Boundary (`AD-19 Contract 2`) & exact `Decimal` precision.
File size < 280 lines.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_cognitive_scope_clause,
    build_time_interval_clause,
    is_missing_table_error,
    safe_uuid,
)
from orcia_core.audit_finops._internal.sql_connector_quotas_helpers import (
    insert_connector_outbox_event,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.audit_finops.outbox_subscriber import map_domain_event_to_ledger_entry
from orcia_core.kernel.events import DomainEvent
from orcia_core.observability.logging import get_logger
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.audit_finops.autonomous_metrics")


async def fetch_autonomous_governance_aggregates_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    time_window: str = "30D",
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Fetch exact SQL aggregates for `SM-A1`, `SM-A2`, and `SM-A3` (`Decimal`)."""
    defaults: dict[str, Any] = {
        "total_autonomous_runs": 0,
        "escalated_runs_count": 0,
        "killed_runs_count": 0,
        "committed_runs_count": 0,
        "sampled_runs_count": 0,
        "pending_samples_count": 0,
        "validated_samples_count": 0,
        "invalidated_samples_count": 0,
        "total_autonomous_cost_usd": Decimal("0.000000"),
        "total_ttm_gain_minutes": Decimal("0.00"),
    }
    if engine is None:
        return defaults
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return defaults

    uuid_val = safe_uuid(scope_id)
    scope_wr, params_wr = build_cognitive_scope_clause(
        scope_type, uuid_val, "wr.workspace_id", allowed_workspace_ids
    )
    scope_pa, params_pa = build_cognitive_scope_clause(
        scope_type, uuid_val, "pa.workspace_id", allowed_workspace_ids
    )
    tw_wr = build_time_interval_clause(time_window, "wr.created_at")
    tw_pa = build_time_interval_clause(time_window, "pa.sampled_at")

    runs_stmt = sa.text(
        f"""
        WITH run_costs AS (
            SELECT al.run_id, COALESCE(SUM(al.cost_usd), 0.000000) AS cost_usd
            FROM audit_ledger al
            WHERE al.run_id IS NOT NULL
            GROUP BY al.run_id
        ),
        wf_baselines AS (
            SELECT DISTINCT ON (wb.workflow_definition_id)
                wb.workflow_definition_id,
                wb.manual_time_minutes
            FROM finops_workflow_baselines wb
            ORDER BY wb.workflow_definition_id, wb.updated_at DESC
        )
        SELECT
            COUNT(*) AS total_autonomous_runs,
            COALESCE(SUM(CASE WHEN wr.status = 'PAUSED_AUTONOMOUS_ESCALATION' THEN 1 ELSE 0 END), 0)
                AS escalated_runs_count,
            COALESCE(SUM(CASE WHEN wr.status = 'KILL_SWITCH_STOPPED' THEN 1 ELSE 0 END), 0)
                AS killed_runs_count,
            COALESCE(SUM(CASE WHEN wr.status = 'COMMITTED_AUTONOMOUS' THEN 1 ELSE 0 END), 0)
                AS committed_runs_count,
            COALESCE(SUM(COALESCE(rc.cost_usd, 0.000000)), 0.000000) AS total_autonomous_cost_usd,
            COALESCE(SUM(COALESCE(wb.manual_time_minutes, 0)), 0) AS total_ttm_gain_minutes
        FROM workflow_runs wr
        LEFT JOIN run_costs rc ON rc.run_id = wr.id
        LEFT JOIN wf_baselines wb ON wb.workflow_definition_id = wr.workflow_def_id
        WHERE wr.execution_regime = 'AUTONOMOUS_CONTRACT' {scope_wr} {tw_wr};
        """
    )

    audits_stmt = sa.text(
        f"""
        SELECT
            COUNT(*) AS sampled_runs_count,
            COALESCE(SUM(CASE WHEN pa.review_status = 'PENDING_SAMPLE' THEN 1 ELSE 0 END), 0)
                AS pending_samples_count,
            COALESCE(SUM(CASE WHEN pa.review_status = 'VALIDATED' THEN 1 ELSE 0 END), 0)
                AS validated_samples_count,
            COALESCE(
                SUM(CASE WHEN pa.review_status = 'INVALIDATED_ROLLED_BACK' THEN 1 ELSE 0 END), 0
            ) AS invalidated_samples_count
        FROM autonomous_post_hoc_audits pa
        WHERE 1=1 {scope_pa} {tw_pa};
        """
    )

    merged_params = {**params_wr, **params_pa}
    try:
        async with engine.connect() as conn:
            r_row = (await conn.execute(runs_stmt, merged_params)).mappings().one()
            a_row = (await conn.execute(audits_stmt, merged_params)).mappings().one()
            return {
                "total_autonomous_runs": int(r_row["total_autonomous_runs"]),
                "escalated_runs_count": int(r_row["escalated_runs_count"]),
                "killed_runs_count": int(r_row["killed_runs_count"]),
                "committed_runs_count": int(r_row["committed_runs_count"]),
                "sampled_runs_count": int(a_row["sampled_runs_count"]),
                "pending_samples_count": int(a_row["pending_samples_count"]),
                "validated_samples_count": int(a_row["validated_samples_count"]),
                "invalidated_samples_count": int(a_row["invalidated_samples_count"]),
                "total_autonomous_cost_usd": Decimal(str(r_row["total_autonomous_cost_usd"])),
                "total_ttm_gain_minutes": Decimal(str(r_row["total_ttm_gain_minutes"])),
            }
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning(
                "fetch_autonomous_governance_aggregates_sql_skipped",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return defaults
        logger.error(
            "fetch_autonomous_governance_aggregates_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


async def fetch_post_hoc_samples_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List post-hoc audit samples joined with workflow metadata."""
    if engine is None:
        return []
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return []

    uuid_val = safe_uuid(scope_id)
    scope_pa, params = build_cognitive_scope_clause(
        scope_type, uuid_val, "pa.workspace_id", allowed_workspace_ids
    )
    params["lim"] = max(1, min(limit, 200))

    stmt = sa.text(
        f"""
        SELECT
            pa.id::text AS id,
            pa.run_id::text AS run_id,
            pa.workspace_id::text AS workspace_id,
            pa.contract_id::text AS contract_id,
            pa.review_status,
            pa.reviewer_user_id::text AS reviewer_user_id,
            pa.review_comment,
            pa.sampled_at,
            pa.reviewed_at,
            wr.status AS run_status,
            wd.uri AS workflow_uri,
            COALESCE(wt.trigger_key, 'execution-autonome') AS trigger_label
        FROM autonomous_post_hoc_audits pa
        JOIN workflow_runs wr ON wr.id = pa.run_id
        JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
        LEFT JOIN workflow_triggers wt ON wt.id = wr.trigger_id
        WHERE 1=1 {scope_pa}
        ORDER BY (pa.review_status = 'PENDING_SAMPLE') DESC, pa.sampled_at DESC
        LIMIT :lim;
        """
    )
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(stmt, params)).mappings().all()
            return [dict(r) for r in rows]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning(
                "fetch_post_hoc_samples_sql_skipped",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return []
        raise


async def insert_post_hoc_sample_sql(
    engine: AsyncEngine,
    *,
    audit_id: str,
    run_id: str,
    workspace_id: str,
    contract_id: str,
    event: DomainEvent | None = None,
    audit_sink: AuditLedgerSinkPort | None = None,
) -> bool:
    """Idempotently persist a post-hoc sample (`ON CONFLICT (run_id) DO NOTHING`)."""
    stmt = sa.text(
        """
        INSERT INTO autonomous_post_hoc_audits (
            id, run_id, workspace_id, contract_id, review_status, sampled_at
        ) VALUES (
            :id, :run_id, :workspace_id, :contract_id, 'PENDING_SAMPLE', NOW()
        )
        ON CONFLICT (run_id) DO NOTHING
        RETURNING id::text;
        """
    )
    async with engine.begin() as conn:
        inserted_id = (
            await conn.execute(
                stmt,
                {
                    "id": UUID(audit_id),
                    "run_id": UUID(run_id),
                    "workspace_id": UUID(workspace_id),
                    "contract_id": UUID(contract_id),
                },
            )
        ).scalar_one_or_none()
        if inserted_id is None:
            return False
        if event is not None:
            await insert_connector_outbox_event(conn, event)
    if event is not None and audit_sink is not None:
        await audit_sink.record_entry(map_domain_event_to_ledger_entry(event))
    return True


async def update_post_hoc_review_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    review_status: str,
    reviewer_user_id: str,
    review_comment: str | None = None,
    workspace_id: str | None = None,
    contract_id: str | None = None,
) -> dict[str, Any] | None:
    """Update (or upsert if reviewing an unsampled run) `autonomous_post_hoc_audits`."""
    upd_stmt = sa.text(
        """
        UPDATE autonomous_post_hoc_audits
        SET review_status = :review_status,
            reviewer_user_id = :reviewer_user_id,
            review_comment = :review_comment,
            reviewed_at = NOW()
        WHERE run_id = :run_id
        RETURNING id::text, run_id::text, workspace_id::text, contract_id::text,
                  review_status, reviewer_user_id::text, review_comment, sampled_at, reviewed_at;
        """
    )
    params = {
        "run_id": UUID(run_id),
        "review_status": review_status,
        "reviewer_user_id": UUID(reviewer_user_id),
        "review_comment": review_comment,
    }
    async with engine.begin() as conn:
        row = (await conn.execute(upd_stmt, params)).mappings().first()
        if row is not None:
            return dict(row)
        if workspace_id is None or contract_id is None:
            return None
        ins_stmt = sa.text(
            """
            INSERT INTO autonomous_post_hoc_audits (
                id, run_id, workspace_id, contract_id, review_status,
                reviewer_user_id, review_comment, sampled_at, reviewed_at
            ) VALUES (
                :id, :run_id, :workspace_id, :contract_id, :review_status,
                :reviewer_user_id, :review_comment, NOW(), NOW()
            )
            ON CONFLICT (run_id) DO UPDATE SET
                review_status = EXCLUDED.review_status,
                reviewer_user_id = EXCLUDED.reviewer_user_id,
                review_comment = EXCLUDED.review_comment,
                reviewed_at = NOW()
            RETURNING id::text, run_id::text, workspace_id::text, contract_id::text,
                      review_status, reviewer_user_id::text, review_comment,
                      sampled_at, reviewed_at;
            """
        )
        inserted = (
            (
                await conn.execute(
                    ins_stmt,
                    {
                        **params,
                        "id": UUID(new_uuid7_str()),
                        "workspace_id": UUID(workspace_id),
                        "contract_id": UUID(contract_id),
                    },
                )
            )
            .mappings()
            .one()
        )
        return dict(inserted)
