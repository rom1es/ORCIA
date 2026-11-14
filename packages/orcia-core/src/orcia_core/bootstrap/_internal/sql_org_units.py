"""PostgreSQL 18 persistence adapter for multi-level `org_units` CRUD (Story 17.2).

Single-query hierarchy loading (`LEFT JOIN` workspace aggregation, zero `N+1`), transactional
cycle/parent-kind validation (`HTTP 422`), non-empty deletion guard (`HTTP 409`), and atomic
synchronization with `platform_settings` (`platform_setup_state_v1`) when present.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.models import OrgUnitNode, OrgUnitType
from orcia_core.permissions.org_hierarchy import (
    OrgUnitKind,
    OrgUnitSummary,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    normalize_member_user_ids,
    normalize_org_unit_slug,
    sort_org_unit_summaries_dfs,
    validate_org_unit_hierarchy,
)


def _parse_member_ids_jsonb(raw: object) -> tuple[str, ...]:
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


async def _load_all_nodes_and_ws_counts(
    conn: AsyncConnection,
) -> tuple[dict[str, OrgUnitNode], dict[str, int]]:
    rows = (
        await conn.execute(
            sa.text(
                """
                SELECT o.id, o.slug, o.name, o.unit_type, o.parent_id,
                       o.billing_enabled, o.lead_user_id, o.member_user_ids_jsonb,
                       COALESCE(ws.ws_cnt, 0) AS attached_ws_cnt
                FROM org_units o
                LEFT JOIN (
                    SELECT owner_org_unit_id, COUNT(*) AS ws_cnt
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
            member_user_ids=_parse_member_ids_jsonb(row[7]),
        )
        nodes_by_id[uid] = node
        ws_counts[uid] = int(row[8] or 0)
    return nodes_by_id, ws_counts


