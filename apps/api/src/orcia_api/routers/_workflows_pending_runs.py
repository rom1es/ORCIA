"""PG18 persistence & ScopeAccessGuard handlers for `workflows` v2 runs (`Story 30.3`)."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, Request

from orcia_api.dependencies._process_llm_bridge import enforce_live_process_prerequisites
from orcia_api.routers._finops_scope_guards import resolve_finops_read_scope
from orcia_api.routers._workflows_helpers import (
    enforce_not_observer,
    load_workflows_store,
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
from orcia_core.workflows import SqlWorkflowDefinitionsV2Store, SqlWorkflowV2RunsStore
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2


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


def extract_workflow_actor_slug(workflow: WorkflowDefinitionV2) -> str:
    """Derive a clean actor slug from `WorkflowDefinitionV2.global_system_prompt_or_ref`."""
    raw_ref = (workflow.global_system_prompt_or_ref or workflow.slug).strip()
    without_fragment = raw_ref.split("#", 1)[0]
    tail = without_fragment.rsplit("/", 1)[-1]
    if tail.endswith(".md"):
        tail = tail[:-3]
    return tail or workflow.slug


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
        request,
        user,
        eff_scope_type,
        eff_scope_id,
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


async def persist_workflow_v2_run_state(
    sql_runs_store: SqlWorkflowV2RunsStore,
    *,
    run_state: BoundedWorkflowRunState,
    workflow: WorkflowDefinitionV2,
    workspace_id: str | None,
) -> None:
    """Upsert `BoundedWorkflowRunState` into PostgreSQL 18 `workflow_v2_runs`."""
    state_payload = run_state.model_dump(mode="json")
    if workspace_id:
        state_payload["workspace_id"] = workspace_id
    await sql_runs_store.upsert_run(
        run_id=run_state.run_id,
        workspace_id=workspace_id,
        workflow_id=run_state.workflow_id,
        workflow_slug=run_state.workflow_slug,
        workflow_title=workflow.title,
        actor_slug=extract_workflow_actor_slug(workflow),
        status=run_state.status,
        reflexive_execution_id=run_state.reflexive_execution_id,
        state_payload=state_payload,
    )


async def load_or_rehydrate_run_state(
    runs_store: dict[str, BoundedWorkflowRunState],
    sql_runs_store: SqlWorkflowV2RunsStore,
    run_id: str,
) -> tuple[BoundedWorkflowRunState | None, str | None]:
    """Load run state from RAM cache or cold PG18 `workflow_v2_runs` (`F5` survival)."""
    cached = runs_store.get(run_id)
    if cached is not None:
        return cached, None
    raw = await sql_runs_store.get_run(run_id)
    if raw is None:
        return None, None
    ws_raw = raw.get("workspace_id")
    ws_id = str(ws_raw).strip() if isinstance(ws_raw, str) and ws_raw.strip() else None
    clean_payload = {k: v for k, v in raw.items() if k != "workspace_id"}
    restored = BoundedWorkflowRunState.model_validate(clean_payload)
    runs_store[run_id] = restored
    return restored, ws_id


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
    """Validate prerequisites, dispatch dual-mode run, and persist in PG18."""
    resolved_ws_id = resolve_workflow_run_workspace_id(payload.workspace_id, request)
    actor = enforce_not_observer(request, persona_key=persona_key, workspace_id=resolved_ws_id)
    if resolved_ws_id is not None:
        await resolve_finops_read_scope(request, actor, "WORKSPACE", resolved_ws_id)

    store = await load_workflows_store(request, sql_store)
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    merged_resources = await enforce_live_process_prerequisites(
        request,
        user=actor,
        workspace_id=resolved_ws_id,
        workflow=wf,
        inputs=payload.inputs,
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
        inputs=payload.inputs,
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
    """Hydrate run state, apply HITL signal, and persist updated state in PG18."""
    run_state, stored_ws_id = await load_or_rehydrate_run_state(runs_store, sql_runs_store, run_id)
    enforce_not_observer(request, persona_key=persona_key, workspace_id=stored_ws_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    wf_store = await load_workflows_store(request, sql_store)
    wf = wf_store.get(run_state.workflow_id) or wf_store.get(run_state.workflow_slug)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{run_state.workflow_id}' not found")

    updated = apply_hitl_signal_to_run(wf, run_state, payload)
    runs_store[run_id] = updated
    await persist_workflow_v2_run_state(
        sql_runs_store,
        run_state=updated,
        workflow=wf,
        workspace_id=stored_ws_id,
    )
    return WorkflowV2RunResponse(run=updated)


__all__ = [
    "execute_hitl_signal_handler",
    "execute_start_workflow_v2_run_handler",
    "extract_workflow_actor_slug",
    "list_pending_process_runs_handler",
    "load_or_rehydrate_run_state",
    "persist_workflow_v2_run_state",
    "resolve_workflow_run_workspace_id",
]
