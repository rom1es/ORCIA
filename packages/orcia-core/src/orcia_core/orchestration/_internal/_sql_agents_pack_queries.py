"""PG18 SQL Queries & Pack Activation Priority Loaders for Agents & Skills (`Story 31.3`)."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.domain.namespacing import ResolutionTier
from orcia_kernel.ids import new_uuid7_str

SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS = sa.text(
    """
    SELECT ci.resource_id, ci.uri, ci.title, ci.description, ci.resource_type, ci.version,
           ci.sha256, ci.item_type, ci.metadata_jsonb, ci.owner_workspace_id,
           dpb.slug AS pack_slug, dpb.bundle_kind AS pack_bundle_kind
    FROM catalog_items ci
    LEFT JOIN declarative_pack_bundles dpb ON dpb.id = ci.pack_bundle_id
    WHERE ci.item_type IN ('USER_SKILL', 'USER_AGENT')
    ORDER BY ci.created_at ASC, ci.resource_id ASC
    """
)


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
    clean_ws = workspace_id.strip()
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
) -> ResolutionTier | None:
    """Determine `WORKSPACE_PACK` vs `SYSTEM_PACK` for a joined pack row."""
    if not pack_slug:
        return None
    norm = pack_slug.strip().lower()
    if norm in active_priorities:
        return "WORKSPACE_PACK"
    if (bundle_kind or "").strip().upper() == "SYSTEM":
        return "SYSTEM_PACK"
    return "WORKSPACE_PACK"


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


__all__ = [
    "SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS",
    "ensure_root_org_unit_id",
    "load_workspace_pack_priorities_pg",
    "optional_uuid",
    "resolve_pack_tier_for_row",
]
