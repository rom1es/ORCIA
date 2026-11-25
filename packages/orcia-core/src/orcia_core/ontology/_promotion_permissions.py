"""Step-by-step promotion target resolution and review authorization helpers."""

from __future__ import annotations

from collections.abc import Sequence

from orcia_core.ontology.errors import (
    ObserverModeReadOnlyError,
    PromotionLevelJumpError,
    ScopeAccessDeniedError,
)
from orcia_core.ontology.models import OntologyLevel
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


def resolve_next_promotion_target(
    source_level: OntologyLevel,
    source_scope_id: str,
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity],
    *,
    explicit_target_level: OntologyLevel | None = None,
    explicit_target_scope_id: str | None = None,
) -> tuple[OntologyLevel, str]:
    """Compute immediate next level (`L4 -> L3 -> L2 -> L1`), rejecting jumps & forged targets."""
    from orcia_core.ontology.permissions import _ancestors, find_org_unit, find_workspace

    if source_level == "1_ENTERPRISE":
        raise PromotionLevelJumpError(detail_code="ERR_ONTOLOGY_L1_PROMOTION_FORBIDDEN")
    if source_level == "4_RUN_EPHEMERAL":
        if explicit_target_level and explicit_target_level not in ("4_WORKSPACE", "3_WORKSPACE"):
            raise PromotionLevelJumpError()
        canonical_level: OntologyLevel = explicit_target_level or "4_WORKSPACE"
        canonical_scope_id = source_scope_id
    elif source_level in ("4_WORKSPACE", "3_WORKSPACE"):
        ws = find_workspace(workspaces, source_scope_id)
        owner = find_org_unit(org_units, ws.owner_org_unit_id) if ws else None
        if owner is None:
            raise PromotionLevelJumpError(detail_code="ERR_ONTOLOGY_TARGET_TEAM_MISSING")
        if owner.unit_type in ("BU", "TRIBE"):
            if explicit_target_level and explicit_target_level != "2_DOMAIN":
                raise PromotionLevelJumpError()
            canonical_level, canonical_scope_id = "2_DOMAIN", owner.id
        else:
            if explicit_target_level and explicit_target_level != "3_TEAM":
                raise PromotionLevelJumpError()
            canonical_level, canonical_scope_id = "3_TEAM", owner.id
    elif source_level == "3_TEAM":
        if explicit_target_level and explicit_target_level != "2_DOMAIN":
            raise PromotionLevelJumpError()
        team = find_org_unit(org_units, source_scope_id)
        parent_bu = (
            next(
                (a for a in _ancestors(org_units, team.id) if a.unit_type in ("BU", "TRIBE")),
                None,
            )
            if team
            else None
        )
        if parent_bu is None:
            raise PromotionLevelJumpError(detail_code="ERR_ONTOLOGY_PARENT_BU_MISSING")
        canonical_level, canonical_scope_id = "2_DOMAIN", parent_bu.id
    else:
        bu = find_org_unit(org_units, source_scope_id)
        parent_bu = (
            next(
                (a for a in _ancestors(org_units, bu.id) if a.unit_type in ("BU", "TRIBE")),
                None,
            )
            if bu
            else None
        )
        if parent_bu is not None:
            if explicit_target_level and explicit_target_level != "2_DOMAIN":
                raise PromotionLevelJumpError()
            canonical_level, canonical_scope_id = "2_DOMAIN", parent_bu.id
        else:
            if explicit_target_level and explicit_target_level != "1_ENTERPRISE":
                raise PromotionLevelJumpError()
            canonical_level, canonical_scope_id = "1_ENTERPRISE", "scope-global"

    if (
        explicit_target_scope_id is not None
        and explicit_target_scope_id.strip() != ""
        and explicit_target_scope_id.strip() != canonical_scope_id
    ):
        raise ScopeAccessDeniedError(
            detail_code="ERR_ONTOLOGY_PROMOTION_TARGET_FORBIDDEN",
            detail_params={
                "requested_scope_id": explicit_target_scope_id,
                "canonical_scope_id": canonical_scope_id,
            },
        )
    return canonical_level, canonical_scope_id


def _has_confidential_workspace_access(
    user: UserIdentity,
    ws: WorkspaceEntity,
    memberships: Sequence[WorkspaceMembershipEntity],
) -> bool:
    from orcia_core.ontology.permissions import _find_ws_membership, _is_personal_workspace

    if _is_personal_workspace(ws):
        return ws.personal_owner_user_id is not None and str(ws.personal_owner_user_id) == str(
            user.id
        )
    if ws.visibility_mode == "CONFIDENTIAL_RESTRICTED":
        mem = _find_ws_membership(user, ws, memberships)
        return (
            mem is not None and mem.access_mode != "READ_ONLY_OBSERVER" and mem.role != "OBSERVER"
        )
    return True


def can_review_promotion_target(
    user: UserIdentity,
    target_level: OntologyLevel,
    target_scope_id: str,
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity] = (),
    memberships: Sequence[WorkspaceMembershipEntity] = (),
    *,
    source_scope_id: str | None = None,
) -> bool:
    """Return True when `user` is authorized to approve/reject a promotion to `target_level`."""
    from orcia_core.ontology.permissions import (
        can_write_ontology_level,
        find_workspace,
        is_observer_user,
        user_effective_roles,
    )

    if is_observer_user(user):
        return False
    for scope_id in (target_scope_id, source_scope_id):
        if not scope_id:
            continue
        ws = find_workspace(workspaces, scope_id)
        if ws is not None and not _has_confidential_workspace_access(user, ws, memberships):
            return False
    if "PLATFORM_ADMIN" in user_effective_roles(user):
        return True
    if target_level == "1_ENTERPRISE":
        return False
    return can_write_ontology_level(
        user, target_level, target_scope_id, org_units, workspaces, memberships
    )


def assert_can_review_promotion(
    user: UserIdentity,
    target_level: OntologyLevel,
    target_scope_id: str,
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity] = (),
    memberships: Sequence[WorkspaceMembershipEntity] = (),
    *,
    source_scope_id: str | None = None,
    instance: str = "/api/v1/ontology-rag/ontology/promotions",
) -> None:
    """Enforce target-level review governance (`ONTOLOGY_LEAD` on BU L2, `PLATFORM_ADMIN` on L1)."""
    from orcia_core.ontology.permissions import is_observer_user

    if is_observer_user(user):
        raise ObserverModeReadOnlyError(instance=instance)
    if not can_review_promotion_target(
        user,
        target_level,
        target_scope_id,
        org_units,
        workspaces,
        memberships,
        source_scope_id=source_scope_id,
    ):
        raise ScopeAccessDeniedError(
            instance=instance,
            detail_code="ERR_ONTOLOGY_VALIDATION_DENIED",
            detail_params={"target_level": target_level, "target_scope_id": target_scope_id},
        )


__all__ = [
    "assert_can_review_promotion",
    "can_review_promotion_target",
    "resolve_next_promotion_target",
]
