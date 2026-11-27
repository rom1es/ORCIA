"""Fail-closed pack slot readiness & `run_lock_manifests` helpers for workflows v2 (`31.4`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException, Request

from orcia_api.dependencies import get_workspace_packs_service
from orcia_api.dependencies._core_providers import is_pg_runtime_active
from orcia_api.routers._finops_scope_guards import resolve_finops_read_scope
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas._workspace_packs import (
    PinnedPackManifestSchema,
    ResolvedPackSlotSchema,
    RunLockManifestReadResponse,
)
from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.packs import PinnedPackManifestEntry
from orcia_core.workflows import SqlWorkflowV2RunsStore
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2


async def enforce_and_snapshot_workspace_packs(
    request: Request,
    *,
    workspace_id: str | None,
    workflow: WorkflowDefinitionV2,
) -> list[PinnedPackManifestEntry]:
    """Fail closed (`422 ERR_PACK_SLOT_UNBOUND`) or snapshot active workspace packs."""
    if not is_pg_runtime_active(request):
        return []
    packs_svc = get_workspace_packs_service(request)
    if not packs_svc.has_engine():
        return []
    return await packs_svc.enforce_run_start_readiness(
        workspace_id=workspace_id,
        workflow_pack_id=workflow.pack_id,
        instance=str(request.url.path),
    )


async def pin_and_sync_v2_run_lock(
    request: Request,
    *,
    run_state: BoundedWorkflowRunState,
    workflow: WorkflowDefinitionV2,
    workspace_id: str | None,
    actor_user_id: str | None,
    pinned_packs: list[PinnedPackManifestEntry],
    v2_run_payload: dict[str, Any] | None = None,
) -> bool:
    """Persist immutable `run_lock_manifests` (+ optional `workflow_v2_runs` atomically)."""
    if not workspace_id or not is_pg_runtime_active(request):
        return False
    packs_svc = get_workspace_packs_service(request)
    if not packs_svc.has_engine():
        return False
    wf_bytes = json.dumps(workflow.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    wf_sha = hashlib.sha256(wf_bytes).hexdigest()
    await packs_svc.pin_run_lock(
        run_id=run_state.run_id,
        workspace_id=workspace_id,
        workflow_id=workflow.id,
        workflow_slug=workflow.slug,
        workflow_version=workflow.version,
        workflow_sha256=wf_sha,
        status=run_state.status,
        actor_user_id=actor_user_id,
        pinned_packs=pinned_packs,
        v2_run_payload=v2_run_payload,
    )
    return True


async def sync_v2_run_status_if_pg(
    request: Request,
    *,
    run_id: str,
    status: str,
) -> None:
    """Update `workflow_runs.status` when PG18 is active without mutating `run_lock_manifests`."""
    if not is_pg_runtime_active(request):
        return
    packs_svc = get_workspace_packs_service(request)
    if not packs_svc.has_engine():
        return
    await packs_svc.sync_run_status(run_id=run_id, status=status)


async def execute_get_run_lock_handler(
    run_id: str,
    request: Request,
    runs_store: dict[str, BoundedWorkflowRunState],
    sql_runs_store: SqlWorkflowV2RunsStore,
    *,
    persona_key: str | None = None,
) -> RunLockManifestReadResponse:
    """Read immutable `run_lock_manifests` snapshot for `run_id` (`ScopeAccessGuard`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    packs_svc = get_workspace_packs_service(request)
    lock_data: dict[str, Any] | None = None
    if packs_svc.has_engine():
        lock_data = await packs_svc.get_run_lock(run_id=run_id)
    if lock_data is None:
        cached = runs_store.get(run_id)
        if cached is None and getattr(sql_runs_store, "_session_maker", None) is not None:
            raw = await sql_runs_store.get_run(run_id)
            if raw is None:
                raise HTTPException(status_code=404, detail=f"Run lock for '{run_id}' not found")
        elif cached is None:
            raise HTTPException(status_code=404, detail=f"Run lock for '{run_id}' not found")
        raise HTTPException(status_code=404, detail=f"Run lock for '{run_id}' not found")

    ws_id = str(lock_data["workspace_id"])
    await resolve_finops_read_scope(request, user, "WORKSPACE", ws_id)
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    return RunLockManifestReadResponse(
        run_id=str(lock_data["run_id"]),
        workspace_id=ws_id,
        workflow_id=str(lock_data.get("workflow_id") or ""),
        workflow_slug=str(lock_data.get("workflow_slug") or ""),
        workflow_version=str(lock_data.get("workflow_version") or ""),
        pinned_packs=[
            PinnedPackManifestSchema.model_validate(item)
            for item in (lock_data.get("pinned_packs") or [])
        ],
        resolved_pack_slots=[
            ResolvedPackSlotSchema.model_validate(item)
            for item in (lock_data.get("resolved_pack_slots") or [])
        ],
        manifest_sha256=str(lock_data["manifest_sha256"]),
        locked_at_iso=str(lock_data.get("locked_at_iso") or ""),
        trace_id=trace_id,
    )


__all__ = [
    "enforce_and_snapshot_workspace_packs",
    "execute_get_run_lock_handler",
    "pin_and_sync_v2_run_lock",
    "sync_v2_run_status_if_pg",
]
