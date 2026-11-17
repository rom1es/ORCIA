"""PostgreSQL 18 persistence for Gate policy recommendations in audit_ledger (`Story 6.3`).

Persists applied policy recommendations into the append-only `audit_ledger`
under event_type = 'SettingsChanged' and category = 'FINOPS_GATE_POLICY_RECOMMENDATION'.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_OID, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.kernel.ids import new_uuid7_str

logger = logging.getLogger(__name__)

SQL_INSERT_APPLIED_RECOMMENDATION = sa.text(
    """
    INSERT INTO audit_ledger (
        id, source_event_id, actor_type, actor_id,
        event_type, summary, trace_id, metadata_jsonb, created_at
    ) VALUES (
        CAST(:id AS uuid), CAST(:source_event_id AS uuid), 'HUMAN_USER', :actor_id,
        'SettingsChanged', :summary, :trace_id, CAST(:metadata_jsonb AS jsonb), NOW()
    )
    ON CONFLICT (source_event_id) DO NOTHING;
    """
)

SQL_FETCH_APPLIED_RECOMMENDATIONS = sa.text(
    """
    SELECT
        metadata_jsonb->>'recommendation_id' AS recommendation_id,
        metadata_jsonb->>'workflow_id' AS workflow_id,
        metadata_jsonb->>'workflow_title' AS workflow_title,
        metadata_jsonb->>'recommendation_type' AS recommendation_type,
        metadata_jsonb->>'suggested_policy' AS suggested_policy,
        metadata_jsonb->>'applied_by' AS applied_by,
        metadata_jsonb->>'applied_at' AS applied_at,
        created_at
    FROM audit_ledger
    WHERE event_type = 'SettingsChanged'
      AND metadata_jsonb->>'category' = 'FINOPS_GATE_POLICY_RECOMMENDATION'
    ORDER BY created_at ASC;
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
) -> None:
    """Persist an applied gate policy recommendation into audit_ledger."""
    if engine is None:
        return

    entry_id = new_uuid7_str()
    source_event_id = str(uuid5(NAMESPACE_OID, f"finops-rec-apply-{rec_id}"))
    applied_at_dt = applied_at or datetime.now(UTC)

    metadata = {
        "category": "FINOPS_GATE_POLICY_RECOMMENDATION",
        "recommendation_id": rec_id,
        "workflow_id": workflow_id,
        "workflow_title": workflow_title,
        "recommendation_type": rec_type,
        "suggested_policy": suggested_policy,
        "applied_by": applied_by,
        "applied_at": applied_at_dt.isoformat(),
    }

    summary = f"Ajustement politique de Gate FinOps: {title} ({workflow_title})"
    trace_id = entry_id.replace("-", "")[:32]

    async with engine.begin() as conn:
        await conn.execute(
            SQL_INSERT_APPLIED_RECOMMENDATION,
            {
                "id": entry_id,
                "source_event_id": source_event_id,
                "actor_id": applied_by,
                "summary": summary,
                "trace_id": trace_id,
                "metadata_jsonb": json.dumps(metadata),
            },
        )
    logger.info(
        "Persisted applied gate recommendation '%s' for workflow '%s' in audit_ledger",
        rec_id,
        workflow_id,
    )


async def fetch_applied_recommendations_sql(
    engine: AsyncEngine | None,
) -> dict[str, dict[str, Any]]:
    """Query audit_ledger for all applied gate recommendations."""
    if engine is None:
        return {}

    async with engine.connect() as conn:
        result = await conn.execute(SQL_FETCH_APPLIED_RECOMMENDATIONS)
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
