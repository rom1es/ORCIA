"""PostgreSQL 18 query & mapping helpers for organizational units (`Story 17.2`).

Encapsulates single-query hierarchy loading (`LEFT JOIN` with `jsonb_agg` on workspaces,
zero `N+1`), member JSONB parsing, node resolution, and `platform_settings` synchronization.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.bootstrap._internal.sql_org_known_users import (
    load_known_org_users_from_postgres18,
)
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.models import OrgUnitNode, OrgUnitType
from orcia_core.permissions.org_hierarchy import (
    AttachedWorkspaceRef,
    OrgUnitKind,
    OrgUnitSummary,
    build_org_unit_summary,
    normalize_member_user_ids,
    sort_org_unit_summaries_dfs,
)
from orcia_kernel.ids import new_uuid7


def parse_member_ids_jsonb(raw: object) -> tuple[str, ...]:
    """Parse JSONB member user IDs into deduplicated tuple."""
    if isinstance(raw, list):
        return normalize_member_user_ids([str(x) for x in raw])
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except ValueError:
            return ()
        if isinstance(decoded, list):
            return normalize_member_user_ids([str(x) for x in decoded])
    return ()


def parse_attached_workspaces_jsonb(raw: object) -> tuple[AttachedWorkspaceRef, ...]:
    """Parse aggregated JSONB workspace array into tuple of AttachedWorkspaceRef."""
    items: list[object] = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                items = decoded
        except ValueError:
            items = []
    refs: list[AttachedWorkspaceRef] = []
    for item in items:
        if isinstance(item, dict):
            refs.append(
                AttachedWorkspaceRef(
                    id=str(item.get("id") or ""),
                    slug=str(item.get("slug") or ""),
                    name=str(item.get("name") or ""),
                )
            )
    return tuple(refs)


async def ensure_org_units_schema(conn: AsyncConnection) -> None:
    """Ensure `lead_user_ids_jsonb` & `ontology_lead_user_ids_jsonb` exist idempotently."""
    reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if reg is None:
        return
    await conn.execute(
        sa.text(
            """
            ALTER TABLE org_units
                ADD COLUMN IF NOT EXISTS lead_user_ids_jsonb
                JSONB NOT NULL DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS ontology_lead_user_ids_jsonb
                JSONB NOT NULL DEFAULT '[]'::jsonb;
            """
        )
    )


async def load_all_nodes_and_workspaces(
    conn: AsyncConnection,
) -> tuple[
    dict[str, OrgUnitNode],
    dict[str, int],
    dict[str, tuple[AttachedWorkspaceRef, ...]],
]:
    """Load all `org_units` and their attached workspaces in a single query (zero N+1)."""
    await ensure_org_units_schema(conn)
    rows = (
        await conn.execute(
            sa.text(
                """
                SELECT o.id, o.slug, o.name, o.unit_type, o.parent_id,
                       o.billing_enabled, o.lead_user_id, o.member_user_ids_jsonb,
                       o.lead_user_ids_jsonb, o.ontology_lead_user_ids_jsonb,
                       COALESCE(ws.ws_cnt, 0) AS attached_ws_cnt,
                       COALESCE(ws.attached_ws_json, '[]'::jsonb) AS attached_ws_json
                FROM org_units o
                LEFT JOIN (
                    SELECT owner_org_unit_id,
                           COUNT(*) AS ws_cnt,
                           COALESCE(
                               jsonb_agg(
                                   jsonb_build_object('id', id::text, 'slug', slug, 'name', name)
                                   ORDER BY name ASC, slug ASC
                               ),
                               '[]'::jsonb
                           ) AS attached_ws_json
                    FROM workspaces
                    GROUP BY owner_org_unit_id
                ) ws ON ws.owner_org_unit_id = o.id
                ORDER BY o.created_at ASC, o.slug ASC
                """
            )
        )
    ).fetchall()
    nodes_by_id: dict[str, OrgUnitNode] = {}
    ws_counts: dict[str, int] = {}
    ws_refs_by_owner: dict[str, tuple[AttachedWorkspaceRef, ...]] = {}
    for row in rows:
        uid = str(row[0])
        parent_str = str(row[4]) if row[4] is not None else None
        node = OrgUnitNode(
            id=uid,
            slug=str(row[1]),
            name=str(row[2]),
            unit_type=cast(OrgUnitType, str(row[3]).upper()),
            parent_id=parent_str,
            billing_enabled=bool(row[5]) if row[5] is not None else True,
            lead_user_id=str(row[6]).strip() if row[6] else None,
            member_user_ids=parse_member_ids_jsonb(row[7]),
            lead_user_ids=parse_member_ids_jsonb(row[8]),
            ontology_lead_user_ids=parse_member_ids_jsonb(row[9]),
        )
        nodes_by_id[uid] = node
        ws_counts[uid] = int(row[10] or 0)
        ws_refs_by_owner[uid] = parse_attached_workspaces_jsonb(row[11])
    return nodes_by_id, ws_counts, ws_refs_by_owner


def build_sorted_summaries(
    nodes_by_id: dict[str, OrgUnitNode],
    ws_counts: dict[str, int],
    ws_refs_by_owner: dict[str, tuple[AttachedWorkspaceRef, ...]],
) -> list[OrgUnitSummary]:
    """Project nodes into DFS-ordered `OrgUnitSummary` items with attached workspaces."""
    items = [
        build_org_unit_summary(
            node,
            nodes_by_id,
            attached_workspaces_count=ws_counts.get(node.id, 0),
            attached_workspaces=ws_refs_by_owner.get(node.id, ()),
        )
        for node in nodes_by_id.values()
        if node.unit_type != "ENTERPRISE"
    ]
    return sort_org_unit_summaries_dfs(items)


def resolve_target_node(
    nodes_by_id: dict[str, OrgUnitNode],
    org_unit_id_or_slug: str,
) -> OrgUnitNode:
    """Find active non-enterprise node by ID or slug or raise `ResourceNotFoundError`."""
    cleaned = org_unit_id_or_slug.strip()
    target = nodes_by_id.get(cleaned)
    if target is None:
        target = next(
            (u for u in nodes_by_id.values() if u.slug == cleaned and u.unit_type != "ENTERPRISE"),
            None,
        )
    if target is None or target.unit_type == "ENTERPRISE":
        raise ResourceNotFoundError(
            detail_override=f"Unité organisationnelle introuvable : '{cleaned}'."
        )
    return target


async def reassign_users_primary_org_unit_before_delete(
    conn: AsyncConnection, target_uuid: UUID, target_parent_id: str | None
) -> None:
    """Reassign users referencing a deleted org unit to parent or enterprise root."""
    fallback_id: UUID | None = None
    if target_parent_id:
        try:
            fallback_id = UUID(target_parent_id)
        except (ValueError, TypeError):
            fallback_id = None
    if fallback_id is None:
        root_res = await conn.execute(
            sa.text(
                """
                SELECT id FROM org_units WHERE id <> :id
                ORDER BY
                    CASE
                        WHEN unit_type = 'ENTERPRISE' THEN 0
                        WHEN unit_type = 'BU' THEN 1
                        ELSE 2
                    END,
                    created_at ASC
                LIMIT 1
                """
            ),
            {"id": target_uuid},
        )
        fallback_id = root_res.scalar()
    if fallback_id is None:
        ref_cnt = (
            await conn.execute(
                sa.text("SELECT COUNT(*) FROM users WHERE primary_org_unit_id = :id"),
                {"id": target_uuid},
            )
        ).scalar_one()
        if int(ref_cnt) > 0:
            ent_id = new_uuid7()
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type, billing_enabled, created_at)
                    VALUES (:id, 'global', 'Plateforme Globale ORCIA', 'ENTERPRISE', TRUE, NOW())
                    ON CONFLICT (slug) DO NOTHING
                    """
                ),
                {"id": ent_id},
            )
            ent_row = (
                await conn.execute(
                    sa.text("SELECT id FROM org_units WHERE slug = 'global' LIMIT 1")
                )
            ).first()
            if ent_row is not None and ent_row[0] is not None:
                fallback_id = ent_row[0]
    if fallback_id is not None:
        await conn.execute(
            sa.text(
                "UPDATE users SET primary_org_unit_id = :fallback_id "
                "WHERE primary_org_unit_id = :target_id"
            ),
            {"fallback_id": fallback_id, "target_id": target_uuid},
        )


