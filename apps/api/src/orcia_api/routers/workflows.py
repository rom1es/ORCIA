"""Process Studio v2, VSM & Dual-Mode Workflows Router (`TASK-05` & `Story 16.3`).

Exposes:
- `GET /api/v1/vsm` & `GET /api/v1/vsm/{vsm_id}`
- `GET /api/v1/workflows/v2`, `/api/v1/workflows/v2/runs` & `/api/v1/workflows/v2/{workflow_id}`
- `PUT /api/v1/workflows/v2/{workflow_id}` (auto-forks `vX.Y.Z-draft` & persists in PG18)
- `POST /api/v1/workflows/v2/{workflow_id}/what-if` (isolated sandbox dry-run, 0 external writes)
- `POST /api/v1/workflows/v2/{workflow_id}/runs` (routed through `ProcessExecutionDispatcher`)
- `GET /api/v1/runs/{run_id}` & `POST /api/v1/runs/{run_id}/hitl-signal`
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from orcia_api.dependencies import (
    get_process_execution_dispatcher,
    get_vsm_v2_sql_store,
    get_workflow_v2_runs_store,
    get_workflows_v2_runs_sql_store,
    get_workflows_v2_sql_store,
)
from orcia_api.routers._workflows_helpers import (
    enforce_not_observer as _enforce_not_observer,
)
from orcia_api.routers._workflows_helpers import (
    get_vsm_definition_from_pg18 as _get_vsm_definition_from_pg18,
)
from orcia_api.routers._workflows_helpers import (
    load_vsm_definitions_from_pg18 as _load_vsm_definitions_from_pg18,
)
from orcia_api.routers._workflows_helpers import (
    load_workflows_store as _load_workflows_store,
)
from orcia_api.routers._workflows_helpers import (
    publish_workflow_outbox_event as _publish_workflow_outbox_event,
)
from orcia_api.routers._workflows_pending_runs import (
    execute_hitl_signal_handler,
    execute_start_workflow_v2_run_handler,
    list_pending_process_runs_handler,
    load_or_rehydrate_run_state,
)
from orcia_api.routers._workflows_what_if import execute_workflow_what_if_simulation
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas.process_studio_v2 import (
    HitlSignalRequest,
    ProcessPendingRunsListResponse,
    SaveWorkflowV2Request,
    SaveWorkflowV2Response,
    StartWorkflowV2RunRequest,
    VsmListResponse,
    WhatIfSimulationRequest,
    WorkflowsV2ListResponse,
    WorkflowV2RunResponse,
)
from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState
from orcia_core.agents import ProcessExecutionDispatcher
from orcia_core.workflows import (
    SqlVsmDefinitionsV2Store,
    SqlWorkflowDefinitionsV2Store,
    SqlWorkflowV2RunsStore,
)
from orcia_core.workflows.schemas_v2 import (
    ImpactAssessmentResult,
    ValueStreamMapSpec,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
    fork_workflow_as_draft,
)

router = APIRouter(
    tags=["Process Studio v2 & VSM (Epic 14)"],
    responses=PROBLEM_RESPONSES,
)

WorkflowSqlStoreDep = Annotated[SqlWorkflowDefinitionsV2Store, Depends(get_workflows_v2_sql_store)]
WorkflowRunsSqlStoreDep = Annotated[
    SqlWorkflowV2RunsStore, Depends(get_workflows_v2_runs_sql_store)
]
VsmSqlStoreDep = Annotated[SqlVsmDefinitionsV2Store, Depends(get_vsm_v2_sql_store)]
RunsStoreDep = Annotated[dict[str, BoundedWorkflowRunState], Depends(get_workflow_v2_runs_store)]
ProcessDispatcherDep = Annotated[
    ProcessExecutionDispatcher, Depends(get_process_execution_dispatcher)
]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@router.get("/api/v1/vsm", response_model=VsmListResponse)
async def list_value_stream_maps(
    request: Request,
    vsm_store: VsmSqlStoreDep,
) -> VsmListResponse:
    """List all declarative Value Stream Maps (`ValueStreamMapSpec`) from PG18."""
    items = await _load_vsm_definitions_from_pg18(request, vsm_store)
    return VsmListResponse(items=items)


@router.get("/api/v1/vsm/{vsm_id}", response_model=ValueStreamMapSpec)
async def get_value_stream_map(
    vsm_id: str,
    request: Request,
    vsm_store: VsmSqlStoreDep,
) -> ValueStreamMapSpec:
    """Fetch a single `ValueStreamMapSpec` from PG18 by ID or slug."""
    vsm = await _get_vsm_definition_from_pg18(request, vsm_store, vsm_id)
    if vsm is None:
        raise HTTPException(status_code=404, detail=f"Value Stream Map '{vsm_id}' not found")
    return vsm


@router.get("/api/v1/workflows/v2", response_model=WorkflowsV2ListResponse)
async def list_workflows_v2(
    request: Request,
    sql_store: WorkflowSqlStoreDep,
) -> WorkflowsV2ListResponse:
    """List all `WorkflowDefinitionV2` definitions (pack baselines + persisted overrides)."""
    store = await _load_workflows_store(request, sql_store)
    unique_by_id: dict[str, WorkflowDefinitionV2] = {}
    for wf in store.values():
        unique_by_id[wf.id] = wf
    return WorkflowsV2ListResponse(items=list(unique_by_id.values()))


@router.get("/api/v1/workflows/v2/runs", response_model=ProcessPendingRunsListResponse)
async def list_workflow_v2_pending_runs(
    request: Request,
    sql_runs_store: WorkflowRunsSqlStoreDep,
    workspace_id: Annotated[str | None, Query(max_length=128)] = None,
    scope_type: Annotated[Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"] | None, Query()] = None,
    scope_id: Annotated[str | None, Query(max_length=128)] = None,
    include_completed: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    persona_key: PersonaQuery = None,
) -> ProcessPendingRunsListResponse:
    """List workspace-scoped pending/active process runs hydrated from PG18."""
    return await list_pending_process_runs_handler(
        request,
        sql_runs_store,
        workspace_id=workspace_id,
        scope_type=scope_type,
        scope_id=scope_id,
        include_completed=include_completed,
        limit=limit,
        persona_key=persona_key,
    )


@router.get("/api/v1/workflows/v2/{workflow_id}", response_model=WorkflowDefinitionV2)
async def get_workflow_v2(
    workflow_id: str,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
) -> WorkflowDefinitionV2:
    """Fetch a `WorkflowDefinitionV2` by ID or slug."""
    store = await _load_workflows_store(request, sql_store)
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return wf


@router.put("/api/v1/workflows/v2/{workflow_id}", response_model=SaveWorkflowV2Response)
async def save_or_fork_workflow_v2(
    workflow_id: str,
    payload: SaveWorkflowV2Request,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
    persona_key: PersonaQuery = None,
) -> SaveWorkflowV2Response:
    """Save a workflow in the Studio; auto-forks `-draft` if `PUBLISHED` and persists to PG18."""
    _enforce_not_observer(request, persona_key=persona_key)
    store = await _load_workflows_store(request, sql_store)
    existing = store.get(workflow_id)
    incoming = payload.workflow
    forked_as_draft = False

    if (
        existing is not None
        and existing.status == WorkflowLifecycleStatus.PUBLISHED
        and not payload.publish
    ):
        draft_shell = fork_workflow_as_draft(existing)
        resolved_draft_ver = (
            incoming.version if incoming.version.endswith("-draft") else draft_shell.version
        )
        saved = incoming.model_copy(
            update={
                "id": existing.id,
                "slug": existing.slug,
                "version": resolved_draft_ver,
                "status": WorkflowLifecycleStatus.DRAFT,
            }
        )
        forked_as_draft = True
        store[f"{saved.id}:draft"] = saved
        store[saved.id] = saved
        store[saved.slug] = saved
    else:
        status = WorkflowLifecycleStatus.PUBLISHED if payload.publish else incoming.status
        ver = incoming.version.removesuffix("-draft") if payload.publish else incoming.version
        saved = incoming.model_copy(update={"status": status, "version": ver})
        store[saved.id] = saved
        store[saved.slug] = saved

    await sql_store.upsert_workflow(saved)
    if payload.publish:
        await _publish_workflow_outbox_event(request, saved)
    return SaveWorkflowV2Response(workflow=saved, forked_as_draft=forked_as_draft)


@router.post("/api/v1/workflows/v2/{workflow_id}/what-if", response_model=ImpactAssessmentResult)
async def run_workflow_v2_what_if_simulation(
    workflow_id: str,
    payload: WhatIfSimulationRequest,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
) -> ImpactAssessmentResult:
    """Execute an isolated dry-run simulation (`external_writes_executed = 0`, `CA-9.3.4`)."""
    store = await _load_workflows_store(request, sql_store)
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return execute_workflow_what_if_simulation(wf, payload)


@router.post("/api/v1/workflows/v2/{workflow_id}/runs", response_model=WorkflowV2RunResponse)
async def start_workflow_v2_run(
    workflow_id: str,
    payload: StartWorkflowV2RunRequest,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
    sql_runs_store: WorkflowRunsSqlStoreDep,
    dispatcher: ProcessDispatcherDep,
    runs_store: RunsStoreDep,
    persona_key: PersonaQuery = None,
) -> WorkflowV2RunResponse:
    """Start a dual-mode workflow run (`ProcessExecutionDispatcher`: Goal vs Milestone)."""
    return await execute_start_workflow_v2_run_handler(
        workflow_id,
        payload,
        request,
        sql_store,
        sql_runs_store,
        dispatcher,
        runs_store,
        persona_key=persona_key,
    )


@router.get("/api/v1/runs/{run_id}", response_model=WorkflowV2RunResponse)
async def get_workflow_v2_run(
    run_id: str,
    runs_store: RunsStoreDep,
    sql_runs_store: WorkflowRunsSqlStoreDep,
) -> WorkflowV2RunResponse:
    """Fetch the live or PG18-persisted state of a workflow v2 run."""
    run_state, _ws_id = await load_or_rehydrate_run_state(runs_store, sql_runs_store, run_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return WorkflowV2RunResponse(run=run_state)


@router.post("/api/v1/runs/{run_id}/hitl-signal", response_model=WorkflowV2RunResponse)
async def send_hitl_signal_to_workflow_v2_run(
    run_id: str,
    payload: HitlSignalRequest,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
    sql_runs_store: WorkflowRunsSqlStoreDep,
    runs_store: RunsStoreDep,
    persona_key: PersonaQuery = None,
) -> WorkflowV2RunResponse:
    """Deliver a human checkpoint, WritePreview approval, or 4-action Anchor Card signal."""
    return await execute_hitl_signal_handler(
        run_id,
        payload,
        request,
        sql_store,
        sql_runs_store,
        runs_store,
        persona_key=persona_key,
    )
