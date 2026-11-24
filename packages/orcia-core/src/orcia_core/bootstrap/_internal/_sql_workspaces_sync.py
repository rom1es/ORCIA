"""PostgreSQL 18 platform_settings & membership sync helpers for workspace creation."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection
from uuid_utils import uuid7

from orcia_core.bootstrap._internal.sql_platform_setup_store import (
    GLOBAL_SETUP_SCOPE_ID,
    PLATFORM_SETUP_SETTING_KEY,
)


async def sync_workspace_owner_memberships(
    conn: AsyncConnection,
    *,
    persisted_ws_uuid: UUID,
    creator_user_id: str | None,
) -> None:
    """Create idempotent owner memberships for workspace creator and active admins."""
    target_user_ids: list[tuple[UUID, str]] = []
    if creator_user_id:
        try:
            creator_uuid = UUID(creator_user_id)
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT id, platform_role FROM users "
                        "WHERE id = :id AND is_active = TRUE LIMIT 1"
                    ),
                    {"id": creator_uuid},
                )
            ).first()
            if row is not None and row[0] is not None:
                role_val = str(row[1] or "PLATFORM_ADMIN")
                if role_val != "OBSERVER":
                    target_user_ids.append((UUID(str(row[0])), role_val))
        except (ValueError, TypeError):
            pass

    admin_rows = (
        await conn.execute(
            sa.text(
                "SELECT id FROM users WHERE platform_role = 'PLATFORM_ADMIN' AND is_active = TRUE"
            )
        )
    ).fetchall()
    seen_uids = {uid for uid, _ in target_user_ids}
    for admin_row in admin_rows:
        if not admin_row or admin_row[0] is None:
            continue
        auid = UUID(str(admin_row[0]))
        if auid not in seen_uids:
            seen_uids.add(auid)
            target_user_ids.append((auid, "PLATFORM_ADMIN"))

    for uid, member_role in target_user_ids:
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_memberships (
                    id, workspace_id, user_id, role, access_mode
                )
                SELECT :id, :ws_id, :user_id, :role, 'CONTRIBUTOR_ACTION_REQUIRED'
                WHERE NOT EXISTS (
                    SELECT 1 FROM workspace_memberships
                    WHERE workspace_id = :ws_id AND user_id = :user_id
                )
                """
            ),
            {
                "id": UUID(str(uuid7())),
                "ws_id": persisted_ws_uuid,
                "user_id": uid,
                "role": member_role,
            },
        )


async def sync_workspace_to_platform_settings(
    conn: AsyncConnection,
    *,
    persisted_ws_uuid: UUID,
    cleaned_name: str,
    resolved_slug: str,
    ui_vis: str,
    resolved_owner_id: UUID,
    resolved_owner_name: str,
    phase: str,
) -> None:
    """Append newly created workspace into `platform_settings` snapshot when initialized."""
    ps_row = (
        await conn.execute(
            sa.text(
                """
                SELECT value_jsonb FROM platform_settings
                WHERE scope_level = 'GLOBAL'
                  AND scope_id = :scope_id
                  AND category = 'iam'
                  AND key = :key
                LIMIT 1
                """
            ),
            {"scope_id": GLOBAL_SETUP_SCOPE_ID, "key": PLATFORM_SETUP_SETTING_KEY},
        )
    ).first()
    if ps_row is None or ps_row[0] is None:
        return
    raw_ps = ps_row[0]
    ps_dict: dict[str, Any] = (
        json.loads(raw_ps)
        if isinstance(raw_ps, str)
        else (dict(raw_ps) if isinstance(raw_ps, dict) else {})
    )
    ws_list = list(ps_dict.get("workspaces") or [])
    ws_id_str = str(persisted_ws_uuid)
    if any(
        str(w.get("workspaceId") or w.get("id") or "") == ws_id_str
        or str(w.get("slug") or "") == resolved_slug
        for w in ws_list
        if isinstance(w, dict)
    ):
        return
    ws_list.append(
        {
            "workspaceId": ws_id_str,
            "name": cleaned_name[:255],
            "slug": resolved_slug,
            "visibilityMode": ui_vis,
            "ownerOrgUnitId": str(resolved_owner_id),
            "ownerOrgUnitName": resolved_owner_name,
            "lifecyclePhase": phase,
            "suggestedWorkflows": [],
            "accessMode": "CONTRIBUTOR_ACTION_REQUIRED",
            "finopsCostUsd": 0,
        }
    )
    ps_dict["workspaces"] = ws_list
    await conn.execute(
        sa.text(
            """
            UPDATE platform_settings
            SET value_jsonb = CAST(:value_jsonb AS jsonb),
                version = version + 1,
                updated_at = NOW()
            WHERE scope_level = 'GLOBAL'
              AND scope_id = :scope_id
              AND category = 'iam'
              AND key = :key
            """
        ),
        {
            "scope_id": GLOBAL_SETUP_SCOPE_ID,
            "key": PLATFORM_SETUP_SETTING_KEY,
            "value_jsonb": json.dumps(ps_dict, ensure_ascii=False, sort_keys=True),
        },
    )


__all__ = ["sync_workspace_owner_memberships", "sync_workspace_to_platform_settings"]
