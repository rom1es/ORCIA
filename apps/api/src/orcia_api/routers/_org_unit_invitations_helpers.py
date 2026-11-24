"""In-memory evaluator attachment helper for scoped org-unit invitations (`Story 20.1`)."""

from __future__ import annotations

from orcia_core.permissions import OrgUnitNode


def apply_in_memory_org_attachment(
    evaluator_nodes: list[OrgUnitNode],
    *,
    evaluator_upsert: object,
    target_node: OrgUnitNode,
    canonical_kind: str,
    principal_id: str,
) -> None:
    """Attach invited user onto in-memory `OrgUnitNode` when PG sync is disabled."""
    del evaluator_nodes
    upsert = evaluator_upsert  # MatrixPermissionEvaluator.upsert_org_unit
    next_leads = list(target_node.lead_user_ids)
    next_onto = list(target_node.ontology_lead_user_ids)
    if canonical_kind in ("TEAM_LEAD", "BU_LEAD") and principal_id not in next_leads:
        next_leads.append(principal_id)
    elif canonical_kind == "ONTOLOGY_LEAD" and principal_id not in next_onto:
        next_onto.append(principal_id)
    if canonical_kind in ("TEAM_LEAD", "BU_LEAD", "ONTOLOGY_LEAD"):
        upsert(  # type: ignore[operator]
            OrgUnitNode(
                id=target_node.id,
                slug=target_node.slug,
                name=target_node.name,
                unit_type=target_node.unit_type,
                parent_id=target_node.parent_id,
                billing_enabled=target_node.billing_enabled,
                lead_user_id=next_leads[0] if next_leads else None,
                lead_user_ids=tuple(next_leads),
                ontology_lead_user_ids=tuple(next_onto),
                member_user_ids=target_node.member_user_ids,
            )
        )
