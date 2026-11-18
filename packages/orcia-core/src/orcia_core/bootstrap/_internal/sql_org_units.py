"""PostgreSQL 18 persistence adapter for multi-level `org_units` CRUD (Story 17.2 / CAP-067).

Single-query hierarchy loading (`LEFT JOIN` workspace aggregation, zero `N+1`), transactional
cycle/parent-kind validation (`HTTP 422`), BU no-direct-members guard (`HTTP 422`), multi-lead
persistence, and atomic bidirectional IAM role synchronization (`BU_LEAD` / `TEAM_LEAD`).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_org_iam_role_sync import (
    resolve_canonical_lead_user_ids,
    sync_iam_lead_roles_from_org_units,
)
from orcia_core.bootstrap._internal.sql_org_ontology_lead_sync import (
    resolve_canonical_ontology_lead_user_ids,
    sync_iam_ontology_lead_roles_from_org_units,
)
from orcia_core.bootstrap._internal.sql_org_units_queries import (
    build_sorted_summaries,
    load_all_nodes_and_workspaces,
    load_known_org_users_from_postgres18,
    query_filtered_org_unit_summaries,
    reassign_users_primary_org_unit_before_delete,
    resolve_target_node,
    sync_platform_settings_org_units_if_present,
)
from orcia_core.permissions.errors import ValidationDomainError
from orcia_core.permissions.models import OrgUnitNode
from orcia_core.permissions.org_hierarchy import (
    OrgUnitKind,
    OrgUnitSummary,
    assert_bu_has_no_members,
    assert_bu_only_ontology_leads,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    normalize_org_unit_slug,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.org_user_validation import resolve_and_validate_org_unit_users


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
    lead_user_ids: Sequence[str] | None = None,
    ontology_lead_user_ids: Sequence[str] | None = None,
    member_user_ids: Sequence[str] | None = None,
) -> OrgUnitSummary:
    """Create a `BU` or `TEAM` on PostgreSQL 18 with hierarchy validation (`UUIDv7`)."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValidationDomainError(detail_override="Le nom de l'unité ne peut pas être vide.")
    normalized_slug = normalize_org_unit_slug(slug, cleaned_name)
    assert_bu_has_no_members(kind, member_user_ids)
    assert_bu_only_ontology_leads(kind, ontology_lead_user_ids)

    async with engine.begin() as conn:
        nodes_by_id, ws_counts, ws_refs = await load_all_nodes_and_workspaces(conn)
        assert_unique_org_unit_slug(normalized_slug, nodes_by_id)
        resolved_parent_id = validate_org_unit_hierarchy(
            unit_id=None,
            kind=kind,
            parent_id=parent_id,
            units_by_id=nodes_by_id,
        )
        resolved_leads, resolved_lead = await resolve_canonical_lead_user_ids(
            conn,
            lead_user_ids=lead_user_ids,
            lead_user_id=lead_user_id,
        )
        resolved_ontology_leads = await resolve_canonical_ontology_lead_user_ids(
            conn,
            ontology_lead_user_ids=ontology_lead_user_ids,
        )
        known_users = await load_known_org_users_from_postgres18(conn)
        _, resolved_members = resolve_and_validate_org_unit_users(
            lead_user_id=None,
            member_user_ids=member_user_ids or (),
            known_users=known_users,
        )
        new_id = generate_new_org_unit_id()
        await conn.execute(
            sa.text(
                """
                INSERT INTO org_units (
                    id, slug, name, unit_type, parent_id,
                    billing_enabled, lead_user_id, lead_user_ids_jsonb,
                    ontology_lead_user_ids_jsonb, member_user_ids_jsonb
                )
                VALUES (
                    :id, :slug, :name, :unit_type, :parent_id,
                    :billing_enabled, :lead_user_id,
                    CAST(:lead_user_ids_jsonb AS jsonb),
                    CAST(:ontology_lead_user_ids_jsonb AS jsonb),
                    CAST(:member_user_ids_jsonb AS jsonb)
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
                "lead_user_ids_jsonb": json.dumps(list(resolved_leads)),
                "ontology_lead_user_ids_jsonb": json.dumps(list(resolved_ontology_leads)),
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
            lead_user_ids=resolved_leads,
            ontology_lead_user_ids=resolved_ontology_leads,
            member_user_ids=resolved_members,
        )
        nodes_by_id[new_id] = new_node
        ws_counts[new_id] = 0
        ws_refs[new_id] = ()
        summaries = build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)
        await sync_platform_settings_org_units_if_present(conn, summaries)
        await sync_iam_lead_roles_from_org_units(conn, resolved_leads)
        await sync_iam_ontology_lead_roles_from_org_units(conn, resolved_ontology_leads)

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
    lead_user_ids: Sequence[str] | None = None,
    lead_user_ids_provided: bool = False,
    ontology_lead_user_ids: Sequence[str] | None = None,
    ontology_lead_user_ids_provided: bool = False,
    member_user_ids: Sequence[str] | None = None,
) -> OrgUnitSummary:
    """Update name, parent_id, billing_enabled, lead_user_ids, or member_user_ids on PG18."""
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

        # Leads resolution
        if lead_user_ids_provided or lead_user_id_provided:
            resolved_leads, resolved_lead = await resolve_canonical_lead_user_ids(
                conn,
                lead_user_ids=lead_user_ids if lead_user_ids_provided else None,
                lead_user_id=lead_user_id if lead_user_id_provided else None,
            )
            next_leads = resolved_leads
            next_lead = resolved_lead
        else:
            next_leads = target.lead_user_ids
            next_lead = target.lead_user_id

        # Ontology leads resolution (BU only)
        if ontology_lead_user_ids_provided:
            assert_bu_only_ontology_leads(target_kind, ontology_lead_user_ids)
            next_ontology_leads = await resolve_canonical_ontology_lead_user_ids(
                conn,
                ontology_lead_user_ids=ontology_lead_user_ids,
            )
        else:
            next_ontology_leads = target.ontology_lead_user_ids

        # Members resolution
        if member_user_ids is not None:
            assert_bu_has_no_members(target_kind, member_user_ids)
            known_users = await load_known_org_users_from_postgres18(conn)
            _, next_members = resolve_and_validate_org_unit_users(
                lead_user_id=None,
                member_user_ids=member_user_ids,
                known_users=known_users,
            )
        else:
            next_members = target.member_user_ids

        await conn.execute(
            sa.text(
                """
                UPDATE org_units
                SET name = :name,
                    parent_id = :parent_id,
                    billing_enabled = :billing_enabled,
                    lead_user_id = :lead_user_id,
                    lead_user_ids_jsonb = CAST(:lead_user_ids_jsonb AS jsonb),
                    ontology_lead_user_ids_jsonb = CAST(:ontology_lead_user_ids_jsonb AS jsonb),
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
                "lead_user_ids_jsonb": json.dumps(list(next_leads)),
                "ontology_lead_user_ids_jsonb": json.dumps(list(next_ontology_leads)),
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
            lead_user_ids=next_leads,
            ontology_lead_user_ids=next_ontology_leads,
            member_user_ids=next_members,
        )
        nodes_by_id[target.id] = updated_node
        summaries = build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)
        await sync_platform_settings_org_units_if_present(conn, summaries)

        impacted = {*target.lead_user_ids, *next_leads}
        if target.lead_user_id:
            impacted.add(target.lead_user_id)
        if next_lead:
            impacted.add(next_lead)
        await sync_iam_lead_roles_from_org_units(conn, list(impacted))
        impacted_ontology = {*target.ontology_lead_user_ids, *next_ontology_leads}
        await sync_iam_ontology_lead_roles_from_org_units(conn, list(impacted_ontology))

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
        assert_org_unit_deletable(
            target_name=target.name,
            child_units_count=child_units_count,
            attached_workspaces_count=ws_counts.get(target.id, 0),
        )
        target_uuid = UUID(target.id)
        await reassign_users_primary_org_unit_before_delete(conn, target_uuid, target.parent_id)
        await conn.execute(sa.text("DELETE FROM org_units WHERE id = :id"), {"id": target_uuid})

        nodes_by_id.pop(target.id, None)
        ws_counts.pop(target.id, None)
        ws_refs.pop(target.id, None)
        summaries = build_sorted_summaries(nodes_by_id, ws_counts, ws_refs)
        await sync_platform_settings_org_units_if_present(conn, summaries)

        old_leads = {*target.lead_user_ids}
        if target.lead_user_id:
            old_leads.add(target.lead_user_id)
        await sync_iam_lead_roles_from_org_units(conn, list(old_leads))
        await sync_iam_ontology_lead_roles_from_org_units(conn, list(target.ontology_lead_user_ids))
    return target.id


__all__ = [
    "create_org_unit_on_postgres18",
    "delete_org_unit_on_postgres18",
    "list_org_units_from_postgres18",
    "update_org_unit_on_postgres18",
]
