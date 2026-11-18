"""Scope & Capability Graph Resolution for Hierarchical OrgUnit Delegation (`Story 20.1`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orcia_core.permissions.models import OrgUnitNode, UserIdentity

BU_TYPES = frozenset({"BU", "TRIBE"})
TEAM_TYPES = frozenset({"TEAM", "SUB_TEAM"})


@dataclass(frozen=True, slots=True)
class OrgUnitCapabilities:
    """Server-evaluated UI/API capabilities for a caller on a single `OrgUnit`."""

    can_edit: bool
    can_create_child: bool
    can_delete: bool
    can_manage_members: bool
    can_manage_ontology_leads: bool
    can_invite_users: bool


@dataclass(frozen=True, slots=True)
class ManagedOrgScope:
    """Resolved organizational visibility and governance scope for a caller."""

    is_platform_admin: bool
    is_global_reader: bool
    is_bu_lead: bool
    is_team_lead: bool
    led_bu_root_ids: frozenset[str]
    governed_bu_ids: frozenset[str]
    direct_led_team_ids: frozenset[str]
    editable_unit_ids: frozenset[str]
    visible_unit_ids: frozenset[str]


def _user_identifiers(user: UserIdentity) -> set[str]:
    ids = {user.id.strip().lower(), user.email.strip().lower()}
    return {x for x in ids if x}


def user_matches_refs(user: UserIdentity, refs: Sequence[str]) -> bool:
    """Return True if `user.id` or `user.email` matches any reference in `refs`."""
    u_ids = _user_identifiers(user)
    return any(str(r).strip().lower() in u_ids for r in refs if str(r).strip())


def user_leads_unit(user: UserIdentity, node: OrgUnitNode) -> bool:
    """Return True if `user` is designated as a lead of `node`."""
    refs = (*node.lead_user_ids, *((node.lead_user_id,) if node.lead_user_id else ()))
    return user_matches_refs(user, refs)


def _user_member_of_unit(user: UserIdentity, node: OrgUnitNode) -> bool:
    return user_matches_refs(user, node.member_user_ids)


def _user_ontology_leads_unit(user: UserIdentity, node: OrgUnitNode) -> bool:
    return user_matches_refs(user, node.ontology_lead_user_ids)


def ancestor_ids(unit_id: str, by_id: dict[str, OrgUnitNode]) -> set[str]:
    """Return all ancestor org unit IDs above `unit_id` without cycles."""
    ancestors: set[str] = set()
    curr = by_id.get(unit_id)
    while curr is not None and curr.parent_id and curr.parent_id in by_id:
        if curr.parent_id in ancestors:
            break
        ancestors.add(curr.parent_id)
        curr = by_id.get(curr.parent_id)
    return ancestors


def _descendant_ids(root_ids: set[str], by_id: dict[str, OrgUnitNode]) -> set[str]:
    descendants: set[str] = set()
    frontier = list(root_ids)
    while frontier:
        parent_id = frontier.pop()
        for node in by_id.values():
            if node.parent_id == parent_id and node.id not in descendants:
                descendants.add(node.id)
                frontier.append(node.id)
    return descendants


def compute_managed_org_scope(
    user: UserIdentity,
    org_units: Sequence[OrgUnitNode],
) -> ManagedOrgScope:
    """Compute visible, editable, and root-protected org unit sets for `user`."""
    by_id = {u.id: u for u in org_units if u.unit_type != "ENTERPRISE"}
    roles = {str(user.platform_role).upper(), *(str(r).upper() for r in user.roles)}
    is_admin = "PLATFORM_ADMIN" in roles
    is_secops = "SECOPS" in roles
    is_bu_role = bool(roles & {"BU_LEAD", "BU_DIRECTOR"})
    is_team_role = "TEAM_LEAD" in roles

    direct_led_bus = {
        n.id for n in by_id.values() if n.unit_type in BU_TYPES and user_leads_unit(user, n)
    }
    if (
        is_bu_role
        and not direct_led_bus
        and user.primary_org_unit_id in by_id
        and by_id[user.primary_org_unit_id].unit_type in BU_TYPES
    ):
        direct_led_bus.add(user.primary_org_unit_id)

    led_bu_roots = {
        bid for bid in direct_led_bus if not (ancestor_ids(bid, by_id) & direct_led_bus)
    }
    governed_bus = direct_led_bus | _descendant_ids(direct_led_bus, by_id)

    direct_led_teams = {
        n.id for n in by_id.values() if n.unit_type in TEAM_TYPES and user_leads_unit(user, n)
    }
    if (
        is_team_role
        and not direct_led_teams
        and user.primary_org_unit_id in by_id
        and by_id[user.primary_org_unit_id].unit_type in TEAM_TYPES
    ):
        direct_led_teams.add(user.primary_org_unit_id)

    if is_admin:
        all_ids = frozenset(by_id.keys())
        return ManagedOrgScope(
            is_platform_admin=True,
            is_global_reader=True,
            is_bu_lead=True,
            is_team_lead=True,
            led_bu_root_ids=frozenset(),
            governed_bu_ids=all_ids,
            direct_led_team_ids=frozenset(),
            editable_unit_ids=all_ids,
            visible_unit_ids=all_ids,
        )

    editable = governed_bus | direct_led_teams
    member_or_onto_ids = {
        n.id
        for n in by_id.values()
        if _user_member_of_unit(user, n) or _user_ontology_leads_unit(user, n)
    }
    if user.primary_org_unit_id in by_id:
        member_or_onto_ids.add(user.primary_org_unit_id)

    if is_secops:
        visible = frozenset(by_id.keys())
    else:
        seed_visible = editable | member_or_onto_ids
        visible_set = set(seed_visible)
        for uid in seed_visible:
            visible_set |= ancestor_ids(uid, by_id)
        visible = frozenset(visible_set)

    return ManagedOrgScope(
        is_platform_admin=False,
        is_global_reader=is_secops,
        is_bu_lead=is_bu_role or bool(direct_led_bus),
        is_team_lead=is_team_role or bool(direct_led_teams),
        led_bu_root_ids=frozenset(led_bu_roots),
        governed_bu_ids=frozenset(governed_bus),
        direct_led_team_ids=frozenset(direct_led_teams),
        editable_unit_ids=frozenset(editable),
        visible_unit_ids=visible,
    )


def compute_org_unit_capabilities(
    user: UserIdentity,
    node: OrgUnitNode,
    scope: ManagedOrgScope,
    *,
    is_observer: bool = False,
) -> OrgUnitCapabilities:
    """Return UI/API capability booleans for `user` on `node`."""
    is_bu = node.unit_type in BU_TYPES
    if is_observer or (user.platform_role == "OBSERVER" and not scope.is_platform_admin):
        return OrgUnitCapabilities(False, False, False, False, False, False)
    if scope.is_platform_admin:
        return OrgUnitCapabilities(
            can_edit=True,
            can_create_child=is_bu,
            can_delete=True,
            can_manage_members=not is_bu,
            can_manage_ontology_leads=is_bu,
            can_invite_users=True,
        )
    if node.id in scope.governed_bu_ids:
        return OrgUnitCapabilities(
            can_edit=True,
            can_create_child=is_bu,
            can_delete=node.id not in scope.led_bu_root_ids,
            can_manage_members=not is_bu,
            can_manage_ontology_leads=is_bu,
            can_invite_users=True,
        )
    if node.id in scope.direct_led_team_ids and not is_bu:
        return OrgUnitCapabilities(
            can_edit=True,
            can_create_child=False,
            can_delete=False,
            can_manage_members=True,
            can_manage_ontology_leads=False,
            can_invite_users=False,
        )
    return OrgUnitCapabilities(False, False, False, False, False, False)


__all__ = [
    "BU_TYPES",
    "TEAM_TYPES",
    "ManagedOrgScope",
    "OrgUnitCapabilities",
    "ancestor_ids",
    "compute_managed_org_scope",
    "compute_org_unit_capabilities",
    "user_leads_unit",
    "user_matches_refs",
]
