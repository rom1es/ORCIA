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

from orcia_core.bootstrap._internal._sql_org_units_mutations import (
    delete_org_unit_on_postgres18,
    update_org_unit_on_postgres18,
)
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
    sync_platform_settings_org_units_if_present,
)
from orcia_core.permissions.errors import ValidationDomainError
from orcia_core.permissions.models import OrgUnitNode
from orcia_core.permissions.org_hierarchy import (
    OrgUnitKind,
    OrgUnitSummary,
    assert_bu_has_no_members,
    assert_bu_only_ontology_leads,
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
        raise ValidationDomainError(detail_code="ERR_ORG_UNIT_EMPTY_NAME")
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


__all__ = [
    "create_org_unit_on_postgres18",
    "delete_org_unit_on_postgres18",
    "list_org_units_from_postgres18",
    "update_org_unit_on_postgres18",
]
