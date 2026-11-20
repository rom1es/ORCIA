"""Epic 11 Story 11.2 Router — Causal DNA Chain, Text-to-Starlark & 2-Pass Glossary (`V4`)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from orcia_api.dependencies import get_auth_service, get_dna_starlark_and_glossary_service
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.dna_glossary import (
    CompileStarlarkMechanismRequest,
    EvaluateStarlarkMechanismRequest,
    GeneratedStarlarkMechanismResponse,
    GlossaryCandidateSchema,
    InFlowPromotionRequest,
    InFlowPromotionResponse,
    StarlarkEvaluationResponse,
    StarlarkStagedEffectSchema,
    StarlarkVerdictSchema,
    TwoPassExtractionRequest,
    TwoPassExtractionResponse,
)
from orcia_core.orchestration.dna_starlark_and_glossary_lifecycle import (
    DnaStarlarkAndGlossaryLifecycleService,
    GeneratedStarlarkMechanism,
    GlossaryCandidateItem,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["workspaces"],
    responses=PROBLEM_RESPONSES,
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
DnaGlossaryServiceDep = Annotated[
    DnaStarlarkAndGlossaryLifecycleService,
    Depends(get_dna_starlark_and_glossary_service),
]


async def _validate_dna_workspace_access(
    request: Request,
    user: UserIdentity,
    workspace_id: UUID,
    *,
    require_write: bool,
) -> None:
    if require_write:
        enforce_observer_headers_guard(request, user)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    if user.platform_role != "PLATFORM_ADMIN":
        ws = auth_svc.evaluator.get_workspace(str(workspace_id))
        if ws is not None:
            access = auth_svc.evaluator.resolve_workspace_access(user, ws.id)
            if access is None:
                raise ScopeAccessDeniedError(instance=str(request.url.path))
            if require_write and access.access_mode == "READ_ONLY_OBSERVER":
                raise ObserverModeReadOnlyError(instance=str(request.url.path))


def _to_candidate_schema(item: GlossaryCandidateItem) -> GlossaryCandidateSchema:
    return GlossaryCandidateSchema(
        candidate_id=item.candidate_id,
        workspace_id=item.workspace_id,
        canonical_term=item.canonical_term,
        fingerprint=item.fingerprint,
        definition_fr=item.definition_fr,
        confidence_score=item.confidence_score,
        level=item.level,
        status=item.status,
        ontology_conflict_warning=item.ontology_conflict_warning,
        pre_checked_for_in_flow_promotion=item.pre_checked_for_in_flow_promotion,
        created_at=item.created_at,
    )


def _to_mechanism_response(
    mech: GeneratedStarlarkMechanism,
) -> GeneratedStarlarkMechanismResponse:
    return GeneratedStarlarkMechanismResponse(
        mechanism_id=mech.mechanism_id,
        rule_id=mech.rule_id,
        directive_title=mech.directive_title,
        norm_title=mech.norm_title,
        script_name=mech.script_name,
        starlark_code=mech.starlark_code,
        sha256=mech.sha256,
        passing_test_payload=mech.passing_test_payload,
        failing_test_payload=mech.failing_test_payload,
        explanation_fr=mech.explanation_fr,
        self_corrected=mech.self_corrected,
        compile_elapsed_ms=mech.compile_elapsed_ms,
        verified_badge_fr=mech.verified_badge_fr,
        causal_breadcrumb=mech.causal_breadcrumb,
        signed_and_active=mech.signed_and_active,
    )


@router.get(
    "/{workspace_id}/dna-mechanisms",
    response_model=list[GeneratedStarlarkMechanismResponse],
    summary="List persisted Starlark DNA mechanisms for a workspace (PG18)",
)
async def list_dna_starlark_mechanisms(
    workspace_id: UUID,
    request: Request,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> list[GeneratedStarlarkMechanismResponse]:
    """Return persisted Starlark DNA mechanisms for the workspace from PostgreSQL 18."""
    await _validate_dna_workspace_access(request, user, workspace_id, require_write=False)
    items = await svc.list_mechanisms_for_workspace_async(workspace_id=workspace_id)
    return [_to_mechanism_response(item) for item in items]


@router.post(
    "/{workspace_id}/dna-mechanisms/compile",
    response_model=GeneratedStarlarkMechanismResponse,
    summary="Compile a French norm into a self-tested Starlark mechanism (< 5 ms, Story 11.2)",
)
async def compile_dna_starlark_mechanism(
    workspace_id: UUID,
    body: CompileStarlarkMechanismRequest,
    request: Request,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> GeneratedStarlarkMechanismResponse:
    """Compile a French norm into a `.star` mechanism, test PASS/FAIL, and persist to PG18."""
    await _validate_dna_workspace_access(request, user, workspace_id, require_write=True)
    mech = await svc.compile_from_natural_language_async(
        workspace_id=workspace_id,
        actor_role=user.platform_role,
        rule_id=body.rule_id,
        directive_title=body.directive_title,
        norm_title=body.norm_title,
        natural_language_rule_fr=body.natural_language_rule_fr,
        target_json_schema=body.target_json_schema,
        required_field=body.required_field,
        regex_pattern=body.regex_pattern,
        passing_test_payload=body.passing_test_payload,
        failing_test_payload=body.failing_test_payload,
        simulate_initial_bad_regex=body.simulate_initial_bad_regex,
        signed_by_user_id=UUID(user.id),
    )
    return _to_mechanism_response(mech)


@router.post(
    "/{workspace_id}/dna-mechanisms/{mechanism_id}/activate",
    response_model=GeneratedStarlarkMechanismResponse,
    summary="Sign and activate a persisted Starlark DNA mechanism in PG18",
)
async def activate_dna_starlark_mechanism(
    workspace_id: UUID,
    mechanism_id: UUID,
    request: Request,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> GeneratedStarlarkMechanismResponse:
    """Sign and activate a Starlark mechanism in PostgreSQL 18."""
    await _validate_dna_workspace_access(request, user, workspace_id, require_write=True)
    mech = await svc.activate_mechanism_async(
        workspace_id=workspace_id,
        mechanism_id=mechanism_id,
        actor_role=user.platform_role,
        signed_by_user_id=UUID(user.id),
    )
    return _to_mechanism_response(mech)


@router.post(
    "/{workspace_id}/dna-mechanisms/{mechanism_id}/evaluate",
    response_model=StarlarkEvaluationResponse,
    summary="Execute a compiled Starlark mechanism at Run-Time (< 2 ms, 0 LLM tokens)",
)
async def evaluate_dna_starlark_mechanism(
    workspace_id: UUID,
    mechanism_id: UUID,
    body: EvaluateStarlarkMechanismRequest,
    request: Request,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> StarlarkEvaluationResponse:
    """Evaluate a compiled `.star` mechanism in `< 2 ms` with `0` LLM tokens."""
    await _validate_dna_workspace_access(request, user, workspace_id, require_write=False)
    res = await svc.evaluate_runtime_mechanism_async(
        workspace_id=workspace_id,
        mechanism_id=mechanism_id,
        payload=body.payload,
    )
    return StarlarkEvaluationResponse(
        passed=res.passed,
        verdicts=[
            StarlarkVerdictSchema(
                rule_id=v.rule_id,
                status=v.status,
                message_fr=v.message_fr,
            )
            for v in res.verdicts
        ],
        staged_effects=[
            StarlarkStagedEffectSchema(
                action_type=e.action_type,
                target_uri=e.target_uri,
                payload=e.payload,
                staged_only=e.staged_only,
            )
            for e in res.staged_effects
        ],
        steps_executed=res.steps_executed,
        elapsed_ms=res.elapsed_ms,
        llm_tokens_consumed=res.llm_tokens_consumed,
    )


@router.post(
    "/{workspace_id}/glossary/extract-two-pass",
    response_model=TwoPassExtractionResponse,
    summary="Run 2-Pass OntologyExtractor (0 $ on git_push, <= 15 FIFO & Top-3 pre-checked V4)",
)
async def extract_workspace_glossary_two_pass(
    workspace_id: UUID,
    body: TwoPassExtractionRequest,
    request: Request,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> TwoPassExtractionResponse:
    """Execute 2-Pass extraction (`0 $` on `git_push`, FIFO `<= 15` & `Top-3` `Verrou V4`)."""
    await _validate_dna_workspace_access(request, user, workspace_id, require_write=True)
    res = svc.extract_glossary_candidates_two_pass(
        workspace_id=workspace_id,
        trigger_type=body.trigger_type,
        raw_candidates=[
            (c.canonical_term, c.definition_fr, c.confidence_score) for c in body.raw_candidates
        ],
        existing_enterprise_terms=body.existing_enterprise_terms,
    )
    return TwoPassExtractionResponse(
        trigger_type=res.trigger_type,
        pass_1_deterministic_executed=res.pass_1_deterministic_executed,
        pass_2_llm_batch_executed=res.pass_2_llm_batch_executed,
        llm_calls_count=res.llm_calls_count,
        purged_expired_ephemeral_count=res.purged_expired_ephemeral_count,
        active_queue_candidates=[_to_candidate_schema(c) for c in res.active_queue_candidates],
        top3_in_flow_prechecked=[_to_candidate_schema(c) for c in res.top3_in_flow_prechecked],
    )


@router.post(
    "/{workspace_id}/glossary/promote-in-flow",
    response_model=InFlowPromotionResponse,
    summary="Promote or reject L4 glossary candidates In-Flow and invalidate prompt cache (V4)",
)
async def promote_workspace_glossary_in_flow(
    workspace_id: UUID,
    body: InFlowPromotionRequest,
    request: Request,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> InFlowPromotionResponse:
    """Promote checked L4 terms to `3_WORKSPACE` `ACTIVE` and invalidate Redis prompt cache."""
    await _validate_dna_workspace_access(request, user, workspace_id, require_write=True)
    res = svc.promote_or_reject_in_flow(
        workspace_id=workspace_id,
        actor_role=user.platform_role,
        promote_candidate_ids=body.promote_candidate_ids,
        reject_candidate_ids=body.reject_candidate_ids,
    )
    return InFlowPromotionResponse(
        workspace_id=res.workspace_id,
        promoted_terms=list(res.promoted_terms),
        rejected_terms=list(res.rejected_terms),
        what_if_impact_warnings=list(res.what_if_impact_warnings),
        assistant_prompt_cache_invalidated=res.assistant_prompt_cache_invalidated,
    )
