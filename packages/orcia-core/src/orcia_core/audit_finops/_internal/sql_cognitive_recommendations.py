"""PostgreSQL 18 persistence for Gate policy recommendations in audit_ledger (`Story 6.3`).

Persists applied policy recommendations into the append-only `audit_ledger`
under event_type = 'SettingsChanged' and category = 'FINOPS_GATE_POLICY_RECOMMENDATION',
with strict workspace attribution (`workspace_id` + `scope_path`) and scope-filtered reads.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_OID, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_cognitive_scope_clause,
    safe_uuid,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.audit_finops.recommendations")

SQL_INSERT_APPLIED_RECOMMENDATION = sa.text(
    """
    INSERT INTO audit_ledger (
        id, source_event_id, workspace_id, scope_path, actor_type, actor_id,
        event_type, summary, trace_id, metadata_jsonb, created_at
    ) VALUES (
        CAST(:id AS uuid), CAST(:source_event_id AS uuid),
        CAST(:workspace_id AS uuid), :scope_path, 'HUMAN_USER', :actor_id,
        'SettingsChanged', :summary, :trace_id, CAST(:metadata_jsonb AS jsonb), NOW()
    )
    ON CONFLICT (source_event_id) DO NOTHING;
    """
)


async def record_applied_policy_recommendation_sql(
    engine: AsyncEngine | None,
    rec_id: str,
    workflow_id: str,
    workflow_title: str,
    rec_type: str,
    title: str,
    suggested_policy: str,
    applied_by: str,
    applied_at: datetime | None = None,
    workspace_id: str | None = None,
) -> None:
    """Persist an applied gate policy recommendation into `audit_ledger` with workspace scope."""
    if engine is None:
        return

    entry_id = new_uuid7_str()
    source_event_id = str(uuid5(NAMESPACE_OID, f"finops-rec-apply-{rec_id}"))
    applied_at_dt = applied_at or datetime.now(UTC)

    resolved_ws_uuid = safe_uuid(workspace_id)
    summary = f"Ajustement politique de Gate FinOps: {title} ({workflow_title})"
    trace_id = entry_id.replace("-", "")[:32]

    async with engine.begin() as conn:
        if safe_uuid(workflow_id) is not None:
            ws_from_def = (
                await conn.execute(
                    sa.text(
                        """
                        UPDATE workflow_definitions
                        SET adaptive_gate_policy = :suggested_policy
                        WHERE id = CAST(:workflow_id AS uuid)
                        RETURNING workspace_id::text;
                        """
                    ),
                    {
                        "workflow_id": workflow_id,
                        "suggested_policy": suggested_policy,
                    },
                )
            ).scalar()
            if resolved_ws_uuid is None and ws_from_def:
                resolved_ws_uuid = safe_uuid(str(ws_from_def))
            if resolved_ws_uuid is None:
                ws_from_run = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT workspace_id::text
                            FROM workflow_runs
                            WHERE workflow_def_id = CAST(:workflow_id AS uuid)
                            ORDER BY created_at DESC
                            LIMIT 1;
                            """
                        ),
                        {"workflow_id": workflow_id},
                    )
                ).scalar()
                if ws_from_run:
                    resolved_ws_uuid = safe_uuid(str(ws_from_run))

        ws_str = str(resolved_ws_uuid) if resolved_ws_uuid is not None else None
        scope_path = f"WORKSPACE/{ws_str}" if ws_str else "GLOBAL"
        metadata = {
            "category": "FINOPS_GATE_POLICY_RECOMMENDATION",
            "recommendation_id": rec_id,
            "workflow_id": workflow_id,
            "workflow_title": workflow_title,
            "workspace_id": ws_str,
            "recommendation_type": rec_type,
            "suggested_policy": suggested_policy,
            "applied_by": applied_by,
            "applied_at": applied_at_dt.isoformat(),
        }

        await conn.execute(
            SQL_INSERT_APPLIED_RECOMMENDATION,
            {
                "id": entry_id,
                "source_event_id": source_event_id,
                "workspace_id": ws_str,
                "scope_path": scope_path,
                "actor_id": applied_by,
                "summary": summary,
                "trace_id": trace_id,
                "metadata_jsonb": json.dumps(metadata),
            },
        )
    logger.info(
        "finops_gate_recommendation_persisted",
        recommendation_id=rec_id,
        workflow_id=workflow_id,
        workspace_id=ws_str,
        suggested_policy=suggested_policy,
    )


async def fetch_applied_recommendations_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> dict[str, dict[str, Any]]:
    """Query `audit_ledger` for applied gate recommendations filtered by RBAC scope."""
    if engine is None:
        return {}
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return {}

    uuid_val = safe_uuid(scope_id)
    scope_clause, params = build_cognitive_scope_clause(
        scope_type, uuid_val, "ar.resolved_ws_id", allowed_workspace_ids
    )
    uuid_pattern = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    stmt = sa.text(
        f"""
        WITH applied_recs AS (
            SELECT
                l.metadata_jsonb->>'recommendation_id' AS recommendation_id,
                l.metadata_jsonb->>'workflow_id' AS workflow_id,
                l.metadata_jsonb->>'workflow_title' AS workflow_title,
                l.metadata_jsonb->>'recommendation_type' AS recommendation_type,
                l.metadata_jsonb->>'suggested_policy' AS suggested_policy,
                l.metadata_jsonb->>'applied_by' AS applied_by,
                l.metadata_jsonb->>'applied_at' AS applied_at,
                l.created_at,
                COALESCE(
                    l.workspace_id,
                    wd.workspace_id,
                    (
                        SELECT wr.workspace_id
                        FROM workflow_runs wr
                        WHERE wr.workflow_def_id = wd.id
                        ORDER BY wr.created_at DESC
                        LIMIT 1
                    )
                ) AS resolved_ws_id
            FROM audit_ledger l
            LEFT JOIN workflow_definitions wd
                ON wd.id = CASE
                    WHEN (l.metadata_jsonb->>'workflow_id') ~* '{uuid_pattern}'
                    THEN CAST(l.metadata_jsonb->>'workflow_id' AS uuid)
                    ELSE NULL
                END
            WHERE l.event_type = 'SettingsChanged'
              AND l.metadata_jsonb->>'category' = 'FINOPS_GATE_POLICY_RECOMMENDATION'
        )
        SELECT
            ar.recommendation_id,
            ar.workflow_id,
            ar.workflow_title,
            ar.recommendation_type,
            ar.suggested_policy,
            ar.applied_by,
            ar.applied_at,
            ar.created_at
        FROM applied_recs ar
        WHERE 1=1 {scope_clause}
        ORDER BY ar.created_at ASC;
        """
    )

    async with engine.connect() as conn:
        result = await conn.execute(stmt, params)
        rows = result.fetchall()

    applied: dict[str, dict[str, Any]] = {}
    for r in rows:
        rec_id = r[0]
        if rec_id:
            applied[rec_id] = {
                "recommendation_id": rec_id,
                "workflow_id": r[1] or "",
                "workflow_title": r[2] or "",
                "recommendation_type": r[3] or "SWITCH_TO_RISK_OR_SAMPLING",
                "suggested_policy": r[4] or "SAMPLING_20_PCT",
                "applied_by": r[5] or "system",
                "applied_at": r[6] or r[7].isoformat(),
            }
    return applied
