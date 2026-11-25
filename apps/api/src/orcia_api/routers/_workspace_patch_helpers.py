"""Scoped `PATCH /api/v1/workspaces/{workspace_id}` guard, persistence & audit (`Story 29.2`)."""

from __future__ import annotations

from typing import Literal, cast

from fastapi import Request

from orcia_api.dependencies import get_audit_ledger_service
from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    should_auto_init_infra,
)
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import (
    sync_evaluator_topology_from_pg,
    user_governs_org_unit,
)
from orcia_api.schemas.org_and_workspaces import WorkspacePatchRequest, WorkspacePatchResponse
from orcia_core.bootstrap.setup_snapshot_cache import invalidate_platform_setup_snapshot_async
from orcia_core.bootstrap.workspaces_patch import patch_workspace_on_postgres18
from orcia_core.kernel.errors import TransientInfraError
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    PrivateWorkspaceVisibilityLockedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.permissions.models import (
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    WorkspaceVisibilityMode,
)
from orcia_core.permissions.service import AuthAndOrganizationService
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry
from orcia_kernel.ids import new_uuid7_str

_GOVERNING_ROLES: frozenset[str] = frozenset(
    {"PLATFORM_ADMIN", "BU_DIRECTOR", "BU_LEAD", "TEAM_LEAD"}
)


def _is_personal_ws(ws: WorkspaceEntity) -> bool:
    return (
        ws.personal_owner_user_id is not None
        or ws.ui_visibility_mode == "PRIVATE_USER"
        or ws.slug.startswith("personal-")
    )


def enforce_workspace_patch_access(
    request: Request,
    svc: AuthAndOrganizationService,
    user: UserIdentity,
    workspace_id: str,
    payload: WorkspacePatchRequest,
) -> WorkspaceEntity:
    """Enforce `ScopeAccessGuard` and `PRIVATE_USER` immutability for workspace `PATCH`."""
    path = str(request.url.path)
    enforce_observer_headers_guard(request, user)
    ws = svc.evaluator.get_workspace(workspace_id)
    if ws is None:
        raise ResourceNotFoundError(instance=path)

    is_personal = _is_personal_ws(ws)
    if is_personal:
        if ws.personal_owner_user_id is not None and str(ws.personal_owner_user_id) != str(user.id):
            raise ScopeAccessDeniedError(instance=path)
        if (
            ws.personal_owner_user_id is None
            and svc.evaluator.resolve_workspace_access(user, ws.id) is None
        ):  # noqa: E501
            raise ScopeAccessDeniedError(instance=path)
        if payload.visibility_mode is not None and payload.visibility_mode != "PRIVATE_USER":
            raise PrivateWorkspaceVisibilityLockedError(instance=path)
        return ws

    if payload.visibility_mode == "PRIVATE_USER":
        raise PrivateWorkspaceVisibilityLockedError(instance=path)

    if ws.visibility_mode == "CONFIDENTIAL_RESTRICTED":
        access = svc.evaluator.resolve_workspace_access(user, ws.id)
        if access is None:
            raise ScopeAccessDeniedError(instance=path)
        if access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=path)
        if access.effective_role not in _GOVERNING_ROLES:
            raise ScopeAccessDeniedError(instance=path)
        return ws

    if not user_governs_org_unit(svc, user, ws.owner_org_unit_id):
        raise ScopeAccessDeniedError(instance=path)
    return ws


async def _record_workspace_patch_audit(
    request: Request,
    *,
    user: UserIdentity,
    ws_id: str,
    ws_slug: str,
    owner_ou_id: str,
    ws_name: str,
    ui_vis: str,
    phase: str,
) -> None:
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    entry = FinopsCostLedgerEntry(
        id=new_uuid7_str(),
        source_event_id=new_uuid7_str(),
        actor_type="USER",
        actor_id=user.id,
        actor_display_name=user.display_name,
        actor_email=user.email,
        event_type="WORKSPACE_UPDATED",
        summary=f"Workspace '{ws_name}' updated (visibility={ui_vis}, phase={phase})",
        trace_id=trace_id,
        workspace_id=ws_id,
        org_unit_id=owner_ou_id,
        scope_path=ws_slug,
        metadata={"visibility_mode": ui_vis, "lifecycle_phase": phase, "name": ws_name},
    )
    audit_svc = get_audit_ledger_service(request)
    engine = get_configured_db_engine(request)
    if engine is None:
        await audit_svc.record_entry(entry)
        return
    async with engine.begin() as conn:
        await audit_svc.record_entry(entry, conn=conn)


async def invalidate_setup_snapshot_for_request(request: Request) -> None:
    """Invalidate cached platform setup snapshot in RAM/Redis after workspace mutation."""
    redis_client = getattr(request.app.state, "redis_client", None)
    await invalidate_platform_setup_snapshot_async(request.app.state, redis_client=redis_client)


