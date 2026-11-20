"""Story 11.2: Causal DNA Chain, Text-to-Starlark Compiler & 2-Pass Glossary Lifecycle (`V4`)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any
from uuid import UUID

from orcia_core.gates import StarlarkEvaluationResult, StarlarkMechanismSandbox
from orcia_core.orchestration._dna_glossary_ops import (
    execute_promote_or_reject_in_flow,
    execute_two_pass_glossary_extraction,
)
from orcia_core.orchestration._dna_starlark_compiler import (
    compile_starlark_from_natural_language,
    evaluate_starlark_mechanism_in_sandbox,
)
from orcia_core.orchestration._dna_starlark_models import (
    DnaStereotype,
    ExtractionTriggerType,
    GeneratedStarlarkMechanism,
    GlossaryCandidateItem,
    InFlowPromotionResult,
    StarlarkMechanismRepositoryPort,
    TwoPassExtractionResult,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.permissions.errors import ObserverModeReadOnlyError


@dataclass
class DnaStarlarkAndGlossaryLifecycleService:
    """Domain service for Story 11.2 (DNA Chain, Text-to-Starlark & 2-Pass Glossary `V4`)."""

    repository: StarlarkMechanismRepositoryPort | None = None
    strict_sql: bool = False
    _sandbox: StarlarkMechanismSandbox = field(default_factory=StarlarkMechanismSandbox)
    _mechanisms: dict[UUID, GeneratedStarlarkMechanism] = field(default_factory=dict)
    _active_concepts: dict[UUID, dict[str, str]] = field(default_factory=dict)
    _pending_queue: dict[UUID, list[GlossaryCandidateItem]] = field(default_factory=dict)
    _rejected_fingerprints: dict[UUID, set[str]] = field(default_factory=dict)
    _cache_invalidation_counter: dict[UUID, int] = field(default_factory=dict)

    def _require_repository_if_strict(self) -> StarlarkMechanismRepositoryPort | None:
        if self.strict_sql and self.repository is None:
            raise RuntimeError(
                "DnaStarlarkAndGlossaryLifecycleService requires a PG18 repository "
                "when strict_sql=True."
            )
        return self.repository

    def compile_from_natural_language(
        self,
        *,
        actor_role: str,
        rule_id: str,
        directive_title: str,
        norm_title: str,
        natural_language_rule_fr: str,
        target_json_schema: dict[str, Any],
        required_field: str,
        regex_pattern: str = r"^[A-Z0-9_-]{3,64}$",
        passing_test_payload: dict[str, Any] | None = None,
        failing_test_payload: dict[str, Any] | None = None,
        simulate_initial_bad_regex: bool = False,
        workspace_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism:
        """Compile a French norm into a self-tested `.star` mechanism (`< 5 ms`, 1 retry)."""
        mech = compile_starlark_from_natural_language(
            self._sandbox,
            actor_role=actor_role,
            rule_id=rule_id,
            directive_title=directive_title,
            norm_title=norm_title,
            natural_language_rule_fr=natural_language_rule_fr,
            target_json_schema=target_json_schema,
            required_field=required_field,
            regex_pattern=regex_pattern,
            passing_test_payload=passing_test_payload,
            failing_test_payload=failing_test_payload,
            simulate_initial_bad_regex=simulate_initial_bad_regex,
            workspace_id=workspace_id,
        )
        self._mechanisms[mech.mechanism_id] = mech
        return mech

    async def compile_from_natural_language_async(
        self,
        *,
        workspace_id: UUID,
        actor_role: str,
        rule_id: str,
        directive_title: str,
        norm_title: str,
        natural_language_rule_fr: str,
        target_json_schema: dict[str, Any],
        required_field: str,
        regex_pattern: str = r"^[A-Z0-9_-]{3,64}$",
        passing_test_payload: dict[str, Any] | None = None,
        failing_test_payload: dict[str, Any] | None = None,
        simulate_initial_bad_regex: bool = False,
        signed_by_user_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism:
        """Compile a Starlark mechanism and persist it in PostgreSQL 18 when configured."""
        repo = self._require_repository_if_strict()
        mech = self.compile_from_natural_language(
            actor_role=actor_role,
            rule_id=rule_id,
            directive_title=directive_title,
            norm_title=norm_title,
            natural_language_rule_fr=natural_language_rule_fr,
            target_json_schema=target_json_schema,
            required_field=required_field,
            regex_pattern=regex_pattern,
            passing_test_payload=passing_test_payload,
            failing_test_payload=failing_test_payload,
            simulate_initial_bad_regex=simulate_initial_bad_regex,
            workspace_id=workspace_id,
        )
        if repo is not None:
            mech = await repo.save_mechanism(
                workspace_id=workspace_id,
                mechanism=mech,
                signed_by_user_id=signed_by_user_id,
            )
            self._mechanisms[mech.mechanism_id] = mech
        return mech

    async def list_mechanisms_for_workspace_async(
        self,
        *,
        workspace_id: UUID,
    ) -> list[GeneratedStarlarkMechanism]:
        """List persisted Starlark mechanisms for a workspace from PG18 (or memory)."""
        repo = self._require_repository_if_strict()
        if repo is not None:
            rows = await repo.list_mechanisms(workspace_id=workspace_id)
            for item in rows:
                self._mechanisms[item.mechanism_id] = item
            return rows
        return [
            m for m in reversed(list(self._mechanisms.values())) if m.workspace_id == workspace_id
        ]

    async def activate_mechanism_async(
        self,
        *,
        workspace_id: UUID,
        mechanism_id: UUID,
        actor_role: str,
        signed_by_user_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism:
        """Sign and activate a Starlark mechanism in PostgreSQL 18 (or memory)."""
        if actor_role == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot compile or activate Gate mechanisms."
            )
        repo = self._require_repository_if_strict()
        if repo is not None:
            activated = await repo.activate_mechanism(
                workspace_id=workspace_id,
                mechanism_id=mechanism_id,
                signed_by_user_id=signed_by_user_id,
            )
            if activated is None:
                raise ResourceNotFoundError(
                    detail_override=f"Unknown Starlark mechanism '{mechanism_id}'."
                )
            self._mechanisms[activated.mechanism_id] = activated
            return activated
        existing = self._mechanisms.get(mechanism_id)
        if existing is None:
            raise ResourceNotFoundError(
                detail_override=f"Unknown Starlark mechanism '{mechanism_id}'."
            )
        updated = replace(existing, signed_and_active=True, workspace_id=workspace_id)
        self._mechanisms[mechanism_id] = updated
        return updated

    def evaluate_runtime_mechanism(
        self,
        *,
        mechanism_id: UUID,
        payload: dict[str, Any],
    ) -> StarlarkEvaluationResult:
        """Execute a compiled `.star` mechanism at Run-Time (`< 2 ms`, `0` LLM tokens)."""
        return evaluate_starlark_mechanism_in_sandbox(
            self._sandbox,
            mechanism=self._mechanisms.get(mechanism_id),
            mechanism_id=mechanism_id,
            payload=payload,
        )

    async def evaluate_runtime_mechanism_async(
        self,
        *,
        workspace_id: UUID,
        mechanism_id: UUID,
        payload: dict[str, Any],
    ) -> StarlarkEvaluationResult:
        """Load from PG18 if needed and evaluate a `.star` mechanism at Run-Time."""
        repo = self._require_repository_if_strict()
        mech = self._mechanisms.get(mechanism_id)
        if mech is None and repo is not None:
            mech = await repo.get_mechanism(workspace_id=workspace_id, mechanism_id=mechanism_id)
            if mech is not None:
                self._mechanisms[mech.mechanism_id] = mech
        return evaluate_starlark_mechanism_in_sandbox(
            self._sandbox,
            mechanism=mech,
            mechanism_id=mechanism_id,
            payload=payload,
        )

    def extract_glossary_candidates_two_pass(
        self,
        *,
        workspace_id: UUID,
        trigger_type: ExtractionTriggerType,
        raw_candidates: list[tuple[str, str, float]],
        existing_enterprise_terms: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> TwoPassExtractionResult:
        """Execute 2-Pass `OntologyExtractor` (`0 $` on `git_push`, FIFO `<= 15` & `Top-3` `V4`)."""
        return execute_two_pass_glossary_extraction(
            workspace_id=workspace_id,
            trigger_type=trigger_type,
            raw_candidates=raw_candidates,
            active_map=self._active_concepts.setdefault(workspace_id, {}),
            rejected_set=self._rejected_fingerprints.setdefault(workspace_id, set()),
            queue=self._pending_queue.setdefault(workspace_id, []),
            existing_enterprise_terms=existing_enterprise_terms,
            now=now,
        )

    def promote_or_reject_in_flow(
        self,
        *,
        workspace_id: UUID,
        actor_role: str,
        promote_candidate_ids: list[UUID],
        reject_candidate_ids: list[UUID],
    ) -> InFlowPromotionResult:
        """Promote checked L4 terms to `3_WORKSPACE` `ACTIVE` and invalidate prompt cache."""
        return execute_promote_or_reject_in_flow(
            workspace_id=workspace_id,
            actor_role=actor_role,
            promote_candidate_ids=promote_candidate_ids,
            reject_candidate_ids=reject_candidate_ids,
            queue=self._pending_queue.setdefault(workspace_id, []),
            active_map=self._active_concepts.setdefault(workspace_id, {}),
            rejected_set=self._rejected_fingerprints.setdefault(workspace_id, set()),
            cache_invalidation_counter=self._cache_invalidation_counter,
        )


__all__ = [
    "DnaStereotype",
    "DnaStarlarkAndGlossaryLifecycleService",
    "ExtractionTriggerType",
    "GeneratedStarlarkMechanism",
    "GlossaryCandidateItem",
    "InFlowPromotionResult",
    "StarlarkMechanismRepositoryPort",
    "TwoPassExtractionResult",
]
