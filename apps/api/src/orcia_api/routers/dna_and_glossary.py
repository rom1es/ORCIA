"""Epic 11 Story 11.2 Router — Causal DNA Chain, Text-to-Starlark & 2-Pass Glossary (`V4`)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from orcia_api.dependencies import get_dna_starlark_and_glossary_service
from orcia_api.routers.auth import resolve_request_user
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
    GlossaryCandidateItem,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["workspaces"],
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
DnaGlossaryServiceDep = Annotated[
    DnaStarlarkAndGlossaryLifecycleService,
    Depends(get_dna_starlark_and_glossary_service),
]


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


@router.post(
    "/{workspace_id}/dna-mechanisms/compile",
    response_model=GeneratedStarlarkMechanismResponse,
    summary="Compile a French norm into a self-tested Starlark mechanism (< 5 ms, Story 11.2)",
)
def compile_dna_starlark_mechanism(
    workspace_id: UUID,
    body: CompileStarlarkMechanismRequest,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> GeneratedStarlarkMechanismResponse:
    """Compile a French norm into a `.star` mechanism and prove PASS/FAIL on test payloads."""
    _ = workspace_id
    mech = svc.compile_from_natural_language(
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
    )
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


@router.post(
    "/{workspace_id}/dna-mechanisms/{mechanism_id}/evaluate",
    response_model=StarlarkEvaluationResponse,
    summary="Execute a compiled Starlark mechanism at Run-Time (< 2 ms, 0 LLM tokens)",
)
def evaluate_dna_starlark_mechanism(
    workspace_id: UUID,
    mechanism_id: UUID,
    body: EvaluateStarlarkMechanismRequest,
    _user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> StarlarkEvaluationResponse:
    """Evaluate a compiled `.star` mechanism in `< 2 ms` with `0` LLM tokens."""
    _ = workspace_id
    res = svc.evaluate_runtime_mechanism(
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
def extract_workspace_glossary_two_pass(
    workspace_id: UUID,
    body: TwoPassExtractionRequest,
    _user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> TwoPassExtractionResponse:
    """Execute 2-Pass extraction (`0 $` on `git_push`, FIFO `<= 15` & `Top-3` `Verrou V4`)."""
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
def promote_workspace_glossary_in_flow(
    workspace_id: UUID,
    body: InFlowPromotionRequest,
    user: CurrentUserDep,
    svc: DnaGlossaryServiceDep,
) -> InFlowPromotionResponse:
    """Promote checked L4 terms to `3_WORKSPACE` `ACTIVE` and invalidate Redis prompt cache."""
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
