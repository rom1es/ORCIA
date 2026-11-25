"""PostgreSQL 18 repository for Autonomous Run Supervision & Emergency Stop (`Story 7.4`)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import is_missing_table_error, safe_uuid
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._internal._sql_autonomous_rollback import (
    restore_help_article_and_rollback_run_sql,
)
from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    fmt_ts,
    insert_outbox_and_audit,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.events import DomainEvent

logger = get_logger("orcia.core.orchestration.sql_autonomous_supervision")


async def list_autonomous_runs_for_workspaces_sql(
    engine: AsyncEngine,
    *,
    workspace_ids: tuple[str, ...],
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fetch autonomous contract runs across authorized workspaces."""
    ws_uuids = [u for raw in workspace_ids if (u := safe_uuid(raw)) is not None]
    if not ws_uuids:
        return []
    stmt = sa.text(
        """
        WITH run_costs AS (
            SELECT al.run_id, COALESCE(SUM(al.cost_usd), 0.000000) AS cost_usd
            FROM audit_ledger al
            WHERE al.run_id IS NOT NULL
            GROUP BY al.run_id
        )
        SELECT
            wr.id::text AS run_id,
            wr.run_key,
            wr.workspace_id::text AS workspace_id,
            wr.workflow_def_id::text AS workflow_def_id,
            wd.uri AS workflow_uri,
            wr.trigger_id::text AS trigger_id,
            COALESCE(wt.trigger_key, 'execution-autonome') AS trigger_label,
            COALESCE(wt.trigger_type, 'MANUAL_AUTONOMOUS') AS trigger_type,
            COALESCE(wt.status, 'ACTIVE') AS trigger_status,
            wr.status AS run_status,
            COALESCE(pa.review_status, 'NONE') AS post_hoc_status,
            COALESCE(ac.id::text, '') AS contract_id,
            COALESCE(rc.cost_usd, 0.000000) AS cost_usd,
            help_art.help_resource_id,
            COALESCE(help_art.previous_version_available, FALSE) AS previous_version_available,
            wr.created_at
        FROM workflow_runs wr
        JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
        LEFT JOIN workflow_triggers wt ON wt.id = wr.trigger_id
        LEFT JOIN autonomous_post_hoc_audits pa ON pa.run_id = wr.id
        LEFT JOIN LATERAL (
            SELECT id
            FROM autonomy_contracts c
            WHERE c.workspace_id = wr.workspace_id
              AND (
                  c.workflow_id = wd.uri
                  OR wd.uri = 'orcia://workflows/' || c.workflow_id
                  OR wd.uri LIKE '%/' || c.workflow_id
              )
            ORDER BY (c.status = 'ACTIVE') DESC, c.signed_at DESC
            LIMIT 1
        ) ac ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                ci.resource_id AS help_resource_id,
                ((ci.metadata_jsonb ? 'previous_version') AND wr.status <> 'ROLLED_BACK')
                    AS previous_version_available
            FROM catalog_items ci
            WHERE ci.item_type = 'HELP_ARTICLE'
              AND (
                  ci.metadata_jsonb->>'autonomous_run_id' = wr.id::text
                  OR ci.metadata_jsonb->>'workflow_uri' = wd.uri
              )
            ORDER BY (ci.metadata_jsonb->>'autonomous_run_id' = wr.id::text) DESC,
                     ci.id DESC
            LIMIT 1
        ) help_art ON TRUE
        LEFT JOIN run_costs rc ON rc.run_id = wr.id
        WHERE wr.workspace_id = ANY(:ws_ids)
          AND wr.execution_regime = 'AUTONOMOUS_CONTRACT'
        ORDER BY wr.created_at DESC
        LIMIT :lim;
        """
    )
    try:
        async with engine.connect() as conn:
            rows = (
                (await conn.execute(stmt, {"ws_ids": ws_uuids, "lim": max(1, min(limit, 200))}))
                .mappings()
                .all()
            )
            return [{**dict(r), "created_at_iso": fmt_ts(r["created_at"]) or ""} for r in rows]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("list_autonomous_runs_sql_skipped", error=str(exc))
            return []
        raise


