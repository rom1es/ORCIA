"""FastAPI Router for Adaptive Human Gates, Chunked Validation & <15s Guard (`Story 4.3`)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_bootstrap_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.human_gates import (
    ChunkApprovalSchemaItem,
    HumanGateChunkDecideRequest,
    HumanGateChunkDecideResponse,
    HumanGateEvaluateRequest,
    HumanGateEvaluateResponse,
    HumanGateEvaluationListResponse,
    HumanGateEvaluationSchemaItem,
    HumanGateFinalizeRequest,
    HumanGateFinalizeResponse,
)
from orcia_core.gates.human import ChunkApprovalRecord, HumanGateEvaluationRecord
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity

router = APIRouter(tags=["gates"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _enforce_human_gate_mutation_guard(
    request: Request, user: UserIdentity, workspace_id: str
) -> None:
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    bootstrap_svc = get_bootstrap_service(request)
    if bootstrap_svc.auth_service.evaluator.get_workspace(workspace_id) is not None:
        bootstrap_svc.auth_service.evaluator.enforce_scope_mutation_guard(
            user, workspace_id, instance=str(request.url.path)
        )


def _serialize_chunk(chunk: ChunkApprovalRecord) -> ChunkApprovalSchemaItem:
    return ChunkApprovalSchemaItem(
        id=chunk.id,
        gate_evaluation_id=chunk.gate_evaluation_id,
        workspace_id=chunk.workspace_id,
        run_id=chunk.run_id,
        step_execution_id=chunk.step_execution_id,
        chunk_key=chunk.chunk_key,
        section_title=chunk.section_title,
        section_index=chunk.section_index,
        content_markdown=chunk.content_markdown,
        word_count=chunk.word_count,
        human_authored_required=chunk.human_authored_required,
        status=chunk.status,
        reviewer_user_id=chunk.reviewer_user_id,
        human_anchor_signature_id=chunk.human_anchor_signature_id,
        human_anchor_sha256=chunk.human_anchor_sha256,
        challenge_reason=chunk.challenge_reason,
        reviewed_at=chunk.reviewed_at,
    )


def _serialize_human_gate(record: HumanGateEvaluationRecord) -> HumanGateEvaluationSchemaItem:
    return HumanGateEvaluationSchemaItem(
        id=record.id,
        workspace_id=record.workspace_id,
        run_id=record.run_id,
        step_execution_id=record.step_execution_id,
        step_key=record.step_key,
        policy=record.policy,
        status=record.status,
        auto_passed=record.auto_passed,
        deterministic_status=record.deterministic_status,
        agentic_score=record.agentic_score,
        ontology_conflicts=record.ontology_conflicts,
        stale_warnings=record.stale_warnings,
        total_word_count=record.total_word_count,
        briefing_4blocks_jsonb=dict(record.briefing_4blocks_jsonb),
        hypotheses_block_inspected=record.hypotheses_block_inspected,
        chunks=[_serialize_chunk(c) for c in record.chunks],
        review_duration_ms=record.review_duration_ms,
        fast_approval_warning=record.fast_approval_warning,
        reviewer_user_id=record.reviewer_user_id,
        outbox_event_id=record.outbox_event_id,
        evaluated_at=record.evaluated_at,
    )


@router.get(
    "/api/v1/gates/human/evaluations",
    response_model=HumanGateEvaluationListResponse,
    summary="List Adaptive Human Gate evaluations (`Story 4.3`, `AD-11`)",
    responses=PROBLEM_RESPONSES,
)
async def list_human_gate_evaluations_endpoint(
    request: Request,
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanGateEvaluationListResponse:
    resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    records = bootstrap_svc.gate_service.human_service.list_evaluations(workspace_id=workspace_id)
    return HumanGateEvaluationListResponse(
        evaluations=[_serialize_human_gate(r) for r in records],
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/gates/human/evaluate",
    response_model=HumanGateEvaluateResponse,
    summary=(
        "Evaluate an Adaptive Human Gate (`mandatory_full`, `risk_or_exception_based`, `sampling`)"
    ),
    responses=PROBLEM_RESPONSES,
)
async def evaluate_human_gate_endpoint(
    payload: HumanGateEvaluateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanGateEvaluateResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    _enforce_human_gate_mutation_guard(request, user, payload.workspace_id)
    trace_id = _trace(request)
    record = bootstrap_svc.gate_service.human_service.evaluate_human_gate(
        workspace_id=payload.workspace_id,
        run_id=payload.run_id,
        step_execution_id=payload.step_execution_id,
        step_key=payload.step_key,
        policy=payload.policy,
        artifact_payload=dict(payload.artifact_payload),
        deterministic_status=payload.deterministic_status,
        agentic_score=payload.agentic_score,
        ontology_conflicts=payload.ontology_conflicts,
        stale_warnings=payload.stale_warnings,
        briefing_4blocks_jsonb=(
            dict(payload.briefing_4blocks_jsonb)
            if payload.briefing_4blocks_jsonb is not None
            else None
        ),
        sampling_override=payload.sampling_override,
        trace_id=trace_id,
    )
    return HumanGateEvaluateResponse(
        evaluation=_serialize_human_gate(record),
        trace_id=trace_id,
    )


@router.post(
    "/api/v1/gates/human/{gate_evaluation_id}/inspect-hypotheses",
    response_model=HumanGateEvaluateResponse,
    summary="Mark Block 4 (`Hypothèses Retenues`) of the 4-Block Review Briefing as inspected",
    responses=PROBLEM_RESPONSES,
)
async def inspect_human_gate_hypotheses_endpoint(
    gate_evaluation_id: str,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanGateEvaluateResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    record = bootstrap_svc.gate_service.human_service.get_evaluation(gate_evaluation_id)
    _enforce_human_gate_mutation_guard(request, user, record.workspace_id)
    updated = bootstrap_svc.gate_service.human_service.inspect_briefing_hypotheses(
        gate_evaluation_id, reviewer_user_id=user.id
    )
    return HumanGateEvaluateResponse(
        evaluation=_serialize_human_gate(updated),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/gates/human/{gate_evaluation_id}/chunks/{chunk_key}/decide",
    response_model=HumanGateChunkDecideResponse,
    summary="Approve, co-edit (with SHA-256 signature), or challenge a section chunk (`UX-DR5`)",
    responses=PROBLEM_RESPONSES,
)
async def decide_human_gate_chunk_endpoint(
    gate_evaluation_id: str,
    chunk_key: str,
    payload: HumanGateChunkDecideRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanGateChunkDecideResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    record = bootstrap_svc.gate_service.human_service.get_evaluation(gate_evaluation_id)
    _enforce_human_gate_mutation_guard(request, user, record.workspace_id)
    chunk = bootstrap_svc.gate_service.human_service.decide_chunk(
        gate_evaluation_id,
        chunk_key,
        action=payload.action,
        reviewer_user_id=user.id,
        co_edited_content=payload.co_edited_content,
        challenge_reason=payload.challenge_reason,
    )
    return HumanGateChunkDecideResponse(
        chunk=_serialize_chunk(chunk),
        evaluation=_serialize_human_gate(record),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/gates/human/{gate_evaluation_id}/finalize",
    response_model=HumanGateFinalizeResponse,
    summary=(
        "Finalize Human Gate approval after checking chunks and <15s Anti-Rubber-Stamping Guard"
    ),
    responses=PROBLEM_RESPONSES,
)
async def finalize_human_gate_endpoint(
    gate_evaluation_id: str,
    payload: HumanGateFinalizeRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HumanGateFinalizeResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    bootstrap_svc = get_bootstrap_service(request)
    record = bootstrap_svc.gate_service.human_service.get_evaluation(gate_evaluation_id)
    _enforce_human_gate_mutation_guard(request, user, record.workspace_id)
    trace_id = _trace(request)
    finalized = bootstrap_svc.gate_service.human_service.finalize_human_gate(
        gate_evaluation_id,
        reviewer_user_id=user.id,
        review_duration_ms=payload.review_duration_ms,
        explicit_hypotheses_confirmation=payload.explicit_hypotheses_confirmation,
        trace_id=trace_id,
    )
    return HumanGateFinalizeResponse(
        evaluation=_serialize_human_gate(finalized),
        trace_id=trace_id,
    )
