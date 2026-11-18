"""Scope topology synchronization and read-side RBAC/ABAC resolvers for FinOps routers."""

from __future__ import annotations

import json
import os
import re
from typing import cast
from uuid import UUID, uuid5

import sqlalchemy as sa
from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.permissions.models import (
    OrgUnitNode,
    OrgUnitType,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceVisibilityMode,
)
from orcia_core.permissions.service import AuthAndOrganizationService
from orcia_kernel.errors import ValidationDomainError

logger = get_logger("orcia.api.finops.guards")


_NAMESPACE_ORCIA_SETUP = UUID("0192c4e0-0000-7000-8000-000000000099")
_SETUP_WS_KEY_RE = re.compile(r"^ws-\d+$")


def validate_uuid(val: str, field_name: str) -> str:
    """Validate UUID syntax and raise `ValidationDomainError` (RFC 9457 422) on failure."""
    try:
        UUID(val)
        return val
    except (ValueError, TypeError, AttributeError) as err:
        raise ValidationDomainError(
            detail_override=f"Invalid UUID format for '{field_name}': {val!r}"
        ) from err


def resolve_workspace_uuid_or_setup_key(raw_ws_id: str, field_name: str = "workspace_id") -> str:
    """Map UI setup workspace key (`ws-1` -> deterministic UUIDv5) or validate UUID."""
    trimmed = raw_ws_id.strip()
    if _SETUP_WS_KEY_RE.match(trimmed):
        return str(uuid5(_NAMESPACE_ORCIA_SETUP, f"ws:{trimmed}"))
    return validate_uuid(trimmed, field_name)


async def sync_evaluator_topology_from_pg(
    request: Request,
    auth_svc: AuthAndOrganizationService,
) -> None:
    """Ensure `auth_svc.evaluator` reflects `org_units` and `workspaces` present in PG18."""
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") == "1":
        return
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        return
    try:
        async with engine.connect() as conn:
            ou_rows = (
                (
                    await conn.execute(
                        sa.text(
                            """
                        SELECT id, slug, name, unit_type, parent_id,
                               lead_user_id, lead_user_ids_jsonb, member_user_ids_jsonb
                        FROM org_units;
                        """
                        )
                    )
                )
                .mappings()
                .all()
            )
            for r in ou_rows:
                ou_id = str(r["id"])
                raw_leads = r.get("lead_user_ids_jsonb") or []
                if isinstance(raw_leads, str):
                    raw_leads = json.loads(raw_leads)
                raw_members = r.get("member_user_ids_jsonb") or []
                if isinstance(raw_members, str):
                    raw_members = json.loads(raw_members)
                auth_svc.evaluator.upsert_org_unit(
                    OrgUnitNode(
                        id=ou_id,
                        slug=str(r["slug"]),
                        name=str(r["name"]),
                        unit_type=cast(OrgUnitType, str(r["unit_type"])),
                        parent_id=str(r["parent_id"]) if r["parent_id"] else None,
                        lead_user_id=str(r["lead_user_id"]) if r["lead_user_id"] else None,
                        lead_user_ids=tuple(str(x) for x in raw_leads),
                        member_user_ids=tuple(str(x) for x in raw_members),
                    )
                )

            ws_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id, slug, name, owner_org_unit_id, visibility_mode "
                            "FROM workspaces;"
                        )
                    )
                )
                .mappings()
                .all()
            )
            for w in ws_rows:
                ws_id = str(w["id"])
                existing = auth_svc.evaluator.get_workspace(ws_id)
                if existing is None or existing.owner_org_unit_id != str(w["owner_org_unit_id"]):
                    auth_svc.evaluator.upsert_workspace(
                        WorkspaceEntity(
                            id=ws_id,
                            slug=str(w["slug"]),
                            name=str(w["name"]),
                            owner_org_unit_id=str(w["owner_org_unit_id"]),
                            visibility_mode=cast(
                                WorkspaceVisibilityMode, str(w["visibility_mode"])
                            ),
                            datasources=existing.datasources if existing else (),
                        )
                    )
    except Exception as exc:
        logger.warning(
            "finops_sync_evaluator_topology_fallback",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        return


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
