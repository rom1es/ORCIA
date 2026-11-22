"""PG18 SQLAlchemy repository for Mode A governance (`workspace_customization_overrides`)."""

from __future__ import annotations

import json
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._internal._sql_assistant_governance_queries import (
    SQL_UPSERT_OVERRIDE,
    decode_manifest,
    manifest_to_user_prefs,
    manifest_to_workspace_settings,
    resolve_optional_user_uuid,
    resolve_ws_context,
    row_to_override_record,
)
from orcia_core.orchestration.assistant_agent import ASSISTANT_WORKFLOW_URI
from orcia_core.orchestration.assistant_governance_models import (
    AssistantCustomizationOverrideRecord,
    UserLayerPreferences,
    WorkspaceLayerSettings,
    _compute_sha256_hex,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_user_preferences,
    build_default_workspace_layer_settings,
    build_frozen_workspace_settings,
)
from orcia_kernel.ids import new_uuid7_str


class SqlAssistantGovernanceRepository:
    """Async PG18 repository for Mode A governance in `workspace_customization_overrides`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `workspace_customization_overrides` exists in PG18."""
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.workspace_customization_overrides')")
                )
            ).scalar()
            return reg is not None

    async def get_user_preferences(
        self, *, workspace_id: str, user_id: str, user_email: str | None = None
    ) -> UserLayerPreferences:
        """Load `USER` layer override from PG18 or return deterministic defaults."""
        async with self._engine.connect() as conn:
            ws_key, ws_uuid, _ = await resolve_ws_context(conn, workspace_id)
            u_uuid = await resolve_optional_user_uuid(conn, user_id=user_id, email=user_email)
            u_key = str(u_uuid) if u_uuid is not None else user_id.strip()
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT override_manifest_jsonb, sha256 "
                            "FROM workspace_customization_overrides "
                            "WHERE target_uri = :uri AND override_layer = 'USER' "
                            "AND (override_key = :ov_key OR override_key = :raw_key "
                            "OR (CAST(:ws_uuid AS uuid) IS NOT NULL "
                            "AND workspace_id = CAST(:ws_uuid AS uuid) "
                            "AND CAST(:u_uuid AS uuid) IS NOT NULL "
                            "AND user_id = CAST(:u_uuid AS uuid))) "
                            "ORDER BY created_at DESC LIMIT 1"
                        ),
                        {
                            "uri": ASSISTANT_WORKFLOW_URI,
                            "ov_key": f"assistant-user-{ws_key}-{u_key}",
                            "raw_key": f"assistant-user-{workspace_id}-{user_id}",
                            "ws_uuid": str(ws_uuid) if ws_uuid is not None else None,
                            "u_uuid": str(u_uuid) if u_uuid is not None else None,
                        },
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            return build_default_user_preferences(workspace_id=workspace_id, user_id=user_id)
        return manifest_to_user_prefs(
            workspace_id=workspace_id,
            user_id=user_id,
            manifest=decode_manifest(row["override_manifest_jsonb"]),
            sha256=str(row["sha256"]),
        )

    async def upsert_user_preferences(
        self,
        *,
        workspace_id: str,
        user_id: str,
        user_email: str | None,
        prefs: UserLayerPreferences,
        record: AssistantCustomizationOverrideRecord,
    ) -> UserLayerPreferences:
        """Persist `USER` layer override into PG18 `workspace_customization_overrides`."""
        async with self._engine.begin() as conn:
            ws_key, ws_uuid, _ = await resolve_ws_context(conn, workspace_id)
            u_uuid = await resolve_optional_user_uuid(conn, user_id=user_id, email=user_email)
            u_key = str(u_uuid) if u_uuid is not None else user_id.strip()
            await conn.execute(
                SQL_UPSERT_OVERRIDE,
                {
                    "id": record.id or new_uuid7_str(),
                    "override_key": f"assistant-user-{ws_key}-{u_key}",
                    "org_unit_id": None,
                    "workspace_id": str(ws_uuid) if ws_uuid is not None else None,
                    "user_id": str(u_uuid) if u_uuid is not None else None,
                    "target_uri": record.target_uri,
                    "override_layer": "USER",
                    "manifest": json.dumps(record.override_manifest_jsonb, ensure_ascii=False),
                    "sha256": record.sha256,
                },
            )
        return prefs

    async def get_team_layer_state(
        self, workspace_id: str
    ) -> tuple[str | None, tuple[bool, Literal["PLATFORM", "TEAM"]] | None]:
        """Read `TEAM` layer instructions and upper-layer MCP freeze flag from PG18."""
        async with self._engine.connect() as conn:
            ws_key, ws_uuid, org_uuid = await resolve_ws_context(conn, workspace_id)
            rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT override_key, override_manifest_jsonb "
                            "FROM workspace_customization_overrides "
                            "WHERE target_uri = :uri AND override_layer = 'TEAM' "
                            "AND (override_key = :k_team OR override_key = :k_freeze "
                            "OR (CAST(:ws_uuid AS uuid) IS NOT NULL "
                            "AND workspace_id = CAST(:ws_uuid AS uuid)) "
                            "OR (CAST(:org_uuid AS uuid) IS NOT NULL "
                            "AND org_unit_id = CAST(:org_uuid AS uuid) AND workspace_id IS NULL)) "
                            "ORDER BY created_at DESC"
                        ),
                        {
                            "uri": ASSISTANT_WORKFLOW_URI,
                            "k_team": f"assistant-team-{ws_key}",
                            "k_freeze": f"assistant-team-mcp-freeze-{ws_key}",
                            "ws_uuid": str(ws_uuid) if ws_uuid is not None else None,
                            "org_uuid": str(org_uuid) if org_uuid is not None else None,
                        },
                    )
                )
                .mappings()
                .all()
            )
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

    async def set_team_mcp_frozen(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None:
        """Persist or clear upper-layer MCP freeze in PG18 `TEAM` override row."""
        async with self._engine.begin() as conn:
            ws_key, ws_uuid, org_uuid = await resolve_ws_context(conn, workspace_id)
            ov_key = f"assistant-team-mcp-freeze-{ws_key}"
            if not frozen:
                await conn.execute(
                    sa.text(
                        "DELETE FROM workspace_customization_overrides WHERE override_key = :k"
                    ),
                    {"k": ov_key},
                )
                return
            manifest = {"mcp_frozen": True, "origin": origin}
            await conn.execute(
                SQL_UPSERT_OVERRIDE,
                {
                    "id": new_uuid7_str(),
                    "override_key": ov_key,
                    "org_unit_id": str(org_uuid) if org_uuid is not None else None,
                    "workspace_id": str(ws_uuid) if ws_uuid is not None else None,
                    "user_id": None,
                    "target_uri": ASSISTANT_WORKFLOW_URI,
                    "override_layer": "TEAM",
                    "manifest": json.dumps(manifest, ensure_ascii=False),
                    "sha256": _compute_sha256_hex(manifest),
                },
            )

    async def get_workspace_settings(self, workspace_id: str) -> WorkspaceLayerSettings:
        """Load `WORKSPACE` layer settings from PG18, merging any upper `TEAM` MCP freeze."""
        _, frozen_entry = await self.get_team_layer_state(workspace_id)
        async with self._engine.connect() as conn:
            ws_key, ws_uuid, _ = await resolve_ws_context(conn, workspace_id)
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT override_manifest_jsonb, sha256 "
                            "FROM workspace_customization_overrides "
                            "WHERE target_uri = :uri AND override_layer = 'WORKSPACE' "
                            "AND (override_key = :ov_key OR override_key = :raw_key "
                            "OR (CAST(:ws_uuid AS uuid) IS NOT NULL "
                            "AND workspace_id = CAST(:ws_uuid AS uuid))) "
                            "ORDER BY created_at DESC LIMIT 1"
                        ),
                        {
                            "uri": ASSISTANT_WORKFLOW_URI,
                            "ov_key": f"assistant-workspace-{ws_key}",
                            "raw_key": f"assistant-workspace-{workspace_id}",
                            "ws_uuid": str(ws_uuid) if ws_uuid is not None else None,
                        },
                    )
                )
                .mappings()
                .first()
            )
        base = build_default_workspace_layer_settings(workspace_id)
        if row is not None:
            base = manifest_to_workspace_settings(
                base=base,
                manifest=decode_manifest(row["override_manifest_jsonb"]),
                sha256=str(row["sha256"]),
            )
        if frozen_entry is not None and frozen_entry[0]:
            return build_frozen_workspace_settings(base, origin=frozen_entry[1])
        return base

    async def upsert_workspace_settings(
        self,
        *,
        workspace_id: str,
        settings: WorkspaceLayerSettings,
        record: AssistantCustomizationOverrideRecord,
    ) -> WorkspaceLayerSettings:
        """Persist `WORKSPACE` layer settings into PG18 `workspace_customization_overrides`."""
        async with self._engine.begin() as conn:
            ws_key, ws_uuid, org_uuid = await resolve_ws_context(conn, workspace_id)
            await conn.execute(
                SQL_UPSERT_OVERRIDE,
                {
                    "id": record.id or new_uuid7_str(),
                    "override_key": f"assistant-workspace-{ws_key}",
                    "org_unit_id": str(org_uuid) if org_uuid is not None else None,
                    "workspace_id": str(ws_uuid) if ws_uuid is not None else None,
                    "user_id": None,
                    "target_uri": record.target_uri,
                    "override_layer": "WORKSPACE",
                    "manifest": json.dumps(record.override_manifest_jsonb, ensure_ascii=False),
                    "sha256": record.sha256,
                },
            )
        return settings

    async def list_overrides(
        self, *, workspace_id: str
    ) -> tuple[AssistantCustomizationOverrideRecord, ...]:
        """List active assistant customization override rows for `workspace_id`."""
        async with self._engine.connect() as conn:
            ws_key, ws_uuid, _ = await resolve_ws_context(conn, workspace_id)
            rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id, override_key, org_unit_id, workspace_id, user_id, "
                            "target_uri, override_layer, override_manifest_jsonb, sha256 "
                            "FROM workspace_customization_overrides "
                            "WHERE target_uri = :uri "
                            "AND (override_key LIKE :prefix "
                            "OR (CAST(:ws_uuid AS uuid) IS NOT NULL "
                            "AND workspace_id = CAST(:ws_uuid AS uuid))) "
                            "ORDER BY created_at ASC"
                        ),
                        {
                            "uri": ASSISTANT_WORKFLOW_URI,
                            "prefix": f"assistant-%-{ws_key}%",
                            "ws_uuid": str(ws_uuid) if ws_uuid is not None else None,
                        },
                    )
                )
                .mappings()
                .all()
            )
        return tuple(row_to_override_record(r) for r in rows)


__all__ = ["SqlAssistantGovernanceRepository"]
