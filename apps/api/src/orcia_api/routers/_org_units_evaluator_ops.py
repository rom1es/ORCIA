"""In-Memory Evaluator CRUD Operations for `/api/v1/org-units` (`Story 17.2` & `20.1`)."""

from __future__ import annotations

from orcia_api.schemas.auth_and_org import OrgUnitCreateRequest, OrgUnitPatchRequest
from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    OrgUnitKind,
    OrgUnitNode,
    OrgUnitSummary,
    assert_bu_has_no_members,
    assert_bu_only_ontology_leads,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    normalize_member_user_ids,
    normalize_org_unit_slug,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError


def create_in_evaluator(
    evaluator: MatrixPermissionEvaluator,
    payload: OrgUnitCreateRequest,
    *,
    resolved_lead: str | None = None,
    resolved_members: tuple[str, ...] | None = None,
) -> OrgUnitSummary:
    """Create unit in memory evaluator when PostgreSQL sync is disabled or disconnected."""
    cleaned_name = payload.name.strip()
    if not cleaned_name:
        raise ValidationDomainError(detail_override="Le nom de l'unité ne peut pas être vide.")
    normalized_slug = normalize_org_unit_slug(payload.slug, cleaned_name)
    units_by_id = {u.id: u for u in evaluator.org_units}
    assert_unique_org_unit_slug(normalized_slug, units_by_id)
    resolved_parent = validate_org_unit_hierarchy(
        unit_id=None,
        kind=payload.kind,
        parent_id=payload.parent_id,
        units_by_id=units_by_id,
    )
    assert_bu_has_no_members(payload.kind, payload.member_user_ids)
    assert_bu_only_ontology_leads(payload.kind, payload.ontology_lead_user_ids)
    effective_lead = resolved_lead or (
        (payload.lead_user_id or "").strip() if payload.lead_user_id else None
    )
    effective_members = (
        resolved_members
        if resolved_members is not None
        else normalize_member_user_ids(payload.member_user_ids)
    )
    effective_leads = (
        tuple(str(x).strip() for x in payload.lead_user_ids if str(x).strip())
        if payload.lead_user_ids is not None
        else tuple([effective_lead] if effective_lead else [])
    )
    effective_onto_leads = (
        tuple(str(x).strip() for x in payload.ontology_lead_user_ids if str(x).strip())
        if payload.ontology_lead_user_ids is not None
        else ()
    )
    node = OrgUnitNode(
        id=generate_new_org_unit_id(),
        slug=normalized_slug,
        name=cleaned_name,
        unit_type=payload.kind,
        parent_id=resolved_parent,
        billing_enabled=payload.billing_enabled,
        lead_user_id=effective_lead,
        lead_user_ids=effective_leads,
        ontology_lead_user_ids=effective_onto_leads,
        member_user_ids=effective_members,
    )
    evaluator.upsert_org_unit(node)
    units_by_id[node.id] = node
    return build_org_unit_summary(node, units_by_id, attached_workspaces_count=0)


def update_in_evaluator(
    evaluator: MatrixPermissionEvaluator,
    org_unit_id: str,
    payload: OrgUnitPatchRequest,
    *,
    resolved_lead: str | None = None,
    resolved_members: tuple[str, ...] | None = None,
) -> OrgUnitSummary:
    """Update unit in memory evaluator when PostgreSQL sync is disabled or disconnected."""
    units_by_id = {u.id: u for u in evaluator.org_units}
    target = evaluator.get_org_unit(org_unit_id)
    if target is None or target.unit_type == "ENTERPRISE":
        raise ResourceNotFoundError(
            detail_override=f"Unité organisationnelle introuvable : '{org_unit_id}'."
        )
    target_kind: OrgUnitKind = "BU" if target.unit_type in ("BU", "TRIBE") else "TEAM"
    next_name = target.name
    if payload.name is not None:
        stripped = payload.name.strip()
        if not stripped:
            raise ValidationDomainError(detail_override="Le nom de l'unité ne peut pas être vide.")
        next_name = stripped

    if "parent_id" in payload.model_fields_set:
        next_parent = validate_org_unit_hierarchy(
            unit_id=target.id,
            kind=target_kind,
            parent_id=payload.parent_id,
            units_by_id=units_by_id,
        )
    else:
        parent_node = units_by_id.get(target.parent_id or "")
        next_parent = (
            None
            if parent_node is not None and parent_node.unit_type == "ENTERPRISE"
            else target.parent_id
        )

    next_billing = (
        target.billing_enabled if payload.billing_enabled is None else payload.billing_enabled
    )
    next_lead = (
        resolved_lead
        if resolved_lead is not None
        else ((payload.lead_user_id or "").strip() or None)
        if "lead_user_id" in payload.model_fields_set
        else target.lead_user_id
    )
    if payload.member_user_ids is not None:
        assert_bu_has_no_members(target_kind, payload.member_user_ids)
        next_members = (
            resolved_members
            if resolved_members is not None
            else normalize_member_user_ids(payload.member_user_ids)
        )
    else:
        next_members = target.member_user_ids

    if payload.lead_user_ids is not None:
        next_leads = tuple(str(x).strip() for x in payload.lead_user_ids if str(x).strip())
    elif "lead_user_id" in payload.model_fields_set:
        next_leads = tuple([next_lead] if next_lead else [])
    else:
        next_leads = target.lead_user_ids

    if "ontology_lead_user_ids" in payload.model_fields_set:
        assert_bu_only_ontology_leads(target_kind, payload.ontology_lead_user_ids)
        next_onto_leads = tuple(
            str(x).strip() for x in (payload.ontology_lead_user_ids or ()) if str(x).strip()
        )
    else:
        next_onto_leads = target.ontology_lead_user_ids

    updated = OrgUnitNode(
        id=target.id,
        slug=target.slug,
        name=next_name,
        unit_type=target_kind,
        parent_id=next_parent,
        billing_enabled=next_billing,
        lead_user_id=next_lead,
        lead_user_ids=next_leads,
        ontology_lead_user_ids=next_onto_leads,
        member_user_ids=next_members,
    )
    evaluator.upsert_org_unit(updated)
    units_by_id[updated.id] = updated
    ws_cnt = sum(1 for w in evaluator.workspaces if w.owner_org_unit_id == updated.id)
    return build_org_unit_summary(updated, units_by_id, attached_workspaces_count=ws_cnt)


def delete_in_evaluator(evaluator: MatrixPermissionEvaluator, org_unit_id: str) -> str:
    """Delete unit in memory evaluator when PostgreSQL sync is disabled or disconnected."""
    target = evaluator.get_org_unit(org_unit_id)
    if target is None or target.unit_type == "ENTERPRISE":
        raise ResourceNotFoundError(
            detail_override=f"Unité organisationnelle introuvable : '{org_unit_id}'."
        )
    child_cnt = sum(
        1 for u in evaluator.org_units if u.parent_id == target.id and u.unit_type != "ENTERPRISE"
    )
    ws_cnt = sum(1 for w in evaluator.workspaces if w.owner_org_unit_id == target.id)
    assert_org_unit_deletable(
        target_name=target.name,
        child_units_count=child_cnt,
        attached_workspaces_count=ws_cnt,
    )
    evaluator.remove_org_unit_node(target.id)
    return target.id


__all__ = [
    "create_in_evaluator",
    "delete_in_evaluator",
    "update_in_evaluator",
]
