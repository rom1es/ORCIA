"""Shared RBAC/ABAC & anti-IDOR guards for FinOps and Audit Ledger routers (`BLOCKING-05`).

Centralizes:
- Observer mode checks (`READ_ONLY_OBSERVER` -> `403 ERR_OBSERVER_MODE_READ_ONLY`)
- Mutation scope guards (`enforce_scope_mutation_guard` & governor validation)
- Audit Ledger anti-IDOR read access enforcement
- Re-export of scope/topology helpers from `_finops_scope_guards`
"""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_scope_guards import (
    resolve_finops_read_scope,
    resolve_run_workspace_server_side,
    resolve_workflow_def_workspace_server_side,
    sync_evaluator_topology_from_pg,
    user_governs_org_unit,
    validate_uuid,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.service import AuthAndOrganizationService
from orcia_kernel.errors import ValidationDomainError


def enforce_observer_headers_guard(request: Request, user: UserIdentity) -> None:
    """Reject `READ_ONLY_OBSERVER` callers immediately with `403 ERR_OBSERVER_MODE_READ_ONLY`."""
    path = str(request.url.path)
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()

    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or active_hat in ("READ_ONLY_OBSERVER", "OBSERVER")
        or observer_hdr in ("1", "true", "yes")
        or user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER")
    ):
        raise ObserverModeReadOnlyError(instance=path)


async def enforce_scope_level_mutation(
    request: Request,
    user: UserIdentity,
    *,
    scope_type: ScopeType,
    scope_id: str | None,
) -> None:
    """Enforce `enforce_scope_mutation_guard` for WORKSPACE or governor role for GLOBAL/BU/TEAM."""
    path = str(request.url.path)
    enforce_observer_headers_guard(request, user)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)

    is_platform_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    if scope_type == "WORKSPACE":
        if scope_id is None:
            raise ValidationDomainError(
                detail_override="scope_id is required for WORKSPACE-scoped FinOps mutation."
            )
        ws = auth_svc.evaluator.get_workspace(scope_id)
        if ws is None:
            raise ResourceNotFoundError(instance=path)
        if is_platform_admin and ws.visibility_mode != "CONFIDENTIAL_RESTRICTED":
            return
        auth_svc.evaluator.enforce_scope_mutation_guard(user, scope_id, instance=path)
        return

    if scope_type == "GLOBAL":
        if not is_platform_admin:
            raise ScopeAccessDeniedError(instance=path)
        return

    # BU or TEAM
    if scope_id is None:
        raise ValidationDomainError(
            detail_override=f"scope_id is required for {scope_type}-scoped FinOps mutation."
        )
    if not auth_svc.evaluator.has_org_unit(scope_id):
        raise ResourceNotFoundError(instance=path)
    if is_platform_admin:
        return
    if scope_type == "BU" and user.platform_role != "BU_DIRECTOR":
        raise ScopeAccessDeniedError(instance=path)
    if scope_type == "TEAM" and user.platform_role not in ("BU_DIRECTOR", "TEAM_LEAD"):
        raise ScopeAccessDeniedError(instance=path)
    if not user_governs_org_unit(auth_svc, user, scope_id):
        raise ScopeAccessDeniedError(instance=path)


def resolve_workspace_canonical_scope_path(
    auth_svc: AuthAndOrganizationService,
    workspace_id: str,
) -> str:
    """Derive canonical hierarchical `scope_path` from workspace `org_unit` topology."""
    ws = auth_svc.evaluator.get_workspace(workspace_id)
    if ws is None:
        return f"org/workspace/{workspace_id}"
    slugs: list[str] = []
    curr_ou_id: str | None = ws.owner_org_unit_id
    visited: set[str] = set()
    while curr_ou_id and curr_ou_id not in visited:
        visited.add(curr_ou_id)
        node = auth_svc.evaluator.get_org_unit(curr_ou_id)
        if node is None:
            break
        slugs.append(node.slug)
        curr_ou_id = node.parent_id
    slugs.reverse()
    chain = "/".join(slugs) if slugs else ws.owner_org_unit_id
    return f"org/{chain}/{ws.slug}"


