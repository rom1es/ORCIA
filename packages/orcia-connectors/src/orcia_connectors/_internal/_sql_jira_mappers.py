"""Row mappers & Outbox helpers for `SqlJiraStagedActionsRepository` (`Story 24.1`)."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_connectors._jira_models import JiraActionType, JiraStagedStatus, StagedJiraActionItem
from orcia_kernel.events import DomainEvent

JIRA_STAGED_SELECT_COLS = (
    "id::text, workspace_id, run_id, step_execution_id, project_alias, project_key, "
    "action_type, issue_key, summary, target_transition, payload_jsonb, status, "
    "idempotency_key, provenance_run_lock_uri, provenance_run_lock_sha256, "
    "external_key, replayed_from_cache"
)


def parse_json_dict(raw: object) -> dict[str, Any]:
    """Decode a JSONB column value into a dictionary."""
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        decoded = json.loads(raw)
        return dict(decoded) if isinstance(decoded, dict) else {}
    return {}


def row_to_staged_item(row: RowMapping) -> StagedJiraActionItem:
    """Convert a `jira_staged_actions` row mapping into `StagedJiraActionItem`."""
    return StagedJiraActionItem(
        staged_action_id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        run_id=str(row["run_id"]),
        step_execution_id=str(row["step_execution_id"]),
        project_alias=str(row["project_alias"]),
        project_key=str(row["project_key"]),
        action_type=cast(JiraActionType, str(row["action_type"])),
        issue_key=str(row["issue_key"]) if row["issue_key"] is not None else None,
        summary=str(row["summary"]),
        target_transition=(
            str(row["target_transition"]) if row["target_transition"] is not None else None
        ),
        fields_payload=parse_json_dict(row["payload_jsonb"]),
        status=cast(JiraStagedStatus, str(row["status"])),
        idempotency_key=str(row["idempotency_key"]),
        provenance_run_lock_uri=(
            str(row["provenance_run_lock_uri"])
            if row["provenance_run_lock_uri"] is not None
            else None
        ),
        provenance_run_lock_sha256=(
            str(row["provenance_run_lock_sha256"])
            if row["provenance_run_lock_sha256"] is not None
            else None
        ),
        executed_issue_key=(str(row["external_key"]) if row["external_key"] is not None else None),
        replayed_from_cache=bool(row["replayed_from_cache"]),
    )


def valid_uuid_or_none(raw: str | None) -> str | None:
    """Return normalized UUID string or `None` if `raw` is not a valid UUID."""
    if not raw or not raw.strip():
        return None
    try:
        return str(UUID(raw.strip()))
    except ValueError:
        return None


async def _resolve_existing_fk_uuid(
    conn: AsyncConnection, table: str, candidate: str | None
) -> str | None:
    uid = valid_uuid_or_none(candidate)
    if uid is None:
        return None
    found = (
        await conn.execute(
            sa.text(f"SELECT id::text FROM {table} WHERE id = CAST(:id AS uuid) LIMIT 1"),
            {"id": uid},
        )
    ).scalar_one_or_none()
    return str(found) if found is not None else None


async def insert_outbox_event_in_conn(conn: AsyncConnection, event: DomainEvent) -> None:
    """Insert `DomainEvent` into `domain_events_outbox` inside the caller transaction."""
    fk_run_id = await _resolve_existing_fk_uuid(conn, "workflow_runs", event.run_id)
    fk_ws_id = await _resolve_existing_fk_uuid(conn, "workspaces", event.workspace_id)
    await conn.execute(
        sa.text(
            """
            INSERT INTO domain_events_outbox (
                event_id, event_type, aggregate_type, aggregate_id,
                run_id, workspace_id, payload_jsonb, trace_id, status, attempts
            ) VALUES (
                CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
                CAST(:payload_jsonb AS jsonb), :trace_id, :status, :attempts
            )
            ON CONFLICT (event_id) DO NOTHING;
            """
        ),
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "run_id": fk_run_id,
            "workspace_id": fk_ws_id,
            "payload_jsonb": json.dumps(event.payload, sort_keys=True, ensure_ascii=False),
            "trace_id": event.trace_id,
            "status": event.status,
            "attempts": event.attempts,
        },
    )


def build_draft_entry(item: StagedJiraActionItem) -> dict[str, Any]:
    """Build compact summary entry for `step_executions.draft_artifact_jsonb`."""
    return {
        "staged_action_id": item.staged_action_id,
        "project_key": item.project_key,
        "action_type": item.action_type,
        "issue_key": item.issue_key,
        "target_transition": item.target_transition,
        "status": item.status,
    }
