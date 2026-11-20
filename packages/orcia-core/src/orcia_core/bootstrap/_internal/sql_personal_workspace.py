"""PostgreSQL 18 automatic & isolated Personal Workspace provisioning (`Story 25.1`)."""

from __future__ import annotations

import json
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import ensure_root_org_unit
from orcia_kernel.ids import new_uuid7_str

_VALID_MEMBERSHIP_ROLES: frozenset[str] = frozenset(
    {
        "PLATFORM_ADMIN",
        "SECOPS",
        "BU_LEAD",
        "BU_DIRECTOR",
        "TEAM_LEAD",
        "ONTOLOGY_LEAD",
        "CONTRIBUTOR",
        "GATE_REVIEWER",
        "ONTOLOGY_STEWARD_L3",
        "OBSERVER",
    }
)


def build_personal_workspace_name(display_name: str, *, locale: str = "fr") -> str:
    """Return a clean localized Personal Workspace name."""
    cleaned_name = display_name.strip()
    if locale.strip().lower().startswith("en"):
        return f"Personal Space — {cleaned_name}"[:255] if cleaned_name else "My Personal Space"
    return f"Espace personnel — {cleaned_name}"[:255] if cleaned_name else "Mon espace personnel"


async def ensure_personal_workspace_on_postgres18(
    conn: AsyncConnection,
    *,
    user_id: str,
    display_name: str,
    locale: str = "fr",
) -> str:
    """Idempotently provision an isolated personal workspace (`PRIVATE_USER`) for `user_id`."""
    user_uuid = UUID(str(user_id).strip())
    owner_org_unit_id = await ensure_root_org_unit(conn)
    slug = f"personal-{user_uuid}"
    ws_name = build_personal_workspace_name(display_name, locale=locale)
    new_ws_uuid = UUID(new_uuid7_str())

    settings_payload = {
        "ui_visibility_mode": "PRIVATE_USER",
        "is_personal_workspace": True,
        "personal_owner_user_id": str(user_uuid),
        "lifecycle_phase": "BUILD",
        "owner_org_unit_id": str(owner_org_unit_id),
        "owner_org_unit_name": "ORCIA Root Organization",
    }

    inserted_row = (
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspaces (
                    id, slug, name, owner_org_unit_id, visibility_mode, settings_jsonb
                )
                VALUES (
                    :id, :slug, :name, :owner_org_unit_id, 'CONFIDENTIAL_RESTRICTED',
                    CAST(:settings_jsonb AS jsonb)
                )
                ON CONFLICT (slug) DO UPDATE
                SET visibility_mode = 'CONFIDENTIAL_RESTRICTED',
                    settings_jsonb = workspaces.settings_jsonb || EXCLUDED.settings_jsonb
                RETURNING id
                """
            ),
            {
                "id": new_ws_uuid,
                "slug": slug,
                "name": ws_name,
                "owner_org_unit_id": owner_org_unit_id,
                "settings_jsonb": json.dumps(settings_payload, ensure_ascii=False),
            },
        )
    ).first()
    persisted_ws_uuid = (
        UUID(str(inserted_row[0]))
        if inserted_row is not None and inserted_row[0] is not None
        else new_ws_uuid
    )

    role_row = (
        await conn.execute(
            sa.text("SELECT platform_role FROM users WHERE id = :uid LIMIT 1"),
            {"uid": user_uuid},
        )
    ).first()
    raw_role = str(role_row[0]).strip().upper() if role_row is not None and role_row[0] else ""
    member_role = raw_role if raw_role in _VALID_MEMBERSHIP_ROLES else "CONTRIBUTOR"

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
            "id": UUID(new_uuid7_str()),
            "ws_id": persisted_ws_uuid,
            "user_id": user_uuid,
            "role": member_role,
        },
    )
    return str(persisted_ws_uuid)


__all__ = [
    "build_personal_workspace_name",
    "ensure_personal_workspace_on_postgres18",
]
