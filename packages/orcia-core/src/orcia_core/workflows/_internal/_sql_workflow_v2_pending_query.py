"""Unified PG18 & memory pending-runs query helpers for `SqlWorkflowV2RunsStore` (`Story 30.3`)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.workflows.sql_workflow_v2_runs")

PENDING_ACTION_STATUSES: frozenset[str] = frozenset(
    {
        "INITIALIZED",
        "RUNNING",
        "WAITING_SUBSTEP_HITL",
        "WAITING_EXTERNAL_GATE",
        "WAITING_FINAL_ANCHOR",
        "WAITING_WRITE_PREVIEW",
        "WAITING_FOR_HUMAN_ARBITRATION",
        "WAITING_FOR_HUMAN_GATE",
        "RETURN_LOOP_TRIGGERED",
        "SLA_SUSPENDED",
        "PAUSED",
        "PAUSED_CIRCUIT_BREAKER",
        "PAUSED_BUDGET_EXCEEDED",
    }
)


def safe_uuid(raw: str | None) -> UUID | None:
    """Parse a UUID string safely, returning `None` on invalid input."""
    if not raw:
        return None
    try:
        return UUID(str(raw).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def normalize_workflow_run_status(raw_status: str) -> str:
    """Map internal workflow/session statuses onto canonical UI-facing states."""
    upper = (raw_status or "").strip().upper()
    if upper in ("PAUSED_CIRCUIT_BREAKER", "PAUSED_BUDGET_EXCEEDED", "SLA_SUSPENDED"):
        return "PAUSED"
    if upper in ("WAITING_FOR_HUMAN_ARBITRATION", "WAITING_FOR_HUMAN_GATE"):
        return "WAITING_SUBSTEP_HITL"
    if upper == "COMPLETED_APPROVED":
        return "COMPLETED"
    return upper or "RUNNING"


async def query_pending_and_active_runs_sql(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    strict_sql: bool,
    workspace_ids: tuple[str, ...] | None,
    include_completed: bool,
    limit: int,
) -> list[dict[str, Any]]:
    """Query PG18 across `workflow_v2_runs`, `reflexive_execution_sessions`, and `workflow_runs`."""
    ws_uuids = [u for raw in (workspace_ids or ()) if (u := safe_uuid(raw)) is not None]
    if workspace_ids is not None and not ws_uuids:
        return []
    ws_strs = [str(u) for u in ws_uuids]

    ws_clause_v2 = "AND workspace_id = ANY(:ws_ids)" if workspace_ids is not None else ""
    ws_clause_rx = "AND workspace_id = ANY(:ws_strs)" if workspace_ids is not None else ""
    ws_clause_wr = "AND wr.workspace_id = ANY(:ws_ids)" if workspace_ids is not None else ""

    stmt = sa.text(
        f"""
        SELECT * FROM (
            SELECT
                run_id,
                workspace_id::text AS workspace_id,
                workflow_id,
                workflow_slug,
                workflow_title,
                actor_slug,
                status,
                reflexive_execution_id,
                created_at,
                updated_at,
                'workflow_v2'::text AS source
            FROM workflow_v2_runs
            WHERE 1=1 {ws_clause_v2}

            UNION ALL

            SELECT
                rx.execution_id AS run_id,
                rx.workspace_id AS workspace_id,
                COALESCE(NULLIF(rx.snapshot_jsonb->>'workflow_id', ''), '') AS workflow_id,
                COALESCE(NULLIF(rx.snapshot_jsonb->>'workflow_slug', ''), '') AS workflow_slug,
                COALESCE(NULLIF(rx.snapshot_jsonb->>'objective', ''), rx.actor_slug)
                    AS workflow_title,
                rx.actor_slug AS actor_slug,
                rx.status AS status,
                rx.execution_id AS reflexive_execution_id,
                rx.created_at AS created_at,
                rx.updated_at AS updated_at,
                'reflexive_session'::text AS source
            FROM reflexive_execution_sessions rx
            WHERE rx.execution_profile = 'PROCESS'
              AND NOT EXISTS (
                  SELECT 1 FROM workflow_v2_runs v2
                  WHERE v2.reflexive_execution_id = rx.execution_id
              )
              {ws_clause_rx}

            UNION ALL

            SELECT
                wr.id::text AS run_id,
                wr.workspace_id::text AS workspace_id,
                wd.uri AS workflow_id,
                wr.run_key AS workflow_slug,
                COALESCE(NULLIF(wd.steps_schema_jsonb->>'title', ''), wd.uri) AS workflow_title,
                'orchestration'::text AS actor_slug,
                wr.status AS status,
                NULL::text AS reflexive_execution_id,
                wr.created_at AS created_at,
                wr.created_at AS updated_at,
                'workflow_run'::text AS source
            FROM workflow_runs wr
            JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
            WHERE NOT EXISTS (
                SELECT 1 FROM workflow_v2_runs v2
                WHERE v2.run_id = wr.id::text
                   OR v2.run_id = wr.run_key
                   OR v2.run_id = ('run-' || wr.id::text)
            )
            {ws_clause_wr}
        ) combined
        ORDER BY updated_at DESC
        LIMIT :limit
        """
    )
    params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
    if workspace_ids is not None:
        params["ws_ids"] = ws_uuids
        params["ws_strs"] = ws_strs

    try:
        async with session_maker() as session:
            rows = (await session.execute(stmt, params)).mappings().all()
    except Exception as exc:
        logger.warning("workflow_v2_runs_list_sql_failed", error_type=type(exc).__name__)
        if strict_sql:
            raise
        return []

    items: list[dict[str, Any]] = []
    for row in rows:
        raw_status = str(row["status"] or "RUNNING")
        norm_status = normalize_workflow_run_status(raw_status)
        is_pending = raw_status in PENDING_ACTION_STATUSES or norm_status in PENDING_ACTION_STATUSES
        if not include_completed and not is_pending:
            continue
        items.append(
            {
                "run_id": str(row["run_id"]),
                "workspace_id": str(row["workspace_id"]) if row["workspace_id"] else None,
                "workflow_id": str(row["workflow_id"] or ""),
                "workflow_slug": str(row["workflow_slug"] or ""),
                "workflow_title": str(row["workflow_title"] or row["workflow_id"] or ""),
                "actor_slug": str(row["actor_slug"] or "assistant"),
                "status": norm_status,
                "raw_status": raw_status,
                "is_pending": is_pending,
                "reflexive_execution_id": (
                    str(row["reflexive_execution_id"]) if row["reflexive_execution_id"] else None
                ),
                "source": str(row["source"]),
                "created_at_iso": row["created_at"].isoformat() if row["created_at"] else "",
                "updated_at_iso": row["updated_at"].isoformat() if row["updated_at"] else "",
            }
        )
    return items


def list_pending_runs_from_memory(
    records: list[dict[str, Any]],
    *,
    workspace_ids: tuple[str, ...] | None,
    include_completed: bool,
    limit: int,
) -> list[dict[str, Any]]:
    """Return pending/active runs from the in-memory test fallback store."""
    allowed = set(workspace_ids) if workspace_ids is not None else None
    items: list[dict[str, Any]] = []
    for rec in reversed(records):
        ws = rec.get("workspace_id")
        if allowed is not None and ws not in allowed:
            continue
        raw_status = str(rec.get("status") or "RUNNING")
        norm_status = normalize_workflow_run_status(raw_status)
        is_pending = raw_status in PENDING_ACTION_STATUSES or norm_status in PENDING_ACTION_STATUSES
        if not include_completed and not is_pending:
            continue
        items.append(
            {
                "run_id": str(rec["run_id"]),
                "workspace_id": ws,
                "workflow_id": str(rec.get("workflow_id") or ""),
                "workflow_slug": str(rec.get("workflow_slug") or ""),
                "workflow_title": str(rec.get("workflow_title") or ""),
                "actor_slug": str(rec.get("actor_slug") or "assistant"),
                "status": norm_status,
                "raw_status": raw_status,
                "is_pending": is_pending,
                "reflexive_execution_id": rec.get("reflexive_execution_id"),
                "source": "workflow_v2",
                "created_at_iso": "",
                "updated_at_iso": "",
            }
        )
        if len(items) >= limit:
            break
    return items


__all__ = [
    "PENDING_ACTION_STATUSES",
    "list_pending_runs_from_memory",
    "normalize_workflow_run_status",
    "query_pending_and_active_runs_sql",
    "safe_uuid",
]
