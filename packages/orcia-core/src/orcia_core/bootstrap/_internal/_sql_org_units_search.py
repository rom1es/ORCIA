"""Filtered PostgreSQL 18 org_units search query helper."""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.permissions.org_hierarchy import OrgUnitKind, OrgUnitSummary


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
    from orcia_core.bootstrap._internal.sql_org_units_queries import (
        ensure_org_units_schema,
        parse_attached_workspaces_jsonb,
        parse_member_ids_jsonb,
    )

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


__all__ = [
    "escape_like_pattern",
    "query_filtered_org_unit_summaries",
    "sync_platform_settings_org_units_if_present",
]
