"""PostgreSQL 18 `AsyncSession` store & pending-runs query for `workflow_v2_runs` (`Story 30.3`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.workflows._internal._sql_workflow_v2_pending_query import (
    PENDING_ACTION_STATUSES,
    list_pending_runs_from_memory,
    query_pending_and_active_runs_sql,
    safe_uuid,
)

logger = get_logger("orcia.workflows.sql_workflow_v2_runs")


class SqlWorkflowV2RunsStore:
    """PostgreSQL 18 repository (`AsyncSession`) for `workflow_v2_runs` & pending validations."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        *,
        strict_sql: bool = False,
    ) -> None:
        self._session_maker = session_maker
        self._strict_sql = strict_sql
        self._memory_fallback: dict[str, dict[str, Any]] = {}

    async def upsert_run(
        self,
        *,
        run_id: str,
        workspace_id: str | None,
        workflow_id: str,
        workflow_slug: str,
        workflow_title: str,
        actor_slug: str,
        status: str,
        reflexive_execution_id: str | None,
        state_payload: dict[str, Any],
    ) -> None:
        """Persist or update a `workflow_v2_runs` row in PG18 (or memory when SQL disabled)."""
        ws_uuid = safe_uuid(workspace_id)
        record = {
            "run_id": run_id,
            "workspace_id": str(ws_uuid) if ws_uuid is not None else None,
            "workflow_id": workflow_id,
            "workflow_slug": workflow_slug,
            "workflow_title": workflow_title,
            "actor_slug": actor_slug,
            "status": status,
            "reflexive_execution_id": reflexive_execution_id,
            "state": dict(state_payload),
        }
        if not self._strict_sql:
            self._memory_fallback[run_id] = record
        if self._session_maker is None:
            return

        stmt = sa.text(
            """
            INSERT INTO workflow_v2_runs (
                id, run_id, workspace_id, workflow_id, workflow_slug,
                workflow_title, actor_slug, status, reflexive_execution_id,
                state_jsonb, created_at, updated_at
            )
            VALUES (
                CAST(:id AS UUID), :run_id, CAST(:workspace_id AS UUID), :workflow_id,
                :workflow_slug, :workflow_title, :actor_slug, :status,
                :reflexive_execution_id, CAST(:state_jsonb AS JSONB), NOW(), NOW()
            )
            ON CONFLICT (run_id) DO UPDATE SET
                workspace_id = COALESCE(EXCLUDED.workspace_id, workflow_v2_runs.workspace_id),
                workflow_title = EXCLUDED.workflow_title,
                actor_slug = EXCLUDED.actor_slug,
                status = EXCLUDED.status,
                reflexive_execution_id = COALESCE(
                    EXCLUDED.reflexive_execution_id, workflow_v2_runs.reflexive_execution_id
                ),
                state_jsonb = EXCLUDED.state_jsonb,
                updated_at = NOW()
            """
        )
        try:
            async with self._session_maker() as session:
                await session.execute(
                    stmt,
                    {
                        "id": new_uuid7_str(),
                        "run_id": run_id,
                        "workspace_id": str(ws_uuid) if ws_uuid is not None else None,
                        "workflow_id": workflow_id,
                        "workflow_slug": workflow_slug,
                        "workflow_title": workflow_title,
                        "actor_slug": actor_slug,
                        "status": status,
                        "reflexive_execution_id": reflexive_execution_id,
                        "state_jsonb": json.dumps(state_payload, ensure_ascii=False),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "workflow_v2_run_sql_upsert_failed",
                run_id=run_id,
                error_type=type(exc).__name__,
            )
            if self._strict_sql:
                raise

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Load a `workflow_v2_runs` state JSON payload from PG18 (or memory fallback)."""
        if self._session_maker is not None:
            stmt = sa.text(
                "SELECT state_jsonb, workspace_id::text "
                "FROM workflow_v2_runs WHERE run_id = :run_id"
            )
            try:
                async with self._session_maker() as session:
                    row = (await session.execute(stmt, {"run_id": run_id})).first()
                if row is not None:
                    raw = row[0]
                    payload = json.loads(raw) if isinstance(raw, str) else dict(raw)
                    if len(row) > 1 and row[1] and not payload.get("workspace_id"):
                        payload["workspace_id"] = str(row[1])
                    return payload
                if self._strict_sql:
                    return None
            except Exception as exc:
                logger.warning(
                    "workflow_v2_run_sql_get_failed",
                    run_id=run_id,
                    error_type=type(exc).__name__,
                )
                if self._strict_sql:
                    raise
        cached = self._memory_fallback.get(run_id)
        if cached is None:
            return None
        payload = dict(cached["state"])
        if cached.get("workspace_id") and not payload.get("workspace_id"):
            payload["workspace_id"] = cached["workspace_id"]
        return payload

    async def list_pending_and_active_runs(
        self,
        *,
        workspace_ids: tuple[str, ...] | None,
        include_completed: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query PG18 (`workflow_v2_runs`, `reflexive_execution_sessions`, `workflow_runs`)."""
        if workspace_ids is not None and len(workspace_ids) == 0:
            return []

        if self._session_maker is None:
            return list_pending_runs_from_memory(
                list(self._memory_fallback.values()),
                workspace_ids=workspace_ids,
                include_completed=include_completed,
                limit=limit,
            )

        return await query_pending_and_active_runs_sql(
            self._session_maker,
            strict_sql=self._strict_sql,
            workspace_ids=workspace_ids,
            include_completed=include_completed,
            limit=limit,
        )


__all__ = ["PENDING_ACTION_STATUSES", "SqlWorkflowV2RunsStore"]
