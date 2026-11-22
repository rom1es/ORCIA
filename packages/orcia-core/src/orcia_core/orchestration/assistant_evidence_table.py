"""Deterministic Server-Side `EvidenceTable` Builder for Assistant Layer 4 (`Story 26.5`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orcia_core.ontology.context_ranker import RankedOntologyConcept
from orcia_core.ontology.models import OntologyAxiomEntity
from orcia_core.orchestration._assistant_citations_verifier import build_evidence_table_impl
from orcia_core.orchestration.assistant_citations_models import (
    EvidenceGlossaryCitation,
    EvidenceSourceCitation,
    EvidenceTable,
    RawGlossaryCandidate,
    RawSourceCandidate,
    SourceAuthorityTier,
    SourceFreshnessStatus,
)
from orcia_core.orchestration.assistant_profile_adaptation import sanitize_layer_marker_tags
from orcia_core.rag.models import HybridRagHit
from orcia_kernel.context_ports import ContextSliceRecord, VectorSearchHitRecord


@dataclass(frozen=True, slots=True)
class ServerEvidenceBuildResult:
    """Server-verified `EvidenceTable` plus sanitized Layer 4 prompt context."""

    evidence_table: EvidenceTable
    layer4_markdown: str
    authorized_uris: frozenset[str]
    masked_count: int


def _is_confidential_uri_or_payload(uri: str, payload: dict[str, object] | None = None) -> bool:
    vis = str((payload or {}).get("visibility_mode") or "").strip().upper()
    return (
        vis == "CONFIDENTIAL_RESTRICTED"
        or uri.startswith("confidential://")
        or "secret-vault" in uri
    )


def _infer_authority_tier(
    uri: str,
    source_kind: str | None = None,
    *,
    datasource_role: str | None = None,
    payload: dict[str, object] | None = None,
) -> SourceAuthorityTier:
    explicit = (
        str(
            (payload or {}).get("authority_tier")
            or (payload or {}).get("datasource_role")
            or (payload or {}).get("role")
            or datasource_role
            or ""
        )
        .strip()
        .upper()
    )
    if explicit == "REFERENCE":
        return "REFERENCE"
    if explicit == "ACTIVE":
        return "ACTIVE"
    lower = uri.lower()
    if source_kind in (
        "BLACKBOARD_SNAPSHOT",
        "CATALOG_ITEM",
        "PERMISSION_POLICY",
    ) or lower.startswith(("orcia://blackboard/", "orcia://catalog/")):
        return "REFERENCE"
    return "ACTIVE"


def _resolve_rag_candidate(
    hit: HybridRagHit | VectorSearchHitRecord,
) -> tuple[RawSourceCandidate, bool]:
    if isinstance(hit, HybridRagHit):
        title = f"{hit.document_key} ({hit.revision_tag})"
        snippet = sanitize_layer_marker_tags(hit.injected_content)
        score = float(hit.rrf_score)
        ds_role: str | None = hit.datasource_role
    else:
        title = hit.document_key or hit.chunk_key
        snippet = sanitize_layer_marker_tags(hit.injected_content)
        score = float(hit.rrf_score)
        ds_role = None
    freshness: SourceFreshnessStatus = "STALE_WARNING" if hit.is_stale else "FRESH"
    if hit.is_stale and "[STALE_WARNING" not in snippet:
        marker = hit.stale_warning_marker or "[STALE_WARNING]"
        snippet = f"{marker} {snippet}".strip()
    candidate = RawSourceCandidate(
        uri=hit.source_uri,
        title=title,
        authority_tier=_infer_authority_tier(hit.source_uri, datasource_role=ds_role),
        freshness=freshness,
        snippet=snippet[:400],
        relevance_score=score,
    )
    is_conf = _is_confidential_uri_or_payload(hit.source_uri)
    return candidate, is_conf


def _resolve_slice_candidate(slice_rec: ContextSliceRecord) -> tuple[RawSourceCandidate, bool]:
    freshness: SourceFreshnessStatus = "STALE_WARNING" if slice_rec.is_stale else "FRESH"
    snippet = sanitize_layer_marker_tags(slice_rec.text_excerpt)
    if slice_rec.is_stale and "[STALE_WARNING" not in snippet:
        marker = slice_rec.stale_warning_marker or "[STALE_WARNING]"
        snippet = f"{marker} {snippet}".strip()
    is_conf = _is_confidential_uri_or_payload(slice_rec.source_uri, slice_rec.structured_payload)
    score = 0.95 if slice_rec.source_kind == "BLACKBOARD_SNAPSHOT" else 0.75
    candidate = RawSourceCandidate(
        uri=slice_rec.source_uri,
        title=slice_rec.title,
        authority_tier=_infer_authority_tier(
            slice_rec.source_uri,
            slice_rec.source_kind,
            payload=slice_rec.structured_payload,
        ),
        freshness=freshness,
        snippet=snippet[:400],
        relevance_score=score,
    )
    return candidate, is_conf


def _to_glossary_candidates(
    concepts: Sequence[RankedOntologyConcept],
    axioms: Sequence[OntologyAxiomEntity],
) -> tuple[RawGlossaryCandidate, ...]:
    items: list[RawGlossaryCandidate] = []
    for rc in concepts:
        lvl = rc.concept.level
        mapped_lvl: str = (
            "N1_DIRECTIVE"
            if lvl == "1_ENTERPRISE"
            else "N2_NORME"
            if lvl == "2_DOMAIN"
            else "N3_MECANISME"
            if lvl in ("3_TEAM", "3_WORKSPACE", "4_WORKSPACE")
            else "L4_GLOSSARY"
        )
        items.append(
            RawGlossaryCandidate(
                term_or_axiom_id=rc.concept.concept_key,
                label=rc.concept.canonical_term,
                ontology_level=mapped_lvl,  # type: ignore[arg-type]
                definition=rc.translated_label,
            )
        )
    for ax in axioms:
        items.append(
            RawGlossaryCandidate(
                term_or_axiom_id=ax.axiom_key,
                label=ax.axiom_key,
                ontology_level="N1_DIRECTIVE" if ax.immutable else "N3_MECANISME",
                definition=ax.rule_expression,
            )
        )
    return tuple(items)


def build_server_evidence_table_for_turn(
    *,
    rag_hits: Sequence[HybridRagHit | VectorSearchHitRecord] = (),
    context_slices: Sequence[ContextSliceRecord] = (),
    ontology_concepts: Sequence[RankedOntologyConcept] = (),
    ontology_axioms: Sequence[OntologyAxiomEntity] = (),
    allowed_source_uris: frozenset[str] | None = None,
    locale: str = "fr",
    max_sources: int = 12,
) -> ServerEvidenceBuildResult:
    """Merge RAG, Blackboard & catalog evidence, enforce `READ_SOURCE` & build Layer 4."""
    deduped: dict[str, RawSourceCandidate] = {}
    masked_count = 0

    def _accept(candidate: RawSourceCandidate, is_conf: bool) -> None:
        nonlocal masked_count
        if not candidate.uri:
            return
        if is_conf and (allowed_source_uris is None or candidate.uri not in allowed_source_uris):
            masked_count += 1
            return
        if allowed_source_uris is not None and candidate.uri not in allowed_source_uris:
            masked_count += 1
            return
        existing = deduped.get(candidate.uri)
        if existing is None or candidate.relevance_score > existing.relevance_score:
            deduped[candidate.uri] = candidate

    for hit in rag_hits:
        cand, is_conf = _resolve_rag_candidate(hit)
        _accept(cand, is_conf)

    for sl in context_slices:
        cand, is_conf = _resolve_slice_candidate(sl)
        _accept(cand, is_conf)

    glossary_candidates = _to_glossary_candidates(ontology_concepts, ontology_axioms)
    table = build_evidence_table_impl(
        sources=tuple(deduped.values())[:max_sources],
        glossary_items=glossary_candidates,
        tool_outputs=(),
    )
    layer4_md = format_evidence_table_for_layer_4(table, locale=locale)
    authorized_uris = frozenset(s.uri for s in table.sources if not s.restricted_access)
    return ServerEvidenceBuildResult(
        evidence_table=table,
        layer4_markdown=layer4_md,
        authorized_uris=authorized_uris,
        masked_count=masked_count,
    )


def format_evidence_table_for_layer_4(table: EvidenceTable, *, locale: str = "fr") -> str:
    """Format verified `EvidenceTable` entries into deterministic Layer 4 prompt context."""
    if not table.sources and not table.glossary_items:
        return ""
    is_en = (locale or "fr").strip().lower().startswith("en")
    lines: list[str] = [
        "[SERVER_EVIDENCE_TABLE_LAYER_4]" if is_en else "[TABLE_PREUVES_SERVEUR_COUCHE_4]"
    ]
    for src in table.sources:
        if src.restricted_access or src.snippet is None:
            continue
        stale_badge = " [STALE_WARNING]" if src.freshness == "STALE_WARNING" else ""
        lines.append(
            f"- [{src.tag}] ({src.authority_tier}/{src.freshness}){stale_badge} "
            f"{src.uri} — {src.title}: {src.snippet}"
        )
    for g in table.glossary_items:
        lines.append(f"- [{g.tag}] ({g.ontology_level}) {g.label}: {g.definition}")
    return "\n".join(lines) if len(lines) > 1 else ""


def evidence_table_to_citation_map_dict(table: EvidenceTable) -> dict[str, object]:
    """Serialize `EvidenceTable` for `assistant_thread_messages.citation_map` JSONB."""
    return {
        "sources": [
            {
                "tag": s.tag,
                "index": s.index,
                "uri": s.uri,
                "title": s.title,
                "authority_tier": s.authority_tier,
                "freshness": s.freshness,
                "restricted_access": s.restricted_access,
            }
            for s in table.sources
        ],
        "glossary_items": [
            {
                "tag": g.tag,
                "index": g.index,
                "term_or_axiom_id": g.term_or_axiom_id,
                "label": g.label,
                "ontology_level": g.ontology_level,
            }
            for g in table.glossary_items
        ],
        "footer_summary_line": table.footer_summary_line,
    }


__all__ = [
    "EvidenceGlossaryCitation",
    "EvidenceSourceCitation",
    "EvidenceTable",
    "ServerEvidenceBuildResult",
    "build_server_evidence_table_for_turn",
    "evidence_table_to_citation_map_dict",
    "format_evidence_table_for_layer_4",
]