async def sync_platform_settings_org_units_if_present(
    conn: AsyncConnection,
    summaries: Sequence[OrgUnitSummary],
) -> None:
    """Keep `platform_settings` (`platform_setup_state_v1`) aligned when present in DB."""
    serialized = [
        {
            "id": item.id,
            "name": item.name,
            "slug": item.slug,
            "level": item.kind,
            "parentId": item.parent_id or "scope-global",
            "billingEnabled": item.billing_enabled,
            **({"leadUserId": item.lead_user_id} if item.lead_user_id else {}),
            **({"leadUserIds": list(item.lead_user_ids)} if item.lead_user_ids else {}),
            **(
                {"ontologyLeadUserIds": list(item.ontology_lead_user_ids)}
                if item.ontology_lead_user_ids
                else {}
            ),
            **({"memberUserIds": list(item.member_user_ids)} if item.member_user_ids else {}),
        }
        for item in summaries
    ]
    await conn.execute(
        sa.text(
            """
            UPDATE platform_settings
            SET value_jsonb = jsonb_set(
                    value_jsonb,
                    '{org_units}',
                    CAST(:org_units_json AS jsonb),
                    true
                ),
                version = version + 1,
                updated_at = NOW()
            WHERE scope_level = 'GLOBAL'
              AND category = 'iam'
              AND key = 'platform_setup_state_v1'
            """
        ),
        {"org_units_json": json.dumps(serialized, ensure_ascii=False)},
    )


