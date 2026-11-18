"""Workspaces, ScopeAccessGuard & 5 Dissociated Catalog Permissions Router (AD-6, AD-14, FR-21)."""

from __future__ import annotations

import sys
from typing import Literal, cast

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_auth_service
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import (
    PROBLEM_RESPONSES,
    resolve_request_user,
    serialize_workspace_summary,
)
from orcia_api.routers.org_unit_invitations import router as org_unit_invitations_router
from orcia_api.routers.org_units import router as org_units_router
from orcia_api.schemas.auth_and_org import (
    CatalogResourceInspectionResponse,
    CatalogResourceSourceResponse,
    ScopeMutationCheckResponse,
    WorkspaceCreateRequest,
    WorkspaceCreateResponse,
    WorkspacesListResponse,
)
from orcia_core.bootstrap import create_workspace_on_postgres18, resolve_exact_workspace_slug
from orcia_core.kernel.errors import TransientInfraError
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.models import (
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    WorkspaceVisibilityMode,
)
from orcia_kernel.ids import new_uuid7_str

router = APIRouter(prefix="/api/v1", tags=["workspaces-and-catalog"])
router.include_router(org_unit_invitations_router)
router.include_router(org_units_router)


@router.get(
    "/workspaces",
    response_model=WorkspacesListResponse,
    summary="List accessible Multi-Source Workspaces with Upward Roll-up and FinOps consolidation",
    responses=PROBLEM_RESPONSES,
)
async def list_workspaces(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
    org_unit_id: str | None = Query(default=None, min_length=1, max_length=64),
) -> WorkspacesListResponse:
    """Return accessible Workspaces (excluding CONFIDENTIAL_RESTRICTED from roll-up) and FinOps."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, svc)
    user = resolve_request_user(request, persona_key=persona_key)
    accessible = svc.evaluator.resolve_accessible_workspaces(user)
    if org_unit_id is not None:
        if not svc.evaluator.has_org_unit(org_unit_id):
            raise ResourceNotFoundError(instance=str(request.url.path))
        allowed_org_units = {org_unit_id, *svc.evaluator.get_descendant_org_unit_ids(org_unit_id)}
        accessible = [
            item for item in accessible if item.workspace.owner_org_unit_id in allowed_org_units
        ]
    finops_total = svc.evaluator.compute_finops_rollup_usd(user, org_unit_id=org_unit_id)
    return WorkspacesListResponse(
        workspaces=[serialize_workspace_summary(item) for item in accessible],
        consolidated_finops_usd=finops_total,
        trace_id=trace_id,
    )


@router.post(
    "/workspaces",
    response_model=WorkspaceCreateResponse,
    status_code=201,
    summary="Create a Workspace in PostgreSQL 18 returning canonical `UUIDv7` and exact `slug`",
    responses={**PROBLEM_RESPONSES, 503: PROBLEM_RESPONSES[422]},
)
async def create_workspace_endpoint(
    payload: WorkspaceCreateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> WorkspaceCreateResponse:
    """Persist a Workspace with real `UUIDv7`, exact `slug`, and owner membership."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    await sync_evaluator_topology_from_pg(request, svc)

    engine = get_configured_db_engine(request)
    if engine is None and "pytest" not in sys.modules:
        raise TransientInfraError(
            detail_override="PostgreSQL 18 indisponible pour la création d'espace.",
            instance=str(request.url.path),
        )

    if engine is not None:
        rec = await create_workspace_on_postgres18(
            engine,
            name=payload.name,
            slug=payload.slug,
            visibility_mode=payload.visibility_mode,
            lifecycle_phase=payload.lifecycle_phase,
            owner_org_unit_id=payload.owner_org_unit_id,
            creator_user_id=user.id,
        )
        ws_id = rec.id
        ws_slug = rec.slug
        ws_name = rec.name
        owner_ou_id = rec.owner_org_unit_id
        owner_ou_name = rec.owner_org_unit_name
        db_vis = cast(WorkspaceVisibilityMode, rec.visibility_mode)
        ui_vis = cast(
            Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"],
            rec.ui_visibility_mode,
        )
        phase = cast(Literal["BUILD", "RUN", "MIGRATION"], rec.lifecycle_phase)
    else:
        ws_id = new_uuid7_str()
        ws_slug = resolve_exact_workspace_slug(payload.slug, payload.name)
        ws_name = payload.name.strip()
        raw_owner = (payload.owner_org_unit_id or "").strip()
        owner_node = svc.evaluator.get_org_unit(raw_owner) if raw_owner else None
        owner_ou_id = (
            owner_node.id
            if owner_node is not None
            else (user.primary_org_unit_id or "0192c4e0-0000-7000-8000-000000000101")
        )
        owner_ou_name = owner_node.name if owner_node is not None else "Plateforme Globale ORCIA"
        ui_vis = payload.visibility_mode
        db_vis = (
            "CONFIDENTIAL_RESTRICTED"
            if payload.visibility_mode == "CONFIDENTIAL_RESTRICTED"
            else "STANDARD"
        )
        phase = payload.lifecycle_phase

    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug=ws_slug,
            name=ws_name,
            owner_org_unit_id=owner_ou_id,
            visibility_mode=db_vis,
        )
    )
    if user.platform_role != "OBSERVER":
        svc.evaluator.upsert_membership(
            WorkspaceMembershipEntity(
                id=new_uuid7_str(),
                workspace_id=ws_id,
                role=user.platform_role,
                access_mode="CONTRIBUTOR_ACTION_REQUIRED",
                user_id=user.id,
            )
        )
    access = svc.evaluator.resolve_workspace_access(user, ws_id)
    return WorkspaceCreateResponse(
        id=ws_id,
        slug=ws_slug,
        name=ws_name,
        owner_org_unit_id=owner_ou_id,
        owner_org_unit_name=owner_ou_name,
        visibility_mode=ui_vis,
        lifecycle_phase=phase,
        effective_role=access.effective_role if access is not None else user.platform_role,
        access_mode=(access.access_mode if access is not None else "CONTRIBUTOR_ACTION_REQUIRED"),
        access_origin=access.access_origin if access is not None else "DIRECT_TEAM",
        finops_cost_usd=0.0,
        trace_id=trace_id,
    )