async def enforce_workspace_governed_mutation(
    request: Request,
    user: UserIdentity,
    workspace_id: str,
    *,
    allowed_roles: tuple[str, ...] = (
        "PLATFORM_ADMIN",
        "BU_DIRECTOR",
        "BU_LEAD",
        "TEAM_LEAD",
        "ARCHITECT",
    ),
) -> str:
    """Enforce observer, workspace existence, scope mutation & governor role checks."""
    path = str(request.url.path)
    await enforce_scope_level_mutation(
        request,
        user,
        scope_type="WORKSPACE",
        scope_id=workspace_id,
    )
    user_roles = {str(user.platform_role).upper(), *(str(r).upper() for r in user.roles)}
    if not (user_roles & set(allowed_roles)):
        raise ScopeAccessDeniedError(instance=path)
    auth_svc = get_auth_service(request)
    return resolve_workspace_canonical_scope_path(auth_svc, workspace_id)


async def enforce_audit_read_access(
    request: Request,
    user: UserIdentity,
    *,
    requested_workspace_id: str | None = None,
    requested_run_id: str | None = None,
) -> tuple[str, ...] | None:
    """Enforce read-side anti-IDOR permissions for `/api/v1/audit/ledger*` endpoints."""
    path = str(request.url.path)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)

    is_platform_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    accessible = auth_svc.evaluator.resolve_accessible_workspaces(user)
    accessible_ids = tuple(a.workspace.id for a in accessible)

    if requested_workspace_id is not None:
        validate_uuid(requested_workspace_id, "workspace_id")
        ws = auth_svc.evaluator.get_workspace(requested_workspace_id)
        if ws is None:
            raise ResourceNotFoundError(instance=path)
        if auth_svc.evaluator.resolve_workspace_access(user, ws.id) is None:
            raise ScopeAccessDeniedError(instance=path)
        return (ws.id,)

    if requested_run_id is not None:
        validate_uuid(requested_run_id, "run_id")
        engine = getattr(request.app.state, "db_engine", None)
        if engine is not None:
            async with engine.connect() as conn:
                run_ws = (
                    await conn.execute(
                        sa.text(
                            "SELECT workspace_id::text FROM workflow_runs "
                            "WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": requested_run_id},
                    )
                ).scalar()
                if run_ws:
                    if auth_svc.evaluator.resolve_workspace_access(user, str(run_ws)) is None:
                        raise ScopeAccessDeniedError(instance=path)
                    return (str(run_ws),)
                ledger_rows = (
                    await conn.execute(
                        sa.text(
                            "SELECT DISTINCT workspace_id::text FROM audit_ledger "
                            "WHERE run_id = CAST(:id AS uuid)"
                        ),
                        {"id": requested_run_id},
                    )
                ).all()
                if ledger_rows:
                    ws_vals = [str(r[0]) for r in ledger_rows if r[0] is not None]
                    if not ws_vals and not is_platform_admin:
                        raise ScopeAccessDeniedError(instance=path)
                    for wid in ws_vals:
                        if auth_svc.evaluator.resolve_workspace_access(user, wid) is None:
                            raise ScopeAccessDeniedError(instance=path)
                    return None if is_platform_admin else accessible_ids

    if is_platform_admin:
        restricted_unaccessible = [
            w
            for w in auth_svc.evaluator.workspaces
            if auth_svc.evaluator.resolve_workspace_access(user, w.id) is None
        ]
        return None if not restricted_unaccessible else accessible_ids

    return accessible_ids


__all__ = [
    "enforce_audit_read_access",
    "enforce_observer_headers_guard",
    "enforce_scope_level_mutation",
    "enforce_workspace_governed_mutation",
    "resolve_finops_read_scope",
    "resolve_run_workspace_server_side",
    "resolve_workspace_canonical_scope_path",
    "resolve_workflow_def_workspace_server_side",
    "sync_evaluator_topology_from_pg",
    "validate_uuid",
]
