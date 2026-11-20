"""2-Pass Glossary Extraction & In-Flow Promotion operations (`Story 11.2`, `Verrou V4`)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from uuid_utils.compat import uuid7

from orcia_core.orchestration._dna_starlark_models import (
    ExtractionTriggerType,
    GlossaryCandidateItem,
    InFlowPromotionResult,
    TwoPassExtractionResult,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError


def term_fingerprint(term: str) -> str:
    """Compute canonical normalized SHA-256 fingerprint prefix for deduplication."""
    normalized = " ".join(term.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def enforce_fifo_cap_15(queue: list[GlossaryCandidateItem]) -> None:
    """Enforce FIFO queue maximum size of 15 pending candidates (`Verrou V4`)."""
    while len(queue) > 15:
        queue.pop(0)


def execute_two_pass_glossary_extraction(
    *,
    workspace_id: UUID,
    trigger_type: ExtractionTriggerType,
    raw_candidates: list[tuple[str, str, float]],
    active_map: dict[str, str],
    rejected_set: set[str],
    queue: list[GlossaryCandidateItem],
    existing_enterprise_terms: dict[str, str] | None = None,
    now: datetime | None = None,
) -> TwoPassExtractionResult:
    """Execute 2-Pass `OntologyExtractor` (`0 $` on `git_push`, FIFO `<= 15` & `Top-3` `V4`)."""
    ref_now = now or datetime.now(UTC)

    cutoff = ref_now - timedelta(days=30)
    kept_queue: list[GlossaryCandidateItem] = []
    purged_count = 0
    for item in queue:
        if item.level == "4_RUN_EPHEMERAL" and item.created_at < cutoff:
            purged_count += 1
        else:
            kept_queue.append(item)
    queue[:] = kept_queue

    existing_fps = {term_fingerprint(t) for t in active_map} | {
        term_fingerprint(c.canonical_term) for c in queue
    }
    filtered_raw: list[tuple[str, str, float]] = []
    for term, definition_fr, score in raw_candidates:
        fp = term_fingerprint(term)
        if fp in existing_fps or fp in rejected_set:
            continue
        existing_fps.add(fp)
        filtered_raw.append((term.strip(), definition_fr.strip(), float(score)))

    if trigger_type == "git_push":
        for term, definition_fr, score in filtered_raw[:15]:
            queue.append(
                GlossaryCandidateItem(
                    candidate_id=uuid7(),
                    workspace_id=workspace_id,
                    canonical_term=term,
                    fingerprint=term_fingerprint(term),
                    definition_fr=definition_fr,
                    confidence_score=score,
                    level="4_RUN_EPHEMERAL",
                    status="PENDING_VALIDATION",
                    ontology_conflict_warning=None,
                    pre_checked_for_in_flow_promotion=False,
                    created_at=ref_now,
                )
            )
        enforce_fifo_cap_15(queue)
        return TwoPassExtractionResult(
            trigger_type=trigger_type,
            pass_1_deterministic_executed=True,
            pass_2_llm_batch_executed=False,
            llm_calls_count=0,
            purged_expired_ephemeral_count=purged_count,
            active_queue_candidates=tuple(queue),
            top3_in_flow_prechecked=(),
        )

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
                fingerprint=term_fingerprint(term),
                definition_fr=definition_fr,
                confidence_score=score,
                level="4_RUN_EPHEMERAL",
                status="PENDING_VALIDATION",
                ontology_conflict_warning=conflict,
                pre_checked_for_in_flow_promotion=score >= 0.85 and conflict is None,
                created_at=ref_now,
            )
        )

    enforce_fifo_cap_15(queue)
    eligible_top3 = sorted(
        [c for c in queue if c.confidence_score >= 0.85 and c.ontology_conflict_warning is None],
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


def execute_promote_or_reject_in_flow(
    *,
    workspace_id: UUID,
    actor_role: str,
    promote_candidate_ids: list[UUID],
    reject_candidate_ids: list[UUID],
    queue: list[GlossaryCandidateItem],
    active_map: dict[str, str],
    rejected_set: set[str],
    cache_invalidation_counter: dict[UUID, int],
) -> InFlowPromotionResult:
    """Promote checked L4 terms to `3_WORKSPACE` `ACTIVE` and invalidate prompt cache."""
    if actor_role == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(
            detail_override="READ_ONLY_OBSERVER cannot promote or reject glossary terms."
        )

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
        cache_invalidation_counter[workspace_id] = (
            cache_invalidation_counter.get(workspace_id, 0) + 1
        )
    return InFlowPromotionResult(
        workspace_id=workspace_id,
        promoted_terms=tuple(promoted_terms),
        rejected_terms=tuple(rejected_terms),
        what_if_impact_warnings=tuple(what_if_warnings),
        assistant_prompt_cache_invalidated=invalidated,
    )
