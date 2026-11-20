"""Domain models and repository port for Starlark DNA mechanisms & 2-pass glossary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

ExtractionTriggerType = Literal["git_push", "mr_pr", "manual_sync", "human_gate"]
DnaStereotype = Literal["CONCEPT", "DIRECTIVE", "NORM", "MECHANISM"]


@dataclass(frozen=True, slots=True)
class GeneratedStarlarkMechanism:
    """Compiled and self-tested Starlark mechanism (`Story 11.2`, `< 5 ms` Design-Time)."""

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
    signed_and_active: bool = False
    workspace_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GlossaryCandidateItem:
    """Candidate term in the `✨ À valider (N <= 15)` FIFO queue (`Verrou V4`)."""

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


@dataclass(frozen=True, slots=True)
class TwoPassExtractionResult:
    """Result of the 2-pass `OntologyExtractor` (`Story 11.2`, `Verrou V4`)."""

    trigger_type: ExtractionTriggerType
    pass_1_deterministic_executed: bool
    pass_2_llm_batch_executed: bool
    llm_calls_count: int
    purged_expired_ephemeral_count: int
    active_queue_candidates: tuple[GlossaryCandidateItem, ...]
    top3_in_flow_prechecked: tuple[GlossaryCandidateItem, ...]


@dataclass(frozen=True, slots=True)
class InFlowPromotionResult:
    """Result of *In-Flow* promotion from the 4-block Review Briefing (`Verrou V4`)."""

    workspace_id: UUID
    promoted_terms: tuple[str, ...]
    rejected_terms: tuple[str, ...]
    what_if_impact_warnings: tuple[str, ...]
    assistant_prompt_cache_invalidated: bool


class StarlarkMechanismRepositoryPort(Protocol):
    """Port for persisting and loading compiled/signed Starlark DNA mechanisms."""

    async def save_mechanism(
        self,
        *,
        workspace_id: UUID,
        mechanism: GeneratedStarlarkMechanism,
        signed_by_user_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism:
        """Upsert a compiled Starlark mechanism for a workspace."""
        ...

    async def get_mechanism(
        self,
        *,
        workspace_id: UUID,
        mechanism_id: UUID,
    ) -> GeneratedStarlarkMechanism | None:
        """Load a compiled Starlark mechanism by `(workspace_id, mechanism_id)`."""
        ...

    async def list_mechanisms(
        self,
        *,
        workspace_id: UUID,
    ) -> list[GeneratedStarlarkMechanism]:
        """List compiled Starlark mechanisms for a workspace ordered by recency."""
        ...

    async def activate_mechanism(
        self,
        *,
        workspace_id: UUID,
        mechanism_id: UUID,
        signed_by_user_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism | None:
        """Mark a persisted Starlark mechanism as signed and active."""
        ...
