"""Workspace-Scoped Pack Activation, Priority Reorder & Slot Bindings Router (`Story 31.4`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_workflow_v2_runs_store,
    get_workflows_v2_runs_sql_store,
    get_workspace_packs_service,
)
from orcia_api.routers._workflows_pack_lock_helpers import execute_get_run_lock_handler
from orcia_api.routers._workspace_packs_guards import (
    enforce_workspace_packs_access,
    refresh_workspace_catalog_consistency,
    serialize_slot_binding,
    serialize_workspace_pack,
    trace_id_for,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas._workspace_packs import (
    ActivateWorkspacePackRequest,
    ActivateWorkspacePackResponse,
    BindWorkspacePackSlotsRequest,
    BindWorkspacePackSlotsResponse,
    DeactivateWorkspacePackResponse,
    ReorderedWorkspacePackItemResponse,
    ReorderWorkspacePacksRequest,
    ReorderWorkspacePacksResponse,
    RunLockManifestReadResponse,
    WorkspacePacksListResponse,
)
from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState
from orcia_core.packs import PackSlotTargetKind, SlotBindingInput, WorkspacePacksService
from orcia_core.workflows import SqlWorkflowV2RunsStore

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/packs",
    tags=["Workspace Packs & Connector Slots (Story 31.4)"],
    responses=PROBLEM_RESPONSES,
)

WorkspacePacksSvcDep = Annotated[WorkspacePacksService, Depends(get_workspace_packs_service)]
WorkspaceIdPath = Annotated[str, Path(min_length=1, max_length=128)]
PackSlugPath = Annotated[str, Path(min_length=1, max_length=128)]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@router.get("", response_model=WorkspacePacksListResponse)
async def list_workspace_packs(
    workspace_id: WorkspaceIdPath,
    request: Request,
    svc: WorkspacePacksSvcDep,
    persona_key: PersonaQuery = None,
) -> WorkspacePacksListResponse:
    """List packs visible to `workspace_id` with activation order, slot bindings & missing slots."""
    _, resolved_ws_id = await enforce_workspace_packs_access(
        request, workspace_id, require_write=False, persona_key=persona_key
    )
    views = await svc.list_workspace_packs(resolved_ws_id, instance=str(request.url.path))
    return WorkspacePacksListResponse(
        workspace_id=resolved_ws_id,
        packs=[serialize_workspace_pack(v) for v in views],
        trace_id=trace_id_for(request),
    )


@router.put("/reorder", response_model=ReorderWorkspacePacksResponse)
async def reorder_workspace_packs(
    workspace_id: WorkspaceIdPath,
    payload: ReorderWorkspacePacksRequest,
    request: Request,
    svc: WorkspacePacksSvcDep,
    persona_key: PersonaQuery = None,
) -> ReorderWorkspacePacksResponse:
    """Atomically reorder active workspace packs via `DEFERRABLE` priority constraint."""
    user, resolved_ws_id = await enforce_workspace_packs_access(
        request, workspace_id, require_write=True, persona_key=persona_key
    )
    trace_id = trace_id_for(request)
    updated = await svc.reorder_packs(
        workspace_id=resolved_ws_id,
        ordered_pack_slugs=payload.ordered_pack_slugs,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    await refresh_workspace_catalog_consistency(request, resolved_ws_id)
    return ReorderWorkspacePacksResponse(
        workspace_id=resolved_ws_id,
        packs=[ReorderedWorkspacePackItemResponse(**item) for item in updated],
        trace_id=trace_id,
    )


@router.post("/{slug}/activate", response_model=ActivateWorkspacePackResponse)
async def activate_workspace_pack(
    workspace_id: WorkspaceIdPath,
    slug: PackSlugPath,
    request: Request,
    svc: WorkspacePacksSvcDep,
    payload: Annotated[ActivateWorkspacePackRequest | None, Body()] = None,
    persona_key: PersonaQuery = None,
) -> ActivateWorkspacePackResponse:
    """Activate a pack in `workspace_id` (fails with `422 ERR_PACK_SLOT_UNBOUND` if unbound)."""
    user, resolved_ws_id = await enforce_workspace_packs_access(
        request, workspace_id, require_write=True, persona_key=persona_key
    )
    body = payload or ActivateWorkspacePackRequest()
    trace_id = trace_id_for(request)
    bindings = [
        SlotBindingInput(
            slot_key=item.slot_key,
            target_kind=PackSlotTargetKind(item.target_kind),
            target_id=item.target_id,
            connector_scheme=item.connector_scheme,
        )
        for item in body.slot_bindings
    ]
    res = await svc.activate_pack(
        workspace_id=resolved_ws_id,
        pack_slug=slug,
        bundle_id=body.bundle_id,
        version=body.version,
        priority_order=body.priority_order,
        slot_bindings=bindings,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    await refresh_workspace_catalog_consistency(request, resolved_ws_id)
    return ActivateWorkspacePackResponse(
        activation_id=str(res["activation_id"]),
        workspace_id=str(res["workspace_id"]),
        pack_bundle_id=str(res["pack_bundle_id"]),
        pack_slug=str(res["pack_slug"]),
        version=str(res["version"]),
        priority_order=int(res["priority_order"]),
        is_active=True,
        activated_at_iso=str(res["activated_at_iso"]),
        trace_id=trace_id,
    )


@router.delete("/{slug}/deactivate", response_model=DeactivateWorkspacePackResponse)
async def deactivate_workspace_pack(
    workspace_id: WorkspaceIdPath,
    slug: PackSlugPath,
    request: Request,
    svc: WorkspacePacksSvcDep,
    persona_key: PersonaQuery = None,
) -> DeactivateWorkspacePackResponse:
    """Deactivate a pack in `workspace_id` (`is_active=FALSE, priority_order=NULL`)."""
    user, resolved_ws_id = await enforce_workspace_packs_access(
        request, workspace_id, require_write=True, persona_key=persona_key
    )
    trace_id = trace_id_for(request)
    res = await svc.deactivate_pack(
        workspace_id=resolved_ws_id,
        pack_slug=slug,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    await refresh_workspace_catalog_consistency(request, resolved_ws_id)
    return DeactivateWorkspacePackResponse(
        workspace_id=str(res["workspace_id"]),
        pack_bundle_id=str(res["pack_bundle_id"]),
        pack_slug=str(res["pack_slug"]),
        is_active=False,
        trace_id=trace_id,
    )


@router.put("/{slug}/slots", response_model=BindWorkspacePackSlotsResponse)
async def bind_workspace_pack_slots(
    workspace_id: WorkspaceIdPath,
    slug: PackSlugPath,
    payload: BindWorkspacePackSlotsRequest,
    request: Request,
    svc: WorkspacePacksSvcDep,
    persona_key: PersonaQuery = None,
) -> BindWorkspacePackSlotsResponse:
    """Bind declared connector slots on a workspace pack and emit `PACK_SLOTS_BOUND`."""
    user, resolved_ws_id = await enforce_workspace_packs_access(
        request, workspace_id, require_write=True, persona_key=persona_key
    )
    trace_id = trace_id_for(request)
    bindings = [
        SlotBindingInput(
            slot_key=item.slot_key,
            target_kind=PackSlotTargetKind(item.target_kind),
            target_id=item.target_id,
            connector_scheme=item.connector_scheme,
        )
        for item in payload.bindings
    ]
    updated = await svc.bind_pack_slots(
        workspace_id=resolved_ws_id,
        pack_slug=slug,
        bindings=bindings,
        bundle_id=payload.bundle_id,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    return BindWorkspacePackSlotsResponse(
        workspace_id=resolved_ws_id,
        pack_slug=slug.strip().lower(),
        slot_bindings=[serialize_slot_binding(b) for b in updated],
        trace_id=trace_id,
    )


run_lock_router = APIRouter(
    tags=["Process Studio v2 & VSM (Epic 14)"],
    responses=PROBLEM_RESPONSES,
)


@run_lock_router.get("/api/v1/runs/{run_id}/lock", response_model=RunLockManifestReadResponse)
async def get_workflow_v2_run_lock(
    run_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    runs_store: Annotated[dict[str, BoundedWorkflowRunState], Depends(get_workflow_v2_runs_store)],
    sql_runs_store: Annotated[SqlWorkflowV2RunsStore, Depends(get_workflows_v2_runs_sql_store)],
    persona_key: PersonaQuery = None,
) -> RunLockManifestReadResponse:
    """Return immutable `run_lock_manifests` snapshot for `run_id` (`Story 31.4`)."""
    return await execute_get_run_lock_handler(
        run_id, request, runs_store, sql_runs_store, persona_key=persona_key
    )
