"""Pure domain authorization & step-by-step promotion rules for 4-Level Ontology (Story 20.2).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Sequence

from orcia_core.ontology._promotion_permissions import (
    assert_can_review_promotion,
    can_review_promotion_target,
    resolve_next_promotion_target,
)
from orcia_core.ontology.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.ontology.models import OntologyLevel
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

_BU_SUPERVISOR_ROLES: frozenset[str] = frozenset({"BU_LEAD", "BU_DIRECTOR"})
_L4_CONTRIBUTOR_ROLES: frozenset[str] = frozenset(
    {"CONTRIBUTOR", "TEAM_LEAD", "ONTOLOGY_LEAD", "BU_LEAD", "BU_DIRECTOR", "ONTOLOGY_STEWARD_L3"}
)


def user_effective_roles(user: UserIdentity) -> frozenset[str]:
    """Return normalized uppercase set of all active roles on `user`."""
    roles = {str(user.platform_role).upper()}
    roles.update(str(r).strip().upper() for r in user.roles if str(r).strip())
    return frozenset(roles)


def is_observer_user(user: UserIdentity) -> bool:
    """Return True when caller's active role is read-only observer."""
    return str(user.platform_role).upper() in ("OBSERVER", "READ_ONLY_OBSERVER")


def _matches_any(user: UserIdentity, refs: Sequence[str]) -> bool:
    uid_l, email_l = user.id.strip().lower(), user.email.strip().lower()
    candidates = {r.strip().lower() for r in refs if r and r.strip()}
    return uid_l in candidates or email_l in candidates


def find_org_unit(org_units: Sequence[OrgUnitNode], scope_id: str) -> OrgUnitNode | None:
    """Resolve an `OrgUnitNode` by ID or slug."""
    return next((u for u in org_units if u.id == scope_id or u.slug == scope_id), None)


def find_workspace(workspaces: Sequence[WorkspaceEntity], scope_id: str) -> WorkspaceEntity | None:
    """Resolve a `WorkspaceEntity` by ID or slug."""
    return next((w for w in workspaces if w.id == scope_id or w.slug == scope_id), None)


def _ancestors(org_units: Sequence[OrgUnitNode], start_id: str) -> tuple[OrgUnitNode, ...]:
    by_id = {u.id: u for u in org_units}
    visited: set[str] = {start_id}
    chain: list[OrgUnitNode] = []
    cur = by_id.get(start_id)
    while cur is not None and cur.parent_id and cur.parent_id not in visited and len(chain) < 32:
        visited.add(cur.parent_id)
        parent = by_id.get(cur.parent_id)
        if parent is None:
            break
        chain.append(parent)
        cur = parent
    return tuple(chain)


def _has_bu_authority(user: UserIdentity, roles: frozenset[str], node: OrgUnitNode) -> bool:
    return _matches_any(user, node.ontology_lead_user_ids) or (
        bool(roles & _BU_SUPERVISOR_ROLES) and _matches_any(user, node.lead_user_ids)
    )


def _is_personal_workspace(ws: WorkspaceEntity) -> bool:
    return ws.personal_owner_user_id is not None or ws.ui_visibility_mode == "PRIVATE_USER"


def _find_ws_membership(
    user: UserIdentity,
    ws: WorkspaceEntity,
    memberships: Sequence[WorkspaceMembershipEntity],
) -> WorkspaceMembershipEntity | None:
    return next(
        (
            m
            for m in memberships
            if m.workspace_id == ws.id
            and (
                m.user_id == user.id
                or (
                    m.invited_org_unit_id is not None
                    and m.invited_org_unit_id == user.primary_org_unit_id
                )
            )
        ),
        None,
    )


def can_write_ontology_level(
    user: UserIdentity,
    level: OntologyLevel,
    scope_id: str,
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity],
    memberships: Sequence[WorkspaceMembershipEntity] = (),
    *,
    allow_ephemeral_fallback: bool = False,
) -> bool:
    """Evaluate L1–L4 direct ontology write authority for `user` at `(level, scope_id)`."""
    if is_observer_user(user):
        return False
    roles = user_effective_roles(user)
    if level in ("3_WORKSPACE", "4_WORKSPACE"):
        ws = find_workspace(workspaces, scope_id)
        if ws is not None:
            if _is_personal_workspace(ws):
                return ws.personal_owner_user_id is not None and str(
                    ws.personal_owner_user_id
                ) == str(user.id)
            if ws.visibility_mode == "CONFIDENTIAL_RESTRICTED":
                mem = _find_ws_membership(user, ws, memberships)
                return (
                    mem is not None
                    and mem.access_mode != "READ_ONLY_OBSERVER"
                    and mem.role != "OBSERVER"
                )
    if "PLATFORM_ADMIN" in roles:
        return True
    if level == "1_ENTERPRISE":
        return False
    if level == "2_DOMAIN":
        bu = find_org_unit(org_units, scope_id)
        return bu is not None and any(
            _has_bu_authority(user, roles, node) for node in (bu, *_ancestors(org_units, bu.id))
        )
    if level == "3_TEAM":
        team = find_org_unit(org_units, scope_id)
        if team is None:
            return False
        if "TEAM_LEAD" in roles and (
            _matches_any(user, team.lead_user_ids)
            or user.primary_org_unit_id in (team.id, team.slug)
        ):
            return True
        return any(_has_bu_authority(user, roles, anc) for anc in _ancestors(org_units, team.id))
    ws = find_workspace(workspaces, scope_id)
    if ws is not None:
        direct = _find_ws_membership(user, ws, memberships)
        if direct is not None:
            return direct.access_mode != "READ_ONLY_OBSERVER" and direct.role != "OBSERVER"
        owner = find_org_unit(org_units, ws.owner_org_unit_id)
        if owner is None:
            return False
        if _matches_any(user, owner.lead_user_ids) or _matches_any(
            user, owner.ontology_lead_user_ids
        ):
            return True
        if (roles & _L4_CONTRIBUTOR_ROLES) and (
            _matches_any(user, owner.member_user_ids)
            or user.primary_org_unit_id in (owner.id, owner.slug)
        ):
            return True
        return any(_has_bu_authority(user, roles, anc) for anc in _ancestors(org_units, owner.id))
    return (allow_ephemeral_fallback or level == "4_RUN_EPHEMERAL") and bool(
        roles & _L4_CONTRIBUTOR_ROLES
    )


