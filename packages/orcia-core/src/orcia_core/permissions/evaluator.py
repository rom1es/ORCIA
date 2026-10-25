"""MatrixPermissionEvaluator: OrgUnit hierarchy, Roll-up, Workspace Isolation & 5 Permissions.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from orcia_core.domain.exceptions import (
    ObserverModeReadOnlyError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import (
    AccessMode,
    CatalogAclEntry,
    EffectiveResourcePermissions,
    OrgUnitNode,
    PlatformRole,
    UserIdentity,
    WorkspaceAccessSummary,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

ADMIN_MODULE_ALLOWED_ROLES: frozenset[PlatformRole] = frozenset(
    {"PLATFORM_ADMIN", "BU_DIRECTOR", "TEAM_LEAD"}
)
ROLLUP_SUPERVISOR_ROLES: frozenset[PlatformRole] = frozenset(
    {"PLATFORM_ADMIN", "BU_DIRECTOR", "TEAM_LEAD"}
)


class MatrixPermissionEvaluator:
    """Pure domain evaluator for ORCIA's 3-axis authorization matrix (AD-6, AD-14, FR-21)."""

    def __init__(
        self, *, org_units: tuple[OrgUnitNode, ...], workspaces: tuple[WorkspaceEntity, ...],
        memberships: tuple[WorkspaceMembershipEntity, ...] = (),
        catalog_acls: tuple[CatalogAclEntry, ...] = (),
    ) -> None:  # fmt: skip
        self._org_units_by_id: dict[str, OrgUnitNode] = {u.id: u for u in org_units}
        self._workspaces_by_id: dict[str, WorkspaceEntity] = {w.id: w for w in workspaces}
        self._memberships = memberships
        self._catalog_acls = catalog_acls

    @property
    def org_units(self) -> tuple[OrgUnitNode, ...]:
        return tuple(self._org_units_by_id.values())

    @property
    def workspaces(self) -> tuple[WorkspaceEntity, ...]:
        return tuple(self._workspaces_by_id.values())

    def upsert_org_unit(self, node: OrgUnitNode) -> OrgUnitNode:
        self._org_units_by_id[node.id] = node
        return node

    def get_workspace(self, workspace_id_or_slug: str) -> WorkspaceEntity | None:
        if workspace_id_or_slug in self._workspaces_by_id:
            return self._workspaces_by_id[workspace_id_or_slug]
        return next(
            (w for w in self._workspaces_by_id.values() if w.slug == workspace_id_or_slug), None
        )

    def upsert_workspace(self, workspace: WorkspaceEntity) -> WorkspaceEntity:
        self._workspaces_by_id[workspace.id] = workspace
        return workspace

    def get_primary_catalog_acl(self, resource_id: str) -> CatalogAclEntry | None:
        return next((e for e in self._catalog_acls if e.resource_id == resource_id), None)

    def get_catalog_acl_by_uri(self, resource_uri: str) -> CatalogAclEntry | None:
        return next((e for e in self._catalog_acls if e.resource_uri == resource_uri), None)

    def upsert_catalog_acl(self, entry: CatalogAclEntry) -> None:
        kept = [e for e in self._catalog_acls if e.id != entry.id and e.resource_id != entry.resource_id]  # noqa: E501  # fmt: skip
        self._catalog_acls = (*kept, entry)

    def upsert_membership(self, mem: WorkspaceMembershipEntity) -> None:
        kept = [m for m in self._memberships if (m.workspace_id, m.user_id) != (mem.workspace_id, mem.user_id)]  # noqa: E501  # fmt: skip
        self._memberships = (*kept, mem)

    def has_org_unit(self, org_unit_id: str) -> bool:
        return org_unit_id in self._org_units_by_id

    def get_ancestor_org_unit_ids(self, org_unit_id: str) -> set[str]:
        ancestors: set[str] = set()
        current = self._org_units_by_id.get(org_unit_id)
        while current is not None and current.parent_id is not None:
            if current.parent_id in ancestors:
                break
            ancestors.add(current.parent_id)
            current = self._org_units_by_id.get(current.parent_id)
        return ancestors

    def get_descendant_org_unit_ids(self, org_unit_id: str) -> set[str]:
        descendants: set[str] = set()
        frontier = [org_unit_id]
        while frontier:
            parent_id = frontier.pop()
            for node in self._org_units_by_id.values():
                if node.parent_id == parent_id and node.id not in descendants:
                    descendants.add(node.id)
                    frontier.append(node.id)
        return descendants

    def is_ancestor_of(self, candidate_ancestor_id: str, target_org_unit_id: str) -> bool:
        return candidate_ancestor_id in self.get_ancestor_org_unit_ids(target_org_unit_id)

    def resolve_workspace_access(
        self, user: UserIdentity, workspace_id: str
    ) -> WorkspaceAccessSummary | None:
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return None

        for mem in self._memberships:
            if mem.workspace_id == workspace.id and mem.user_id == user.id:
                return WorkspaceAccessSummary(
                    workspace, mem.role, mem.access_mode, "DIRECT_TEAM", True
                )

        if workspace.owner_org_unit_id == user.primary_org_unit_id:
            mode: AccessMode = (
                "READ_ONLY_OBSERVER"
                if user.platform_role == "OBSERVER"
                else "CONTRIBUTOR_ACTION_REQUIRED"
            )
            return WorkspaceAccessSummary(workspace, user.platform_role, mode, "DIRECT_TEAM", True)

        for mem in self._memberships:
            if (
                mem.workspace_id == workspace.id
                and mem.invited_org_unit_id is not None
                and mem.invited_org_unit_id == user.primary_org_unit_id
            ):
                return WorkspaceAccessSummary(
                    workspace, mem.role, mem.access_mode, "PARTNER_INVITE", False
                )

        if user.platform_role in ROLLUP_SUPERVISOR_ROLES and self.is_ancestor_of(
            user.primary_org_unit_id, workspace.owner_org_unit_id
        ):
            if workspace.visibility_mode == "CONFIDENTIAL_RESTRICTED":
                return None
            return WorkspaceAccessSummary(
                workspace,
                "OBSERVER",
                "READ_ONLY_OBSERVER",
                "GLOBAL_ADMIN" if user.platform_role == "PLATFORM_ADMIN" else "ROLLUP_PARENT",
                True,
            )

        return None

    def resolve_accessible_workspaces(self, user: UserIdentity) -> list[WorkspaceAccessSummary]:
        summaries = (self.resolve_workspace_access(user, ws_id) for ws_id in self._workspaces_by_id)
        return [s for s in summaries if s is not None]

    def compute_finops_rollup_usd(
        self, user: UserIdentity, org_unit_id: str | None = None
    ) -> float:
        allowed_org_units = (
            {org_unit_id, *self.get_descendant_org_unit_ids(org_unit_id)}
            if org_unit_id is not None
            else None
        )
        total = sum(
            item.workspace.finops_cost_usd
            for item in self.resolve_accessible_workspaces(user)
            if item.finops_visible
            and (allowed_org_units is None or item.workspace.owner_org_unit_id in allowed_org_units)
        )
        return round(total, 4)

    def enforce_scope_mutation_guard(
        self, user: UserIdentity, workspace_id: str, *, instance: str | None = None
    ) -> WorkspaceAccessSummary:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            raise ResourceNotFoundError(instance=instance)
        access = self.resolve_workspace_access(user, ws.id)
        if access is None:
            raise ScopeAccessDeniedError(instance=instance)
        if access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        return access

    def _entry_applies_to_user(
        self,
        entry: CatalogAclEntry,
        user: UserIdentity,
        user_ancestors: set[str],
        workspace_id: str | None,
    ) -> bool:
        if user.platform_role == "PLATFORM_ADMIN":
            return True
        if (
            entry.grantee_transverse_group
            and entry.grantee_transverse_group in user.transverse_groups
        ):
            return True
        if entry.visibility_scope == "PENDING_APPROVAL" and user.platform_role == "BU_DIRECTOR":
            return True
        ws_scoped = entry.visibility_scope == "SHARED_WORKSPACE" or (
            entry.visibility_scope == "DRAFT" and entry.owner_workspace_id is not None
        )
        ws_matches = (
            (workspace_id == entry.owner_workspace_id and workspace_id is not None)
            if ws_scoped
            else True
        )
        if (
            entry.owner_org_unit_id == user.primary_org_unit_id
            and entry.grantee_org_unit_id in (None, user.primary_org_unit_id)
            and ws_matches
        ):
            return True
        if entry.visibility_scope in ("SHARED_TEAM", "SHARED_BU", "PUBLISHED_ORG") and (
            entry.visibility_scope == "PUBLISHED_ORG"
            or entry.owner_org_unit_id in {user.primary_org_unit_id, *user_ancestors}
            or (
                entry.grantee_org_unit_id is not None
                and entry.grantee_org_unit_id in {user.primary_org_unit_id, *user_ancestors}
            )
        ):
            return True
        return (
            entry.visibility_scope == "SHARED_WORKSPACE"
            and workspace_id is not None
            and workspace_id in (entry.owner_workspace_id, entry.grantee_workspace_id)
            and self.resolve_workspace_access(user, workspace_id) is not None
        )

    def evaluate_catalog_resource(
        self, user: UserIdentity, resource_id: str, *,
        workspace_id: str | None = None, require_read_source: bool = False, instance: str | None = None,  # noqa: E501
    ) -> tuple[EffectiveResourcePermissions, str | None]:  # fmt: skip
        entries = [e for e in self._catalog_acls if e.resource_id == resource_id]
        if not entries:
            raise ResourceNotFoundError(instance=instance)

        primary = entries[0]
        can_discover = can_execute = can_read_source = can_edit = can_admin = False
        user_ancestors = self.get_ancestor_org_unit_ids(user.primary_org_unit_id)

        for entry in entries:
            if self._entry_applies_to_user(entry, user, user_ancestors, workspace_id):
                can_discover = can_discover or entry.can_discover
                can_execute = can_execute or entry.can_execute
                can_read_source = can_read_source or entry.can_read_source
                if user.platform_role != "OBSERVER":
                    can_edit = can_edit or entry.can_edit
                    can_admin = can_admin or entry.can_admin

        if not can_discover:
            raise ScopeAccessDeniedError(instance=instance)
        if require_read_source and not can_read_source:
            raise ReadSourceDeniedError(
                instance=instance, permission_broker_hint=f"jira://IAM/PERM-READ-SOURCE-{resource_id}",
            )  # fmt: skip
        effective = EffectiveResourcePermissions(
            primary.resource_id, primary.resource_uri, primary.title, primary.visibility_scope,
            can_discover, can_execute, can_read_source, can_edit, can_admin,
        )  # fmt: skip
        return effective, (primary.system_prompt_secret if can_read_source else None)

    @staticmethod
    def evaluate_module_permissions(
        user: UserIdentity, *, scope_level: str | None = None, has_workspaces: bool = True
    ) -> dict[str, bool]:
        is_admin = user.platform_role in ADMIN_MODULE_ALLOWED_ROLES
        return {
            "cockpit": True,
            "inbox": has_workspaces,
            "catalog": True,
            "ontology": has_workspaces and (scope_level in (None, "TEAM", "WORKSPACE") or is_admin),
            "gates": has_workspaces,
            "finops": has_workspaces,
            "admin": is_admin,
            "bootstrap": is_admin,
        }

    @classmethod
    def enforce_module_access(
        cls, user: UserIdentity, module_key: str, *, instance: str | None = None
    ) -> None:
        if not cls.evaluate_module_permissions(user).get(module_key, False):
            raise ScopeAccessDeniedError(instance=instance)
