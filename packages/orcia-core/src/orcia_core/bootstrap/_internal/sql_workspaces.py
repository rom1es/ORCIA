"""PostgreSQL 18 persistence adapter for direct Workspace creation (`UUIDv7` & exact `slug`)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.bootstrap._internal._sql_workspaces_sync import (
    sync_workspace_owner_memberships,
    sync_workspace_to_platform_settings,
)
from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    ensure_root_org_unit,
    normalize_setup_slug,
)
from orcia_core.permissions.errors import ValidationDomainError

_EXACT_SLUG_RE = re.compile(r"^[a-z0-9-]+$")


@dataclass(frozen=True, slots=True)
class WorkspaceCreationRecord:
    """Persisted PostgreSQL 18 Workspace record returned by `POST /api/v1/workspaces`."""

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    owner_org_unit_name: str
    visibility_mode: str
    ui_visibility_mode: str
    lifecycle_phase: str
    finops_cost_usd: float


def resolve_exact_workspace_slug(raw_slug: str | None, name: str) -> str:
    """Preserve exact valid `^[a-z0-9-]+$` slug when provided; else normalize from `name`."""
    trimmed_slug = (raw_slug or "").strip()
    if trimmed_slug:
        if not _EXACT_SLUG_RE.fullmatch(trimmed_slug) or len(trimmed_slug) < 2:
            raise ValidationDomainError(
                detail_code="ERR_WORKSPACE_INVALID_SLUG",
                detail_params={"slug": trimmed_slug},
            )
        return trimmed_slug[:120]
    normalized = normalize_setup_slug(name, "workspace")
    if len(normalized) < 2:
        raise ValidationDomainError(detail_code="ERR_WORKSPACE_DERIVED_SLUG_INVALID")
    return normalized


async def create_workspace_on_postgres18(
    engine: AsyncEngine,
    *,
    name: str,
    slug: str | None = None,
    visibility_mode: str = "STANDARD",
    lifecycle_phase: str = "BUILD",
    owner_org_unit_id: str | None = None,
    creator_user_id: str | None = None,
) -> WorkspaceCreationRecord:
    """Create a Workspace on PostgreSQL 18 with `UUIDv7`, exact `slug`, and owner membership."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValidationDomainError(detail_code="ERR_WORKSPACE_EMPTY_NAME")
    resolved_slug = resolve_exact_workspace_slug(slug, cleaned_name)
    ui_vis = (visibility_mode or "STANDARD").strip().upper()
    db_vis = "CONFIDENTIAL_RESTRICTED" if ui_vis == "CONFIDENTIAL_RESTRICTED" else "STANDARD"
    phase = (lifecycle_phase or "BUILD").strip().upper()
    if phase not in ("BUILD", "RUN", "MIGRATION"):
        phase = "BUILD"

    new_ws_uuid = UUID(str(uuid7()))

    async with engine.begin() as conn:
        existing_slug = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE slug = :slug LIMIT 1"),
                {"slug": resolved_slug},
            )
        ).first()
        if existing_slug is not None:
            raise ValidationDomainError(
                detail_code="ERR_WORKSPACE_SLUG_EXISTS",
                detail_params={"slug": resolved_slug},
            )

        root_org_id = await ensure_root_org_unit(conn)
        resolved_owner_id = root_org_id
        resolved_owner_name = "ORCIA Root Organization"
        raw_owner = (owner_org_unit_id or "").strip()
        if raw_owner and raw_owner != "scope-global":
            owner_row = None
            try:
                owner_uuid_cand = UUID(raw_owner)
                owner_row = (
                    await conn.execute(
                        sa.text("SELECT id, name FROM org_units WHERE id = :id LIMIT 1"),
                        {"id": owner_uuid_cand},
                    )
                ).first()
            except (ValueError, TypeError):
                owner_row = (
                    await conn.execute(
                        sa.text("SELECT id, name FROM org_units WHERE slug = :slug LIMIT 1"),
                        {"slug": raw_owner},
                    )
                ).first()
            if owner_row is not None and owner_row[0] is not None:
                resolved_owner_id = UUID(str(owner_row[0]))
                resolved_owner_name = str(owner_row[1] or resolved_owner_name)

        settings_payload: dict[str, Any] = {
            "lifecycle_phase": phase,
            "ui_workspace_id": str(new_ws_uuid),
            "ui_visibility_mode": ui_vis,
            "owner_org_unit_id": str(resolved_owner_id),
            "owner_org_unit_name": resolved_owner_name,
        }
        inserted = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workspaces (
                        id, slug, name, owner_org_unit_id, visibility_mode, settings_jsonb
                    )
                    VALUES (
                        :id, :slug, :name, :owner_org_unit_id, :visibility_mode,
                        CAST(:settings_jsonb AS jsonb)
                    )
                    RETURNING id
                    """
                ),
                {
                    "id": new_ws_uuid,
                    "slug": resolved_slug,
                    "name": cleaned_name[:255],
                    "owner_org_unit_id": resolved_owner_id,
                    "visibility_mode": db_vis,
                    "settings_jsonb": json.dumps(settings_payload, ensure_ascii=False),
                },
            )
        ).first()
        persisted_ws_uuid = (
            UUID(str(inserted[0]))
            if inserted is not None and inserted[0] is not None
            else new_ws_uuid
        )

        await sync_workspace_owner_memberships(
            conn,
            persisted_ws_uuid=persisted_ws_uuid,
            creator_user_id=creator_user_id,
        )
        await sync_workspace_to_platform_settings(
            conn,
            persisted_ws_uuid=persisted_ws_uuid,
            cleaned_name=cleaned_name,
            resolved_slug=resolved_slug,
            ui_vis=ui_vis,
            resolved_owner_id=resolved_owner_id,
            resolved_owner_name=resolved_owner_name,
            phase=phase,
        )

    return WorkspaceCreationRecord(
        id=str(persisted_ws_uuid),
        slug=resolved_slug,
        name=cleaned_name[:255],
        owner_org_unit_id=str(resolved_owner_id),
        owner_org_unit_name=resolved_owner_name,
        visibility_mode=db_vis,
        ui_visibility_mode=ui_vis,
        lifecycle_phase=phase,
        finops_cost_usd=0.0,
    )


__all__ = [
    "WorkspaceCreationRecord",
    "create_workspace_on_postgres18",
    "resolve_exact_workspace_slug",
]
