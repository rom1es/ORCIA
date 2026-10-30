"""FastAPI Router for Deterministic Gates, Pattern Drift & Bootstrap Skills (`Story 4.1`)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_bootstrap_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.bootstrap import SystemBootstrapRunItem
from orcia_api.schemas.catalog import CatalogItemResponse
from orcia_api.schemas.gates import (
    DeterministicGateEvaluateRequest,
    DeterministicGateEvaluateResponse,
    GateEvaluationSchemaItem,
    GateEvaluationsListResponse,
    InitExistingProjectRequest,
    InitExistingProjectResponse,
    InitSkillRequest,
    InitSkillResponse,
    PatternDriftFindingSchemaItem,
    WorkspaceSpineBaselineSchemaItem,
)
from orcia_core.bootstrap import InitExistingProjectInput, InitSkillInput
from orcia_core.catalog.models import CatalogItemEntity
from orcia_core.gates.models import (
    DeterministicGateInput,
    GateEvaluationEntity,
    OntologyAxiomCheckRule,
)
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(tags=["gates"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_gate_evaluation(entity: GateEvaluationEntity) -> GateEvaluationSchemaItem:
    return GateEvaluationSchemaItem(
        id=entity.id,
        workspace_id=entity.workspace_id,
        run_id=entity.run_id,
        step_execution_id=entity.step_execution_id,
        step_key=entity.step_key,
        gate_type=entity.gate_type,
        sandbox_tier=entity.sandbox_tier,
        status=entity.status,
        score=entity.score,
        schema_validation_passed=entity.schema_validation_passed,
        ontology_axioms_passed=entity.ontology_axioms_passed,
        pattern_drift_passed=entity.pattern_drift_passed,
        pattern_drift_findings=[
            PatternDriftFindingSchemaItem(
                rule_id=f.rule_id,
                forbidden_symbol=f.forbidden_symbol,
                severity=f.severity,
                message=f.message,
            )
            for f in entity.pattern_drift_findings
        ],
        missing_sections=list(entity.missing_sections),
        violated_axioms=list(entity.violated_axioms),
        duration_ms=entity.duration_ms,
        outbox_event_id=entity.outbox_event_id,
        evaluated_at=entity.evaluated_at,
        sandbox_exit_code=entity.sandbox_exit_code,
        sandbox_stderr=entity.sandbox_stderr,
    )


def _serialize_catalog_item(item: CatalogItemEntity) -> CatalogItemResponse:
    return CatalogItemResponse(
        id=item.id,
        resource_id=item.resource_id,
        uri=item.uri,
        scheme=item.scheme,
        title=item.title,
        description=item.description,
        resource_type=item.resource_type,
        source_format=item.source_format,
        version=item.version,
        sha256=item.sha256,
        sha256_short=item.sha256_short,
        cas_key=item.cas_key,
        visibility_scope=item.visibility_scope,
        granted_permissions=["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
        source_masked=False,
    )


@router.post(
    "/api/v1/gates/deterministic/evaluate",
    response_model=DeterministicGateEvaluateResponse,
    summary="Evaluate a Deterministic Gate in the out-of-process Tier 1 Sandbox (`AD-9`, `FR-17`)",
    responses=PROBLEM_RESPONSES,
)
async def evaluate_deterministic_gate_endpoint(
    payload: DeterministicGateEvaluateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> DeterministicGateEvaluateResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    bootstrap_svc.auth_service.evaluator.enforce_scope_mutation_guard(
        user, payload.workspace_id, instance=str(request.url.path)
    )
    gate_eval = bootstrap_svc.gate_service.evaluate_deterministic_gate(
        DeterministicGateInput(
            workspace_id=payload.workspace_id,
            run_id=payload.run_id,
            step_execution_id=payload.step_execution_id,
            step_key=payload.step_key,
            artifact_payload=dict(payload.artifact_payload),
            required_sections=tuple(payload.required_sections),
            ontology_axioms=tuple(
                OntologyAxiomCheckRule(
                    axiom_key=ax.axiom_key,
                    forbidden_term=ax.forbidden_term,
                    required_term=ax.required_term,
                )
                for ax in payload.ontology_axioms
            ),
            allowed_dependencies=(
                tuple(payload.allowed_dependencies)
                if payload.allowed_dependencies is not None
                else None
            ),
            timeout_ms=payload.timeout_ms,
            max_memory_mb=payload.max_memory_mb,
            simulate_timeout_sleep_ms=payload.simulate_timeout_sleep_ms,
            simulate_network_escape=payload.simulate_network_escape,
            simulate_fs_escape_path=payload.simulate_fs_escape_path,
            simulate_tmp_overflow_mb=payload.simulate_tmp_overflow_mb,
            simulate_memory_alloc_mb=payload.simulate_memory_alloc_mb,
        ),
        raise_on_failure=payload.raise_on_failure,
    )
    return DeterministicGateEvaluateResponse(
        evaluation=_serialize_gate_evaluation(gate_eval),
        trace_id=_trace(request),
    )


@router.get(
    "/api/v1/gates/evaluations",
    response_model=GateEvaluationsListResponse,
    summary="List Deterministic, Agentic & Human Gate evaluations (`AD-9..11`)",
    responses=PROBLEM_RESPONSES,
)
async def list_gate_evaluations_endpoint(
    request: Request,
    run_id: str | None = Query(default=None, min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> GateEvaluationsListResponse:
    resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    evals = bootstrap_svc.gate_service.list_evaluations(run_id=run_id)
    return GateEvaluationsListResponse(
        evaluations=[_serialize_gate_evaluation(e) for e in evals],
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/bootstrap/init-existing-project",
    response_model=InitExistingProjectResponse,
    summary="Execute governed `orcia://system/bootstrap/init-existing-project` (`FR-28`, `AD-16`)",
    responses=PROBLEM_RESPONSES,
)
async def execute_init_existing_project_endpoint(
    payload: InitExistingProjectRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> InitExistingProjectResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    outcome = bootstrap_svc.execute_init_existing_project(
        user,
        InitExistingProjectInput(
            workspace_id=payload.workspace_id,
            repository_uri=payload.repository_uri,
            detected_dependencies=tuple(payload.detected_dependencies),
            architecture_paradigm=payload.architecture_paradigm,
            human_anchor_justification=payload.human_anchor_justification,
            human_anchor_signature=payload.human_anchor_signature,
            spine_version=payload.spine_version,
        ),
        instance=str(request.url.path),
    )
    bl = outcome.spine_baseline
    return InitExistingProjectResponse(
        run=SystemBootstrapRunItem(**asdict(outcome.run)),
        spine_baseline=WorkspaceSpineBaselineSchemaItem(
            workspace_id=bl.workspace_id,
            spine_version=bl.spine_version,
            status=bl.status,
            allowed_dependencies=list(bl.allowed_dependencies),
            spine_markdown=bl.spine_markdown,
            content_sha256=bl.content_sha256,
            signed_by_user_id=bl.signed_by_user_id,
            human_anchor_signature=bl.human_anchor_signature,
        ),
        catalog_item=_serialize_catalog_item(outcome.catalog_item),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/bootstrap/init-skill",
    response_model=InitSkillResponse,
    summary=(
        "Execute governed `orcia://system/bootstrap/init-skill` with Tier 1 Sandbox certification"
    ),
    responses=PROBLEM_RESPONSES,
)
async def execute_init_skill_endpoint(
    payload: InitSkillRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> InitSkillResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    outcome = bootstrap_svc.execute_init_skill(
        user,
        InitSkillInput(
            workspace_id=payload.workspace_id,
            skill_key=payload.skill_key,
            skill_uri=payload.skill_uri,
            title=payload.title,
            description=payload.description,
            version=payload.version,
            test_payload=dict(payload.test_payload),
            required_sections=tuple(payload.required_sections),
            timeout_ms=payload.timeout_ms,
            max_memory_mb=payload.max_memory_mb,
            visibility_scope=payload.visibility_scope,
            simulate_timeout_sleep_ms=payload.simulate_timeout_sleep_ms,
            simulate_network_escape=payload.simulate_network_escape,
            simulate_fs_escape_path=payload.simulate_fs_escape_path,
            simulate_memory_alloc_mb=payload.simulate_memory_alloc_mb,
        ),
        instance=str(request.url.path),
    )
    return InitSkillResponse(
        run=SystemBootstrapRunItem(**asdict(outcome.run)),
        catalog_item=_serialize_catalog_item(outcome.catalog_item),
        gate_evaluation=_serialize_gate_evaluation(outcome.gate_evaluation),
        trace_id=_trace(request),
    )
