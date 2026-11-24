"""Parent FK resolution & SQL mappers for `SqlTaskNotificationRepository` (`0021_story_5_1`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.orchestration._orchestration_cc_notif_locales import get_notif_copy
from orcia_core.orchestration.presence_and_sse import (
    NotificationScopeKind,
    NotificationStatus,
    NotificationType,
    TaskNotificationEntity,
)
from orcia_kernel.ids import new_uuid7_str

_ORCIA_NOTIF_NS = UUID("0195f000-0000-7000-8000-00000000d000")
_DEFAULT_ORG_UNIT_ID = UUID("0192c4e0-0000-7000-8000-000000000101")
_DEFAULT_WF_DEF_ID = UUID("0195f000-0000-7000-8000-000000000601")


def coerce_uuid(raw_id: str | None) -> UUID:
    """Convert any identifier string into a valid UUID (deterministic UUIDv5 for non-UUID keys)."""
    if raw_id is None or not raw_id.strip():
        return UUID(new_uuid7_str())
    cleaned = raw_id.strip()
    try:
        return UUID(cleaned)
    except ValueError:
        return uuid5(_ORCIA_NOTIF_NS, cleaned)


def iso_or_none(val: Any) -> str | None:
    """Convert DB datetime/value to ISO-8601 UTC string."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return (
            val.astimezone(UTC).isoformat() if val.tzinfo else val.replace(tzinfo=UTC).isoformat()
        )
    return str(val)


def dt_or_none(raw: str | None) -> datetime | None:
    """Parse ISO-8601 string into timezone-aware UTC datetime."""
    if not raw:
        return None
    dt = datetime.fromisoformat(raw)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def row_to_notification_entity(row: RowMapping) -> TaskNotificationEntity:
    """Map a PG18 `task_notifications` row into `TaskNotificationEntity`."""
    return TaskNotificationEntity(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        target_team_id=str(row["target_team_id"]) if row["target_team_id"] is not None else None,
        target_user_id=str(row["target_user_id"]) if row["target_user_id"] is not None else None,
        run_id=str(row["run_id"]),
        step_execution_id=str(row["step_execution_id"]),
        step_key=str(row["step_key"]),
        notification_type=cast(NotificationType, str(row["notification_type"])),
        scope_kind=cast(NotificationScopeKind, str(row["scope_kind"])),
        title=str(row["title"]),
        summary=str(row["summary"] or ""),
        status=cast(NotificationStatus, str(row["status"])),
        claimed_by_user_id=(
            str(row["claimed_by_user_id"]) if row["claimed_by_user_id"] is not None else None
        ),
        claimed_by_display_name=(
            str(row["claimed_by_display_name"])
            if row["claimed_by_display_name"] is not None
            else None
        ),
        claimed_at=iso_or_none(row["claimed_at"]),
        lock_expires_at=iso_or_none(row["lock_expires_at"]),
        source_event_id=(
            str(row["source_event_id"]) if row["source_event_id"] is not None else None
        ),
        created_at=iso_or_none(row["created_at"]) or datetime.now(UTC).isoformat(),
    )


async def resolve_nullable_user(conn: AsyncConnection, user_id: str | None) -> UUID | None:
    """Resolve `users.id` if present in PG18, else return `None`."""
    if not user_id or not user_id.strip():
        return None
    row = (
        await conn.execute(
            sa.text(
                "SELECT id FROM users WHERE id::text = :uid OR lower(email) = lower(:uid) LIMIT 1"
            ),
            {"uid": user_id.strip()},
        )
    ).first()
    return UUID(str(row[0])) if row is not None else None


async def _resolve_or_ensure_org_unit(conn: AsyncConnection) -> UUID:
    any_org = (
        await conn.execute(sa.text("SELECT id FROM org_units ORDER BY created_at ASC LIMIT 1"))
    ).scalar_one_or_none()
    if any_org is not None:
        return UUID(str(any_org))
    await conn.execute(
        sa.text(
            "INSERT INTO org_units (id, slug, name, unit_type, parent_id) VALUES ("
            "CAST(:id AS uuid), 'orcia-enterprise', 'Entreprise ORCIA', 'ENTERPRISE', NULL"
            ") ON CONFLICT (slug) DO NOTHING"
        ),
        {"id": str(_DEFAULT_ORG_UNIT_ID)},
    )
    resolved = (
        await conn.execute(sa.text("SELECT id FROM org_units ORDER BY created_at ASC LIMIT 1"))
    ).scalar_one()
    return UUID(str(resolved))


