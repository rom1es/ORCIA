"""Process Studio v2, VSM & Dual-Mode Workflows Router (`TASK-05` & `Story 16.3`).

Exposes:
- `GET /api/v1/vsm` & `GET /api/v1/vsm/{vsm_id}`
- `GET /api/v1/workflows/v2` & `GET /api/v1/workflows/v2/{workflow_id}` (PostgreSQL 18 rehydration)
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
    get_workflows_v2_sql_store,
)
from orcia_api.routers._workflows_helpers import (
    enforce_not_observer as _enforce_not_observer,
)
from orcia_api.routers._workflows_helpers import (
    get_runs_store as _get_runs_store,
)
from orcia_api.routers._workflows_helpers import (
    get_vsm_store as _get_vsm_store,
)
from orcia_api.routers._workflows_helpers import (
    load_workflows_store as _load_workflows_store,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas.process_studio_v2 import (
    HitlSignalRequest,
    SaveWorkflowV2Request,
    SaveWorkflowV2Response,
    StartWorkflowV2RunRequest,
    VsmListResponse,
    WhatIfSimulationRequest,
    WorkflowsV2ListResponse,
    WorkflowV2RunResponse,
)
from orcia_connectors.bounded_workflow_v2 import (
    BoundedWorkflowRunState,
    apply_hitl_signal_to_run,
)
from orcia_core.agents import ProcessExecutionDispatcher
from orcia_core.kernel.errors import resolve_locale
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.workflows import SqlWorkflowDefinitionsV2Store
from orcia_core.workflows.gates.pipeline import GatePipelineExecutor
from orcia_core.workflows.schemas_v2 import (
    ImpactAssessmentResult,
    ProcessOrchestrationType,
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
ProcessDispatcherDep = Annotated[
    ProcessExecutionDispatcher, Depends(get_process_execution_dispatcher)
]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@router.get("/api/v1/vsm", response_model=VsmListResponse)
async def list_value_stream_maps(request: Request) -> VsmListResponse:
    """List all declarative Value Stream Maps (`ValueStreamMapSpec`)."""
    store = _get_vsm_store(request)
    unique_by_id = {v.id: v for v in store.values()}
    return VsmListResponse(items=list(unique_by_id.values()))


@router.get("/api/v1/vsm/{vsm_id}", response_model=ValueStreamMapSpec)
async def get_value_stream_map(vsm_id: str, request: Request) -> ValueStreamMapSpec:
    """Fetch a single `ValueStreamMapSpec` by ID or slug."""
    store = _get_vsm_store(request)
    vsm = store.get(vsm_id)
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

    enabled_steps = [s for s in wf.sub_steps if s.enabled]
    headings = wf.contract.required_markdown_sections or [f"# {wf.title}", "## Contexte"]
    sample_md = payload.sample_artifact_markdown or (
        "\n\n".join(
            f"{h}\nSimulation What-If isolée pour {wf.title} avec section complète et détaillée."
            for h in headings
        )
        + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
    )
    gate_report = GatePipelineExecutor().execute_pipeline(
        pipeline=wf.controls,
        artifact_text=sample_md,
        execution_mode=wf.execution_mode,
    )
    findings = [
        {
            "control_id": r.control_id,
            "type": "deterministic",
            "status": r.status,
            "violations": r.violations,
        }
        for r in gate_report.deterministic_records
    ] + [
        {
            "control_id": p.control_id,
            "type": "probabilistic",
            "status": p.status,
            "risk_score": p.risk_score,
            "findings": p.findings,
        }
        for p in gate_report.probabilistic_records
    ]
    step_units = (
        max(1, len(wf.allowed_delegate_agents) + 1)
        if wf.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC
        else max(1, len(enabled_steps))
    )
    est_tokens = step_units * 1450
    return ImpactAssessmentResult(
        workflow_id=wf.id,
        version=wf.version,
        sandbox_isolated=True,
        external_writes_executed=0,
        sub_steps_evaluated=len(enabled_steps) if enabled_steps else step_units,
        deterministic_gates_passed=gate_report.deterministic_passed,
        probabilistic_gates_passed=gate_report.overall_status == "NOMINAL",
        estimated_tokens=est_tokens,
        estimated_cost_usd=round(est_tokens * 0.000003, 4),
        findings=findings,
    )


@router.post("/api/v1/workflows/v2/{workflow_id}/runs", response_model=WorkflowV2RunResponse)
async def start_workflow_v2_run(
    workflow_id: str,
    payload: StartWorkflowV2RunRequest,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
    dispatcher: ProcessDispatcherDep,
    persona_key: PersonaQuery = None,
) -> WorkflowV2RunResponse:
    """Start a dual-mode workflow run (`ProcessExecutionDispatcher`: Goal vs Milestone)."""
    actor = _enforce_not_observer(request, persona_key=persona_key)
    store = await _load_workflows_store(request, sql_store)
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

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
        actor_user_id=actor.id,
        locale=locale,
    )
    run_state = BoundedWorkflowRunState.from_unified_result(unified)
    runs_store = _get_runs_store(request)
    runs_store[run_id] = run_state
    return WorkflowV2RunResponse(run=run_state)


@router.get("/api/v1/runs/{run_id}", response_model=WorkflowV2RunResponse)
async def get_workflow_v2_run(run_id: str, request: Request) -> WorkflowV2RunResponse:
    """Fetch the live state of a workflow v2 run."""
    runs_store = _get_runs_store(request)
    run_state = runs_store.get(run_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return WorkflowV2RunResponse(run=run_state)


@router.post("/api/v1/runs/{run_id}/hitl-signal", response_model=WorkflowV2RunResponse)
async def send_hitl_signal_to_workflow_v2_run(
    run_id: str,
    payload: HitlSignalRequest,
    request: Request,
    sql_store: WorkflowSqlStoreDep,
    persona_key: PersonaQuery = None,
) -> WorkflowV2RunResponse:
    """Deliver a human checkpoint, WritePreview approval, or 4-action Anchor Card signal."""
    _enforce_not_observer(request, persona_key=persona_key)
    runs_store = _get_runs_store(request)
    run_state = runs_store.get(run_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    wf_store = await _load_workflows_store(request, sql_store)
    wf = wf_store.get(run_state.workflow_id) or wf_store.get(run_state.workflow_slug)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{run_state.workflow_id}' not found")

    updated = apply_hitl_signal_to_run(wf, run_state, payload)
    runs_store[run_id] = updated
    return WorkflowV2RunResponse(run=updated)
