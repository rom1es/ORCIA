"""Workspaces, ScopeAccessGuard & 5 Dissociated Catalog Permissions Router (AD-6, AD-14, FR-21)."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.routers.auth import (
    PROBLEM_RESPONSES,
    get_auth_service,
    resolve_request_user,
    serialize_workspace_summary,
)
from orcia_core.domain.exceptions import ResourceNotFoundError
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.schemas.auth_and_org import (
    CatalogResourceInspectionResponse,
    CatalogResourceSourceResponse,
    ScopeMutationCheckResponse,
    WorkspacesListResponse,
)

router = APIRouter(prefix="/api/v1", tags=["workspaces-and-catalog"])


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
    user = resolve_request_user(request, persona_key=persona_key)
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
