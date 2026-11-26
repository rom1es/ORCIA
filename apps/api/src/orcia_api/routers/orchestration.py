"""FastAPI Router for Story 3.1: Workflow-as-Code, Multi-Audience Templates & `run-lock.json`."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_orchestration_service,
    get_workspace_packs_service,
)
from orcia_api.dependencies._core_providers import is_pg_runtime_active
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers._orchestration_v1_serializers import (
    serialize_compiled_template,
    serialize_run,
    serialize_workflow,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.routers.orchestration_sql_wiring import (
    hydrate_orchestration_runs_from_sql,
    hydrate_run_from_sql_if_missing,
    sync_instantiated_run_to_sql,
)
from orcia_api.schemas.orchestration import (
    ArtifactTemplateCompileRequest,
    ArtifactTemplateCompileResponse,
    OrchestrationSetupStateResponse,
    WorkflowManifestRegisterRequest,
    WorkflowManifestRegisterResponse,
    WorkflowManifestValidateRequest,
    WorkflowManifestValidateResponse,
    WorkflowRunInstantiateRequest,
    WorkflowRunInstantiateResponse,
    WorkflowValidationFindingSchemaItem,
)
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration-setup"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _extract_pack_id_from_workflow(wf: object) -> str | None:
    pack_id = getattr(wf, "pack_id", None)
    if isinstance(pack_id, str) and pack_id.strip():
        return pack_id.strip()
    uri = str(getattr(wf, "uri", "") or "").strip()
    for prefix in ("orcia://packs/", "packs://"):
        if uri.lower().startswith(prefix):
            rest = uri[len(prefix) :].split("/", 1)[0]
            slug = rest.split("@", 1)[0].strip()
            if slug:
                return slug
    return None


@router.get(
    "/state",
    response_model=OrchestrationSetupStateResponse,
    summary="Get Story 3.1 Workflow-as-Code DAGs, compiled template, and recursive run-lock state",
    responses=PROBLEM_RESPONSES,
)
async def get_orchestration_state(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OrchestrationSetupStateResponse:
    """Return registered Workflow-as-Code definitions, runs, and compiled ADR template."""
    resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    await hydrate_orchestration_runs_from_sql(request, svc)
    compiled_tpl = svc.compile_artifact_template(
        "tpl-architecture-decision-record",
        variables={"project_name": "Claims Core Engine", "jira_key": "PAY-142"},
        instance=str(request.url.path),
    )
    return OrchestrationSetupStateResponse(
        workflows=[serialize_workflow(wf) for wf in svc.workflows],
        runs=[serialize_run(r) for r in svc.runs],
        compiled_default_template=serialize_compiled_template(compiled_tpl),
        trace_id=_trace(request),
    )


@router.post(
    "/workflows/validate",
    response_model=WorkflowManifestValidateResponse,
    summary="Validate a Workflow-as-Code YAML/JSON manifest with exact line numbers",
    responses=PROBLEM_RESPONSES,
)
async def validate_workflow_manifest(
    payload: WorkflowManifestValidateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> WorkflowManifestValidateResponse:
    """Validate DAG syntax, criticality vs regime, Intention -> Code, and SUB_WORKFLOW <= 3."""
    resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    report = svc.validate_workflow_manifest(
        payload.raw_manifest,
        workspace_id=payload.workspace_id,
        raise_on_error=True,
        instance=str(request.url.path),
    )
    return WorkflowManifestValidateResponse(
        valid=report.valid,
        workflow=serialize_workflow(report.workflow) if report.workflow else None,
        findings=[
            WorkflowValidationFindingSchemaItem(
                line=f.line,
                rule_code=f.rule_code,
                field_path=f.field_path,
                message=f.message,
            )
            for f in report.findings
        ],
        resolved_max_nesting_depth=report.resolved_max_nesting_depth,
        topological_order=list(report.topological_order),
        trace_id=_trace(request),
    )


@router.post(
    "/workflows/register",
    response_model=WorkflowManifestRegisterResponse,
    summary="Validate and register a Workflow-as-Code YAML/JSON manifest",
    responses=PROBLEM_RESPONSES,
)
async def register_workflow_manifest(
    payload: WorkflowManifestRegisterRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> WorkflowManifestRegisterResponse:
    """Register a validated Workflow-as-Code manifest (`ScopeAccessGuard` enforced)."""
    user = resolve_request_user(request, persona_key=persona_key)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    wf = get_orchestration_service(request).register_workflow_manifest(
        user,
        payload.raw_manifest,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    return WorkflowManifestRegisterResponse(
        workflow=serialize_workflow(wf),
        trace_id=_trace(request),
    )


@router.post(
    "/templates/compile",
    response_model=ArtifactTemplateCompileResponse,
    summary="Compile a Multi-Audience Artifact Template into Human Markdown + Ontology JSON Schema",
    responses=PROBLEM_RESPONSES,
)
async def compile_artifact_template(
    payload: ArtifactTemplateCompileRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> ArtifactTemplateCompileResponse:
    """Compile dual-view Multi-Audience Artifact Template (`FR-12`)."""
    resolve_request_user(request, persona_key=persona_key)
    compiled = get_orchestration_service(request).compile_artifact_template(
        payload.template_key,
        variables=payload.variables,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    return ArtifactTemplateCompileResponse(
        compiled_template=serialize_compiled_template(compiled),
        trace_id=_trace(request),
    )


@router.post(
    "/runs/instantiate",
    response_model=WorkflowRunInstantiateResponse,
    summary="Instantiate a Workflow Run and recursively pin run-lock.json (SUB_WORKFLOW <= 3)",
    responses=PROBLEM_RESPONSES,
)
async def instantiate_workflow_run(
    payload: WorkflowRunInstantiateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> WorkflowRunInstantiateResponse:
    """Instantiate a Workflow Run and lock all sources, overrides, KB hash, and sub-workflows."""
    user = resolve_request_user(request, persona_key=persona_key)
    enforce_observer_headers_guard(request, user)
    svc = get_orchestration_service(request)
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    if payload.parent_run_id:
        await hydrate_run_from_sql_if_missing(request, svc, payload.parent_run_id)
    path = str(request.url.path)
    svc._enforce_mutation_guard(user, payload.workspace_id, instance=path)
    wf_def = svc.engine._get_workflow(payload.workflow_uri, instance=path)
    pinned_packs = []
    if is_pg_runtime_active(request) and payload.workspace_id:
        packs_svc = get_workspace_packs_service(request)
        if packs_svc.has_engine():
            pinned_packs = await packs_svc.enforce_run_start_readiness(
                workspace_id=payload.workspace_id,
                workflow_pack_id=_extract_pack_id_from_workflow(wf_def),
                instance=path,
            )
    run = svc.instantiate_workflow_run(
        user,
        workflow_uri=payload.workflow_uri,
        workspace_id=payload.workspace_id,
        parent_run_id=payload.parent_run_id,
        parent_step_execution_id=payload.parent_step_execution_id,
        trigger_id=payload.trigger_id,
        trigger_idempotency_key=payload.trigger_idempotency_key,
        execution_identity_mode=payload.execution_identity_mode,
        instance=path,
    )
    wf = svc.engine._get_workflow(run.workflow_uri, instance=path)
    initial_steps = svc.engine.initialize_run_steps(run, wf)
    await sync_instantiated_run_to_sql(request, run, initial_steps=initial_steps)
    if pinned_packs and is_pg_runtime_active(request):
        await get_workspace_packs_service(request).attach_pinned_packs_to_run_lock(
            run_id=run.id, pinned_packs=pinned_packs
        )
    return WorkflowRunInstantiateResponse(
        run=serialize_run(run),
        trace_id=_trace(request),
    )