def assert_can_write_ontology_level(
    user: UserIdentity,
    level: OntologyLevel,
    scope_id: str,
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity],
    memberships: Sequence[WorkspaceMembershipEntity] = (),
    *,
    instance: str = "/api/v1/ontology-rag/ontology/concepts",
    allow_ephemeral_fallback: bool = False,
) -> None:
    """Raise 403 (`ObserverModeReadOnlyError` or `ScopeAccessDeniedError`) if write denied."""
    if is_observer_user(user):
        raise ObserverModeReadOnlyError(instance=instance)
    if not can_write_ontology_level(
        user,
        level,
        scope_id,
        org_units,
        workspaces,
        memberships,
        allow_ephemeral_fallback=allow_ephemeral_fallback,
    ):
        raise ScopeAccessDeniedError(
            instance=instance,
            detail_code="ERR_ONTOLOGY_ACCESS_DENIED_SCOPE",
            detail_params={"level": level, "scope_id": scope_id},
        )


def can_read_ontology_item(
    user: UserIdentity,
    level: OntologyLevel,
    scope_id: str,
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity],
    memberships: Sequence[WorkspaceMembershipEntity] = (),
) -> bool:
    """Return True if `user` can read a concept or proposal at `(level, scope_id)`."""
    if level == "1_ENTERPRISE":
        return True
    if level in ("3_WORKSPACE", "4_WORKSPACE"):
        ws = find_workspace(workspaces, scope_id)
        if ws is None:
            return False
        if _is_personal_workspace(ws):
            return ws.personal_owner_user_id is not None and str(ws.personal_owner_user_id) == str(
                user.id
            )
        if ws.visibility_mode == "CONFIDENTIAL_RESTRICTED":
            return _find_ws_membership(user, ws, memberships) is not None
    if "PLATFORM_ADMIN" in user_effective_roles(user):
        return True
    if can_write_ontology_level(user, level, scope_id, org_units, workspaces, memberships):
        return True
    if level == "2_DOMAIN":
        bu = find_org_unit(org_units, scope_id)
        if bu is None:
            return False
        children: dict[str, list[str]] = {}
        for u in org_units:
            if u.parent_id:
                children.setdefault(u.parent_id, []).append(u.id)
        subtree, stack = set(), [bu.id]
        while stack:
            cur = stack.pop()
            if cur not in subtree:
                subtree.add(cur)
                stack.extend(children.get(cur, ()))
        if user.primary_org_unit_id in subtree:
            return True
        return any(
            u.id in subtree
            and (_matches_any(user, u.member_user_ids) or _matches_any(user, u.lead_user_ids))  # noqa: E501
            for u in org_units
        )
    if level == "3_TEAM":
        team = find_org_unit(org_units, scope_id)
        if team is None:
            return False
        return user.primary_org_unit_id in (team.id, team.slug) or _matches_any(
            user, team.member_user_ids
        )
    ws = find_workspace(workspaces, scope_id)
    if ws is None:
        return False
    if any(m.workspace_id == ws.id and m.user_id == user.id for m in memberships):
        return True
    owner = find_org_unit(org_units, ws.owner_org_unit_id)
    if owner is None:
        return False
    if (
        user.primary_org_unit_id in (owner.id, owner.slug)
        or _matches_any(user, owner.member_user_ids)
        or _matches_any(user, owner.lead_user_ids)
        or _matches_any(user, owner.ontology_lead_user_ids)
    ):
        return True
    return any(
        _matches_any(user, anc.lead_user_ids)
        or _matches_any(user, anc.ontology_lead_user_ids)
        or _matches_any(user, anc.member_user_ids)
        or user.primary_org_unit_id in (anc.id, anc.slug)
        for anc in _ancestors(org_units, owner.id)
        if anc.unit_type in ("BU", "TRIBE")
    )


__all__ = [
    "assert_can_review_promotion",
    "assert_can_write_ontology_level",
    "can_read_ontology_item",
    "can_review_promotion_target",
    "can_write_ontology_level",
    "find_org_unit",
    "find_workspace",
    "is_observer_user",
    "resolve_next_promotion_target",
    "user_effective_roles",
]
