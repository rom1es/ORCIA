"""SQL statements & row mappers for `SqlAssistantGovernanceRepository` (`<= 300 L`)."""

from __future__ import annotations

import json
from typing import Any, Literal, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.orchestration._internal._sql_assistant_folders_queries import (
    resolve_workspace_uuid,
)
from orcia_core.orchestration.assistant_governance_models import (
    AssistantArbitrationPolicy,
    AssistantCustomizationOverrideRecord,
    AssistantOverrideScope,
    AssistantResponseFormat,
    AssistantResponseTone,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)

SQL_UPSERT_OVERRIDE = sa.text(
    """
    INSERT INTO workspace_customization_overrides (
        id, override_key, org_unit_id, workspace_id, user_id,
        target_uri, override_layer, override_manifest_jsonb, sha256
    ) VALUES (
        CAST(:id AS uuid), :override_key, CAST(:org_unit_id AS uuid),
        CAST(:workspace_id AS uuid), CAST(:user_id AS uuid),
        :target_uri, :override_layer, CAST(:manifest AS jsonb), :sha256
    )
    ON CONFLICT (override_key) DO UPDATE SET
        org_unit_id = EXCLUDED.org_unit_id,
        workspace_id = EXCLUDED.workspace_id,
        user_id = EXCLUDED.user_id,
        override_layer = EXCLUDED.override_layer,
        override_manifest_jsonb = EXCLUDED.override_manifest_jsonb,
        sha256 = EXCLUDED.sha256
    """
)


