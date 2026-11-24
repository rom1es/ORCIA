"""Pure-domain Ontology Context Ranker, Translator & Axiom Selector (`Story 26.5`, `H-12`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from orcia_core.ontology.impact_and_promotion import OntologyGovernanceService
from orcia_core.ontology.models import (
    ONTOLOGY_LEVEL_PRIORITY,
    OntologyAxiomEntity,
    OntologyConceptEntity,
    ResolvedOntologySnapshot,
)
from orcia_core.ontology.resolver import ProfileSemanticTranslator
from orcia_core.ports.embedding import EmbeddingPort

_TOKEN_RE = re.compile(r"[a-z0-9_\u00c0-\u00ff-]{3,}", re.IGNORECASE)
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "what",
        "how",
        "why",
        "who",
        "when",
        "where",
        "which",
        "les",
        "des",
        "une",
        "pour",
        "dans",
        "avec",
        "sur",
        "par",
        "qui",
        "que",
        "quoi",
        "est",
        "sont",
        "aux",
        "du",
        "pas",
        "plus",
        "comment",
    }
)


def _meaningful_tokens(text: str) -> set[str]:
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOPWORDS}


@dataclass(frozen=True, slots=True)
class RankedOntologyConcept:
    """Single ontology concept ranked by relevance and translated for `active_hat`."""

    concept: OntologyConceptEntity
    translated_label: str
    relevance_score: float


@dataclass(frozen=True, slots=True)
class RankedOntologyContext:
    """Ranked Layer 2 ontology concepts and applicable axioms for a user turn."""

    selected_concepts: tuple[RankedOntologyConcept, ...]
    applicable_axioms: tuple[OntologyAxiomEntity, ...]
    snapshot_concept_count: int


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _compute_lexical_score(concept: OntologyConceptEntity, query_text: str) -> float:
    q_lower = query_text.lower().strip()
    if not q_lower:
        return 0.0
    q_tokens = _meaningful_tokens(q_lower)
    score = 0.0

    term_lower = concept.canonical_term.lower()
    if term_lower and term_lower in q_lower:
        score += 3.5
    else:
        term_tokens = _meaningful_tokens(term_lower)
        if term_tokens and q_tokens:
            score += 2.0 * len(term_tokens & q_tokens)

    for syn in concept.synonyms:
        syn_lower = syn.lower()
        if syn_lower and syn_lower in q_lower:
            score += 2.5
        else:
            syn_tokens = _meaningful_tokens(syn_lower)
            if syn_tokens and q_tokens:
                score += 1.25 * len(syn_tokens & q_tokens)

    for banned in concept.banned_terms:
        if banned.lower() in q_lower:
            score += 2.0

    def_tokens = _meaningful_tokens(concept.definition_text)
    if def_tokens and q_tokens:
        score += 0.6 * len(def_tokens & q_tokens)
    return round(score, 6)


def rank_ontology_snapshot_for_query(
    snapshot: ResolvedOntologySnapshot,
    *,
    query_text: str,
    active_hat: str,
    query_embedding: Sequence[float] | None = None,
    concept_embeddings: dict[str, Sequence[float]] | None = None,
    top_k: int = 8,
) -> RankedOntologyContext:
    """Rank active resolved L1-L4 concepts by lexical + optional vector relevance."""
    active_concepts = [
        c for c in snapshot.concepts_by_term.values() if c.snapshot_branch_status == "ACTIVE"
    ]
    if not active_concepts:
        return RankedOntologyContext(
            selected_concepts=(),
            applicable_axioms=(),
            snapshot_concept_count=0,
        )

    scored: list[RankedOntologyConcept] = []
    for concept in active_concepts:
        lex_score = _compute_lexical_score(concept, query_text)
        vec_score = 0.0
        if query_embedding is not None and concept_embeddings is not None:
            c_vec = concept_embeddings.get(concept.concept_key)
            if c_vec is not None:
                vec_score = max(0.0, _cosine_similarity(query_embedding, c_vec))
        total_score = round(lex_score + (3.0 * vec_score if vec_score > 0.25 else 0.0), 6)
        if total_score <= 0.0:
            continue
        translated = ProfileSemanticTranslator.translate_concept(concept, active_hat)
        scored.append(
            RankedOntologyConcept(
                concept=concept,
                translated_label=translated,
                relevance_score=total_score,
            )
        )

    scored.sort(
        key=lambda item: (
            -item.relevance_score,
            -ONTOLOGY_LEVEL_PRIORITY.get(item.concept.level, 0),
            item.concept.canonical_term.lower(),
        )
    )
    selected = tuple(scored[: max(1, top_k)])
    selected_keys = {item.concept.concept_key for item in selected}
    applicable_axioms = tuple(ax for ax in snapshot.axioms if ax.concept_key in selected_keys)
    return RankedOntologyContext(
        selected_concepts=selected,
        applicable_axioms=applicable_axioms,
        snapshot_concept_count=len(active_concepts),
    )


async def rank_ontology_with_optional_embedding_async(
    governance_service: OntologyGovernanceService,
    *,
    workspace_id: str,
    query_text: str,
    active_hat: str,
    embedding_port: EmbeddingPort | None = None,
    enterprise_scope_id: str = "scope-global",
    domain_scope_id: str = "",
    team_chain_scope_ids: tuple[str, ...] = (),
    run_scope_id: str | None = None,
    top_k: int = 8,
) -> RankedOntologyContext:
    """Resolve `workspace_id` ontology snapshot and rank concepts (+ embeddings if active)."""
    snapshot = governance_service.resolve_snapshot(
        enterprise_scope_id=enterprise_scope_id,
        domain_scope_id=domain_scope_id,
        team_chain_scope_ids=team_chain_scope_ids,
        workspace_scope_id=workspace_id,
        run_scope_id=run_scope_id,
    )
    active_concepts = [
        c for c in snapshot.concepts_by_term.values() if c.snapshot_branch_status == "ACTIVE"
    ]
    query_embedding: Sequence[float] | None = None
    concept_embeddings: dict[str, Sequence[float]] | None = None

    if embedding_port is not None and active_concepts and query_text.strip():
        concept_texts = [
            f"{c.canonical_term} {' '.join(c.synonyms)} {c.definition_text}"
            for c in active_concepts
        ]
        all_vecs = await embedding_port.embed([query_text, *concept_texts])
        if len(all_vecs) == 1 + len(active_concepts):
            query_embedding = all_vecs[0]
            concept_embeddings = {
                c.concept_key: vec for c, vec in zip(active_concepts, all_vecs[1:], strict=True)
            }

    return rank_ontology_snapshot_for_query(
        snapshot,
        query_text=query_text,
        active_hat=active_hat,
        query_embedding=query_embedding,
        concept_embeddings=concept_embeddings,
        top_k=top_k,
    )


def format_ranked_ontology_summary(
    ranked: RankedOntologyContext,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], str | None]:
    """Serialize ranked concepts & axioms into prompt dicts and a formatted Layer 2 block."""
    if not ranked.selected_concepts and not ranked.applicable_axioms:
        return (), (), None
    concepts_dicts = tuple(
        {
            "key": rc.concept.concept_key,
            "level": rc.concept.level,
            "canonical_term": rc.concept.canonical_term,
            "definition": rc.translated_label,
            "relevance_score": rc.relevance_score,
        }
        for rc in ranked.selected_concepts
    )
    axioms_dicts = tuple(
        {
            "axiom_key": ax.axiom_key,
            "concept_key": ax.concept_key,
            "immutable": ax.immutable,
            "formal_rule": ax.rule_expression,
        }
        for ax in ranked.applicable_axioms
    )
    lines = [
        f"- [{rc.concept.level}] {rc.concept.canonical_term}: {rc.translated_label}"
        for rc in ranked.selected_concepts
    ]
    for ax in ranked.applicable_axioms:
        lines.append(f"- Axiom [IMMUTABLE={ax.immutable}] {ax.axiom_key}: {ax.rule_expression}")
    return concepts_dicts, axioms_dicts, ("\n".join(lines) if lines else None)


def build_websearch_or_query(user_prompt: str, extra_terms: Sequence[str] = ()) -> str:
    """Build a PostgreSQL `websearch_to_tsquery` OR expression from prompt & ontology terms."""
    combined = " ".join([user_prompt, *extra_terms])
    ordered: list[str] = []
    for tok in _TOKEN_RE.findall(combined.lower()):
        if tok not in _STOPWORDS and tok not in ordered:
            ordered.append(tok)
    if not ordered:
        return user_prompt.strip()
    return " OR ".join(ordered[:16])


__all__ = [
    "RankedOntologyConcept",
    "RankedOntologyContext",
    "build_websearch_or_query",
    "format_ranked_ontology_summary",
    "rank_ontology_snapshot_for_query",
    "rank_ontology_with_optional_embedding_async",
]
