"""PostgreSQL 18 Relational Sync & Reconciliation for Platform Setup (`org_units` & `workspaces`).

Keeps relational tables (`org_units`, `workspaces`, `llm_model_endpoints`) strictly aligned with
`platform_settings` (`platform_setup_state_v1`), including hierarchy (`parent_id`,
`owner_org_unit_id`), deletion cleanup, and symmetric fallback hydration on load.
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

ROOT_ORG_UNIT_ID = UUID("0192c4e0-0000-7000-8000-000000000001")
_NAMESPACE_ORCIA_SETUP = UUID("0192c4e0-0000-7000-8000-000000000099")
_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9-]+")


def deterministic_setup_uuid(seed: str) -> UUID:
    """Return a deterministic UUIDv5 (or parsed UUID) for a setup entity key."""
    try:
        return UUID(seed)
    except (ValueError, TypeError):
        return uuid5(_NAMESPACE_ORCIA_SETUP, seed)


def normalize_setup_slug(raw: str, fallback: str) -> str:
    """Normalize an identifier into a URL-safe lowercase slug."""
    cleaned = _SLUG_CLEAN_RE.sub("-", raw.strip().lower()).strip("-")
    return (cleaned or fallback)[:120]


async def ensure_root_org_unit(conn: AsyncConnection) -> UUID:
    """Ensure the root `ENTERPRISE` organization unit exists and return its UUID."""
    row = (
        await conn.execute(
            sa.text(
                """
                INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """
            ),
            {"id": ROOT_ORG_UNIT_ID},
        )
    ).first()
    if row is not None and row[0] is not None:
        return UUID(str(row[0]))
    return ROOT_ORG_UNIT_ID


async def _purge_removed_org_units(
    conn: AsyncConnection,
    *,
    root_org_id: UUID,
    active_org_uuids: list[UUID],
) -> None:
    """Re-point foreign keys and delete `BU`/`TEAM` rows removed from the setup snapshot."""
    stale_rows = (
        await conn.execute(
            sa.text(
                """
                SELECT id FROM org_units
                WHERE unit_type IN ('BU', 'TEAM')
                """
            )
        )
    ).fetchall()
    active_set = set(active_org_uuids)
    stale_ids = [UUID(str(r[0])) for r in stale_rows if UUID(str(r[0])) not in active_set]
    if not stale_ids:
        return

    for stale_id in stale_ids:
        await conn.execute(
            sa.text("UPDATE org_units SET parent_id = :root_id WHERE parent_id = :stale_id"),
            {"root_id": root_org_id, "stale_id": stale_id},
        )
        await conn.execute(
            sa.text(
                "UPDATE users SET primary_org_unit_id = :root_id "
                "WHERE primary_org_unit_id = :stale_id"
            ),
            {"root_id": root_org_id, "stale_id": stale_id},
        )
        await conn.execute(
            sa.text(
                "UPDATE workspaces SET owner_org_unit_id = :root_id "
                "WHERE owner_org_unit_id = :stale_id"
            ),
            {"root_id": root_org_id, "stale_id": stale_id},
        )
        await conn.execute(
            sa.text(
                "UPDATE catalog_items SET owner_org_unit_id = :root_id "
                "WHERE owner_org_unit_id = :stale_id"
            ),
            {"root_id": root_org_id, "stale_id": stale_id},
        )
        await conn.execute(
            sa.text("DELETE FROM org_units WHERE id = :stale_id AND unit_type IN ('BU', 'TEAM')"),
            {"stale_id": stale_id},
        )


async def _purge_removed_workspaces(
    conn: AsyncConnection,
    *,
    active_ws_uuids: list[UUID],
) -> None:
    """Delete `workspaces` rows removed from the setup snapshot when not locked by snapshots."""
    existing_rows = (await conn.execute(sa.text("SELECT id FROM workspaces"))).fetchall()
    active_set = set(active_ws_uuids)
    stale_ids = [UUID(str(r[0])) for r in existing_rows if UUID(str(r[0])) not in active_set]
    for stale_ws_id in stale_ids:
        has_immutable_snapshot = (
            await conn.execute(
                sa.text(
                    "SELECT count(*) FROM blackboard_snapshots bs "
                    "JOIN workflow_runs wr ON wr.id = bs.run_id "
                    "WHERE wr.workspace_id = :ws_id"
                ),
                {"ws_id": stale_ws_id},
            )
        ).scalar_one()
        if int(has_immutable_snapshot or 0) == 0:
            await conn.execute(
                sa.text("DELETE FROM workspaces WHERE id = :ws_id"),
                {"ws_id": stale_ws_id},
            )


async def sync_relational_tables_on_postgres18(
    conn: AsyncConnection,
    *,
    org_units: list[dict[str, Any]],
    workspaces: list[dict[str, Any]],
    llm_tiers: list[dict[str, Any]],
) -> None:
    """Synchronize `org_units`, `workspaces`, and `llm_model_endpoints` with the setup snapshot."""
    root_org_id = await ensure_root_org_unit(conn)

    # 1. Synchronize org_units (BU first, then TEAM to preserve parent_id hierarchy)
    indexed_orgs = list(enumerate(org_units))
    indexed_orgs.sort(
        key=lambda pair: 0 if str(pair[1].get("level") or "BU").upper() != "TEAM" else 1
    )
    org_uuid_by_ref: dict[str, UUID] = {}
    org_name_by_ref: dict[str, str] = {}
    active_org_uuids: list[UUID] = []

    for idx, org in indexed_orgs:
        org_key = str(org.get("id") or f"org-{idx + 1}")
        org_uuid = deterministic_setup_uuid(f"org:{org_key}")
        name = str(org.get("name") or org_key).strip() or org_key
        slug = normalize_setup_slug(str(org.get("slug") or name), f"org-{idx + 1}")
        level = str(org.get("level") or "BU").upper()
        unit_type = "TEAM" if level == "TEAM" else "BU"
        raw_parent = str(org.get("parentId") or "").strip()
        resolved_parent_uuid = org_uuid_by_ref.get(raw_parent, root_org_id)

        row = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                    VALUES (:id, :slug, :name, :unit_type, :parent_id)
                    ON CONFLICT (slug) DO UPDATE
                    SET name = EXCLUDED.name,
                        unit_type = EXCLUDED.unit_type,
                        parent_id = EXCLUDED.parent_id
                    RETURNING id
                    """
                ),
                {
                    "id": org_uuid,
                    "slug": slug,
                    "name": name[:255],
                    "unit_type": unit_type,
                    "parent_id": resolved_parent_uuid,
                },
            )
        ).first()
        persisted_uuid = UUID(str(row[0])) if row is not None and row[0] is not None else org_uuid
        active_org_uuids.append(persisted_uuid)
        org_uuid_by_ref[org_key] = persisted_uuid
        org_uuid_by_ref[slug] = persisted_uuid
        org_name_by_ref[org_key] = name
        org_name_by_ref[slug] = name

    await _purge_removed_org_units(conn, root_org_id=root_org_id, active_org_uuids=active_org_uuids)

    # 2. Synchronize workspaces
    active_ws_uuids: list[UUID] = []
    for idx, ws in enumerate(workspaces):
        ws_key = str(ws.get("workspaceId") or ws.get("id") or f"ws-{idx + 1}")
        ws_uuid = deterministic_setup_uuid(f"ws:{ws_key}")
        name = str(ws.get("name") or ws_key).strip() or ws_key
        raw_slug = str(ws.get("slug") or name)
        slug = normalize_setup_slug(raw_slug, f"ws-{idx + 1}")
        vis_raw = str(ws.get("visibilityMode") or "STANDARD").upper()
        visibility_mode = (
            "CONFIDENTIAL_RESTRICTED" if vis_raw == "CONFIDENTIAL_RESTRICTED" else "STANDARD"
        )
        phase = str(ws.get("lifecyclePhase") or "BUILD").upper()
        owner_ref = str(ws.get("ownerOrgUnitId") or "").strip()
        owner_uuid = org_uuid_by_ref.get(owner_ref, root_org_id)
        owner_name = str(ws.get("ownerOrgUnitName") or "").strip() or org_name_by_ref.get(
            owner_ref, ""
        )
        settings_payload: dict[str, Any] = {
            "lifecycle_phase": phase,
            "ui_workspace_id": ws_key,
            "ui_visibility_mode": vis_raw,
        }
        if owner_ref:
            settings_payload["owner_org_unit_id"] = owner_ref
        if owner_name:
            settings_payload["owner_org_unit_name"] = owner_name
        settings_json = json.dumps(settings_payload, ensure_ascii=False)
        ws_row = (
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
                    ON CONFLICT (slug) DO UPDATE
                    SET name = EXCLUDED.name,
                        owner_org_unit_id = EXCLUDED.owner_org_unit_id,
                        visibility_mode = EXCLUDED.visibility_mode,
                        settings_jsonb = EXCLUDED.settings_jsonb
                    RETURNING id
                    """
                ),
                {
                    "id": ws_uuid,
                    "slug": slug,
                    "name": name[:255],
                    "owner_org_unit_id": owner_uuid,
                    "visibility_mode": visibility_mode,
                    "settings_jsonb": settings_json,
                },
            )
        ).first()
        persisted_ws_uuid = (
            UUID(str(ws_row[0])) if ws_row is not None and ws_row[0] is not None else ws_uuid
        )
        active_ws_uuids.append(persisted_ws_uuid)

    await _purge_removed_workspaces(conn, active_ws_uuids=active_ws_uuids)

    # 3. Synchronize llm_model_endpoints from llm_tiers
    for idx, tier_item in enumerate(llm_tiers):
        tier_name = str(tier_item.get("tier") or f"tier-{idx + 1}").strip().lower()
        primary_model = str(tier_item.get("primaryModel") or "model-primary").strip()
        model_family = str(tier_item.get("modelFamily") or "family-a").strip()
        endpoint_key = normalize_setup_slug(f"tier-{tier_name}-{primary_model}", f"tier-{idx + 1}")
        ep_uuid = deterministic_setup_uuid(f"llm-ep:{endpoint_key}")
        provider_slug = primary_model.split("/", 1)[0] if "/" in primary_model else "openai-compat"
        await conn.execute(
            sa.text(
                """
                INSERT INTO llm_model_endpoints (
                    id, endpoint_key, provider_slug, model_family, model_name,
                    endpoint_uri, connectivity_verified, is_active
                )
                VALUES (
                    :id, :endpoint_key, :provider_slug, :model_family, :model_name,
                    :endpoint_uri, TRUE, TRUE
                )
                ON CONFLICT (endpoint_key) DO UPDATE
                SET model_family = EXCLUDED.model_family,
                    model_name = EXCLUDED.model_name,
                    is_active = TRUE
                """
            ),
            {
                "id": ep_uuid,
                "endpoint_key": endpoint_key[:128],
                "provider_slug": provider_slug[:64] or "local",
                "model_family": model_family[:64] or "family-a",
                "model_name": primary_model[:128] or "default-model",
                "endpoint_uri": f"https://llm.orcia.local/{endpoint_key}",
            },
        )
