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

from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    ensure_root_org_unit,
    normalize_setup_slug,
)
from orcia_core.bootstrap._internal.sql_platform_setup_store import (
    GLOBAL_SETUP_SCOPE_ID,
    PLATFORM_SETUP_SETTING_KEY,
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
                detail_override=(
                    f"Slug d'espace invalide : '{trimmed_slug}'. "
                    "Utilisez uniquement minuscules, chiffres et tirets (`^[a-z0-9-]+$`)."
                )
            )
        return trimmed_slug[:120]
    normalized = normalize_setup_slug(name, "workspace")
    if len(normalized) < 2:
        raise ValidationDomainError(
            detail_override="Impossible de dériver un slug valide depuis le nom de l'espace."
        )
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
        raise ValidationDomainError(detail_override="Le nom de l'espace ne peut pas être vide.")
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
                detail_override=f"Un espace avec le slug '{resolved_slug}' existe déjà."
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

        # Idempotent owner memberships for creator + active PLATFORM_ADMIN users
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
                    "SELECT id FROM users "
                    "WHERE platform_role = 'PLATFORM_ADMIN' AND is_active = TRUE"
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

        # Keep platform_settings JSONB snapshot in sync if already initialized
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
                {
                    "scope_id": GLOBAL_SETUP_SCOPE_ID,
                    "key": PLATFORM_SETUP_SETTING_KEY,
                },
            )
        ).first()
        if ps_row is not None and ps_row[0] is not None:
            raw_ps = ps_row[0]
            ps_dict: dict[str, Any] = (
                json.loads(raw_ps)
                if isinstance(raw_ps, str)
                else (dict(raw_ps) if isinstance(raw_ps, dict) else {})
            )
            ws_list = list(ps_dict.get("workspaces") or [])
            ws_id_str = str(persisted_ws_uuid)
            if not any(
                str(w.get("workspaceId") or w.get("id") or "") == ws_id_str
                or str(w.get("slug") or "") == resolved_slug
                for w in ws_list
                if isinstance(w, dict)
            ):
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
