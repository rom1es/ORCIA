"""Shared RBAC & ScopeAccessGuard callbacks for guarded entity deletion (`Story 31.5`)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import (
    sync_evaluator_topology_from_pg,
    user_governs_org_unit,
)
from orcia_api.routers._workspace_packs_guards import trace_id_for
from orcia_api.routers.auth import resolve_request_user
from orcia_core.packs import decode_json_dict
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.service import AuthAndOrganizationService

DraftAuthFn = Callable[[str, str, str], None]


def _assert_workspace_write_access(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    workspace_id: str,
    *,
    instance: str,
) -> None:
    ws = auth_svc.evaluator.get_workspace(workspace_id)
    if (
        ws is not None
        and ws.ui_visibility_mode == "PRIVATE_USER"
        and (ws.personal_owner_user_id is None or str(ws.personal_owner_user_id) != str(user.id))
    ):
        raise ScopeAccessDeniedError(instance=instance)
    acc = auth_svc.evaluator.resolve_workspace_access(user, workspace_id)
    if acc is None:
        raise ScopeAccessDeniedError(instance=instance)
    if acc.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)


def _is_admin(user: UserIdentity) -> bool:
    return user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles


def _assert_scope_write(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    *,
    scope_type: str,
    scope_id: str,
    instance: str,
) -> None:
    if _is_admin(user):
        return
    st = scope_type.strip().upper()
    if st == "WORKSPACE" and scope_id:
        _assert_workspace_write_access(auth_svc, user, scope_id, instance=instance)
        return
    if st in ("BU", "TEAM") and scope_id:
        if not user_governs_org_unit(auth_svc, user, scope_id):
            raise ScopeAccessDeniedError(instance=instance)
        return
    raise ScopeAccessDeniedError(instance=instance)


async def prepare_entity_delete_guards(
    request: Request,
    *,
    persona_key: str | None = None,
) -> tuple[UserIdentity, AuthAndOrganizationService, str, DraftAuthFn]:
    """Verify non-observer write posture, sync topology, and return draft authorizer."""
    path = str(request.url.path)
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    if (
        user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR")
        or "OBSERVER" in user.roles
        or "READ_ONLY_OBSERVER" in user.roles
        or (persona_key or "").strip().lower() in ("claire", "observer")
    ):
        raise ObserverModeReadOnlyError(instance=path)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)

    def authorize_draft(_bundle_id: str, draft_scope_type: str, draft_scope_id: str) -> None:
        _assert_scope_write(
            auth_svc,
            user,
            scope_type=draft_scope_type,
            scope_id=draft_scope_id,
            instance=path,
        )

    return user, auth_svc, trace_id_for(request), authorize_draft


def build_catalog_target_authorizer(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    *,
    instance: str,
) -> Callable[[str, str], None]:
    """Authorize catalog asset deletion based on owning workspace or admin role."""

    def _auth(ws_id: str, vis: str) -> None:
        _ = vis
        if ws_id:
            _assert_workspace_write_access(auth_svc, user, ws_id, instance=instance)
        elif not _is_admin(user):
            raise ScopeAccessDeniedError(instance=instance)

    return _auth


def build_wf_vsm_target_authorizer(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    *,
    instance: str,
) -> Callable[[dict[str, Any]], None]:
    """Authorize standalone Workflow v2 / VSM v2 deletion by scope metadata."""

    def _auth(row: dict[str, Any]) -> None:
        if _is_admin(user):
            return
        spec = decode_json_dict(row.get("spec_jsonb"))
        ws_owner = str(spec.get("owner_workspace_id") or spec.get("workspace_id") or "").strip()
        if ws_owner:
            _assert_workspace_write_access(auth_svc, user, ws_owner, instance=instance)
            return
        pid = str(row.get("pack_id") or "").strip()
        for pfx in ("workspace:", "ws:"):
            if pid.lower().startswith(pfx):
                _assert_workspace_write_access(
                    auth_svc, user, pid[len(pfx) :].split(":", 1)[0], instance=instance
                )
                return
        stype = str(spec.get("scope_type") or "").strip().upper()
        sid = str(spec.get("scope_id") or "").strip()
        if stype and sid:
            _assert_scope_write(auth_svc, user, scope_type=stype, scope_id=sid, instance=instance)
            return
        if "TEAM_LEAD" in user.roles or user.platform_role in ("TEAM_LEAD", "ARCHITECT"):
            return
        raise ScopeAccessDeniedError(instance=instance)

    return _auth


def build_ontology_target_authorizer(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    *,
    entity_type: str,
    instance: str,
) -> Callable[[dict[str, Any]], None]:
    """Authorize ontology concept/relation/axiom deletion per L1–L4 level RBAC."""

    def _check_level(lvl: object, sid: object) -> None:
        if _is_admin(user):
            return
        lstr = str(lvl or "").strip().upper()
        sstr = str(sid or "").strip()
        if lstr in ("2_DOMAIN", "2_BU", "2_ORG_UNIT", "TEAM", "3_TEAM"):
            if "ONTOLOGY_LEAD" in user.roles or (
                sstr and user_governs_org_unit(auth_svc, user, sstr)
            ):
                return
            raise ScopeAccessDeniedError(instance=instance)
        if lstr in ("3_WORKSPACE", "4_WORKSPACE", "4_RUN_EPHEMERAL", "WORKSPACE") and sstr:
            _assert_workspace_write_access(auth_svc, user, sstr, instance=instance)
            return
        raise ScopeAccessDeniedError(instance=instance)

    def _auth(row: dict[str, Any]) -> None:
        if entity_type == "ONTOLOGY_RELATION":
            if row.get("src_level"):
                _check_level(row.get("src_level"), row.get("src_scope_id"))
            if row.get("tgt_level"):
                _check_level(row.get("tgt_level"), row.get("tgt_scope_id"))
            if not row.get("src_level") and not row.get("tgt_level") and not _is_admin(user):
                raise ScopeAccessDeniedError(instance=instance)
            return
        _check_level(row.get("level"), row.get("scope_id"))

    return _auth


def build_policy_target_authorizer(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    *,
    instance: str,
) -> Callable[[dict[str, Any]], None]:
    """Authorize Permission Broker policy deletion."""

    def _auth(row: dict[str, Any]) -> None:
        if _is_admin(user):
            return
        pk = str(row.get("policy_key") or "").strip()
        for pfx in ("ws:", "workspace:"):
            if pk.lower().startswith(pfx):
                _assert_workspace_write_access(
                    auth_svc, user, pk[len(pfx) :].split(":", 1)[0], instance=instance
                )
                return
        raise ScopeAccessDeniedError(instance=instance)

    return _auth


def build_dna_target_authorizer(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    *,
    instance: str,
) -> Callable[[dict[str, Any]], None]:
    """Authorize DNA mechanism deletion against its owning CUSTOM DRAFT bundle scope."""

    def _auth(row: dict[str, Any]) -> None:
        if not row.get("bid"):
            if not _is_admin(user):
                raise ScopeAccessDeniedError(instance=instance)
            return
        _assert_scope_write(
            auth_svc,
            user,
            scope_type=str(row.get("scope_type") or "WORKSPACE"),
            scope_id=str(row.get("scope_id") or ""),
            instance=instance,
        )

    return _auth


__all__ = [
    "DraftAuthFn",
    "build_catalog_target_authorizer",
    "build_dna_target_authorizer",
    "build_ontology_target_authorizer",
    "build_policy_target_authorizer",
    "build_wf_vsm_target_authorizer",
    "prepare_entity_delete_guards",
]