async def list_autonomous_runs_sql(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fetch autonomous contract runs for a workspace joined with trigger & post-hoc status."""
    return await list_autonomous_runs_for_workspaces_sql(
        engine, workspace_ids=(workspace_id,), limit=limit
    )


async def get_autonomous_run_sql(engine: AsyncEngine, *, run_id: str) -> dict[str, Any] | None:
    """Return single autonomous run metadata or `None` if absent."""
    run_uuid = safe_uuid(run_id)
    if run_uuid is None:
        return None
    stmt = sa.text(
        """
        SELECT
            wr.id::text AS run_id,
            wr.workspace_id::text AS workspace_id,
            wr.trigger_id::text AS trigger_id,
            wr.status AS run_status,
            wd.uri AS workflow_uri,
            COALESCE(wt.trigger_key, 'execution-autonome') AS trigger_label,
            COALESCE(wt.trigger_type, 'MANUAL_AUTONOMOUS') AS trigger_type,
            COALESCE(wt.status, 'ACTIVE') AS trigger_status,
            COALESCE(pa.review_status, 'NONE') AS post_hoc_status,
            COALESCE(ac.id::text, '') AS contract_id,
            help_art.help_resource_id,
            wr.created_at
        FROM workflow_runs wr
        JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
        LEFT JOIN workflow_triggers wt ON wt.id = wr.trigger_id
        LEFT JOIN autonomous_post_hoc_audits pa ON pa.run_id = wr.id
        LEFT JOIN LATERAL (
            SELECT id
            FROM autonomy_contracts c
            WHERE c.workspace_id = wr.workspace_id
              AND (
                  c.workflow_id = wd.uri
                  OR wd.uri = 'orcia://workflows/' || c.workflow_id
                  OR wd.uri LIKE '%/' || c.workflow_id
              )
            ORDER BY (c.status = 'ACTIVE') DESC, c.signed_at DESC
            LIMIT 1
        ) ac ON TRUE
        LEFT JOIN LATERAL (
            SELECT ci.resource_id AS help_resource_id
            FROM catalog_items ci
            WHERE ci.item_type = 'HELP_ARTICLE'
              AND (
                  ci.metadata_jsonb->>'autonomous_run_id' = wr.id::text
                  OR ci.metadata_jsonb->>'workflow_uri' = wd.uri
              )
            ORDER BY (ci.metadata_jsonb->>'autonomous_run_id' = wr.id::text) DESC,
                     ci.id DESC
            LIMIT 1
        ) help_art ON TRUE
        WHERE wr.id = :run_id;
        """
    )
    async with engine.connect() as conn:
        row = (await conn.execute(stmt, {"run_id": run_uuid})).mappings().first()
        return dict(row) if row is not None else None


async def is_run_kill_switch_stopped_sql(engine: AsyncEngine, *, run_id: str) -> bool:
    """Return `True` if `workflow_runs.status == 'KILL_SWITCH_STOPPED'`."""
    run_uuid = safe_uuid(run_id)
    if run_uuid is None:
        return False
    async with engine.connect() as conn:
        status = (
            await conn.execute(
                sa.text("SELECT status FROM workflow_runs WHERE id = :run_id"),
                {"run_id": run_uuid},
            )
        ).scalar_one_or_none()
        return str(status or "") == "KILL_SWITCH_STOPPED"


async def update_autonomous_run_status_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    status: str,
) -> None:
    """Update `workflow_runs.status` unless emergency stop (`KILL_SWITCH_STOPPED`) fired."""
    run_uuid = safe_uuid(run_id)
    if run_uuid is None:
        return
    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    """
                    UPDATE workflow_runs
                    SET status = :status
                    WHERE id = :run_id
                      AND status <> 'KILL_SWITCH_STOPPED';
                    """
                ),
                {"run_id": run_uuid, "status": status},
            )
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("update_autonomous_run_status_sql_skipped", error=str(exc))
            return
        raise


async def apply_emergency_stop_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    suspend_trigger: bool,
    event: DomainEvent,
    audit_sink: AuditLedgerSinkPort | None = None,
) -> dict[str, Any] | None:
    """Transition a run to `KILL_SWITCH_STOPPED`, optionally suspend trigger, emit Outbox."""
    run_uuid = safe_uuid(run_id)
    if run_uuid is None:
        return None
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text(
                        """
                    UPDATE workflow_runs
                    SET status = 'KILL_SWITCH_STOPPED'
                    WHERE id = :run_id
                    RETURNING id::text AS run_id, workspace_id::text AS workspace_id,
                              trigger_id::text AS trigger_id, status;
                    """
                    ),
                    {"run_id": run_uuid},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        trigger_suspended = False
        if suspend_trigger and row["trigger_id"] is not None:
            await conn.execute(
                sa.text(
                    """
                    UPDATE workflow_triggers
                    SET status = 'CIRCUIT_OPEN', updated_at = NOW()
                    WHERE id = CAST(:trig_id AS uuid);
                    """
                ),
                {"trig_id": str(row["trigger_id"])},
            )
            trigger_suspended = True
        await insert_outbox_and_audit(conn, event, audit_sink)
        return {**dict(row), "trigger_suspended": trigger_suspended}


__all__ = [
    "apply_emergency_stop_sql",
    "get_autonomous_run_sql",
    "is_run_kill_switch_stopped_sql",
    "list_autonomous_runs_for_workspaces_sql",
    "list_autonomous_runs_sql",
    "restore_help_article_and_rollback_run_sql",
    "update_autonomous_run_status_sql",
]