async def execute_workspace_patch(
    request: Request,
    *,
    svc: AuthAndOrganizationService,
    user: UserIdentity,
    workspace_id: str,
    payload: WorkspacePatchRequest,
) -> WorkspacePatchResponse:
    """Validate, persist, sync evaluator & membership, and write `audit_ledger` on `PATCH`."""
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    await sync_evaluator_topology_from_pg(request, svc)
    ws = enforce_workspace_patch_access(request, svc, user, workspace_id, payload)

    engine = get_configured_db_engine(request)
    if engine is None and should_auto_init_infra("DATABASE_URL"):
        raise TransientInfraError(
            detail_code="ERR_ORG_PG_UNAVAILABLE_WORKSPACE",
            instance=str(request.url.path),
        )

    if engine is not None:
        rec = await patch_workspace_on_postgres18(
            engine,
            workspace_id=ws.id,
            actor_user_id=user.id,
            actor_role=user.platform_role,
            name=payload.name,
            visibility_mode=payload.visibility_mode,
            lifecycle_phase=payload.lifecycle_phase,
            instance=str(request.url.path),
        )
        ws_id, ws_slug, ws_name = rec.id, rec.slug, rec.name
        owner_ou_id, owner_ou_name = rec.owner_org_unit_id, rec.owner_org_unit_name
        db_vis = cast(WorkspaceVisibilityMode, rec.visibility_mode)
        ui_vis = cast(
            Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"],
            rec.ui_visibility_mode,
        )
        phase = cast(Literal["BUILD", "RUN", "MIGRATION"], rec.lifecycle_phase)
        finops_cost = rec.finops_cost_usd
        personal_owner = rec.personal_owner_user_id
    else:
        if payload.name is not None:
            cleaned_name = payload.name.strip()
            if not cleaned_name:
                raise ValidationDomainError(detail_code="ERR_WORKSPACE_EMPTY_NAME")
            ws_name = cleaned_name[:255]
        else:
            ws_name = ws.name
        is_personal = _is_personal_ws(ws)
        ui_vis = cast(
            Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"],
            "PRIVATE_USER"
            if is_personal
            else (payload.visibility_mode or ws.ui_visibility_mode or ws.visibility_mode),
        )
        db_vis = (
            "CONFIDENTIAL_RESTRICTED"
            if ui_vis in ("CONFIDENTIAL_RESTRICTED", "PRIVATE_USER")
            else "STANDARD"
        )
        phase = cast(
            Literal["BUILD", "RUN", "MIGRATION"],
            payload.lifecycle_phase or getattr(ws, "lifecycle_phase", None) or "BUILD",
        )
        ws_id, ws_slug = ws.id, ws.slug
        owner_ou_id = ws.owner_org_unit_id
        owner_node = svc.evaluator.get_org_unit(owner_ou_id)
        owner_ou_name = owner_node.name if owner_node is not None else "ORCIA"
        finops_cost = ws.finops_cost_usd
        personal_owner = ws.personal_owner_user_id

    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug=ws_slug,
            name=ws_name,
            owner_org_unit_id=owner_ou_id,
            visibility_mode=db_vis,
            finops_cost_usd=finops_cost,
            datasources=ws.datasources,
            personal_owner_user_id=personal_owner,
            ui_visibility_mode=ui_vis,
            lifecycle_phase=phase,
        )
    )
    if db_vis == "CONFIDENTIAL_RESTRICTED" and user.platform_role != "OBSERVER":
        svc.evaluator.upsert_membership(
            WorkspaceMembershipEntity(
                id=new_uuid7_str(),
                workspace_id=ws_id,
                role=user.platform_role,
                access_mode="CONTRIBUTOR_ACTION_REQUIRED",
                user_id=user.id,
            )
        )

    await invalidate_setup_snapshot_for_request(request)
    await _record_workspace_patch_audit(
        request,
        user=user,
        ws_id=ws_id,
        ws_slug=ws_slug,
        owner_ou_id=owner_ou_id,
        ws_name=ws_name,
        ui_vis=ui_vis,
        phase=phase,
    )
    access = svc.evaluator.resolve_workspace_access(user, ws_id)
    return WorkspacePatchResponse(
        id=ws_id,
        slug=ws_slug,
        name=ws_name,
        owner_org_unit_id=owner_ou_id,
        owner_org_unit_name=owner_ou_name,
        visibility_mode=ui_vis,
        lifecycle_phase=phase,
        effective_role=access.effective_role if access is not None else user.platform_role,
        access_mode=access.access_mode if access is not None else "CONTRIBUTOR_ACTION_REQUIRED",
        access_origin=access.access_origin if access is not None else "DIRECT_TEAM",
        finops_cost_usd=finops_cost,
        trace_id=trace_id,
    )


__all__ = ["enforce_workspace_patch_access", "execute_workspace_patch"]
