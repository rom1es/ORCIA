"""SQL statements & row mappers for `SqlAssistantGovernanceRepository` (`<= 300 L`)."""

from __future__ import annotations

import json
from typing import Any, cast
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
