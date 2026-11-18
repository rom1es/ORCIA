"""Scoped OrgUnit User Invitation & Anti-Escalation Rules (`Story 20.1`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

from collections.abc import Sequence

from orcia_core.permissions.errors import (
    InvalidIamRoleError,
    ObserverModeReadOnlyError,
    OrgUnitScopeForbiddenError,
    PrivilegeEscalationForbiddenError,
    ValidationDomainError,
)
from orcia_core.permissions.models import OrgUnitNode, UserIdentity
from orcia_core.permissions.org_delegation_scope import (
    BU_TYPES,
    compute_managed_org_scope,
)

_PRIVILEGED_ROLES = frozenset({"PLATFORM_ADMIN", "SECOPS"})


def resolve_org_invitation_roles(
    assignment_role: str,
    *,
    target_unit: OrgUnitNode,
    instance: str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Validate requested invitation role against target unit kind and anti-escalation policy."""
    norm = assignment_role.strip().upper()
    if norm in _PRIVILEGED_ROLES:
        raise PrivilegeEscalationForbiddenError(instance=instance)
    is_bu = target_unit.unit_type in BU_TYPES
    if norm in ("TEAM_MEMBER", "CONTRIBUTOR"):
        if is_bu:
            raise ValidationDomainError(
                instance=instance,
                detail_override="Un membre d'équipe doit être rattaché à une Équipe (TEAM).",
            )
        return "TEAM_MEMBER", ("CONTRIBUTOR",)
    if norm == "OBSERVER":
        if is_bu:
            raise ValidationDomainError(
                instance=instance,
                detail_override="Un observateur d'équipe doit être rattaché à une Équipe (TEAM).",
            )
        return "TEAM_MEMBER", ("OBSERVER",)
    if norm == "TEAM_LEAD":
        if is_bu:
            raise ValidationDomainError(
                instance=instance,
                detail_override="Le rôle TEAM_LEAD doit être rattaché à une Équipe (TEAM).",
            )
        return "TEAM_LEAD", ("TEAM_LEAD",)
    if norm == "BU_LEAD":
        if not is_bu:
            raise ValidationDomainError(
                instance=instance,
                detail_override="Le rôle BU_LEAD doit être rattaché à une Direction (BU).",
            )
        return "BU_LEAD", ("BU_LEAD",)
    if norm == "ONTOLOGY_LEAD":
        if not is_bu:
            raise ValidationDomainError(
                instance=instance,
                detail_override=(
                    "Le rôle ONTOLOGY_LEAD (Référent Glossaire) doit être rattaché "
                    "à une Direction (BU)."
                ),
            )
        return "ONTOLOGY_LEAD", ("ONTOLOGY_LEAD",)
    raise InvalidIamRoleError(instance=instance)


def assert_can_invite_org_user(
    user: UserIdentity,
    *,
    target_unit: OrgUnitNode,
    assignment_role: str,
    org_units: Sequence[OrgUnitNode],
    instance: str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Verify caller authority (`PLATFORM_ADMIN` or `BU_LEAD` on subtree) and anti-escalation."""
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    # Check anti-escalation before scope so 403 ERR_PRIVILEGE_ESCALATION_FORBIDDEN always wins
    canonical_kind, effective_roles = resolve_org_invitation_roles(
        assignment_role,
        target_unit=target_unit,
        instance=instance,
    )
    scope = compute_managed_org_scope(user, org_units)
    if not scope.is_platform_admin and (
        not scope.governed_bu_ids or target_unit.id not in scope.governed_bu_ids
    ):
        raise OrgUnitScopeForbiddenError(instance=instance)
    return canonical_kind, effective_roles


__all__ = [
    "assert_can_invite_org_user",
    "resolve_org_invitation_roles",
]