def escape_like_pattern(raw: str) -> str:
    """Escape `%`, `_`, and `\\` for SQL ILIKE with ESCAPE '\\\\'."""
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def query_filtered_org_unit_summaries(
    conn: AsyncConnection,
    *,
    q: str | None = None,
    kind: OrgUnitKind | None = None,
    limit: int | None = None,
) -> list[OrgUnitSummary]:
    """Execute single-query filtered search on PostgreSQL 18 with deterministic ordering."""
    where_clauses = ["o.unit_type != 'ENTERPRISE'"]
    params: dict[str, object] = {}

    if kind is not None:
        where_clauses.append("o.unit_type = :kind")
        params["kind"] = kind

    if q is not None and q.strip():
        where_clauses.append(
            "(o.name ILIKE :q_pattern ESCAPE '\\' OR o.slug ILIKE :q_pattern ESCAPE '\\')"
        )
        params["q_pattern"] = f"%{escape_like_pattern(q.strip())}%"

    where_sql = " AND ".join(where_clauses)
    limit_sql = " LIMIT :limit" if limit is not None else ""
    if limit is not None:
        params["limit"] = limit

    await ensure_org_units_schema(conn)
    query = sa.text(
        f"""
        SELECT o.id, o.slug, o.name, o.unit_type,
               CASE WHEN p.unit_type = 'ENTERPRISE' THEN NULL ELSE o.parent_id END AS parent_id,
               o.billing_enabled, o.lead_user_id, o.member_user_ids_jsonb,
               o.lead_user_ids_jsonb, o.ontology_lead_user_ids_jsonb,
               COALESCE(ws.ws_cnt, 0) AS attached_ws_cnt,
               COALESCE(ws.attached_ws_json, '[]'::jsonb) AS attached_ws_json
        FROM org_units o
        LEFT JOIN org_units p ON p.id = o.parent_id
        LEFT JOIN (
            SELECT owner_org_unit_id,
                   COUNT(*) AS ws_cnt,
                   COALESCE(
                       jsonb_agg(
                           jsonb_build_object('id', id::text, 'slug', slug, 'name', name)
                           ORDER BY name ASC, slug ASC
                       ),
                       '[]'::jsonb
                   ) AS attached_ws_json
            FROM workspaces
            GROUP BY owner_org_unit_id
        ) ws ON ws.owner_org_unit_id = o.id
        WHERE {where_sql}
        ORDER BY o.unit_type ASC, o.name ASC, o.slug ASC
        {limit_sql}
        """
    )
    rows = (await conn.execute(query, params)).fetchall()
    summaries: list[OrgUnitSummary] = []
    for row in rows:
        unit_type = str(row[3]).upper()
        summaries.append(
            OrgUnitSummary(
                id=str(row[0]),
                slug=str(row[1]),
                name=str(row[2]),
                kind="BU" if unit_type in ("BU", "TRIBE") else "TEAM",
                parent_id=str(row[4]) if row[4] is not None else None,
                billing_enabled=bool(row[5]) if row[5] is not None else True,
                lead_user_id=str(row[6]).strip() if row[6] else None,
                member_user_ids=parse_member_ids_jsonb(row[7]),
                attached_workspaces_count=int(row[10] or 0),
                attached_workspaces=parse_attached_workspaces_jsonb(row[11]),
                lead_user_ids=parse_member_ids_jsonb(row[8]),
                ontology_lead_user_ids=parse_member_ids_jsonb(row[9]),
            )
        )
    return summaries


__all__ = [
    "build_sorted_summaries",
    "ensure_org_units_schema",
    "escape_like_pattern",
    "load_all_nodes_and_workspaces",
    "load_known_org_users_from_postgres18",
    "parse_attached_workspaces_jsonb",
    "parse_member_ids_jsonb",
    "query_filtered_org_unit_summaries",
    "reassign_users_primary_org_unit_before_delete",
    "resolve_target_node",
    "sync_platform_settings_org_units_if_present",
]
