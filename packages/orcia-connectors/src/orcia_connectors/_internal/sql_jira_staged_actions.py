"""PostgreSQL 18 SQLAlchemy Async repository for `jira_staged_actions` & Outbox (`Story 24.1`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_connectors._internal._sql_jira_mappers import (
    JIRA_STAGED_SELECT_COLS,
    build_draft_entry,
    insert_outbox_event_in_conn,
    row_to_staged_item,
    valid_uuid_or_none,
)
from orcia_connectors._jira_models import StagedJiraActionItem
from orcia_kernel.events import DomainEvent


class SqlJiraStagedActionsRepository:
    """Async SQLAlchemy repository for `jira_staged_actions` + `domain_events_outbox`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def insert_staged_action(
        self,
        item: StagedJiraActionItem,
        *,
        staged_by: str | None = None,
        outbox_event: DomainEvent | None = None,
    ) -> StagedJiraActionItem:
        """Persist a staged Jira action and optional Outbox event in one ACID transaction."""
        async with self._engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            f"""
                            INSERT INTO jira_staged_actions (
                                id, workspace_id, run_id, step_execution_id,
                                project_alias, project_key, action_type, issue_key,
                                summary, target_transition, payload_jsonb, status,
                                idempotency_key, provenance_run_lock_uri,
                                provenance_run_lock_sha256, external_key,
                                replayed_from_cache, staged_by, created_at, updated_at
                            ) VALUES (
                                CAST(:id AS uuid), :workspace_id, :run_id, :step_execution_id,
                                :project_alias, :project_key, :action_type, :issue_key,
                                :summary, :target_transition, CAST(:payload_jsonb AS jsonb),
                                :status, :idempotency_key, :provenance_run_lock_uri,
                                :provenance_run_lock_sha256, :external_key,
                                :replayed_from_cache, :staged_by, NOW(), NOW()
                            )
                            ON CONFLICT (idempotency_key) DO UPDATE SET
                                updated_at = NOW()
                            RETURNING {JIRA_STAGED_SELECT_COLS};
                            """
                        ),
                        {
                            "id": item.staged_action_id,
                            "workspace_id": item.workspace_id,
                            "run_id": item.run_id,
                            "step_execution_id": item.step_execution_id,
                            "project_alias": item.project_alias,
                            "project_key": item.project_key,
                            "action_type": item.action_type,
                            "issue_key": item.issue_key,
                            "summary": item.summary,
                            "target_transition": item.target_transition,
                            "payload_jsonb": json.dumps(
                                item.fields_payload, ensure_ascii=False, sort_keys=True
                            ),
                            "status": item.status,
                            "idempotency_key": item.idempotency_key,
                            "provenance_run_lock_uri": item.provenance_run_lock_uri,
                            "provenance_run_lock_sha256": item.provenance_run_lock_sha256,
                            "external_key": item.executed_issue_key,
                            "replayed_from_cache": item.replayed_from_cache,
                            "staged_by": staged_by,
                        },
                    )
                )
                .mappings()
                .one()
            )
            if outbox_event is not None:
                await insert_outbox_event_in_conn(conn, outbox_event)
            return row_to_staged_item(row)

    async def get_staged_action(self, staged_action_id: str) -> StagedJiraActionItem | None:
        """Fetch one staged or executed Jira action by UUID from PG18."""
        uid = valid_uuid_or_none(staged_action_id)
        if uid is None:
            return None
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            f"SELECT {JIRA_STAGED_SELECT_COLS} FROM jira_staged_actions "
                            "WHERE id = CAST(:id AS uuid) LIMIT 1;"
                        ),
                        {"id": uid},
                    )
                )
                .mappings()
                .first()
            )
            return row_to_staged_item(row) if row is not None else None

    async def list_staged_actions(
        self, *, workspace_id: str | None = None
    ) -> list[StagedJiraActionItem]:
        """List staged/executed Jira actions ordered chronologically from PG18."""
        clean_ws = workspace_id.strip() if workspace_id else ""
        async with self._engine.connect() as conn:
            if clean_ws:
                rows = (
                    (
                        await conn.execute(
                            sa.text(
                                f"SELECT {JIRA_STAGED_SELECT_COLS} FROM jira_staged_actions "
                                "WHERE workspace_id = :ws ORDER BY created_at ASC, id ASC;"
                            ),
                            {"ws": clean_ws},
                        )
                    )
                    .mappings()
                    .all()
                )
            else:
                rows = (
                    (
                        await conn.execute(
                            sa.text(
                                f"SELECT {JIRA_STAGED_SELECT_COLS} FROM jira_staged_actions "
                                "ORDER BY created_at ASC, id ASC;"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            return [row_to_staged_item(r) for r in rows]

    async def get_step_draft_artifact(self, step_execution_id: str) -> dict[str, Any]:
        """Build `step_executions.draft_artifact_jsonb` directly from PG18."""
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        sa.text(
                            f"SELECT {JIRA_STAGED_SELECT_COLS} FROM jira_staged_actions "
                            "WHERE step_execution_id = :step_id ORDER BY created_at ASC, id ASC;"
                        ),
                        {"step_id": step_execution_id},
                    )
                )
                .mappings()
                .all()
            )
            return {"staged_actions": [build_draft_entry(row_to_staged_item(r)) for r in rows]}

    async def mark_executed(
        self,
        item: StagedJiraActionItem,
        *,
        approved_by: str | None = None,
        outbox_event: DomainEvent | None = None,
    ) -> StagedJiraActionItem:
        """Mark a staged Jira action as `EXECUTED` and emit Outbox event atomically."""
        async with self._engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            f"""
                            UPDATE jira_staged_actions
                            SET status = 'EXECUTED',
                                provenance_run_lock_uri = :run_lock_uri,
                                provenance_run_lock_sha256 = :run_lock_sha256,
                                external_key = :external_key,
                                replayed_from_cache = :replayed_from_cache,
                                approved_by = COALESCE(:approved_by, approved_by),
                                updated_at = NOW()
                            WHERE id = CAST(:id AS uuid)
                            RETURNING {JIRA_STAGED_SELECT_COLS};
                            """
                        ),
                        {
                            "id": item.staged_action_id,
                            "run_lock_uri": item.provenance_run_lock_uri,
                            "run_lock_sha256": item.provenance_run_lock_sha256,
                            "external_key": item.executed_issue_key,
                            "replayed_from_cache": item.replayed_from_cache,
                            "approved_by": approved_by,
                        },
                    )
                )
                .mappings()
                .one()
            )
            if outbox_event is not None:
                await insert_outbox_event_in_conn(conn, outbox_event)
            return row_to_staged_item(row)

    async def enqueue_outbox_event(self, event: DomainEvent) -> None:
        """Persist a `DomainEvent` in `domain_events_outbox` inside a PG18 transaction."""
        async with self._engine.begin() as conn:
            await insert_outbox_event_in_conn(conn, event)