async def _sync_platform_settings_org_units_if_present(
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


def _build_sorted_summaries(
    nodes_by_id: dict[str, OrgUnitNode],
    ws_counts: dict[str, int],
) -> list[OrgUnitSummary]:
    items = [
        build_org_unit_summary(
            node,
            nodes_by_id,
            attached_workspaces_count=ws_counts.get(node.id, 0),
        )
        for node in nodes_by_id.values()
        if node.unit_type != "ENTERPRISE"
    ]
    return sort_org_unit_summaries_dfs(items)


def _resolve_target_node(
    nodes_by_id: dict[str, OrgUnitNode],
    org_unit_id_or_slug: str,
) -> OrgUnitNode:
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


async def list_org_units_from_postgres18(engine: AsyncEngine) -> list[OrgUnitSummary]:
    """Return all non-enterprise `OrgUnitSummary` items ordered in DFS tree order."""
    async with engine.connect() as conn:
        nodes_by_id, ws_counts = await _load_all_nodes_and_ws_counts(conn)
    return _build_sorted_summaries(nodes_by_id, ws_counts)


async def create_org_unit_on_postgres18(
    engine: AsyncEngine,
    *,
    name: str,
    kind: OrgUnitKind,
    slug: str | None = None,
    parent_id: str | None = None,
    billing_enabled: bool = True,
    lead_user_id: str | None = None,
    member_user_ids: Sequence[str] | None = None,
) -> OrgUnitSummary:
    """Create a `BU` or `TEAM` on PostgreSQL 18 with hierarchy validation (`UUIDv7`)."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValidationDomainError(detail_override="Le nom de l'unité ne peut pas être vide.")
    normalized_slug = normalize_org_unit_slug(slug, cleaned_name)
    normalized_lead = (lead_user_id or "").strip() or None
    normalized_members = normalize_member_user_ids(member_user_ids)

    async with engine.begin() as conn:
        nodes_by_id, ws_counts = await _load_all_nodes_and_ws_counts(conn)
        assert_unique_org_unit_slug(normalized_slug, nodes_by_id)
        resolved_parent_id = validate_org_unit_hierarchy(
            unit_id=None,
            kind=kind,
            parent_id=parent_id,
            units_by_id=nodes_by_id,
        )
        new_id = generate_new_org_unit_id()
        await conn.execute(
            sa.text(
                """
                INSERT INTO org_units (
                    id, slug, name, unit_type, parent_id,
                    billing_enabled, lead_user_id, member_user_ids_jsonb
                )
                VALUES (
                    :id, :slug, :name, :unit_type, :parent_id,
                    :billing_enabled, :lead_user_id, CAST(:member_user_ids_jsonb AS jsonb)
                )
                """
            ),
            {
                "id": UUID(new_id),
                "slug": normalized_slug,
                "name": cleaned_name,
                "unit_type": kind,
                "parent_id": UUID(resolved_parent_id) if resolved_parent_id else None,
                "billing_enabled": billing_enabled,
                "lead_user_id": normalized_lead,
                "member_user_ids_jsonb": json.dumps(list(normalized_members)),
            },
        )
        new_node = OrgUnitNode(
            id=new_id,
            slug=normalized_slug,
            name=cleaned_name,
            unit_type=kind,
            parent_id=resolved_parent_id,
            billing_enabled=billing_enabled,
            lead_user_id=normalized_lead,
            member_user_ids=normalized_members,
        )
        nodes_by_id[new_id] = new_node
        ws_counts[new_id] = 0
        summaries = _build_sorted_summaries(nodes_by_id, ws_counts)
        await _sync_platform_settings_org_units_if_present(conn, summaries)

    return build_org_unit_summary(new_node, nodes_by_id, attached_workspaces_count=0)


async def update_org_unit_on_postgres18(
    engine: AsyncEngine,
    *,
    org_unit_id: str,
    name: str | None = None,
    parent_id: str | None = None,
    parent_id_provided: bool = False,
    billing_enabled: bool | None = None,
    lead_user_id: str | None = None,
    lead_user_id_provided: bool = False,
    member_user_ids: Sequence[str] | None = None,
) -> OrgUnitSummary:
    """Update name, parent_id, billing_enabled, lead_user_id, or member_user_ids on PG18."""
    async with engine.begin() as conn:
        nodes_by_id, ws_counts = await _load_all_nodes_and_ws_counts(conn)
        target = _resolve_target_node(nodes_by_id, org_unit_id)
        target_kind: OrgUnitKind = "BU" if target.unit_type in ("BU", "TRIBE") else "TEAM"

        next_name = target.name
        if name is not None:
            stripped = name.strip()
            if not stripped:
                raise ValidationDomainError(
                    detail_override="Le nom de l'unité ne peut pas être vide."
                )
            next_name = stripped

        if parent_id_provided:
            next_parent_id = validate_org_unit_hierarchy(
                unit_id=target.id,
                kind=target_kind,
                parent_id=parent_id,
                units_by_id=nodes_by_id,
            )
        else:
            existing_parent = nodes_by_id.get(target.parent_id or "")
            next_parent_id = (
                None
                if existing_parent is not None and existing_parent.unit_type == "ENTERPRISE"
                else target.parent_id
            )

        next_billing = target.billing_enabled if billing_enabled is None else billing_enabled
        next_lead = (
            ((lead_user_id or "").strip() or None) if lead_user_id_provided else target.lead_user_id
        )
        next_members = (
            normalize_member_user_ids(member_user_ids)
            if member_user_ids is not None
            else target.member_user_ids
        )

        await conn.execute(
            sa.text(
                """
                UPDATE org_units
                SET name = :name,
                    parent_id = :parent_id,
                    billing_enabled = :billing_enabled,
                    lead_user_id = :lead_user_id,
                    member_user_ids_jsonb = CAST(:member_user_ids_jsonb AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": UUID(target.id),
                "name": next_name,
                "parent_id": UUID(next_parent_id) if next_parent_id else None,
                "billing_enabled": next_billing,
                "lead_user_id": next_lead,
                "member_user_ids_jsonb": json.dumps(list(next_members)),
            },
        )
        updated_node = OrgUnitNode(
            id=target.id,
            slug=target.slug,
            name=next_name,
            unit_type=target_kind,
            parent_id=next_parent_id,
            billing_enabled=next_billing,
            lead_user_id=next_lead,
            member_user_ids=next_members,
        )
        nodes_by_id[target.id] = updated_node
        summaries = _build_sorted_summaries(nodes_by_id, ws_counts)
        await _sync_platform_settings_org_units_if_present(conn, summaries)

    return build_org_unit_summary(
        updated_node,
        nodes_by_id,
        attached_workspaces_count=ws_counts.get(target.id, 0),
    )


async def delete_org_unit_on_postgres18(
    engine: AsyncEngine,
    *,
    org_unit_id: str,
) -> str:
    """Delete an `OrgUnit` on PG18 or raise `OrgUnitNotEmptyError` (`HTTP 409`) if non-empty."""
    async with engine.begin() as conn:
        nodes_by_id, ws_counts = await _load_all_nodes_and_ws_counts(conn)
        target = _resolve_target_node(nodes_by_id, org_unit_id)
        child_units_count = sum(
            1
            for node in nodes_by_id.values()
            if node.parent_id == target.id and node.unit_type != "ENTERPRISE"
        )
        attached_ws_count = ws_counts.get(target.id, 0)
        assert_org_unit_deletable(
            target_name=target.name,
            child_units_count=child_units_count,
            attached_workspaces_count=attached_ws_count,
        )
        await conn.execute(
            sa.text("DELETE FROM org_units WHERE id = :id"),
            {"id": UUID(target.id)},
        )
        nodes_by_id.pop(target.id, None)
        ws_counts.pop(target.id, None)
        summaries = _build_sorted_summaries(nodes_by_id, ws_counts)
        await _sync_platform_settings_org_units_if_present(conn, summaries)
    return target.id