async def ensure_notification_parents(
    conn: AsyncConnection,
    *,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
    target_team_id: str | None,
    target_user_id: str | None,
) -> tuple[UUID, UUID, UUID, UUID | None, UUID | None]:
    """Ensure parent `workspaces`, `workflow_runs`, and `step_executions` rows exist in PG18."""
    ws_uuid = coerce_uuid(workspace_id)
    run_uuid = coerce_uuid(run_id)
    step_uuid = coerce_uuid(step_execution_id)

    ws_row = (
        await conn.execute(
            sa.text(
                "SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) OR slug = :raw LIMIT 1"
            ),
            {"ws": str(ws_uuid), "raw": workspace_id.strip()},
        )
    ).first()
    if ws_row is not None:
        ws_uuid = UUID(str(ws_row[0]))
    else:
        org_uuid = await _resolve_or_ensure_org_unit(conn)
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (CAST(:id AS uuid), :slug, :name, CAST(:org_id AS uuid), 'STANDARD') "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {
                "id": str(ws_uuid),
                "slug": f"ws-notif-{str(ws_uuid)[-12:]}",
                "name": get_notif_copy()["notif_ws_name"],
                "org_id": str(org_uuid),
            },
        )
        ws_check = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) LIMIT 1"),
                {"ws": str(ws_uuid)},
            )
        ).first()
        if ws_check is None:
            fallback_ws = (
                await conn.execute(
                    sa.text("SELECT id FROM workspaces ORDER BY created_at ASC LIMIT 1")
                )
            ).first()
            if fallback_ws is not None:
                ws_uuid = UUID(str(fallback_ws[0]))

    wf_def_row = (
        await conn.execute(
            sa.text("SELECT id FROM workflow_definitions ORDER BY created_at ASC LIMIT 1")
        )
    ).first()
    if wf_def_row is not None:
        wf_def_uuid = UUID(str(wf_def_row[0]))
    else:
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions ("
                "id, workspace_id, uri, version, source_format, steps_schema_jsonb, sha256"
                ") VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), "
                "'orcia://system/workflows/inbox-task-parent', '1.0.0', 'ORCIA', "
                "'{}'::jsonb, :sha256) ON CONFLICT (uri) DO NOTHING"
            ),
            {"id": str(_DEFAULT_WF_DEF_ID), "ws": str(ws_uuid), "sha256": "0" * 64},
        )
        wf_def_uuid = UUID(
            str(
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id FROM workflow_definitions ORDER BY created_at ASC LIMIT 1"
                        )
                    )
                ).scalar_one()
            )
        )

    await conn.execute(
        sa.text(
            "INSERT INTO workflow_runs ("
            "id, run_key, workspace_id, workflow_def_id, root_run_id, status"
            ") VALUES (CAST(:id AS uuid), :run_key, CAST(:ws AS uuid), "
            "CAST(:wf_def_id AS uuid), CAST(:id AS uuid), 'WAITING_FOR_HUMAN_ARBITRATION') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(run_uuid),
            "run_key": f"run-notif-{str(run_uuid)}",
            "ws": str(ws_uuid),
            "wf_def_id": str(wf_def_uuid),
        },
    )
    await conn.execute(
        sa.text(
            "INSERT INTO step_executions ("
            "id, step_execution_key, run_id, step_key, step_index, status"
            ") VALUES (CAST(:id AS uuid), :step_exec_key, CAST(:run_id AS uuid), "
            ":step_key, 0, 'WAITING_FOR_HUMAN_ARBITRATION') ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(step_uuid),
            "step_exec_key": f"step-notif-{str(step_uuid)}",
            "run_id": str(run_uuid),
            "step_key": step_key[:128] or "step-1",
        },
    )

    resolved_team: UUID | None = None
    if target_team_id:
        team_row = (
            await conn.execute(
                sa.text("SELECT id FROM org_units WHERE id = CAST(:id AS uuid) LIMIT 1"),
                {"id": str(coerce_uuid(target_team_id))},
            )
        ).first()
        resolved_team = UUID(str(team_row[0])) if team_row is not None else None
    resolved_user = await resolve_nullable_user(conn, target_user_id)
    return ws_uuid, run_uuid, step_uuid, resolved_team, resolved_user
