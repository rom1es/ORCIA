"""HTTP/OpenAPI 3.1 transport schemas for Epic 11 Story 11.2 (DNA Chain, Starlark, Glossary V4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompileStarlarkMechanismRequest(BaseModel):
    """Request to compile a French norm into a self-tested `.star` mechanism (`Story 11.2`)."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(..., min_length=2, max_length=128)
    directive_title: str = Field(..., min_length=2, max_length=255)
    norm_title: str = Field(..., min_length=2, max_length=255)
    natural_language_rule_fr: str = Field(..., min_length=5, max_length=2000)
    target_json_schema: dict[str, Any] = Field(default_factory=dict)
    required_field: str = Field(..., min_length=1, max_length=128)
    regex_pattern: str = Field(default=r"^[A-Z0-9_-]{3,64}$", min_length=1, max_length=512)
    passing_test_payload: dict[str, Any] | None = None
    failing_test_payload: dict[str, Any] | None = None
    simulate_initial_bad_regex: bool = False


class GeneratedStarlarkMechanismResponse(BaseModel):
    """Response representing a compiled and self-tested `.star` mechanism."""

    model_config = ConfigDict(extra="forbid")

    mechanism_id: UUID
    rule_id: str
    directive_title: str
    norm_title: str
    script_name: str
    starlark_code: str
    sha256: str
    passing_test_payload: dict[str, Any]
    failing_test_payload: dict[str, Any]
    explanation_fr: str
    self_corrected: bool
    compile_elapsed_ms: float
    verified_badge_fr: str
    causal_breadcrumb: str
    signed_and_active: bool


class EvaluateStarlarkMechanismRequest(BaseModel):
    """Request to execute a `.star` mechanism at Run-Time (`< 2 ms`, `0` LLM tokens)."""

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]


class StarlarkVerdictSchema(BaseModel):
    """Single rule verdict emitted by `orcia_sys.emit_verdict`."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    status: Literal["PASS", "FAIL"]
    message_fr: str


class StarlarkStagedEffectSchema(BaseModel):
    """Staged side-effect emitted by `orcia_sys.emit_effect` (`AD-3`)."""

    model_config = ConfigDict(extra="forbid")

    action_type: str
    target_uri: str
    payload: dict[str, Any]
    staged_only: bool


class StarlarkEvaluationResponse(BaseModel):
    """Response from `StarlarkMechanismSandbox.evaluate_script()`."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    verdicts: list[StarlarkVerdictSchema]
    staged_effects: list[StarlarkStagedEffectSchema]
    steps_executed: int
    elapsed_ms: float
    llm_tokens_consumed: int


class RawGlossaryCandidateInput(BaseModel):
    """Input candidate term for 2-pass extraction."""

    model_config = ConfigDict(extra="forbid")

    canonical_term: str = Field(..., min_length=2, max_length=255)
    definition_fr: str = Field(..., min_length=3, max_length=2000)
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)


class TwoPassExtractionRequest(BaseModel):
    """Request to run the 2-pass `OntologyExtractor` (`Story 11.2`, `Verrou V4`)."""

    model_config = ConfigDict(extra="forbid")

    trigger_type: Literal["git_push", "mr_pr", "manual_sync", "human_gate"]
    raw_candidates: list[RawGlossaryCandidateInput] = Field(default_factory=list)
    existing_enterprise_terms: dict[str, str] = Field(default_factory=dict)


class GlossaryCandidateSchema(BaseModel):
    """Candidate term in the `✨ À valider (N <= 15)` FIFO queue."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID
    workspace_id: UUID
    canonical_term: str
    fingerprint: str
    definition_fr: str
    confidence_score: float
    level: Literal["3_WORKSPACE", "4_RUN_EPHEMERAL"]
    status: Literal["PENDING_VALIDATION", "ACTIVE", "REJECTED_CANDIDATE"]
    ontology_conflict_warning: str | None
    pre_checked_for_in_flow_promotion: bool
    created_at: datetime


class TwoPassExtractionResponse(BaseModel):
    """Response from the 2-pass `OntologyExtractor` (`Verrou V4`)."""

    model_config = ConfigDict(extra="forbid")

    trigger_type: Literal["git_push", "mr_pr", "manual_sync", "human_gate"]
    pass_1_deterministic_executed: bool
    pass_2_llm_batch_executed: bool
    llm_calls_count: int
    purged_expired_ephemeral_count: int
    active_queue_candidates: list[GlossaryCandidateSchema]
    top3_in_flow_prechecked: list[GlossaryCandidateSchema]


class InFlowPromotionRequest(BaseModel):
    """Request to promote or reject L4 glossary candidates *In-Flow* (`Verrou V4`)."""

    model_config = ConfigDict(extra="forbid")

    promote_candidate_ids: list[UUID] = Field(default_factory=list)
    reject_candidate_ids: list[UUID] = Field(default_factory=list)


class InFlowPromotionResponse(BaseModel):
    """Response from *In-Flow* glossary promotion (`Verrou V4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    promoted_terms: list[str]
    rejected_terms: list[str]
    what_if_impact_warnings: list[str]
    assistant_prompt_cache_invalidated: bool