def decode_manifest(raw: Any) -> dict[str, Any]:
    """Decode a JSON/JSONB override manifest payload into a dictionary."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    return {}


async def resolve_optional_user_uuid(
    conn: AsyncConnection, *, user_id: str, email: str | None = None
) -> UUID | None:
    """Resolve `users.id` if present in PostgreSQL 18, otherwise return `None`."""
    row = (
        await conn.execute(
            sa.text(
                "SELECT id FROM users "
                "WHERE id::text = :uid OR (:email <> '' AND lower(email) = lower(:email)) "
                "LIMIT 1"
            ),
            {"uid": user_id.strip(), "email": (email or "").strip()},
        )
    ).first()
    return UUID(str(row[0])) if row is not None and row[0] is not None else None


async def resolve_ws_context(
    conn: AsyncConnection, workspace_id: str
) -> tuple[str, UUID | None, UUID | None]:
    """Return `(canonical_ws_key, ws_uuid, owner_org_unit_id)` for `workspace_id`."""
    ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=False)
    if ws_uuid is None:
        return workspace_id.strip(), None, None
    org_row = (
        await conn.execute(
            sa.text(
                "SELECT owner_org_unit_id FROM workspaces WHERE id = CAST(:ws AS uuid) LIMIT 1"
            ),
            {"ws": str(ws_uuid)},
        )
    ).first()
    org_uuid = UUID(str(org_row[0])) if org_row is not None and org_row[0] is not None else None
    return str(ws_uuid), ws_uuid, org_uuid


def row_to_override_record(row: RowMapping) -> AssistantCustomizationOverrideRecord:
    """Convert a `workspace_customization_overrides` row into a domain record."""
    return AssistantCustomizationOverrideRecord(
        id=str(row["id"]),
        override_key=str(row["override_key"]),
        org_unit_id=str(row["org_unit_id"]) if row["org_unit_id"] is not None else None,
        workspace_id=str(row["workspace_id"]) if row["workspace_id"] is not None else None,
        user_id=str(row["user_id"]) if row["user_id"] is not None else None,
        target_uri=str(row["target_uri"]),
        override_layer=cast(AssistantOverrideScope, str(row["override_layer"])),
        override_manifest_jsonb=decode_manifest(row["override_manifest_jsonb"]),
        sha256=str(row["sha256"]),
    )


def manifest_to_user_prefs(
    *, workspace_id: str, user_id: str, manifest: dict[str, Any], sha256: str
) -> UserLayerPreferences:
    """Hydrate `UserLayerPreferences` from a persisted `USER` manifest."""
    return UserLayerPreferences(
        user_id=user_id,
        workspace_id=workspace_id,
        response_tone=cast(AssistantResponseTone, str(manifest.get("response_tone", "BALANCED"))),
        favorite_format=cast(
            AssistantResponseFormat, str(manifest.get("favorite_format", "STRUCTURED_SECTIONS"))
        ),
        default_hat=str(manifest.get("default_hat", "PM")),
        personal_instructions=str(manifest.get("personal_instructions", "")),
        sha256=sha256,
    )


def manifest_to_workspace_settings(
    *, base: WorkspaceLayerSettings, manifest: dict[str, Any], sha256: str
) -> WorkspaceLayerSettings:
    """Hydrate `WorkspaceLayerSettings` from a persisted `WORKSPACE` manifest."""
    return WorkspaceLayerSettings(
        workspace_id=base.workspace_id,
        workspace_instructions=str(
            manifest.get("workspace_instructions", base.workspace_instructions)
        ),
        default_checked_sources=tuple(
            str(x) for x in manifest.get("default_checked_sources", base.default_checked_sources)
        ),
        recommended_agents=tuple(
            str(x) for x in manifest.get("recommended_agents", base.recommended_agents)
        ),
        arbitration_policy=cast(
            AssistantArbitrationPolicy,
            str(manifest.get("arbitration_policy", base.arbitration_policy)),
        ),
        welcome_suggestions=tuple(
            str(x) for x in manifest.get("welcome_suggestions", base.welcome_suggestions)
        ),
        mcp_expose_assistant=bool(manifest.get("mcp_expose_assistant", base.mcp_expose_assistant)),
        mcp_frozen_by_upper_layer=False,
        mcp_frozen_origin=None,
        mcp_endpoint_url=base.mcp_endpoint_url,
        mcp_tool_name=base.mcp_tool_name,
        mcp_ide_config_json=base.mcp_ide_config_json,
        sha256=sha256,
    )


SQL_SELECT_MODE_A_BUNDLE = sa.text(
    """
    WITH target_ws AS (
        SELECT id, owner_org_unit_id
        FROM workspaces
        WHERE id::text = :ws OR slug = :ws
        LIMIT 1
    ),
    target_user AS (
        SELECT id
        FROM users
        WHERE id::text = :uid OR (:email <> '' AND lower(email) = lower(:email))
        LIMIT 1
    )
    SELECT o.override_layer, o.override_key, o.override_manifest_jsonb, o.sha256
    FROM workspace_customization_overrides o
    LEFT JOIN target_ws w ON TRUE
    LEFT JOIN target_user u ON TRUE
    WHERE o.target_uri = :uri
      AND o.override_layer IN ('TEAM', 'WORKSPACE', 'USER')
      AND (
          (o.override_layer = 'USER' AND (
              o.override_key = (
                  'assistant-user-' || COALESCE(w.id::text, :ws)
                  || '-' || COALESCE(u.id::text, :uid)
              )
              OR o.override_key = ('assistant-user-' || :ws || '-' || :uid)
              OR (w.id IS NOT NULL AND o.workspace_id = w.id
                  AND u.id IS NOT NULL AND o.user_id = u.id)
          ))
          OR (o.override_layer = 'WORKSPACE' AND (
              o.override_key = ('assistant-workspace-' || COALESCE(w.id::text, :ws))
              OR o.override_key = ('assistant-workspace-' || :ws)
              OR (w.id IS NOT NULL AND o.workspace_id = w.id)
          ))
          OR (o.override_layer = 'TEAM' AND (
              o.override_key = ('assistant-team-' || COALESCE(w.id::text, :ws))
              OR o.override_key = ('assistant-team-mcp-freeze-' || COALESCE(w.id::text, :ws))
              OR (w.id IS NOT NULL AND o.workspace_id = w.id)
              OR (w.owner_org_unit_id IS NOT NULL
                  AND o.org_unit_id = w.owner_org_unit_id AND o.workspace_id IS NULL)
          ))
      )
    ORDER BY o.created_at DESC
    """
)


def parse_team_rows(
    rows: Any,
) -> tuple[str | None, tuple[bool, Literal["PLATFORM", "TEAM"]] | None]:
    """Extract `TEAM` instructions and upper-layer MCP freeze flag from override rows."""
    team_instr: str | None = None
    frozen_entry: tuple[bool, Literal["PLATFORM", "TEAM"]] | None = None
    for row in rows:
        m = decode_manifest(row["override_manifest_jsonb"])
        if team_instr is None and isinstance(m.get("team_instructions"), str):
            team_instr = str(m["team_instructions"])
        if frozen_entry is None and m.get("mcp_frozen") is True:
            origin = str(m.get("origin", "TEAM"))
            frozen_entry = (True, "PLATFORM" if origin == "PLATFORM" else "TEAM")
    return team_instr, frozen_entry


def rows_to_mode_a_bundle(
    rows: Any,
    *,
    workspace_id: str,
    user_id: str,
    default_user_prefs: UserLayerPreferences,
    default_ws_settings: WorkspaceLayerSettings,
) -> tuple[
    UserLayerPreferences,
    WorkspaceLayerSettings,
    str | None,
    tuple[bool, Literal["PLATFORM", "TEAM"]] | None,
]:
    """Decode consolidated Mode A SQL query rows into USER, WORKSPACE, and TEAM state."""
    user_row: Any = None
    ws_row: Any = None
    team_rows: list[Any] = []
    for row in rows:
        layer = str(row["override_layer"])
        if layer == "USER" and user_row is None:
            user_row = row
        elif layer == "WORKSPACE" and ws_row is None:
            ws_row = row
        elif layer == "TEAM":
            team_rows.append(row)
    user_prefs = (
        manifest_to_user_prefs(
            workspace_id=workspace_id,
            user_id=user_id,
            manifest=decode_manifest(user_row["override_manifest_jsonb"]),
            sha256=str(user_row["sha256"]),
        )
        if user_row is not None
        else default_user_prefs
    )
    ws_settings = (
        manifest_to_workspace_settings(
            base=default_ws_settings,
            manifest=decode_manifest(ws_row["override_manifest_jsonb"]),
            sha256=str(ws_row["sha256"]),
        )
        if ws_row is not None
        else default_ws_settings
    )
    team_instr, frozen_entry = parse_team_rows(team_rows)
    return user_prefs, ws_settings, team_instr, frozen_entry
