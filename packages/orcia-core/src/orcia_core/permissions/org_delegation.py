"""Hierarchical OrgUnit Delegation Guards & Re-exports (`Story 20.1`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

from collections.abc import Sequence

from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrgUnitLastLeadRemovalForbiddenError,
    OrgUnitRootDeleteForbiddenError,
    OrgUnitScopeForbiddenError,
)
from orcia_core.permissions.models import OrgUnitNode, UserIdentity
from orcia_core.permissions.org_delegation_invitations import (
    assert_can_invite_org_user,
    resolve_org_invitation_roles,
)
from orcia_core.permissions.org_delegation_scope import (
    TEAM_TYPES,
    ManagedOrgScope,
    OrgUnitCapabilities,
    ancestor_ids,
    compute_managed_org_scope,
    compute_org_unit_capabilities,
    user_leads_unit,
    user_matches_refs,
)


def assert_can_create_org_unit(
    user: UserIdentity,
    *,
    parent_id: str | None,
    org_units: Sequence[OrgUnitNode],
    instance: str | None = None,
) -> None:
    """Enforce subtree confinement for `POST /api/v1/org-units`."""
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    scope = compute_managed_org_scope(user, org_units)
    if scope.is_platform_admin:
        return
    if not scope.governed_bu_ids:
        raise OrgUnitScopeForbiddenError(instance=instance)
    cleaned_parent = (parent_id or "").strip() or None
    if cleaned_parent is None or cleaned_parent == "scope-global":
        raise OrgUnitScopeForbiddenError(
            instance=instance,
            detail_override=(
                "Un Responsable de Direction (BU) doit rattacher toute nouvelle sous-BU ou "
                "équipe sous une BU de son périmètre."
            ),
        )
    if cleaned_parent not in scope.governed_bu_ids:
        raise OrgUnitScopeForbiddenError(instance=instance)


def assert_can_update_org_unit(
    user: UserIdentity,
    *,
    target: OrgUnitNode,
    parent_id_provided: bool,
    next_parent_id: str | None,
    billing_enabled_provided: bool,
    next_billing_enabled: bool,
    lead_user_ids_provided: bool,
    next_lead_user_ids: Sequence[str],
    ontology_lead_user_ids_provided: bool,
    next_ontology_lead_user_ids: Sequence[str],
    org_units: Sequence[OrgUnitNode],
    instance: str | None = None,
) -> None:
    """Enforce subtree confinement, field restrictions, and anti-eviction on `PATCH`."""
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    scope = compute_managed_org_scope(user, org_units)
    if scope.is_platform_admin:
        return

    by_id = {u.id: u for u in org_units if u.unit_type != "ENTERPRISE"}
    is_governed_by_bu = target.id in scope.governed_bu_ids
    is_led_team = target.id in scope.direct_led_team_ids and target.unit_type in TEAM_TYPES

    if not is_governed_by_bu and not is_led_team:
        raise OrgUnitScopeForbiddenError(instance=instance)

    if is_governed_by_bu:
        if parent_id_provided and next_parent_id != target.parent_id:
            if target.id in scope.led_bu_root_ids:
                raise OrgUnitScopeForbiddenError(
                    instance=instance,
                    detail_override="Impossible de déplacer votre Direction (BU) racine.",
                )
            if not next_parent_id or next_parent_id not in scope.governed_bu_ids:
                raise OrgUnitScopeForbiddenError(instance=instance)
    else:
        # TEAM_LEAD editing their own team: name, lead_user_ids, member_user_ids only
        if parent_id_provided and next_parent_id != target.parent_id:
            raise OrgUnitScopeForbiddenError(
                instance=instance,
                detail_override="Un Responsable d'Équipe ne peut pas modifier l'unité parente.",
            )
        if billing_enabled_provided and next_billing_enabled != target.billing_enabled:
            raise OrgUnitScopeForbiddenError(
                instance=instance,
                detail_override=(
                    "Un Responsable d'Équipe ne peut pas modifier la facturation FinOps."
                ),
            )
        if ontology_lead_user_ids_provided and tuple(next_ontology_lead_user_ids) != tuple(
            target.ontology_lead_user_ids
        ):
            raise OrgUnitScopeForbiddenError(
                instance=instance,
                detail_override=(
                    "Les référents glossaire ne peuvent être modifiés que sur une Direction (BU)."
                ),
            )

    if lead_user_ids_provided:
        parent_bu_intervention = bool(ancestor_ids(target.id, by_id) & scope.governed_bu_ids)
        if not parent_bu_intervention:
            cleaned_next = [str(x).strip() for x in next_lead_user_ids if str(x).strip()]
            if not cleaned_next:
                raise OrgUnitLastLeadRemovalForbiddenError(instance=instance)
            if (
                user_leads_unit(user, target)
                and not user_matches_refs(user, cleaned_next)
                and len(target.lead_user_ids) <= 1
            ):
                raise OrgUnitLastLeadRemovalForbiddenError(instance=instance)


def assert_can_delete_org_unit(
    user: UserIdentity,
    *,
    target: OrgUnitNode,
    org_units: Sequence[OrgUnitNode],
    instance: str | None = None,
) -> None:
    """Enforce deletion rules (`403 ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN` on root BU)."""
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    scope = compute_managed_org_scope(user, org_units)
    if scope.is_platform_admin:
        return
    if target.id in scope.led_bu_root_ids:
        raise OrgUnitRootDeleteForbiddenError(instance=instance)
    if target.id not in scope.governed_bu_ids:
        raise OrgUnitScopeForbiddenError(instance=instance)


__all__ = [
    "ManagedOrgScope",
    "OrgUnitCapabilities",
    "assert_can_create_org_unit",
    "assert_can_delete_org_unit",
    "assert_can_invite_org_user",
    "assert_can_update_org_unit",
    "compute_managed_org_scope",
    "compute_org_unit_capabilities",
    "resolve_org_invitation_roles",
]
