"""PG18 persistence & ScopeAccessGuard handlers for `workflows` v2 runs (`Story 30.3`, `31.4`)."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, Request

from orcia_api.dependencies import get_auth_service
from orcia_api.dependencies._process_llm_bridge import enforce_live_process_prerequisites
from orcia_api.routers._agents_lifecycle_guards import enforce_active_agents_for_workflow
from orcia_api.routers._finops_scope_guards import resolve_finops_read_scope
from orcia_api.routers._workflows_helpers import enforce_not_observer, load_workflows_store
from orcia_api.routers._workflows_pack_lock_helpers import (
    enforce_and_snapshot_workspace_packs,
    pin_and_sync_v2_run_lock,
    sync_v2_run_status_if_pg,
)
from orcia_api.routers._workflows_run_state_helpers import (
    extract_workflow_actor_slug,
    load_or_rehydrate_run_state,
    persist_workflow_v2_run_state,
    remember_run_workspace,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.process_studio_v2 import (
    HitlSignalRequest,
    ProcessPendingRunItemResponse,
    ProcessPendingRunsListResponse,
    StartWorkflowV2RunRequest,
    WorkflowV2RunResponse,
)
from orcia_connectors.bounded_workflow_v2 import (
    BoundedWorkflowRunState,
    apply_hitl_signal_to_run,
)
from orcia_core.agents import ProcessExecutionDispatcher
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.kernel.errors import resolve_locale
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.packs import sanitize_workflow_inputs_for_slots
from orcia_core.workflows import SqlWorkflowDefinitionsV2Store, SqlWorkflowV2RunsStore


def resolve_workflow_run_workspace_id(
    payload_workspace_id: str | None,
    request: Request,
) -> str | None:
    """Resolve optional workspace UUID from request payload or header (`scope-global` -> None)."""
    raw = (
        payload_workspace_id
        if payload_workspace_id is not None
        else request.headers.get("X-Orcia-Workspace-Id")
    )
    cleaned = (raw or "").strip().removeprefix("scope-ws-").strip()
    if not cleaned or cleaned.lower() == "scope-global":
        return None
    return cleaned


async def list_pending_process_runs_handler(
    request: Request,
    sql_runs_store: SqlWorkflowV2RunsStore,
    *,
    workspace_id: str | None = None,
    scope_type: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"] | None = None,
    scope_id: str | None = None,
    include_completed: bool = False,
    limit: int = 50,
    persona_key: str | None = None,
) -> ProcessPendingRunsListResponse:
    """Return real PG18 pending/active process runs guarded by `ScopeAccessGuard`."""
    user = resolve_request_user(request, persona_key=persona_key)
    eff_scope_type: ScopeType
    eff_scope_id: str | None
    if scope_type is not None:
        eff_scope_type = scope_type
        eff_scope_id = scope_id
    else:
        cleaned_ws = (workspace_id or "").strip().removeprefix("scope-ws-").strip()
        if cleaned_ws and cleaned_ws.lower() != "scope-global":
            eff_scope_type = "WORKSPACE"
            eff_scope_id = cleaned_ws
        else:
            eff_scope_type = "GLOBAL"
            eff_scope_id = None

    allowed_workspace_ids = await resolve_finops_read_scope(
        request, user, eff_scope_type, eff_scope_id
    )
    rows = await sql_runs_store.list_pending_and_active_runs(
        workspace_ids=allowed_workspace_ids,
        include_completed=include_completed,
        limit=limit,
    )
    items = [ProcessPendingRunItemResponse.model_validate(r) for r in rows]
    pending_count = sum(1 for item in items if item.is_pending)
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    return ProcessPendingRunsListResponse(
        items=items,
        pending_count=pending_count,
        total_count=len(items),
        trace_id=trace_id,
    )


async def execute_get_workflow_v2_run_handler(
    run_id: str,
    request: Request,
    runs_store: dict[str, BoundedWorkflowRunState],
    sql_runs_store: SqlWorkflowV2RunsStore,
    *,
    persona_key: str | None = None,
) -> WorkflowV2RunResponse:
    """Resolve actor, enforce `ScopeAccessGuard` on workspace runs, and return run state."""
    user = resolve_request_user(request, persona_key=persona_key)
    run_state, stored_ws_id = await load_or_rehydrate_run_state(runs_store, sql_runs_store, run_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    if stored_ws_id:
        await resolve_finops_read_scope(request, user, "WORKSPACE", stored_ws_id)
    return WorkflowV2RunResponse(run=run_state)


async def execute_start_workflow_v2_run_handler(
    workflow_id: str,
    payload: StartWorkflowV2RunRequest,
    request: Request,
    sql_store: SqlWorkflowDefinitionsV2Store,
    sql_runs_store: SqlWorkflowV2RunsStore,
    dispatcher: ProcessExecutionDispatcher,
    runs_store: dict[str, BoundedWorkflowRunState],
    *,
    persona_key: str | None = None,
) -> WorkflowV2RunResponse:
    """Validate prerequisites + pack slots, dispatch run, and pin `run_lock_manifests`."""
    raw_ws_id = resolve_workflow_run_workspace_id(payload.workspace_id, request)
    actor = enforce_not_observer(request, persona_key=persona_key, workspace_id=None)
    resolved_ws_id = raw_ws_id
    if raw_ws_id is not None:
        await resolve_finops_read_scope(request, actor, "WORKSPACE", raw_ws_id)
        ws_obj = get_auth_service(request).evaluator.get_workspace(raw_ws_id)
        if ws_obj is not None:
            resolved_ws_id = ws_obj.id
        enforce_not_observer(request, persona_key=persona_key, workspace_id=resolved_ws_id)

    store = await load_workflows_store(request, sql_store)
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    await enforce_active_agents_for_workflow(request, wf, instance=str(request.url.path))
    pinned_packs = await enforce_and_snapshot_workspace_packs(
        request, workspace_id=resolved_ws_id, workflow=wf
    )
    effective_inputs = sanitize_workflow_inputs_for_slots(payload.inputs, pinned_packs)
    merged_resources = await enforce_live_process_prerequisites(
        request,
        user=actor,
        workspace_id=resolved_ws_id,
        workflow=wf,
        inputs=effective_inputs,
        explicit_resources=payload.initial_resources,
    )

    run_id = f"run-{new_uuid7_str()}"
    reentry: Literal["initial", "corrections"] = (
        "corrections" if payload.reentry_mode == "corrections" else "initial"
    )
    locale = resolve_locale(request.headers.get("accept-language"))
    unified = await dispatcher.dispatch(
        wf,
        run_id=run_id,
        inputs=effective_inputs,
        iteration=payload.iteration,
        reentry_mode=reentry,
        correction_remarks=payload.correction_remarks,
        auto_approve_checkpoints=payload.auto_approve_checkpoints,
        workspace_id=resolved_ws_id,
        actor_user_id=actor.id,
        locale=locale,
        initial_resources=merged_resources,
    )
    run_state = BoundedWorkflowRunState.from_unified_result(unified)
    runs_store[run_id] = run_state
    remember_run_workspace(runs_store, run_id, resolved_ws_id)
    v2_run_payload = {
        "workflow_title": wf.title,
        "actor_slug": extract_workflow_actor_slug(wf),
        "reflexive_execution_id": run_state.reflexive_execution_id,
        "state": run_state.model_dump(mode="json"),
    }
    atomic_pg_persisted = await pin_and_sync_v2_run_lock(
        request,
        run_state=run_state,
        workflow=wf,
        workspace_id=resolved_ws_id,
        actor_user_id=actor.id,
        pinned_packs=pinned_packs,
        v2_run_payload=v2_run_payload,
    )
    if atomic_pg_persisted:
        if not getattr(sql_runs_store, "_strict_sql", False):
            sql_runs_store._memory_fallback[run_id] = {
                "run_id": run_id,
                "workspace_id": resolved_ws_id,
                "workflow_id": wf.id,
                "workflow_slug": wf.slug,
                **v2_run_payload,
                "status": run_state.status,
            }
    else:
        await persist_workflow_v2_run_state(
            sql_runs_store,
            run_state=run_state,
            workflow=wf,
            workspace_id=resolved_ws_id,
        )
    return WorkflowV2RunResponse(run=run_state)


async def execute_hitl_signal_handler(
    run_id: str,
    payload: HitlSignalRequest,
    request: Request,
    sql_store: SqlWorkflowDefinitionsV2Store,
    sql_runs_store: SqlWorkflowV2RunsStore,
    runs_store: dict[str, BoundedWorkflowRunState],
    *,
    persona_key: str | None = None,
) -> WorkflowV2RunResponse:
    """Hydrate run state, enforce scope/observer guards, apply HITL signal, and persist."""
    run_state, stored_ws_id = await load_or_rehydrate_run_state(runs_store, sql_runs_store, run_id)
    actor = enforce_not_observer(request, persona_key=persona_key, workspace_id=stored_ws_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    if stored_ws_id:
        await resolve_finops_read_scope(request, actor, "WORKSPACE", stored_ws_id)
        enforce_not_observer(request, persona_key=persona_key, workspace_id=stored_ws_id)

    wf_store = await load_workflows_store(request, sql_store)
    wf = wf_store.get(run_state.workflow_id) or wf_store.get(run_state.workflow_slug)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{run_state.workflow_id}' not found")

    updated = apply_hitl_signal_to_run(wf, run_state, payload)
    runs_store[run_id] = updated
    remember_run_workspace(runs_store, run_id, stored_ws_id)
    await persist_workflow_v2_run_state(
        sql_runs_store,
        run_state=updated,
        workflow=wf,
        workspace_id=stored_ws_id,
    )
    await sync_v2_run_status_if_pg(request, run_id=run_id, status=updated.status)
    return WorkflowV2RunResponse(run=updated)


__all__ = [
    "execute_get_workflow_v2_run_handler",
    "execute_hitl_signal_handler",
    "execute_start_workflow_v2_run_handler",
    "extract_workflow_actor_slug",
    "list_pending_process_runs_handler",
    "load_or_rehydrate_run_state",
    "persist_workflow_v2_run_state",
    "resolve_workflow_run_workspace_id",
]
