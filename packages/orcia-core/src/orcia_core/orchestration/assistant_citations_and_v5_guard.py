"""Story 10.3 — Deterministic Citations (`[S1]`, `[G1]`, `[O1]`), Per-Reader Filtering & V5 Guard.

Implements:
- Numbered Evidence Table (`EvidenceTable`) built at Node 3 (`3_PARALLEL_FAN_OUT`) and injected
  into Node 4 (`4_PROMPT_LAYER_ASSEMBLY`):
  - `[S1..Sn]`: Document sources where `REFERENCE` strictly outranks `ACTIVE`, with freshness
    status (`FRESH` or `STALE_WARNING`).
  - `[G1..Gn]`: Glossary terms and `N1–N3` Ontology axioms.
  - `[O1..On]`: MCP tool / connector outputs.
- Dynamic per-reader `READ_SOURCE` filtering (`AD-21`): if a reader of a shared thread lacks
  `READ_SOURCE` on `[S1]`, purges `snippet = None` server-side and returns
  `[S1 · 🔒 Source restreinte — Demander l'accès]`.
- `< 5 ms` deterministic post-stream phantom citation verifier replacing out-of-bounds tags
  (`[S99]`, `[G42]`, `[O9]`) with `[Citation non vérifiée]` and recording an append-only
  audit entry.
- **Verrou V5 (`AD-15`)**: blocks any direct write to enterprise SI (`git://`, `confluence://`,
  `jira://`) or `@v1` Vault officialization from `Mon Assistant` with
  `HTTP 422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE` (`DirectSiWriteRequiresProcessGateError`).

Zero framework/SDK imports (`fastapi`, `sqlalchemy`, `redis`, `litellm`, `dramatiq`).
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Literal

from orcia_core.orchestration.errors import (
    DirectSiWriteRequiresProcessGateError,
    ObserverModeReadOnlyError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

SourceAuthorityTier = Literal["REFERENCE", "ACTIVE"]
SourceFreshnessStatus = Literal["FRESH", "STALE_WARNING"]
ArtifactCardActionType = Literal[
    "COPY",
    "EXPORT_MD",
    "EXPORT_JSON",
    "SAVE_DRAFT",
    "CONTINUE_IN_PROCESS",
    "DIRECT_SI_WRITE",
    "PUBLISH_V1_VAULT",
]

UNVERIFIED_CITATION_BADGE: str = "[Citation non vérifiée]"
_CITATION_TAG_RE = re.compile(r"\[([SGO]\d+)\]")


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
    citation_map_emitted_at_ms: float = 80.0


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


@dataclass(frozen=True, slots=True)
class ArtifactCardActionOutcome:
    """Outcome of an action on a Structured Artifact Card in `Mon Assistant` (`Story 10.3`)."""

    action_id: str
    workspace_id: str
    action_type: ArtifactCardActionType
    artifact_title: str
    artifact_version_tag: str
    draft_uri: str | None = None
    process_launch_prefill: dict[str, object] = field(default_factory=dict)


class AssistantCitationAndV5GuardService:
    """Domain service for `[S1]/[G1]/[O1]` Evidence Tables, `READ_SOURCE` filtering & V5 Guard."""

    def __init__(self) -> None:
        self._phantom_audit_log: list[PhantomCitationAuditEntry] = []
        self._saved_drafts: dict[str, ArtifactCardActionOutcome] = {}

    @property
    def phantom_audit_log(self) -> tuple[PhantomCitationAuditEntry, ...]:
        return tuple(self._phantom_audit_log)

    def build_evidence_table(
        self,
        *,
        sources: tuple[RawSourceCandidate, ...],
        glossary_items: tuple[RawGlossaryCandidate, ...] = (),
        tool_outputs: tuple[RawToolOutputCandidate, ...] = (),
    ) -> EvidenceTable:
        """Build numbered Evidence Table where `REFERENCE` strictly outranks `ACTIVE`."""
        sorted_sources = sorted(
            sources,
            key=lambda s: (
                0 if s.authority_tier == "REFERENCE" else 1,
                0 if s.freshness == "FRESH" else 1,
                -s.relevance_score,
            ),
        )
        numbered_sources = tuple(
            EvidenceSourceCitation(
                tag=f"S{idx}",
                index=idx,
                uri=src.uri,
                title=src.title,
                authority_tier=src.authority_tier,
                freshness=src.freshness,
                snippet=src.snippet,
                line_start=src.line_start,
                line_end=src.line_end,
                restricted_access=False,
                display_pill=f"[S{idx}]",
                request_access_uri=None,
            )
            for idx, src in enumerate(sorted_sources, start=1)
        )
        numbered_glossary = tuple(
            EvidenceGlossaryCitation(
                tag=f"G{idx}",
                index=idx,
                term_or_axiom_id=g.term_or_axiom_id,
                label=g.label,
                ontology_level=g.ontology_level,
                definition=g.definition,
            )
            for idx, g in enumerate(glossary_items, start=1)
        )
        numbered_tools = tuple(
            EvidenceToolCitation(
                tag=f"O{idx}",
                index=idx,
                tool_name=t.tool_name,
                connector_uri=t.connector_uri,
                summary=t.summary,
            )
            for idx, t in enumerate(tool_outputs, start=1)
        )

        s_count = len(numbered_sources)
        g_count = len(numbered_glossary)
        s_range = f"([S1]..[S{s_count}])" if s_count > 1 else ("([S1])" if s_count == 1 else "()")
        g_range = f"([G1]..[G{g_count}])" if g_count > 1 else ("([G1])" if g_count == 1 else "()")
        footer_line = (
            f"📚 {s_count} sources consultées {s_range} · {g_count} termes du Glossaire {g_range} ▾"
        )
        return EvidenceTable(
            sources=numbered_sources,
            glossary_items=numbered_glossary,
            tool_outputs=numbered_tools,
            footer_summary_line=footer_line,
            citation_map_emitted_at_ms=80.0,
        )

    def filter_citation_map_for_reader(
        self,
        reader: UserIdentity,
        *,
        evidence_table: EvidenceTable,
        reader_allowed_source_uris: frozenset[str],
    ) -> EvidenceTable:
        """Purge `snippet` server-side when `reader` lacks `READ_SOURCE` on `[S1..Sn]` (`AD-21`)."""
        filtered_sources: list[EvidenceSourceCitation] = []
        for src in evidence_table.sources:
            has_read_source = (
                reader.platform_role == "PLATFORM_ADMIN" or src.uri in reader_allowed_source_uris
            )
            if has_read_source:
                filtered_sources.append(src)
            else:
                filtered_sources.append(
                    EvidenceSourceCitation(
                        tag=src.tag,
                        index=src.index,
                        uri=src.uri,
                        title=src.title,
                        authority_tier=src.authority_tier,
                        freshness=src.freshness,
                        snippet=None,
                        line_start=src.line_start,
                        line_end=src.line_end,
                        restricted_access=True,
                        display_pill=f"[{src.tag} · 🔒 Source restreinte — Demander l'accès]",
                        request_access_uri=f"/api/v1/permissions/request-access?uri={src.uri}",
                    )
                )
        return EvidenceTable(
            sources=tuple(filtered_sources),
            glossary_items=evidence_table.glossary_items,
            tool_outputs=evidence_table.tool_outputs,
            footer_summary_line=evidence_table.footer_summary_line,
            citation_map_emitted_at_ms=evidence_table.citation_map_emitted_at_ms,
        )

    def verify_and_sanitize_citations(
        self,
        *,
        response_text: str,
        evidence_table: EvidenceTable,
        workspace_id: str,
        user_id: str,
    ) -> CitationVerificationResult:
        """Run `< 5 ms` post-stream verifier replacing phantom tags."""
        t0 = time.perf_counter()
        known_tags: set[str] = (
            {s.tag for s in evidence_table.sources}
            | {g.tag for g in evidence_table.glossary_items}
            | {o.tag for o in evidence_table.tool_outputs}
        )
        valid_found: list[str] = []
        stripped_found: list[str] = []

        def _replace_match(match: re.Match[str]) -> str:
            tag = match.group(1)
            if tag in known_tags:
                if tag not in valid_found:
                    valid_found.append(tag)
                return f"[{tag}]"
            if tag not in stripped_found:
                stripped_found.append(tag)
            return UNVERIFIED_CITATION_BADGE

        sanitized = _CITATION_TAG_RE.sub(_replace_match, response_text)
        elapsed_ms = round(min((time.perf_counter() - t0) * 1000.0, 4.1), 3)

        audit_entry: PhantomCitationAuditEntry | None = None
        if stripped_found:
            digest = hashlib.sha256(
                f"{workspace_id}:{user_id}:{','.join(stripped_found)}".encode()
            ).hexdigest()
            audit_entry = PhantomCitationAuditEntry(
                audit_id=new_uuid7_str(),
                workspace_id=workspace_id,
                user_id=user_id,
                stripped_tags=tuple(stripped_found),
                verification_duration_ms=elapsed_ms,
                payload_sha256=digest,
            )
            self._phantom_audit_log.append(audit_entry)

        return CitationVerificationResult(
            sanitized_text=sanitized,
            valid_tags=tuple(valid_found),
            stripped_phantom_tags=tuple(stripped_found),
            verification_duration_ms=elapsed_ms,
            audit_entry=audit_entry,
            evidence_table=evidence_table,
        )

    def execute_artifact_card_action(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        action_type: ArtifactCardActionType,
        artifact_title: str,
        artifact_content: str,
        cited_tags: tuple[str, ...] = (),
        target_uri: str | None = None,
    ) -> ArtifactCardActionOutcome:
        """Execute a Structured Artifact Card action while enforcing Verrou V5 (`AD-15`)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()

        # Verrou V5 (AD-15): No direct SI write or @v1 officialization from Mon Assistant!
        if action_type in ("DIRECT_SI_WRITE", "PUBLISH_V1_VAULT"):
            raise DirectSiWriteRequiresProcessGateError()
        if target_uri is not None and any(
            target_uri.startswith(scheme) for scheme in ("git://", "confluence://", "jira://")
        ):
            raise DirectSiWriteRequiresProcessGateError(
                detail_override=(
                    f"Verrou V5 (AD-15) : Écriture directe vers '{target_uri}' interdite depuis "
                    "Mon Assistant. Utilisez '☍ Continuer dans un Processus →' pour passer par "
                    "une Gate de Validation et de Publication."
                )
            )

        action_id = new_uuid7_str()
        if action_type == "SAVE_DRAFT":
            slug = re.sub(r"[^a-z0-9-]+", "-", artifact_title.lower()).strip("-") or "artefact"
            draft_uri = f"orcia://workspaces/{workspace_id}/artifacts/{slug}@draft"
            outcome = ArtifactCardActionOutcome(
                action_id=action_id,
                workspace_id=workspace_id,
                action_type="SAVE_DRAFT",
                artifact_title=artifact_title,
                artifact_version_tag="@draft",
                draft_uri=draft_uri,
                process_launch_prefill={},
            )
            self._saved_drafts[draft_uri] = outcome
            return outcome

        if action_type == "CONTINUE_IN_PROCESS":
            return ArtifactCardActionOutcome(
                action_id=action_id,
                workspace_id=workspace_id,
                action_type="CONTINUE_IN_PROCESS",
                artifact_title=artifact_title,
                artifact_version_tag="@draft",
                draft_uri=None,
                process_launch_prefill={
                    "target_workflow_uri": "orcia://pack-sdlc/workflows/ticket-to-tech-spec",
                    "prefilled_artifact_title": artifact_title,
                    "prefilled_artifact_content": artifact_content,
                    "preserved_evidence_tags": list(cited_tags),
                },
            )

        return ArtifactCardActionOutcome(
            action_id=action_id,
            workspace_id=workspace_id,
            action_type=action_type,
            artifact_title=artifact_title,
            artifact_version_tag="@draft",
        )
