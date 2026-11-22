"""Pre-Stream Workspace Scope, Observer Mode & Server-Side READ_SOURCE Guards (`Story 26.1`)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Request

from orcia_api.dependencies._core_providers import (
    get_auth_service,
    get_permission_broker_service,
)
from orcia_api.dependencies._topology_sync import sync_evaluator_topology_from_pg
from orcia_core.kernel.errors import OrciaDomainError
from orcia_core.orchestration.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.evaluator import _user_leads_node
from orcia_core.permissions.models import UserIdentity, WorkspaceAccessSummary


def _is_observer_request(request: Request, user: UserIdentity) -> bool:
    hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    return hdr == "READ_ONLY_OBSERVER" or user.platform_role in ("OBSERVER", "BU_DIRECTOR")


def require_not_observer_write(request: Request, user: UserIdentity) -> None:
    """Reject read-only observers pre-lookup (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`)."""
    if _is_observer_request(request, user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))


def _user_leads_org_or_ancestors(evaluator: Any, user: UserIdentity, org_unit_id: str) -> bool:
    node = evaluator.get_org_unit(org_unit_id)
    if node is None:
        return False
    if _user_leads_node(user, node) or (
        user.primary_org_unit_id == node.id and user.platform_role in ("TEAM_LEAD", "BU_LEAD")
    ):
        return True
    for anc_id in evaluator.get_ancestor_org_unit_ids(node.id):
        anc = evaluator.get_org_unit(anc_id)
        if anc is not None and (
            _user_leads_node(user, anc)
            or (
                user.primary_org_unit_id == anc.id
                and user.platform_role in ("TEAM_LEAD", "BU_LEAD")
            )
        ):
            return True
    return False


async def enforce_assistant_workspace_guard(
    request: Request,
    user: UserIdentity,
    scope_id: str,
    *,
    require_write: bool = True,
    require_manage: bool = False,
    scope_level: str = "WORKSPACE",
) -> WorkspaceAccessSummary | None:
    """Enforce pre-stream observer, leadership, and scope access via MatrixPermissionEvaluator."""
    instance = str(request.url.path)
    if (require_write or require_manage) and _is_observer_request(request, user):
        raise ObserverModeReadOnlyError(instance=instance)

    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    evaluator = auth_svc.evaluator

    clean_scope = (scope_id or "").strip()
    if not clean_scope:
        raise ScopeAccessDeniedError(
            detail_override="Workspace or scope identifier is required.", instance=instance
        )

    is_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    norm_level = (scope_level or "WORKSPACE").strip().upper()
    if norm_level == "TEAM":
        org_node = evaluator.get_org_unit(clean_scope)
        if org_node is None or not (
            is_admin or _user_leads_org_or_ancestors(evaluator, user, org_node.id)
        ):
            raise ScopeAccessDeniedError(instance=instance)
        return None

    if norm_level == "GLOBAL":
        if clean_scope != "scope-global":
            raise ScopeAccessDeniedError(instance=instance)
        if (require_write or require_manage) and not is_admin:
            raise ScopeAccessDeniedError(instance=instance)
        is_partner_external = (
            user.human_profile_archetype == "PARTNER_EXTERNAL" or "PARTNER_EXTERNAL" in user.roles
        )
        if is_partner_external:
            raise ScopeAccessDeniedError(instance=instance)
        return None

    access = evaluator.resolve_workspace_access(user, clean_scope)
    if access is None:
        raise ScopeAccessDeniedError(instance=instance)
    if (require_write or require_manage) and access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    if require_manage and not (
        is_admin
        or _user_leads_org_or_ancestors(evaluator, user, access.workspace.owner_org_unit_id)
    ):
        raise ScopeAccessDeniedError(
            detail_override="Workspace or ancestor leadership required for governance changes.",
            instance=instance,
        )
    return access


async def can_user_manage_workspace_governance(
    request: Request,
    user: UserIdentity,
    workspace_id: str,
) -> bool:
    """Return True when `user` is allowed to manage Mode A/B governance on `workspace_id`."""
    try:
        await enforce_assistant_workspace_guard(
            request,
            user,
            workspace_id,
            require_write=True,
            require_manage=True,
            scope_level="GLOBAL" if workspace_id == "scope-global" else "WORKSPACE",
        )
        return True
    except OrciaDomainError:
        return False


async def resolve_assistant_workspace_uuid(
    request: Request,
    workspace_id: str | None,
) -> str:
    """Resolve workspace slug or UUID to canonical workspace UUID (`GLOBAL` fallback)."""
    clean = (workspace_id or "").strip()
    if not clean or clean == "scope-global":
        return "GLOBAL"
    auth_svc = getattr(request.app.state, "auth_service", None)
    if auth_svc is None:
        return clean
    ws = auth_svc.evaluator.get_workspace(clean)
    if ws is None:
        await sync_evaluator_topology_from_pg(request, auth_svc)
        ws = auth_svc.evaluator.get_workspace(clean)
    return ws.id if ws is not None else clean


def filter_allowed_source_uris_with_evaluator(
    evaluator: Any,
    broker: Any,
    user: UserIdentity,
    *,
    workspace_id: str,
    candidate_uris: tuple[str, ...],
) -> frozenset[str]:
    """Synchronously evaluate `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` per URI (`AD-21`)."""
    if not candidate_uris:
        return frozenset()
    ws = evaluator.get_workspace(workspace_id)
    resolved_ws_id = ws.id if ws is not None else workspace_id
    if ws is not None and evaluator.resolve_workspace_access(user, ws.id) is None:
        return frozenset()

    allowed: set[str] = set()
    user_roles = {user.platform_role, *user.roles, *user.transverse_groups}
    for uri in candidate_uris:
        acl = evaluator.get_catalog_acl_by_uri(uri)
        if acl is not None:
            try:
                eff, _ = evaluator.evaluate_catalog_resource(
                    user,
                    acl.resource_id,
                    workspace_id=resolved_ws_id,
                    require_read_source=True,
                )
                if eff.can_read_source:
                    allowed.add(uri)
            except OrciaDomainError:
                pass
            continue

        if uri.startswith(f"orcia://blackboard/{resolved_ws_id}/") or uri.startswith(
            f"orcia://blackboard/{workspace_id}/"
        ):
            allowed.add(uri)
            continue

        if broker is not None:
            try:
                policy = broker.resolve_matching_policy(uri)
                has_cred = broker.has_passthrough_credential(user.id, policy.connector_scheme, uri)
                if policy.required_role in user_roles or has_cred:
                    allowed.add(uri)
            except OrciaDomainError:
                pass

    return frozenset(allowed)


async def prepare_server_source_uri_authorizer(
    request: Request,
    user: UserIdentity,
    *,
    workspace_id: str,
) -> Callable[[tuple[str, ...]], frozenset[str]]:
    """Sync PG18 topology once and return a sync URI authorizer closure for Node 3."""
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    evaluator = auth_svc.evaluator
    broker = getattr(request.app.state, "permission_broker_service", None)
    if broker is None:
        try:
            broker = get_permission_broker_service(request)
        except RuntimeError:
            broker = None
    if broker is not None and hasattr(broker, "list_policies_async"):
        await broker.list_policies_async()
    return lambda uris: filter_allowed_source_uris_with_evaluator(
        evaluator, broker, user, workspace_id=workspace_id, candidate_uris=uris
    )


async def resolve_server_allowed_source_uris(
    request: Request,
    user: UserIdentity,
    *,
    workspace_id: str,
    candidate_uris: tuple[str, ...],
) -> frozenset[str]:
    """Compute server-side `READ_SOURCE` allowlist via Catalog ACLs and Permission Broker."""
    if not candidate_uris:
        return frozenset()
    authorizer = await prepare_server_source_uri_authorizer(
        request, user, workspace_id=workspace_id
    )
    return authorizer(candidate_uris)


__all__ = [
    "can_user_manage_workspace_governance",
    "enforce_assistant_workspace_guard",
    "filter_allowed_source_uris_with_evaluator",
    "prepare_server_source_uri_authorizer",
    "require_not_observer_write",
    "resolve_assistant_workspace_uuid",
    "resolve_server_allowed_source_uris",
]
