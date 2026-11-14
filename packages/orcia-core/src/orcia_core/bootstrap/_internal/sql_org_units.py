"""PostgreSQL 18 persistence adapter for multi-level `org_units` CRUD (Story 17.2).

Single-query hierarchy loading (`LEFT JOIN` workspace aggregation, zero `N+1`), transactional
cycle/parent-kind validation (`HTTP 422`), non-empty deletion guard (`HTTP 409`), and atomic
synchronization with `platform_settings` (`platform_setup_state_v1`) when present.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_org_units_queries import (
    build_sorted_summaries,
    load_all_nodes_and_workspaces,
    load_known_org_users_from_postgres18,
    query_filtered_org_unit_summaries,
    resolve_target_node,
    sync_platform_settings_org_units_if_present,
)
from orcia_core.permissions.errors import ValidationDomainError
from orcia_core.permissions.models import OrgUnitNode
from orcia_core.permissions.org_hierarchy import (
    OrgUnitKind,
    OrgUnitSummary,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    normalize_org_unit_slug,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.org_user_validation import resolve_and_validate_org_unit_users
from orcia_kernel.ids import new_uuid7


async def list_org_units_from_postgres18(
    engine: AsyncEngine,
    *,
    q: str | None = None,
    kind: OrgUnitKind | None = None,
    limit: int | None = None,
) -> list[OrgUnitSummary]:
    """Return non-enterprise `OrgUnitSummary` items (filtered or ordered in DFS tree order)."""
    async with engine.connect() as conn:
        if q is not None or kind is not None or limit is not None:
            return await query_filtered_org_unit_summaries(conn, q=q, kind=kind, limit=limit)
        nodes_by_id, ws_counts, ws_refs = await load_all_nodes_and_workspaces(conn)
    return build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)


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

    async with engine.begin() as conn:
        nodes_by_id, ws_counts, ws_refs = await load_all_nodes_and_workspaces(conn)
        assert_unique_org_unit_slug(normalized_slug, nodes_by_id)
        resolved_parent_id = validate_org_unit_hierarchy(
            unit_id=None,
            kind=kind,
            parent_id=parent_id,
            units_by_id=nodes_by_id,
        )
        known_users = await load_known_org_users_from_postgres18(conn)
        resolved_lead, resolved_members = resolve_and_validate_org_unit_users(
            lead_user_id=lead_user_id,
            member_user_ids=member_user_ids or (),
            known_users=known_users,
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
                "lead_user_id": resolved_lead,
                "member_user_ids_jsonb": json.dumps(list(resolved_members)),
            },
        )
        new_node = OrgUnitNode(
            id=new_id,
            slug=normalized_slug,
            name=cleaned_name,
            unit_type=kind,
            parent_id=resolved_parent_id,
            billing_enabled=billing_enabled,
            lead_user_id=resolved_lead,
            member_user_ids=resolved_members,
        )
        nodes_by_id[new_id] = new_node
        ws_counts[new_id] = 0
        ws_refs[new_id] = ()
        summaries = build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)
        await sync_platform_settings_org_units_if_present(conn, summaries)

    return build_org_unit_summary(
        new_node,
        nodes_by_id,
        attached_workspaces_count=0,
        attached_workspaces=(),
    )


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
        nodes_by_id, ws_counts, ws_refs = await load_all_nodes_and_workspaces(conn)
        target = resolve_target_node(nodes_by_id, org_unit_id)
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

        should_validate_users = (lead_user_id_provided and bool((lead_user_id or "").strip())) or (
            member_user_ids is not None
        )

        if should_validate_users:
            known_users = await load_known_org_users_from_postgres18(conn)
            candidate_lead = lead_user_id if lead_user_id_provided else target.lead_user_id
            candidate_members = (
                member_user_ids if member_user_ids is not None else target.member_user_ids
            )
            resolved_lead, resolved_members = resolve_and_validate_org_unit_users(
                lead_user_id=candidate_lead,
                member_user_ids=candidate_members,
                known_users=known_users,
            )
            next_lead = resolved_lead if lead_user_id_provided else target.lead_user_id
            next_members = (
                resolved_members if member_user_ids is not None else target.member_user_ids
            )
        else:
            next_lead = (
                ((lead_user_id or "").strip() or None)
                if lead_user_id_provided
                else target.lead_user_id
            )
            next_members = target.member_user_ids

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
        summaries = build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)
        await sync_platform_settings_org_units_if_present(conn, summaries)

    return build_org_unit_summary(
        updated_node,
        nodes_by_id,
        attached_workspaces_count=ws_counts.get(target.id, 0),
        attached_workspaces=ws_refs.get(target.id, ()),
    )


async def delete_org_unit_on_postgres18(
    engine: AsyncEngine,
    *,
    org_unit_id: str,
) -> str:
    """Delete an `OrgUnit` on PG18 or raise `OrgUnitNotEmptyError` (`HTTP 409`) if non-empty."""
    async with engine.begin() as conn:
        nodes_by_id, ws_counts, ws_refs = await load_all_nodes_and_workspaces(conn)
        target = resolve_target_node(nodes_by_id, org_unit_id)
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
        target_uuid = UUID(target.id)
        fallback_parent_id: UUID | None = None
        if target.parent_id:
            try:
                fallback_parent_id = UUID(target.parent_id)
            except (ValueError, TypeError):
                fallback_parent_id = None

        if fallback_parent_id is None:
            root_res = await conn.execute(
                sa.text(
                    """
                    SELECT id FROM org_units
                    WHERE id <> :id
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
            fallback_parent_id = root_res.scalar()

        if fallback_parent_id is None:
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
                        INSERT INTO org_units (
                            id, slug, name, unit_type, billing_enabled, created_at
                        )
                        VALUES (
                            :id, 'global', 'Plateforme Globale ORCIA', 'ENTERPRISE', TRUE, NOW()
                        )
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
                    fallback_parent_id = ent_row[0]

        if fallback_parent_id is not None:
            await conn.execute(
                sa.text(
                    """
                    UPDATE users
                    SET primary_org_unit_id = :fallback_id
                    WHERE primary_org_unit_id = :target_id
                    """
                ),
                {"fallback_id": fallback_parent_id, "target_id": target_uuid},
            )

        await conn.execute(
            sa.text("DELETE FROM org_units WHERE id = :id"),
            {"id": target_uuid},
        )
        nodes_by_id.pop(target.id, None)
        ws_counts.pop(target.id, None)
        ws_refs.pop(target.id, None)
        summaries = build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)
        await sync_platform_settings_org_units_if_present(conn, summaries)
    return target.id


__all__ = [
    "create_org_unit_on_postgres18",
    "delete_org_unit_on_postgres18",
    "list_org_units_from_postgres18",
    "update_org_unit_on_postgres18",
]
