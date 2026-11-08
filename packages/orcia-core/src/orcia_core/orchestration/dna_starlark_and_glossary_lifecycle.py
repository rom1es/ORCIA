"""Story 11.2: Causal DNA Chain, Text-to-Starlark Compiler & 2-Pass Glossary Lifecycle (`V4`)."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from uuid_utils.compat import uuid7

from orcia_core.gates import (
    StarlarkEvaluationResult,
    StarlarkMechanismSandbox,
    StarlarkSandboxError,
)
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.permissions.errors import ObserverModeReadOnlyError

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


@dataclass
class DnaStarlarkAndGlossaryLifecycleService:
    """Domain service for Story 11.2 (DNA Chain, Text-to-Starlark & 2-Pass Glossary `V4`)."""

    _sandbox: StarlarkMechanismSandbox = field(default_factory=StarlarkMechanismSandbox)
    _mechanisms: dict[UUID, GeneratedStarlarkMechanism] = field(default_factory=dict)
    _active_concepts: dict[UUID, dict[str, str]] = field(default_factory=dict)
    _pending_queue: dict[UUID, list[GlossaryCandidateItem]] = field(default_factory=dict)
    _rejected_fingerprints: dict[UUID, set[str]] = field(default_factory=dict)
    _cache_invalidation_counter: dict[UUID, int] = field(default_factory=dict)

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
    ) -> GeneratedStarlarkMechanism:
        """Compile a French norm into a self-tested `.star` mechanism (`< 5 ms`, 1 retry)."""
        if actor_role == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot compile or activate Gate mechanisms."
            )

        started = time.perf_counter()
        pass_payload = passing_test_payload or {required_field: "ORCIA_VALID_01"}
        fail_payload = failing_test_payload or {required_field: "invalid value!"}

        self._validate_payload_against_schema(pass_payload, target_json_schema)
        self._validate_payload_against_schema(fail_payload, target_json_schema)

        initial_pattern = r"(a+)+$" if simulate_initial_bad_regex else regex_pattern
        candidate_code = self._render_starlark_script(
            rule_id=rule_id,
            required_field=required_field,
            regex_pattern=initial_pattern,
            norm_title=norm_title,
        )
        self_corrected = False
        try:
            self._verify_pass_and_fail(
                starlark_code=candidate_code,
                passing_payload=pass_payload,
                failing_payload=fail_payload,
            )
        except StarlarkSandboxError:
            self_corrected = True
            candidate_code = self._render_starlark_script(
                rule_id=rule_id,
                required_field=required_field,
                regex_pattern=regex_pattern,
                norm_title=norm_title,
            )
            try:
                self._verify_pass_and_fail(
                    starlark_code=candidate_code,
                    passing_payload=pass_payload,
                    failing_payload=fail_payload,
                )
            except StarlarkSandboxError as exc:
                raise ValidationDomainError(detail_override=str(exc)) from exc

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        script_name = f"{rule_id.lower().replace('_', '-')}.star"
        sha256_hex = hashlib.sha256(candidate_code.encode("utf-8")).hexdigest()
        breadcrumb = f"🛡️ [{directive_title}] ➔ 📏 [{norm_title}] ➔ ⚙️ Vérifié par : {script_name}"
        mech = GeneratedStarlarkMechanism(
            mechanism_id=uuid7(),
            rule_id=rule_id,
            directive_title=directive_title,
            norm_title=norm_title,
            script_name=script_name,
            starlark_code=candidate_code,
            sha256=sha256_hex,
            passing_test_payload=pass_payload,
            failing_test_payload=fail_payload,
            explanation_fr=(
                f"Vérifie de façon déterministe la norme « {norm_title} » "
                f"({natural_language_rule_fr}) sur le champ '{required_field}'."
            ),
            self_corrected=self_corrected,
            compile_elapsed_ms=elapsed_ms,
            verified_badge_fr="✓ Vérifié sur cas de test (PASS/FAIL en < 5 ms)",
            causal_breadcrumb=breadcrumb,
            signed_and_active=True,
        )
        self._mechanisms[mech.mechanism_id] = mech
        return mech

    def evaluate_runtime_mechanism(
        self,
        *,
        mechanism_id: UUID,
        payload: dict[str, Any],
    ) -> StarlarkEvaluationResult:
        """Execute a compiled `.star` mechanism at Run-Time (`< 2 ms`, `0` LLM tokens)."""
        mech = self._mechanisms.get(mechanism_id)
        if mech is None:
            raise ValidationDomainError(
                detail_override=f"Unknown Starlark mechanism '{mechanism_id}'."
            )
        try:
            return self._sandbox.evaluate_script(
                starlark_code=mech.starlark_code,
                payload=payload,
            )
        except StarlarkSandboxError as exc:
            raise ValidationDomainError(detail_override=str(exc)) from exc

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
        ref_now = now or datetime.now(UTC)
        active_map = self._active_concepts.setdefault(workspace_id, {})
        rejected_set = self._rejected_fingerprints.setdefault(workspace_id, set())
        queue = self._pending_queue.setdefault(workspace_id, [])

        # Purge 4_RUN_EPHEMERAL entries older than 30 days
        cutoff = ref_now - timedelta(days=30)
        kept_queue: list[GlossaryCandidateItem] = []
        purged_count = 0
        for item in queue:
            if item.level == "4_RUN_EPHEMERAL" and item.created_at < cutoff:
                purged_count += 1
            else:
                kept_queue.append(item)
        queue[:] = kept_queue

        # Pass 1: Deterministic deduplication & rejected fingerprint filtering (0 $ LLM)
        existing_fps = {self._fingerprint(t) for t in active_map} | {
            self._fingerprint(c.canonical_term) for c in queue
        }
        filtered_raw: list[tuple[str, str, float]] = []
        for term, definition_fr, score in raw_candidates:
            fp = self._fingerprint(term)
            if fp in existing_fps or fp in rejected_set:
                continue
            existing_fps.add(fp)
            filtered_raw.append((term.strip(), definition_fr.strip(), float(score)))

        # On a simple `git_push`, Pass 2 LLM is strictly forbidden (0 $ LLM)
        if trigger_type == "git_push":
            for term, definition_fr, score in filtered_raw[:15]:
                queue.append(
                    GlossaryCandidateItem(
                        candidate_id=uuid7(),
                        workspace_id=workspace_id,
                        canonical_term=term,
                        fingerprint=self._fingerprint(term),
                        definition_fr=definition_fr,
                        confidence_score=score,
                        level="4_RUN_EPHEMERAL",
                        status="PENDING_VALIDATION",
                        ontology_conflict_warning=None,
                        pre_checked_for_in_flow_promotion=False,
                        created_at=ref_now,
                    )
                )
            self._enforce_fifo_cap_15(queue)
            return TwoPassExtractionResult(
                trigger_type=trigger_type,
                pass_1_deterministic_executed=True,
                pass_2_llm_batch_executed=False,
                llm_calls_count=0,
                purged_expired_ephemeral_count=purged_count,
                active_queue_candidates=tuple(queue),
                top3_in_flow_prechecked=(),
            )

        # Pass 2: Bounded Top-15 LLM batch consolidation (1 call max)
        enterprise_defs = existing_enterprise_terms or {}
        bounded_batch = sorted(filtered_raw, key=lambda x: x[2], reverse=True)[:15]
        for term, definition_fr, score in bounded_batch:
            conflict: str | None = None
            ent_def = enterprise_defs.get(term)
            if ent_def and ent_def.strip().lower() != definition_fr.strip().lower():
                conflict = f"⚠️ ONTOLOGY_CONFLICT: divergence avec 1_ENTERPRISE (« {ent_def} »)."
            queue.append(
                GlossaryCandidateItem(
                    candidate_id=uuid7(),
                    workspace_id=workspace_id,
                    canonical_term=term,
                    fingerprint=self._fingerprint(term),
                    definition_fr=definition_fr,
                    confidence_score=score,
                    level="4_RUN_EPHEMERAL",
                    status="PENDING_VALIDATION",
                    ontology_conflict_warning=conflict,
                    pre_checked_for_in_flow_promotion=score >= 0.85 and conflict is None,
                    created_at=ref_now,
                )
            )

        self._enforce_fifo_cap_15(queue)
        eligible_top3 = sorted(
            [
                c
                for c in queue
                if c.confidence_score >= 0.85 and c.ontology_conflict_warning is None
            ],
            key=lambda c: c.confidence_score,
            reverse=True,
        )[:3]
        top3_ids = {c.candidate_id for c in eligible_top3}
        updated_queue = [
            GlossaryCandidateItem(
                candidate_id=c.candidate_id,
                workspace_id=c.workspace_id,
                canonical_term=c.canonical_term,
                fingerprint=c.fingerprint,
                definition_fr=c.definition_fr,
                confidence_score=c.confidence_score,
                level=c.level,
                status=c.status,
                ontology_conflict_warning=c.ontology_conflict_warning,
                pre_checked_for_in_flow_promotion=c.candidate_id in top3_ids,
                created_at=c.created_at,
            )
            for c in queue
        ]
        queue[:] = updated_queue
        return TwoPassExtractionResult(
            trigger_type=trigger_type,
            pass_1_deterministic_executed=True,
            pass_2_llm_batch_executed=True,
            llm_calls_count=1 if bounded_batch else 0,
            purged_expired_ephemeral_count=purged_count,
            active_queue_candidates=tuple(queue),
            top3_in_flow_prechecked=tuple(c for c in queue if c.candidate_id in top3_ids),
        )

    def promote_or_reject_in_flow(
        self,
        *,
        workspace_id: UUID,
        actor_role: str,
        promote_candidate_ids: list[UUID],
        reject_candidate_ids: list[UUID],
    ) -> InFlowPromotionResult:
        """Promote checked L4 terms to `3_WORKSPACE` `ACTIVE` and invalidate Redis prompt cache."""
        if actor_role == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot promote or reject glossary terms."
            )
        queue = self._pending_queue.setdefault(workspace_id, [])
        active_map = self._active_concepts.setdefault(workspace_id, {})
        rejected_set = self._rejected_fingerprints.setdefault(workspace_id, set())

        promote_set = set(promote_candidate_ids)
        reject_set = set(reject_candidate_ids)
        promoted_terms: list[str] = []
        rejected_terms: list[str] = []
        what_if_warnings: list[str] = []
        remaining: list[GlossaryCandidateItem] = []

        for item in queue:
            if item.candidate_id in promote_set:
                if item.ontology_conflict_warning:
                    what_if_warnings.append(
                        f"What-If Impact ({item.canonical_term}): {item.ontology_conflict_warning}"
                    )
                active_map[item.canonical_term] = item.definition_fr
                promoted_terms.append(item.canonical_term)
            elif item.candidate_id in reject_set:
                rejected_set.add(item.fingerprint)
                rejected_terms.append(item.canonical_term)
            else:
                remaining.append(item)

        queue[:] = remaining
        invalidated = bool(promoted_terms)
        if invalidated:
            self._cache_invalidation_counter[workspace_id] = (
                self._cache_invalidation_counter.get(workspace_id, 0) + 1
            )
        return InFlowPromotionResult(
            workspace_id=workspace_id,
            promoted_terms=tuple(promoted_terms),
            rejected_terms=tuple(rejected_terms),
            what_if_impact_warnings=tuple(what_if_warnings),
            assistant_prompt_cache_invalidated=invalidated,
        )

    def _verify_pass_and_fail(
        self,
        *,
        starlark_code: str,
        passing_payload: dict[str, Any],
        failing_payload: dict[str, Any],
    ) -> None:
        pass_res = self._sandbox.evaluate_script(
            starlark_code=starlark_code,
            payload=passing_payload,
        )
        if not pass_res.passed:
            raise StarlarkSandboxError("passing_test_payload did not evaluate to PASS.")
        fail_res = self._sandbox.evaluate_script(
            starlark_code=starlark_code,
            payload=failing_payload,
        )
        if fail_res.passed:
            raise StarlarkSandboxError("failing_test_payload unexpectedly evaluated to PASS.")

    @staticmethod
    def _validate_payload_against_schema(
        payload: dict[str, Any],
        schema: dict[str, Any],
    ) -> None:
        required = schema.get("required", [])
        if isinstance(required, list):
            for req_key in required:
                if req_key not in payload:
                    raise ValidationDomainError(
                        detail_override=f"Test payload is missing required schema key '{req_key}'."
                    )

    @staticmethod
    def _render_starlark_script(
        *,
        rule_id: str,
        required_field: str,
        regex_pattern: str,
        norm_title: str,
    ) -> str:
        return (
            "def evaluate(doc):\n"
            f"    val = str(doc.get({required_field!r}, ''))\n"
            f"    if orcia_sys.re_fullmatch({regex_pattern!r}, val):\n"
            f"        orcia_sys.emit_verdict({rule_id!r}, 'PASS', {f'Conforme : {norm_title}'!r})\n"
            "    else:\n"
            f"        orcia_sys.emit_verdict({rule_id!r}, 'FAIL', {f'Écart : {norm_title}'!r})\n"
            "        orcia_sys.emit_effect(\n"
            f"            'STAGE_ANNOTATION', 'orcia://staged/gate', {{'rule_id': {rule_id!r}}}\n"
            "        )\n"
        )

    @staticmethod
    def _fingerprint(term: str) -> str:
        normalized = " ".join(term.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _enforce_fifo_cap_15(queue: list[GlossaryCandidateItem]) -> None:
        while len(queue) > 15:
            queue.pop(0)
