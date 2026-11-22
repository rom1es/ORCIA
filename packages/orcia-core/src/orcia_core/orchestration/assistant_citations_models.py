"""Domain Models for Citations (`[S1]`, `[G1]`, `[O1]`) & V5 Artifact Guard (`Story 10.3`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceAuthorityTier = Literal["REFERENCE", "ACTIVE"]
SourceFreshnessStatus = Literal["FRESH", "STALE_WARNING"]


@dataclass(frozen=True, slots=True)
class RawSourceCandidate:
    """Candidate document source retrieved at Node 3 (`3_PARALLEL_FAN_OUT`)."""

    uri: str
    title: str
    authority_tier: SourceAuthorityTier
    freshness: SourceFreshnessStatus
    snippet: str
    line_start: int = 1
    line_end: int = 25
    relevance_score: float = 0.9


@dataclass(frozen=True, slots=True)
class RawGlossaryCandidate:
    """Candidate Glossary term or `N1–N3` Ontology axiom retrieved at Node 3."""

    term_or_axiom_id: str
    label: str
    ontology_level: Literal["N1_DIRECTIVE", "N2_NORME", "N3_MECANISME", "L4_GLOSSARY"]
    definition: str


@dataclass(frozen=True, slots=True)
class RawToolOutputCandidate:
    """Candidate MCP tool or governed connector output retrieved at Node 3."""

    tool_name: str
    connector_uri: str
    summary: str


@dataclass(frozen=True, slots=True)
class EvidenceSourceCitation:
    """Numbered `[S1..Sn]` source entry in the Evidence Table (`Story 10.3`)."""

    tag: str
    index: int
    uri: str
    title: str
    authority_tier: SourceAuthorityTier
    freshness: SourceFreshnessStatus
    snippet: str | None
    line_start: int
    line_end: int
    restricted_access: bool = False
    display_pill: str = ""
    request_access_uri: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceGlossaryCitation:
    """Numbered `[G1..Gn]` Glossary / Ontology axiom entry in the Evidence Table."""

    tag: str
    index: int
    term_or_axiom_id: str
    label: str
    ontology_level: Literal["N1_DIRECTIVE", "N2_NORME", "N3_MECANISME", "L4_GLOSSARY"]
    definition: str


@dataclass(frozen=True, slots=True)
class EvidenceToolCitation:
    """Numbered `[O1..On]` MCP tool / connector entry in the Evidence Table."""

    tag: str
    index: int
    tool_name: str
    connector_uri: str
    summary: str


@dataclass(frozen=True, slots=True)
class EvidenceTable:
    """Complete numbered Evidence Table (`[S1..Sn]`, `[G1..Gn]`, `[O1..On]`) (`Story 10.3`)."""

    sources: tuple[EvidenceSourceCitation, ...]
    glossary_items: tuple[EvidenceGlossaryCitation, ...]
    tool_outputs: tuple[EvidenceToolCitation, ...]
    footer_summary_line: str
    citation_map_emitted_at_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class PhantomCitationAuditEntry:
    """Append-only audit record emitted when an out-of-bounds citation tag is stripped."""

    audit_id: str
    workspace_id: str
    user_id: str
    stripped_tags: tuple[str, ...]
    verification_duration_ms: float
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class CitationVerificationResult:
    """Result of `< 5 ms` post-stream citation verification (`Story 10.3`)."""

    sanitized_text: str
    valid_tags: tuple[str, ...]
    stripped_phantom_tags: tuple[str, ...]
    verification_duration_ms: float
    audit_entry: PhantomCitationAuditEntry | None
    evidence_table: EvidenceTable
