"""FastAPI Router for Story 3.1: Workflow-as-Code, Multi-Audience Templates & `run-lock.json`."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import (
    CompiledArtifactTemplate,
    RecursiveRunLockManifest,
    SubWorkflowLockEntry,
    WorkflowAsCodeDefinition,
    WorkflowOrchestrationSetupService,
    WorkflowRunEntity,
    build_default_orchestration_setup_service,
)
from orcia_core.schemas.catalog import RunLockSourceTripletItem
from orcia_core.schemas.orchestration import (
    ArtifactTemplateCompileRequest,
    ArtifactTemplateCompileResponse,
    CompiledArtifactTemplateSchemaItem,
    CompiledMarkdownChunkSchemaItem,
    OrchestrationSetupStateResponse,
    RecursiveRunLockManifestSchemaItem,
    SubWorkflowLockSchemaItem,
    WorkflowAsCodeDefinitionSchemaItem,
    WorkflowManifestRegisterRequest,
    WorkflowManifestRegisterResponse,
    WorkflowManifestValidateRequest,
    WorkflowManifestValidateResponse,
    WorkflowRunInstantiateRequest,
    WorkflowRunInstantiateResponse,
    WorkflowRunSchemaItem,
    WorkflowStepSpecSchemaItem,
    WorkflowValidationFindingSchemaItem,
)

_DEFAULT_ORCHESTRATION_SERVICE = build_default_orchestration_setup_service()

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration-setup"])


def get_orchestration_service(request: Request) -> WorkflowOrchestrationSetupService:
    """Return active `WorkflowOrchestrationSetupService` attached to `app.state` or default."""
    svc: WorkflowOrchestrationSetupService | None = getattr(
        request.app.state, "orchestration_service", None
    )
    return svc if svc is not None else _DEFAULT_ORCHESTRATION_SERVICE


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_workflow(wf: WorkflowAsCodeDefinition) -> WorkflowAsCodeDefinitionSchemaItem:
    return WorkflowAsCodeDefinitionSchemaItem(
        id=wf.id,
        workspace_id=wf.workspace_id,
        uri=wf.uri,
        title=wf.title,
        description=wf.description,
        version=wf.version,
        criticality=wf.criticality,
        execution_regime=wf.execution_regime,
        tie_break_policy=wf.tie_break_policy,
        mode=wf.mode,
        adaptive_gate_policy=wf.adaptive_gate_policy,
        max_cost_usd=wf.max_cost_usd,
        scalars=dict(wf.scalars),
        datasources=list(wf.datasources),
        rules=list(wf.rules),
        facts=list(wf.facts),
        steps=[
            WorkflowStepSpecSchemaItem(
                step_key=s.step_key,
                title=s.title,
                step_type=s.step_type,
                instructions=s.instructions,
                depends_on=list(s.depends_on),
                feedback_target_step_key=s.feedback_target_step_key,
                max_agent_retries=s.max_agent_retries,
                agent_uri=s.agent_uri,
                skill_uri=s.skill_uri,
                sub_workflow_uri=s.sub_workflow_uri,
                input_mapping=dict(s.input_mapping),
                output_mapping=dict(s.output_mapping),
                template_key=s.template_key,
                kb_uris=list(s.kb_uris),
                human_authored_required=s.human_authored_required,
                requires_human_gate=s.requires_human_gate,
                declares_intention=s.declares_intention,
                writes_code=s.writes_code,
                reverse_doc_from_code=s.reverse_doc_from_code,
                verification_window_seconds=s.verification_window_seconds,
                line_number=s.line_number,
            )
            for s in wf.steps
        ],
        sha256=wf.sha256,
        max_nesting_depth=wf.max_nesting_depth,
    )


def _serialize_compiled_template(
    compiled: CompiledArtifactTemplate,
) -> CompiledArtifactTemplateSchemaItem:
    return CompiledArtifactTemplateSchemaItem(
        template_key=compiled.template_key,
        uri=compiled.uri,
        version=compiled.version,
        human_markdown_view=compiled.human_markdown_view,
        cognitive_chunks=[
            CompiledMarkdownChunkSchemaItem(
                chunk_index=c.chunk_index,
                section_key=c.section_key,
                section_title=c.section_title,
                markdown_content=c.markdown_content,
                word_count=c.word_count,
                human_authored_required=c.human_authored_required,
            )
            for c in compiled.cognitive_chunks
        ],
        agent_json_schema=dict(compiled.agent_json_schema),
        bound_ontology_terms=list(compiled.bound_ontology_terms),
        sha256=compiled.sha256,
    )


def _serialize_sub_lock(entry: SubWorkflowLockEntry) -> SubWorkflowLockSchemaItem:
    return SubWorkflowLockSchemaItem(
        step_key=entry.step_key,
        workflow_uri=entry.workflow_uri,
        workflow_version=entry.workflow_version,
        workflow_sha256=entry.workflow_sha256,
        effective_workflow_sha256=entry.effective_workflow_sha256,
        nesting_depth=entry.nesting_depth,
        applied_override_keys=list(entry.applied_override_keys),
        sources=[
            RunLockSourceTripletItem(
                alias=s.alias,
                scheme=s.scheme,
                uri=s.uri,
                resolved_version=s.resolved_version,
                sha256=s.sha256,
                cas_key=s.cas_key,
            )
            for s in entry.sources
        ],
        sub_workflow_locks=[_serialize_sub_lock(child) for child in entry.sub_workflow_locks],
    )


def _serialize_run_lock(rl: RecursiveRunLockManifest) -> RecursiveRunLockManifestSchemaItem:
    return RecursiveRunLockManifestSchemaItem(
        run_id=rl.run_id,
        workspace_id=rl.workspace_id,
        workflow_uri=rl.workflow_uri,
        workflow_version=rl.workflow_version,
        workflow_sha256=rl.workflow_sha256,
        effective_workflow_sha256=rl.effective_workflow_sha256,
        overrides_sha256=rl.overrides_sha256,
        kb_snapshot_hash=rl.kb_snapshot_hash,
        applied_override_keys=list(rl.applied_override_keys),
        sources=[
            RunLockSourceTripletItem(
                alias=s.alias,
                scheme=s.scheme,
                uri=s.uri,
                resolved_version=s.resolved_version,
                sha256=s.sha256,
                cas_key=s.cas_key,
            )
            for s in rl.sources
        ],
        sub_workflow_locks=[_serialize_sub_lock(sub) for sub in rl.sub_workflow_locks],
        manifest_sha256=rl.manifest_sha256,
    )


def _serialize_run(run: WorkflowRunEntity) -> WorkflowRunSchemaItem:
    return WorkflowRunSchemaItem(
        id=run.id,
        run_key=run.run_key,
        workspace_id=run.workspace_id,
        workflow_def_id=run.workflow_def_id,
        workflow_uri=run.workflow_uri,
        parent_run_id=run.parent_run_id,
        parent_step_execution_id=run.parent_step_execution_id,
        root_run_id=run.root_run_id,
        nesting_depth=run.nesting_depth,
        execution_regime=run.execution_regime,
        criticality=run.criticality,
        trigger_id=run.trigger_id,
        trigger_idempotency_key=run.trigger_idempotency_key,
        status=run.status,
        initiated_by_user_id=run.initiated_by_user_id,
        execution_identity_mode=run.execution_identity_mode,
        budget_max_usd=run.budget_max_usd,
        run_lock=_serialize_run_lock(run.run_lock),
    )


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
    compiled_tpl = svc.compile_artifact_template(
        "tpl-architecture-decision-record",
        variables={"project_name": "Claims Core Engine", "jira_key": "PAY-142"},
        instance=str(request.url.path),
    )
    return OrchestrationSetupStateResponse(
        workflows=[_serialize_workflow(wf) for wf in svc.workflows],
        runs=[_serialize_run(r) for r in svc.runs],
        compiled_default_template=_serialize_compiled_template(compiled_tpl),
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
        workflow=_serialize_workflow(report.workflow) if report.workflow else None,
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
    wf = get_orchestration_service(request).register_workflow_manifest(
        user,
        payload.raw_manifest,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    return WorkflowManifestRegisterResponse(
        workflow=_serialize_workflow(wf),
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
        compiled_template=_serialize_compiled_template(compiled),
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
    run = get_orchestration_service(request).instantiate_workflow_run(
        user,
        workflow_uri=payload.workflow_uri,
        workspace_id=payload.workspace_id,
        parent_run_id=payload.parent_run_id,
        parent_step_execution_id=payload.parent_step_execution_id,
        trigger_id=payload.trigger_id,
        trigger_idempotency_key=payload.trigger_idempotency_key,
        execution_identity_mode=payload.execution_identity_mode,
        instance=str(request.url.path),
    )
    return WorkflowRunInstantiateResponse(
        run=_serialize_run(run),
        trace_id=_trace(request),
    )