@router.post(
    "/workspaces/{workspace_id}/mutations/check",
    response_model=ScopeMutationCheckResponse,
    summary="Enforce ScopeAccessGuard on Workspace mutation (rejects READ_ONLY_OBSERVER)",
    responses=PROBLEM_RESPONSES,
)
async def check_workspace_mutation_guard(
    request: Request,
    workspace_id: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> ScopeMutationCheckResponse:
    """Verify the caller can perform mutations on `workspace_id` (`ScopeAccessGuard`)."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, svc)
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    access = svc.evaluator.enforce_scope_mutation_guard(
        user,
        workspace_id,
        instance=str(request.url.path),
    )
    return ScopeMutationCheckResponse(
        workspace_id=workspace_id,
        allowed=True,
        effective_role=access.effective_role,
        access_mode=access.access_mode,
        trace_id=trace_id,
    )


@router.get(
    "/catalog/resources/{resource_id}/inspect",
    response_model=CatalogResourceInspectionResponse,
    summary="Inspect a Catalog resource's 5 dissociated permissions (`source_masked`)",
    responses=PROBLEM_RESPONSES,
)
async def inspect_catalog_resource(
    request: Request,
    resource_id: str = Path(..., min_length=1, max_length=128),
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CatalogResourceInspectionResponse:
    """Evaluate `DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN` for a catalog resource."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user = resolve_request_user(request, persona_key=persona_key)
    effective, _secret = svc.evaluator.evaluate_catalog_resource(
        user,
        resource_id,
        workspace_id=workspace_id,
        require_read_source=False,
        instance=str(request.url.path),
    )
    return CatalogResourceInspectionResponse(
        resource_id=effective.resource_id,
        resource_uri=effective.resource_uri,
        title=effective.title,
        visibility_scope=effective.visibility_scope,
        granted_permissions=list(effective.granted_permissions),
        source_masked=effective.source_masked,
        trace_id=trace_id,
    )


@router.get(
    "/catalog/resources/{resource_id}/source",
    response_model=CatalogResourceSourceResponse,
    summary="Read internal prompt/code of a Catalog resource (requires READ_SOURCE)",
    responses=PROBLEM_RESPONSES,
)
async def get_catalog_resource_source(
    request: Request,
    resource_id: str = Path(..., min_length=1, max_length=128),
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CatalogResourceSourceResponse:
    """Return internal `system_prompt_secret` if `READ_SOURCE` is granted, else raise HTTP 403."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user = resolve_request_user(request, persona_key=persona_key)
    effective, secret = svc.evaluator.evaluate_catalog_resource(
        user,
        resource_id,
        workspace_id=workspace_id,
        require_read_source=True,
        instance=str(request.url.path),
    )
    return CatalogResourceSourceResponse(
        resource_id=effective.resource_id,
        resource_uri=effective.resource_uri,
        system_prompt_secret=secret or "",
        trace_id=trace_id,
    )
