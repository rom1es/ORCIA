"""Story 10.3 — Deterministic Citations (`[S1]`, `[G1]`, `[O1]`), Per-Reader Filtering & V5 Guard.

Zero framework/SDK imports (`fastapi`, `sqlalchemy`, `redis`, `litellm`, `dramatiq`).
"""

from __future__ import annotations

import hashlib
import re
import time

from orcia_core.orchestration.assistant_citations_models import (
    ArtifactCardActionOutcome,
    ArtifactCardActionType,
    CitationVerificationResult,
    EvidenceGlossaryCitation,
    EvidenceSourceCitation,
    EvidenceTable,
    EvidenceToolCitation,
    PhantomCitationAuditEntry,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
    SourceAuthorityTier,
    SourceFreshnessStatus,
    build_artifact_card_outcome,
)
from orcia_core.orchestration.errors import (
    DirectSiWriteRequiresProcessGateError,
    ObserverModeReadOnlyError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

UNVERIFIED_CITATION_BADGE: str = "[Citation non vérifiée]"
_CITATION_TAG_RE = re.compile(r"\[([SGO]\d+)\]")


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
        t0 = time.perf_counter()
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
            citation_map_emitted_at_ms=round((time.perf_counter() - t0) * 1000.0, 3),
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
            has_read_source = src.uri in reader_allowed_source_uris
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
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

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
        target_workflow_uri: str | None = None,
    ) -> ArtifactCardActionOutcome:
        """Execute a Structured Artifact Card action while enforcing Verrou V5 (`AD-15`)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()

        # Verrou V5 (AD-15): No direct SI write or @v1 officialization from Mon Assistant!
        if action_type in ("DIRECT_SI_WRITE", "PUBLISH_V1_VAULT"):
            raise DirectSiWriteRequiresProcessGateError()
        if (
            target_uri is not None
            and "://" in target_uri
            and not target_uri.startswith(("orcia://", "local://"))
        ):
            raise DirectSiWriteRequiresProcessGateError(
                detail_override=(
                    f"Verrou V5 (AD-15) : Écriture directe vers '{target_uri}' interdite depuis "
                    "Mon Assistant. Utilisez '☍ Continuer dans un Processus →' pour passer par "
                    "une Gate de Validation et de Publication."
                )
            )

        outcome = build_artifact_card_outcome(
            workspace_id=workspace_id,
            action_type=action_type,
            artifact_title=artifact_title,
            artifact_content=artifact_content,
            cited_tags=cited_tags,
            target_workflow_uri=target_workflow_uri,
        )
        if action_type == "SAVE_DRAFT" and outcome.draft_uri is not None:
            self._saved_drafts[outcome.draft_uri] = outcome
        return outcome


__all__ = [
    "UNVERIFIED_CITATION_BADGE",
    "ArtifactCardActionOutcome",
    "ArtifactCardActionType",
    "AssistantCitationAndV5GuardService",
    "CitationVerificationResult",
    "EvidenceGlossaryCitation",
    "EvidenceSourceCitation",
    "EvidenceTable",
    "EvidenceToolCitation",
    "PhantomCitationAuditEntry",
    "RawGlossaryCandidate",
    "RawSourceCandidate",
    "RawToolOutputCandidate",
    "SourceAuthorityTier",
    "SourceFreshnessStatus",
]
