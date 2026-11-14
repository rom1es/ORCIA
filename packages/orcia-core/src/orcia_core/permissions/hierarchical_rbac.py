"""Hierarchical 6-Verb RBAC/ABAC Engine, Delegation & Anti-Lockout (`Story 8.1`, `Story 17.3`).

Implements:
- 6 atomic verbs: `create`, `read`, `update`, `delete`, `execute`, `grant`
- Native 6-role matrix (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`,
  `OBSERVER`)
- Hierarchical evaluation along `org -> bu -> team -> workspace -> pack -> resource`
- `ACTION_ITEM-8.1` & `17.3`: Explicit `DENY` priority, `INHERITANCE_BLOCK`, and `resource_kind`
- `ACTION_ITEM-8.2`: Contextual ABAC conditions on `execute` (`env`, `max_tokens_per_run`)
- `ACTION_ITEM-8.3`: `hidden_when_unauthorized` (`HTTP 404`) vs passive discovery (`locked: true`)
- Bounded delegation (`grant` confinement) & Anti-lockout invariants (`ERR_ADMIN_LOCKOUT_PREVENTED`)
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from orcia_core.permissions.errors import (
    AdminLockoutPreventedError,
    GrantEscalationForbiddenError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    SecretConfigReadDeniedError,
)
from orcia_core.permissions.iam_accounts import validate_grant_resource_kind
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.role_matrix import (
    ALL_PERMISSION_VERBS,
    DEFAULT_ROLE_PERMISSION_MATRIX,
    GrantResourceKind,
    OfficialIamRole,
    PermissionEffect,
    PermissionVerb,
    ResourceDiscoveryOutcome,
    RoleMatrixDescriptor,
    RolePermissionGrant,
    SubjectType,
    iter_scope_prefixes,
    list_native_role_matrix,
    normalize_scope_path,
)
from orcia_kernel.events import AccessRequested, DomainEvent, PermissionGranted, PermissionRevoked
from orcia_kernel.ids import new_uuid7_str


class HierarchicalRbacService:
    """Domain service for the 6-verb hierarchical RBAC/ABAC model (`Story 8.1`, `Story 17.3`)."""

    def __init__(
        self,
        *,
        initial_grants: tuple[RolePermissionGrant, ...] = (),
        active_platform_admin_ids: set[str] | None = None,
        active_auth_methods: set[str] | None = None,
    ) -> None:
        self._grants: dict[str, RolePermissionGrant] = {g.id: g for g in initial_grants}
        self._active_admin_ids: set[str] = set(
            active_platform_admin_ids
            or {
                "0195f000-0000-7000-8000-000000000201",
                "0195f000-0000-7000-8000-000000000206",
            }
        )
        self._active_auth_methods: set[str] = set(active_auth_methods or {"OIDC", "LOCAL"})
        self._revoked_subjects: set[str] = set()
        self._outbox_events: list[DomainEvent] = []
        self._hidden_scopes: set[str] = {
            normalize_scope_path(g.scope_path) for g in initial_grants if g.hidden_when_unauthorized
        }

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._outbox_events)

    def list_grants(self, scope_path: str | None = None) -> list[RolePermissionGrant]:
        if scope_path is None:
            return list(self._grants.values())
        norm = normalize_scope_path(scope_path)
        return [
            g
            for g in self._grants.values()
            if g.scope_path == norm or norm.startswith(f"{g.scope_path}/")
        ]

    def replace_grants(self, grants: tuple[RolePermissionGrant, ...]) -> None:
        self._grants = {g.id: g for g in grants}

    def set_scope_hidden_when_unauthorized(self, scope_path: str, hidden: bool = True) -> None:
        norm = normalize_scope_path(scope_path)
        if hidden:
            self._hidden_scopes.add(norm)
        else:
            self._hidden_scopes.discard(norm)

    def _matches_conditions(
        self, grant: RolePermissionGrant, context: dict[str, Any] | None
    ) -> bool:
        """Evaluate ABAC conditions on `execute` and granular `resource_kind` (`Story 17.3`)."""
        ctx = context or {}
        requested_kind = str(ctx.get("resource_kind") or "ALL").strip().upper()
        if grant.resource_kind != "ALL" and requested_kind != grant.resource_kind:
            return False
        if not grant.conditions:
            return True
        allowed_envs = grant.conditions.get("allowed_environments")
        if allowed_envs is not None and ctx.get("env") not in allowed_envs:
            return False
        req_env = grant.conditions.get("env")
        if req_env is not None and ctx.get("env") != req_env:
            return False
        max_tokens = grant.conditions.get("max_tokens_per_run")
        requested_tokens = ctx.get("requested_tokens", 0)
        return not (max_tokens is not None and int(requested_tokens) > int(max_tokens))

    def _grant_applies_to_resource_kind(
        self, grant: RolePermissionGrant, context: dict[str, Any] | None
    ) -> bool:
        if grant.resource_kind == "ALL":
            return True
        ctx = context or {}
        requested_kind = str(ctx.get("resource_kind") or "ALL").strip().upper()
        return requested_kind == grant.resource_kind

    def resolve_effective_verbs(
        self,
        *,
        subject_id: str,
        subject_type: SubjectType = "USER",
        roles: tuple[str, ...] = (),
        scope_path: str,
        context: dict[str, Any] | None = None,
    ) -> set[PermissionVerb]:
        """Compute effective allowed verbs along `scope_path` with `DENY` & `inheritance_block`."""
        if subject_id in self._revoked_subjects:
            return set()
        if ("PLATFORM_ADMIN" in roles or "SECOPS" in roles) and subject_type == "USER":
            prefixes = iter_scope_prefixes(scope_path)
            denied_admin: set[PermissionVerb] = set()
            for pfx in prefixes:
                for g in self._grants.values():
                    if (
                        g.scope_path == pfx
                        and g.effect == "DENY"
                        and self._grant_applies_to_resource_kind(g, context)
                        and (
                            (g.subject_type == subject_type and g.subject_id == subject_id)
                            or (g.subject_type == "ROLE" and g.subject_id in roles)
                        )
                    ):
                        denied_admin.add(g.verb)
            return set(ALL_PERMISSION_VERBS) - denied_admin

        prefixes = iter_scope_prefixes(scope_path)
        allowed: set[PermissionVerb] = set()
        denied: set[PermissionVerb] = set()

        for pfx in prefixes:
            matching = [
                g
                for g in self._grants.values()
                if g.scope_path == pfx
                and (
                    (g.subject_type == subject_type and g.subject_id == subject_id)
                    or (g.subject_type == "ROLE" and g.subject_id in roles)
                )
            ]
            if any(
                (g.inheritance_block or g.effect == "INHERITANCE_BLOCK")
                and self._grant_applies_to_resource_kind(g, context)
                for g in matching
            ):
                allowed.clear()
            for g in matching:
                if g.effect == "INHERITANCE_BLOCK":
                    continue
                if g.effect == "DENY":
                    if self._grant_applies_to_resource_kind(g, context):
                        denied.add(g.verb)
                elif self._matches_conditions(g, context):
                    allowed.add(g.verb)

        return allowed - denied

    def evaluate_resource_access(
        self,
        *,
        subject_id: str,
        subject_type: SubjectType = "USER",
        roles: tuple[str, ...] = (),
        scope_path: str,
        title: str = "Resource",
        context: dict[str, Any] | None = None,
        require_secret_read: bool = False,
        require_execute: bool = False,
        instance: str | None = None,
    ) -> ResourceDiscoveryOutcome:
        """Evaluate access on a resource (`execute` vs `read` isolation & passive lock)."""
        norm_path = normalize_scope_path(scope_path)
        verbs = self.resolve_effective_verbs(
            subject_id=subject_id,
            subject_type=subject_type,
            roles=roles,
            scope_path=norm_path,
            context=context,
        )
        ordered_verbs = tuple(v for v in ALL_PERMISSION_VERBS if v in verbs)
        has_read = "read" in verbs
        has_execute = "execute" in verbs

        if require_secret_read and not has_read:
            if has_execute:
                raise SecretConfigReadDeniedError(instance=instance)
            if norm_path in self._hidden_scopes:
                raise ResourceNotFoundError(instance=instance)
            raise ScopeAccessDeniedError(instance=instance)

        if require_execute and not has_execute:
            if norm_path in self._hidden_scopes:
                raise ResourceNotFoundError(instance=instance)
            raise ScopeAccessDeniedError(instance=instance)

        if not has_read and not has_execute:
            if norm_path in self._hidden_scopes:
                raise ResourceNotFoundError(instance=instance)
            return ResourceDiscoveryOutcome(
                scope_path=norm_path,
                title=title,
                allowed_verbs=ordered_verbs,
                locked=True,
                reason="MISSING_PERMISSION",
                can_request_access=True,
                secret_config_visible=False,
            )

        return ResourceDiscoveryOutcome(
            scope_path=norm_path,
            title=title,
            allowed_verbs=ordered_verbs,
            locked=False,
            reason=None,
            can_request_access=False,
            secret_config_visible=has_read,
        )

    def delegate_grant(
        self,
        delegator: UserIdentity,
        *,
        subject_type: SubjectType,
        subject_id: str,
        scope_path: str,
        verbs: tuple[PermissionVerb, ...],
        effect: PermissionEffect = "ALLOW",
        inheritance_block: bool = False,
        resource_kind: GrantResourceKind = "ALL",
        conditions: dict[str, Any] | None = None,
        hidden_when_unauthorized: bool = False,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> list[RolePermissionGrant]:
        """Delegate a subset of held permissions (`Droits délégués <= Droits détenus`, `AD-21`)."""
        if delegator.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        norm_path = normalize_scope_path(scope_path)
        valid_res_kind = validate_grant_resource_kind(resource_kind, instance=instance)
        delegator_roles = (
            (delegator.platform_role, "SECOPS")
            if delegator.human_profile_archetype == "SECOPS"
            else (delegator.platform_role,)
        )
        held = self.resolve_effective_verbs(
            subject_id=delegator.id,
            subject_type="USER",
            roles=delegator_roles,
            scope_path=norm_path,
        )
        if "grant" not in held:
            raise GrantEscalationForbiddenError(instance=instance)
        requested_set = set(verbs)
        if not requested_set or not requested_set.issubset(held):
            raise GrantEscalationForbiddenError(instance=instance)

        if hidden_when_unauthorized:
            self._hidden_scopes.add(norm_path)

        effective_block = inheritance_block or (effect == "INHERITANCE_BLOCK")
        outbox_effect = "ALLOW" if effect == "INHERITANCE_BLOCK" else effect
        created: list[RolePermissionGrant] = []
        for verb in verbs:
            grant = RolePermissionGrant(
                id=new_uuid7_str(),
                subject_type=subject_type,
                subject_id=subject_id,
                scope_path=norm_path,
                verb=verb,
                effect=effect,
                inheritance_block=effective_block,
                resource_kind=valid_res_kind,
                conditions=dict(conditions or {}),
                hidden_when_unauthorized=hidden_when_unauthorized,
                granted_by_user_id=delegator.id,
            )
            self._grants[grant.id] = grant
            created.append(grant)
            self._outbox_events.append(
                PermissionGranted.create(
                    grant_id=grant.id,
                    workspace_id=workspace_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    scope_path=norm_path,
                    verb=verb,
                    granted_by_user_id=delegator.id,
                    effect=outbox_effect,
                )
            )
        return created

    def revoke_grant(
        self,
        actor: UserIdentity,
        grant_id: str,
        *,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> RolePermissionGrant:
        """Revoke an existing grant and enforce anti-lockout invariants (`AD-21`)."""
        if actor.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        grant = self._grants.get(grant_id)
        if grant is None:
            raise ResourceNotFoundError(instance=instance)

        if (
            grant.subject_type == "USER"
            and grant.subject_id in self._active_admin_ids
            and len(self._active_admin_ids) <= 1
            and grant.verb in ("grant", "update", "delete")
        ):
            raise AdminLockoutPreventedError(instance=instance)

        self._grants.pop(grant_id)
        self._outbox_events.append(
            PermissionRevoked.create(
                grant_id=grant.id,
                workspace_id=workspace_id,
                subject_type=grant.subject_type,
                subject_id=grant.subject_id,
                scope_path=grant.scope_path,
                verb=grant.verb,
                revoked_by_user_id=actor.id,
            )
        )
        return grant

    def revoke_subject_immediately(self, actor: UserIdentity, subject_id: str) -> None:
        if actor.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()
        if subject_id in self._active_admin_ids and len(self._active_admin_ids) <= 1:
            raise AdminLockoutPreventedError()
        self._revoked_subjects.add(subject_id)

    def remove_platform_admin(
        self, actor: UserIdentity, target_admin_user_id: str, *, instance: str | None = None
    ) -> None:
        if actor.platform_role != "PLATFORM_ADMIN":
            raise ScopeAccessDeniedError(instance=instance)
        remaining = self._active_admin_ids - {target_admin_user_id}
        if not remaining:
            raise AdminLockoutPreventedError(instance=instance)
        self._active_admin_ids.discard(target_admin_user_id)

    def disable_auth_method(
        self, actor: UserIdentity, auth_method: str, *, instance: str | None = None
    ) -> None:
        if actor.platform_role != "PLATFORM_ADMIN":
            raise ScopeAccessDeniedError(instance=instance)
        norm = auth_method.strip().upper()
        remaining = self._active_auth_methods - {norm}
        if not remaining:
            raise AdminLockoutPreventedError(instance=instance)
        self._active_auth_methods.discard(norm)

    def enforce_step_boundary_execution_guard(
        self,
        *,
        subject_id: str,
        subject_type: SubjectType,
        roles: tuple[str, ...] = (),
        scope_path: str,
        context: dict[str, Any] | None = None,
        instance: str | None = None,
    ) -> None:
        verbs = self.resolve_effective_verbs(
            subject_id=subject_id,
            subject_type=subject_type,
            roles=roles,
            scope_path=scope_path,
            context=context,
        )
        if "execute" not in verbs:
            raise ScopeAccessDeniedError(
                detail_override=(
                    f"Right 'execute' revoked or denied at DBOS step boundary for "
                    f"subject '{subject_id}' on '{scope_path}'."
                ),
                instance=instance,
            )

    def request_access(
        self,
        requester: UserIdentity,
        *,
        scope_path: str,
        requested_verb: PermissionVerb = "execute",
        justification: str = "",
        workspace_id: str | None = None,
    ) -> AccessRequested:
        norm_path = normalize_scope_path(scope_path)
        event = AccessRequested.create(
            request_id=new_uuid7_str(),
            workspace_id=workspace_id,
            requester_user_id=requester.id,
            scope_path=norm_path,
            requested_verb=requested_verb,
            justification=justification.strip(),
        )
        self._outbox_events.append(event)
        return event


__all__ = [
    "ALL_PERMISSION_VERBS",
    "DEFAULT_ROLE_PERMISSION_MATRIX",
    "GrantResourceKind",
    "HierarchicalRbacService",
    "OfficialIamRole",
    "PermissionEffect",
    "PermissionVerb",
    "ResourceDiscoveryOutcome",
    "RoleMatrixDescriptor",
    "RolePermissionGrant",
    "SubjectType",
    "iter_scope_prefixes",
    "list_native_role_matrix",
    "normalize_scope_path",
    "replace",
]
