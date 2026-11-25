"""PostgreSQL 18 persistence adapter for scoped `PATCH /api/v1/workspaces/{id}` (`Story 29.2`)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal._sql_workspaces_sync import ensure_user_workspace_membership
from orcia_core.bootstrap._internal.sql_platform_setup_store import (
    GLOBAL_SETUP_SCOPE_ID,
    PLATFORM_SETUP_SETTING_KEY,
)
from orcia_core.permissions.errors import (
    PrivateWorkspaceVisibilityLockedError,
    ResourceNotFoundError,
    ValidationDomainError,
)


@dataclass(frozen=True, slots=True)
class WorkspacePatchResult:
    """Persisted PG18 Workspace record returned by `PATCH /api/v1/workspaces/{id}`."""

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    owner_org_unit_name: str
    visibility_mode: str
    ui_visibility_mode: str
    lifecycle_phase: str
    finops_cost_usd: float
    personal_owner_user_id: str | None = None


def _decode_jsonb(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return dict(decoded)
        except ValueError:
            return {}
    return {}


async def _sync_patched_workspace_platform_settings(
    conn: AsyncConnection,
    *,
    ws_id_str: str,
    ws_slug: str,
    next_name: str,
    next_ui_vis: str,
    next_phase: str,
) -> None:
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
    ps_dict = _decode_jsonb(ps_row[0])
    ws_list = list(ps_dict.get("workspaces") or [])
    changed = False
    updated_list: list[Any] = []
    for item in ws_list:
        if not isinstance(item, dict):
            updated_list.append(item)
            continue
        item_id = str(item.get("workspaceId") or item.get("id") or "")
        item_slug = str(item.get("slug") or "")
        if item_id == ws_id_str or (ws_slug and item_slug == ws_slug):
            patched_item = dict(item)
            patched_item["name"] = next_name
            patched_item["visibilityMode"] = next_ui_vis
            patched_item["lifecyclePhase"] = next_phase
            updated_list.append(patched_item)
            changed = True
        else:
            updated_list.append(item)
    if not changed:
        return
    ps_dict["workspaces"] = updated_list
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


async def patch_workspace_on_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    actor_user_id: str | None,
    actor_role: str,
    name: str | None = None,
    visibility_mode: str | None = None,
    lifecycle_phase: str | None = None,
    instance: str | None = None,
) -> WorkspacePatchResult:
    """Update Workspace fields in PG18 with `PRIVATE_USER` lock and self-lockout membership."""
    try:
        ws_uuid = UUID(str(workspace_id).strip())
    except (ValueError, TypeError) as err:
        raise ResourceNotFoundError(instance=instance) from err

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT w.id, w.slug, w.name, w.owner_org_unit_id, w.visibility_mode,
                           w.finops_cost_usd, w.settings_jsonb, o.name AS owner_ou_name
                    FROM workspaces w
                    LEFT JOIN org_units o ON o.id = w.owner_org_unit_id
                    WHERE w.id = :ws_id
                    FOR UPDATE OF w
                    """
                ),
                {"ws_id": ws_uuid},
            )
        ).first()
        if row is None:
            raise ResourceNotFoundError(instance=instance)

        ws_slug = str(row[1])
        cur_name = str(row[2])
        owner_ou_id = str(row[3])
        cur_db_vis = str(row[4] or "STANDARD")
        finops_cost = float(row[5] or 0.0)
        settings = _decode_jsonb(row[6])
        owner_ou_name = str(row[7] or settings.get("owner_org_unit_name") or "ORCIA")
        personal_owner = (
            str(settings["personal_owner_user_id"]).strip()
            if settings.get("personal_owner_user_id")
            else None
        )
        cur_ui_vis = str(settings.get("ui_visibility_mode") or cur_db_vis).strip().upper()
        cur_phase = str(settings.get("lifecycle_phase") or "BUILD").strip().upper()
        is_personal = (
            cur_ui_vis == "PRIVATE_USER"
            or personal_owner is not None
            or ws_slug.startswith("personal-")
        )

        if visibility_mode is not None:
            req_vis = visibility_mode.strip().upper()
            if is_personal and req_vis != "PRIVATE_USER":
                raise PrivateWorkspaceVisibilityLockedError(instance=instance)
            if not is_personal and req_vis == "PRIVATE_USER":
                raise PrivateWorkspaceVisibilityLockedError(instance=instance)
            next_ui_vis = req_vis
        else:
            next_ui_vis = "PRIVATE_USER" if is_personal else cur_ui_vis

        next_db_vis = (
            "CONFIDENTIAL_RESTRICTED"
            if next_ui_vis in ("CONFIDENTIAL_RESTRICTED", "PRIVATE_USER")
            else "STANDARD"
        )

        if name is not None:
            cleaned_name = name.strip()
            if not cleaned_name:
                raise ValidationDomainError(detail_code="ERR_WORKSPACE_EMPTY_NAME")
            next_name = cleaned_name[:255]
        else:
            next_name = cur_name

        if lifecycle_phase is not None:
            req_phase = lifecycle_phase.strip().upper()
            if req_phase not in ("BUILD", "RUN", "MIGRATION"):
                raise ValidationDomainError(detail_code="ERR_VALIDATION_FAILED", instance=instance)
            next_phase = req_phase
        else:
            next_phase = cur_phase if cur_phase in ("BUILD", "RUN", "MIGRATION") else "BUILD"

        settings["lifecycle_phase"] = next_phase
        settings["ui_visibility_mode"] = next_ui_vis
        await conn.execute(
            sa.text(
                """
                UPDATE workspaces
                SET name = :name,
                    visibility_mode = :vis,
                    settings_jsonb = CAST(:settings AS jsonb)
                WHERE id = :ws_id
                """
            ),
            {
                "ws_id": ws_uuid,
                "name": next_name,
                "vis": next_db_vis,
                "settings": json.dumps(settings, ensure_ascii=False, sort_keys=True),
            },
        )

        if next_db_vis == "CONFIDENTIAL_RESTRICTED":
            await ensure_user_workspace_membership(
                conn,
                workspace_uuid=ws_uuid,
                user_id=actor_user_id,
                fallback_role=actor_role,
            )

        await _sync_patched_workspace_platform_settings(
            conn,
            ws_id_str=str(ws_uuid),
            ws_slug=ws_slug,
            next_name=next_name,
            next_ui_vis=next_ui_vis,
            next_phase=next_phase,
        )

    return WorkspacePatchResult(
        id=str(ws_uuid),
        slug=ws_slug,
        name=next_name,
        owner_org_unit_id=owner_ou_id,
        owner_org_unit_name=owner_ou_name,
        visibility_mode=next_db_vis,
        ui_visibility_mode=next_ui_vis,
        lifecycle_phase=next_phase,
        finops_cost_usd=finops_cost,
        personal_owner_user_id=personal_owner,
    )


__all__ = ["WorkspacePatchResult", "patch_workspace_on_postgres18"]
