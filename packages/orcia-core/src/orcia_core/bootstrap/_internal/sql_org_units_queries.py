"""PostgreSQL 18 query & mapping helpers for organizational units (`Story 17.2`).

Encapsulates single-query hierarchy loading (`LEFT JOIN` with `jsonb_agg` on workspaces,
zero `N+1`), member JSONB parsing, node resolution, and `platform_settings` synchronization.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.bootstrap._internal.sql_iam_account_helpers import ensure_iam_accounts_schema
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.models import OrgUnitNode, OrgUnitType
from orcia_core.permissions.org_hierarchy import (
    AttachedWorkspaceRef,
    OrgUnitSummary,
    build_org_unit_summary,
    normalize_member_user_ids,
    sort_org_unit_summaries_dfs,
)
from orcia_core.permissions.org_user_validation import KnownOrgUser


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


async def load_all_nodes_and_workspaces(
    conn: AsyncConnection,
) -> tuple[
    dict[str, OrgUnitNode],
    dict[str, int],
    dict[str, tuple[AttachedWorkspaceRef, ...]],
]:
    """Load all `org_units` and their attached workspaces in a single query (zero N+1)."""
    rows = (
        await conn.execute(
            sa.text(
                """
                SELECT o.id, o.slug, o.name, o.unit_type, o.parent_id,
                       o.billing_enabled, o.lead_user_id, o.member_user_ids_jsonb,
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
        )
        nodes_by_id[uid] = node
        ws_counts[uid] = int(row[8] or 0)
        ws_refs_by_owner[uid] = parse_attached_workspaces_jsonb(row[9])
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


async def load_known_org_users_from_postgres18(
    conn: AsyncConnection,
) -> list[KnownOrgUser]:
    """Load active known human accounts from `iam_accounts` and `users` (single query, zero N+1)."""
    await ensure_iam_accounts_schema(conn)
    rows = (
        await conn.execute(
            sa.text(
                """
                SELECT principal_id, display_name, email
                FROM iam_accounts
                WHERE account_kind = 'HUMAN' AND status <> 'DISABLED'
                UNION ALL
                SELECT email AS principal_id, display_name, email
                FROM users
                WHERE is_active = TRUE
                """
            )
        )
    ).fetchall()

    users_by_key: dict[str, KnownOrgUser] = {}
    for row in rows:
        principal_id = str(row[0] or "").strip()
        if not principal_id:
            continue
        display_name = str(row[1] or "").strip() or principal_id
        email = str(row[2] or "").strip() if row[2] else None
        canon_key = principal_id.lower()
        alt_key = email.lower() if email else None

        existing = users_by_key.get(canon_key) or (users_by_key.get(alt_key) if alt_key else None)
        if existing is not None:
            merged_email = existing.email or email
            merged_display = (
                existing.display_name
                if existing.display_name != existing.principal_id
                else display_name
            )
            merged = KnownOrgUser(
                principal_id=existing.principal_id,
                display_name=merged_display,
                email=merged_email,
            )
            users_by_key[existing.principal_id.lower()] = merged
            if merged_email:
                users_by_key[merged_email.lower()] = merged
        else:
            created = KnownOrgUser(
                principal_id=principal_id,
                display_name=display_name,
                email=email,
            )
            users_by_key[canon_key] = created
            if alt_key:
                users_by_key[alt_key] = created

    unique_users = {id(u): u for u in users_by_key.values()}.values()
    return sorted(unique_users, key=lambda u: (u.display_name.lower(), u.principal_id.lower()))


__all__ = [
    "build_sorted_summaries",
    "load_all_nodes_and_workspaces",
    "load_known_org_users_from_postgres18",
    "parse_attached_workspaces_jsonb",
    "parse_member_ids_jsonb",
    "resolve_target_node",
    "sync_platform_settings_org_units_if_present",
]
