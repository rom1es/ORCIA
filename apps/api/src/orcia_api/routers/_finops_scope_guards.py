"""Scope topology synchronization and read-side RBAC/ABAC resolvers for FinOps routers."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_topology_sync import sync_evaluator_topology_from_pg
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.service import AuthAndOrganizationService
from orcia_kernel.errors import ValidationDomainError


def validate_uuid(val: str, field_name: str) -> str:
    """Validate UUID syntax and raise `ValidationDomainError` (RFC 9457 422) on failure."""
    trimmed = (val or "").strip()
    try:
        UUID(trimmed)
        return trimmed
    except (ValueError, TypeError, AttributeError) as err:
        raise ValidationDomainError(
            detail_override=f"Invalid UUID format for '{field_name}': {val!r}"
        ) from err


def user_governs_org_unit(
    auth_svc: AuthAndOrganizationService,
    user: UserIdentity,
    org_unit_id: str,
) -> bool:
    """Return `True` if `user` has administrative or lead governance over `org_unit_id`."""
    if user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles:
        return True
    governor_roles = {"BU_DIRECTOR", "BU_LEAD", "TEAM_LEAD"}
    user_roles = {str(user.platform_role).upper(), *(str(r).upper() for r in user.roles)}
    if user.primary_org_unit_id == org_unit_id and (user_roles & governor_roles):
        return True
    if auth_svc.evaluator.is_ancestor_of(user.primary_org_unit_id, org_unit_id) and (
        user_roles & governor_roles
    ):
        return True
    for node in auth_svc.evaluator.org_units:
        extra = (node.lead_user_id,) if node.lead_user_id else ()
        leads = {x.lower() for x in (*node.lead_user_ids, *extra)}
        if (user.id.lower() in leads or user.email.lower() in leads) and (
            node.id == org_unit_id or auth_svc.evaluator.is_ancestor_of(node.id, org_unit_id)
        ):
            return True
    return False


async def resolve_finops_read_scope(
    request: Request,
    user: UserIdentity,
    scope_type: ScopeType,
    scope_id: str | None,
) -> tuple[str, ...] | None:
    """Enforce read RBAC/ABAC; return allowed workspace UUIDs or `None` for unrestricted admin."""
    path = str(request.url.path)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)

    is_platform_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    accessible = auth_svc.evaluator.resolve_accessible_workspaces(user)
    accessible_ids = tuple(a.workspace.id for a in accessible)

    if scope_type == "WORKSPACE":
        if scope_id is None:
            raise ValidationDomainError(
                detail_override="scope_id is required when scope_type is 'WORKSPACE'."
            )
        ws = auth_svc.evaluator.get_workspace(scope_id)
        if ws is None:
            raise ResourceNotFoundError(instance=path)
        if ws.ui_visibility_mode == "PRIVATE_USER" and (
            ws.personal_owner_user_id is None or str(ws.personal_owner_user_id) != str(user.id)
        ):
            raise ScopeAccessDeniedError(instance=path)
        if auth_svc.evaluator.resolve_workspace_access(user, ws.id) is None:
            raise ScopeAccessDeniedError(instance=path)
        return (ws.id,)

    if scope_type in ("BU", "TEAM"):
        if scope_id is None:
            raise ValidationDomainError(
                detail_override=f"scope_id is required when scope_type is '{scope_type}'."
            )
        if not auth_svc.evaluator.has_org_unit(scope_id):
            raise ResourceNotFoundError(instance=path)
        allowed_ous = {scope_id, *auth_svc.evaluator.get_descendant_org_unit_ids(scope_id)}
        ws_under_scope = [
            a.workspace.id for a in accessible if a.workspace.owner_org_unit_id in allowed_ous
        ]
        if (
            not is_platform_admin
            and not user_governs_org_unit(auth_svc, user, scope_id)
            and not ws_under_scope
        ):
            raise ScopeAccessDeniedError(instance=path)
        if is_platform_admin:
            restricted_unaccessible = [
                w
                for w in auth_svc.evaluator.workspaces
                if w.owner_org_unit_id in allowed_ous
                and auth_svc.evaluator.resolve_workspace_access(user, w.id) is None
            ]
            return None if not restricted_unaccessible else accessible_ids
        return tuple(ws_under_scope)

    # GLOBAL read
    if is_platform_admin:
        restricted_unaccessible = [
            w
            for w in auth_svc.evaluator.workspaces
            if auth_svc.evaluator.resolve_workspace_access(user, w.id) is None
        ]
        return None if not restricted_unaccessible else accessible_ids

    if user.platform_role not in ("BU_DIRECTOR", "TEAM_LEAD", "OBSERVER") and not accessible_ids:
        raise ScopeAccessDeniedError(instance=path)
    return accessible_ids


async def resolve_run_workspace_server_side(
    request: Request,
    run_id: str,
) -> str | None:
    """Resolve `workflow_runs.workspace_id` from PostgreSQL (anti-IDOR server-side derivation)."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        return None
    async with engine.connect() as conn:
        ws_id = (
            await conn.execute(
                sa.text(
                    "SELECT workspace_id::text FROM workflow_runs WHERE id = CAST(:id AS uuid)"
                ),
                {"id": run_id},
            )
        ).scalar()
        return str(ws_id) if ws_id else None


async def resolve_workflow_def_workspace_server_side(
    request: Request,
    workflow_def_id: str,
) -> str | None:
    """Resolve `workflow_definitions.workspace_id` from PostgreSQL."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        return None
    async with engine.connect() as conn:
        ws_id = (
            await conn.execute(
                sa.text(
                    "SELECT workspace_id::text FROM workflow_definitions "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": workflow_def_id},
            )
        ).scalar()
        return str(ws_id) if ws_id else None


__all__ = [
    "resolve_finops_read_scope",
    "resolve_run_workspace_server_side",
    "resolve_workflow_def_workspace_server_side",
    "sync_evaluator_topology_from_pg",
    "user_governs_org_unit",
    "validate_uuid",
]
