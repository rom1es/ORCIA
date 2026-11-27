"""PG18 SQL Queries & Pack Activation Priority Loaders for Agents & Skills (`Story 31.3`)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.domain.namespacing import ResolutionTier
from orcia_kernel.ids import new_uuid7_str

SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS = sa.text(
    """
    SELECT ci.resource_id, ci.uri, ci.title, ci.description, ci.resource_type, ci.version,
           ci.sha256, ci.item_type, ci.metadata_jsonb, ci.owner_workspace_id::text,
           dpb.slug AS pack_slug, dpb.bundle_kind AS pack_bundle_kind,
           ci.pack_bundle_id::text, dpb.scope_type, dpb.scope_id
    FROM catalog_items ci
    LEFT JOIN declarative_pack_bundles dpb ON dpb.id = ci.pack_bundle_id
    WHERE ci.item_type IN ('USER_SKILL', 'USER_AGENT')
    ORDER BY ci.created_at ASC, ci.resource_id ASC
    """
)


async def load_workspace_scope_context_pg(
    conn: AsyncConnection,
    workspace_id: str | None,
) -> tuple[str | None, frozenset[str]]:
    """Resolve `(workspace_uuid, ancestor_org_unit_ids)` for `workspace_id`, if present."""
    if not workspace_id or not workspace_id.strip():
        return None, frozenset()
    clean = workspace_id.strip().removeprefix("scope-ws-").strip()
    reg_ws = (await conn.execute(sa.text("SELECT to_regclass('public.workspaces')"))).scalar()
    if reg_ws is None:
        return clean, frozenset()
    ws_row = (
        await conn.execute(
            sa.text(
                "SELECT id::text, owner_org_unit_id::text FROM workspaces "
                "WHERE id::text = :ws OR LOWER(slug) = LOWER(:ws) LIMIT 1"
            ),
            {"ws": clean},
        )
    ).first()
    if ws_row is None:
        return clean, frozenset()
    ws_uuid = str(ws_row[0])
    org_id = str(ws_row[1]) if ws_row[1] is not None else None
    if not org_id:
        return ws_uuid, frozenset()
    reg_ou = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if reg_ou is None:
        return ws_uuid, frozenset({org_id})
    anc_rows = (
        await conn.execute(
            sa.text(
                """
                WITH RECURSIVE anc AS (
                    SELECT id, parent_id, 0 AS depth FROM org_units WHERE id::text = :org_id
                    UNION ALL
                    SELECT ou.id, ou.parent_id, anc.depth + 1
                    FROM org_units ou JOIN anc ON ou.id = anc.parent_id
                    WHERE anc.depth < 8
                )
                SELECT id::text FROM anc
                """
            ),
            {"org_id": org_id},
        )
    ).scalars()
    ancestors = frozenset(str(r) for r in anc_rows) or frozenset({org_id})
    return ws_uuid, ancestors


async def load_workspace_pack_priorities_pg(
    conn: AsyncConnection,
    workspace_id: str | None,
) -> tuple[dict[str, int], set[str]]:
    """Return `(active_priorities_by_slug, inactive_pack_slugs)` for a workspace."""
    if not workspace_id or not workspace_id.strip():
        return {}, set()
    reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.workspace_pack_activations')"))
    ).scalar()
    if reg is None:
        return {}, set()
    clean_ws = workspace_id.strip().removeprefix("scope-ws-").strip()
    rows = (
        await conn.execute(
            sa.text(
                """
                SELECT wpa.pack_slug, wpa.priority_order, wpa.is_active
                FROM workspace_pack_activations wpa
                LEFT JOIN workspaces w ON w.id = wpa.workspace_id
                WHERE wpa.workspace_id::text = :ws OR LOWER(w.slug) = LOWER(:ws)
                ORDER BY wpa.priority_order ASC NULLS LAST, wpa.pack_slug ASC
                """
            ),
            {"ws": clean_ws},
        )
    ).fetchall()
    priorities: dict[str, int] = {}
    inactive: set[str] = set()
    for row in rows:
        slug = str(row[0]).strip().lower()
        prio = int(row[1]) if row[1] is not None else 9999
        is_active = bool(row[2])
        if is_active:
            priorities[slug] = prio
        else:
            inactive.add(slug)
    return priorities, inactive


def resolve_pack_tier_for_row(
    *,
    pack_slug: str | None,
    bundle_kind: str | None,
    active_priorities: dict[str, int],
    workspace_scoped: bool = False,
) -> ResolutionTier | None:
    """Determine `WORKSPACE_PACK` vs `SYSTEM_PACK` for a joined pack row."""
    if not pack_slug:
        return None
    norm = pack_slug.strip().lower()
    if norm in active_priorities:
        return "WORKSPACE_PACK"
    if (bundle_kind or "").strip().upper() == "SYSTEM":
        return "SYSTEM_PACK"
    if workspace_scoped:
        return None
    return "WORKSPACE_PACK"


def is_pack_bundle_visible_in_scope(
    *,
    scope_type: str | None,
    scope_id: str | None,
    ws_uuid: str | None,
    ancestor_org_unit_ids: frozenset[str],
) -> bool:
    """Check whether a pack bundle `(scope_type, scope_id)` is visible in `ws_uuid`."""
    if scope_type is None:
        return True
    st = scope_type.strip().upper()
    sid = (scope_id or "").strip()
    if st == "GLOBAL":
        return True
    if st == "WORKSPACE":
        return ws_uuid is not None and sid == ws_uuid
    if st in ("BU", "TEAM"):
        return bool(sid and sid in ancestor_org_unit_ids)
    return False


def should_include_catalog_row(
    *,
    workspace_id: str | None,
    ws_uuid: str | None,
    ancestor_orgs: frozenset[str],
    effective_owner_ws: str | None,
    pack_bundle_id: str | None,
    pack_slug: str | None,
    bundle_kind: str | None,
    bundle_scope_type: str | None,
    bundle_scope_id: str | None,
    active_priorities: dict[str, int],
    unrestricted: bool,
    allowed_workspace_ids: frozenset[str] | None,
    allowed_org_ids: frozenset[str] | None,
) -> bool:
    """Filter standalone and pack-backed `catalog_items` rows by workspace/caller scope."""
    is_pack = bool(pack_bundle_id or pack_slug)
    if workspace_id and workspace_id.strip():
        clean_raw = workspace_id.strip().removeprefix("scope-ws-").strip()
        if not is_pack:
            allowed = {x for x in (ws_uuid, clean_raw) if x}
            return effective_owner_ws is None or effective_owner_ws in allowed
        if not is_pack_bundle_visible_in_scope(
            scope_type=bundle_scope_type,
            scope_id=bundle_scope_id,
            ws_uuid=ws_uuid,
            ancestor_org_unit_ids=ancestor_orgs,
        ):
            return False
        if (bundle_kind or "").strip().upper() == "SYSTEM":
            return True
        return bool(pack_slug and pack_slug in active_priorities)

    if unrestricted:
        return True
    ws_set = allowed_workspace_ids or frozenset()
    org_set = allowed_org_ids or frozenset()
    if not is_pack:
        return effective_owner_ws is None or effective_owner_ws in ws_set
    if (bundle_kind or "").strip().upper() == "SYSTEM" or (
        bundle_scope_type or "GLOBAL"
    ).strip().upper() == "GLOBAL":
        return True
    st = (bundle_scope_type or "").strip().upper()
    sid = (bundle_scope_id or "").strip()
    if st == "WORKSPACE":
        return sid in ws_set
    if st in ("BU", "TEAM"):
        return sid in org_set
    return False


async def ensure_root_org_unit_id(conn: AsyncConnection) -> UUID:
    """Return an existing root `org_units.id` or create `orcia-root` idempotently."""
    sql = (
        "SELECT id FROM org_units "
        "ORDER BY (CASE WHEN slug = 'orcia-root' THEN 0 ELSE 1 END), created_at ASC LIMIT 1"
    )
    existing = (await conn.execute(sa.text(sql))).first()
    if existing is not None:
        return UUID(str(existing[0]))
    row = await conn.execute(
        sa.text(
            "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
            "VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id"
        ),
        {"id": UUID(new_uuid7_str())},
    )
    return UUID(str(row.scalar_one()))


def optional_uuid(raw_id: str | None) -> UUID | None:
    if not raw_id:
        return None
    try:
        return UUID(str(raw_id).strip())
    except (ValueError, TypeError):
        return None


def unpack_scoped_catalog_row(
    row: Any,
    *,
    workspace_id: str | None,
    ws_uuid: str | None,
    ancestor_orgs: frozenset[str],
    active_priorities: dict[str, int],
    unrestricted: bool,
    allowed_workspace_ids: frozenset[str] | None,
    allowed_org_ids: frozenset[str] | None,
) -> dict[str, Any] | None:
    """Unpack and scope-filter one joined `catalog_items` row (`None` if excluded)."""
    col_ws = str(row[9]) if len(row) > 9 and row[9] is not None else None
    pack_slug = str(row[10]).strip().lower() if len(row) > 10 and row[10] else None
    bundle_kind = str(row[11]).strip().upper() if len(row) > 11 and row[11] else None
    pack_bundle_id = str(row[12]) if len(row) > 12 and row[12] is not None else None
    b_scope_type = str(row[13]).strip().upper() if len(row) > 13 and row[13] else None
    b_scope_id = str(row[14]).strip() if len(row) > 14 and row[14] else None
    raw_meta = row[8]
    meta = raw_meta if isinstance(raw_meta, dict) else json.loads(str(raw_meta or "{}"))
    eff_owner_ws = col_ws or (
        str(meta.get("owner_workspace_id")).strip() if meta.get("owner_workspace_id") else None
    )
    if not should_include_catalog_row(
        workspace_id=workspace_id,
        ws_uuid=ws_uuid,
        ancestor_orgs=ancestor_orgs,
        effective_owner_ws=eff_owner_ws,
        pack_bundle_id=pack_bundle_id,
        pack_slug=pack_slug,
        bundle_kind=bundle_kind,
        bundle_scope_type=b_scope_type,
        bundle_scope_id=b_scope_id,
        active_priorities=active_priorities,
        unrestricted=unrestricted,
        allowed_workspace_ids=allowed_workspace_ids,
        allowed_org_ids=allowed_org_ids,
    ):
        return None
    return {
        "meta": meta,
        "col_ws": col_ws,
        "pack_slug": pack_slug,
        "bundle_kind": bundle_kind,
    }


__all__ = [
    "SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS",
    "ensure_root_org_unit_id",
    "is_pack_bundle_visible_in_scope",
    "load_workspace_pack_priorities_pg",
    "load_workspace_scope_context_pg",
    "optional_uuid",
    "resolve_pack_tier_for_row",
    "should_include_catalog_row",
    "unpack_scoped_catalog_row",
]
