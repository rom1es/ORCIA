"""PostgreSQL 18 update/delete mutation helpers for `org_units`."""

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
    build_org_unit_summary,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.org_user_validation import resolve_and_validate_org_unit_users


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
                raise ValidationDomainError(detail_code="ERR_ORG_UNIT_EMPTY_NAME")
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

        if lead_user_ids_provided or lead_user_id_provided:
            resolved_leads, resolved_lead = await resolve_canonical_lead_user_ids(
                conn,
                lead_user_ids=lead_user_ids if lead_user_ids_provided else None,
                lead_user_id=lead_user_id if lead_user_id_provided else None,
            )
            next_leads, next_lead = resolved_leads, resolved_lead
        else:
            next_leads, next_lead = target.lead_user_ids, target.lead_user_id

        if ontology_lead_user_ids_provided:
            assert_bu_only_ontology_leads(target_kind, ontology_lead_user_ids)
            next_ontology_leads = await resolve_canonical_ontology_lead_user_ids(
                conn,
                ontology_lead_user_ids=ontology_lead_user_ids,
            )
        else:
            next_ontology_leads = target.ontology_lead_user_ids

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


__all__ = ["delete_org_unit_on_postgres18", "update_org_unit_on_postgres18"]
