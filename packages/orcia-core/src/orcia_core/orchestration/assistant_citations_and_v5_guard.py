"""Story 10.3 / 26.4b — Deterministic Citations (`[S1]`, `[G1]`, `[O1]`), V5 Guard & Audit.

Zero framework/SDK imports (`fastapi`, `sqlalchemy`, `redis`, `litellm`, `dramatiq`).
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration._assistant_citations_verifier import (
    UNVERIFIED_CITATION_BADGE,
    build_evidence_table_impl,
    verify_and_sanitize_citations_impl,
)
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
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort, FinopsCostLedgerEntry

logger = get_logger("orcia.core.orchestration.citations")


def _parse_optional_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(value.strip()))
    except (ValueError, TypeError, AttributeError):
        return None


class AssistantCitationAndV5GuardService:
    """Domain service for `[S1]/[G1]/[O1]` Evidence Tables, `READ_SOURCE` filtering & V5 Guard."""

    def __init__(self, *, audit_ledger_sink: AuditLedgerSinkPort | None = None) -> None:
        self._audit_ledger_sink: AuditLedgerSinkPort | None = audit_ledger_sink
        # Retained temporarily until Story 26.7 removes `/artifacts/action` (E2E spec 21).
        self._saved_drafts: dict[str, ArtifactCardActionOutcome] = {}

    def set_audit_ledger_sink(self, sink: AuditLedgerSinkPort | None) -> None:
        """Bind or refresh the append-only `AuditLedgerSinkPort` from the Composition Root."""
        self._audit_ledger_sink = sink

    def build_evidence_table(
        self,
        *,
        sources: tuple[RawSourceCandidate, ...],
        glossary_items: tuple[RawGlossaryCandidate, ...] = (),
        tool_outputs: tuple[RawToolOutputCandidate, ...] = (),
    ) -> EvidenceTable:
        """Build numbered Evidence Table where `REFERENCE` strictly outranks `ACTIVE`."""
        return build_evidence_table_impl(
            sources=sources, glossary_items=glossary_items, tool_outputs=tool_outputs
        )

    def filter_citation_map_for_reader(
        self,
        reader: UserIdentity,
        *,
        evidence_table: EvidenceTable,
        reader_allowed_source_uris: frozenset[str],
    ) -> EvidenceTable:
        """Purge `snippet` server-side when `reader` lacks `READ_SOURCE` on `[S1..Sn]` (`AD-21`)."""
        _ = reader
        filtered_sources: list[EvidenceSourceCitation] = []
        for src in evidence_table.sources:
            if src.uri in reader_allowed_source_uris:
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
        return verify_and_sanitize_citations_impl(
            response_text=response_text,
            evidence_table=evidence_table,
            workspace_id=workspace_id,
            user_id=user_id,
        )

    async def verify_and_sanitize_citations_async(
        self,
        *,
        response_text: str,
        evidence_table: EvidenceTable,
        workspace_id: str,
        user_id: str,
        user_email: str | None = None,
        user_display_name: str | None = None,
        turn_id: str | None = None,
        trace_id: str | None = None,
        audit_ledger_sink: AuditLedgerSinkPort | None = None,
    ) -> CitationVerificationResult:
        """Verify citations and record `ASSISTANT_PHANTOM_CITATION_PURGED` in `audit_ledger`."""
        result = self.verify_and_sanitize_citations(
            response_text=response_text,
            evidence_table=evidence_table,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        sink = audit_ledger_sink or self._audit_ledger_sink
        if result.audit_entry is not None and sink is not None:
            seed = (
                turn_id.strip()
                if turn_id and turn_id.strip()
                else result.audit_entry.payload_sha256
            )
            source_event_id = str(
                uuid5(NAMESPACE_URL, f"assistant-phantom-citation:{workspace_id}:{user_id}:{seed}")
            )
            entry = FinopsCostLedgerEntry(
                id=result.audit_entry.audit_id,
                source_event_id=source_event_id,
                workspace_id=_parse_optional_uuid(workspace_id),
                scope_path=f"WORKSPACE/{workspace_id}" if workspace_id else "GLOBAL",
                actor_type="HUMAN",
                actor_id=user_id,
                actor_display_name=user_display_name,
                actor_email=user_email,
                event_type="ASSISTANT_PHANTOM_CITATION_PURGED",
                summary=f"Purged phantom citations: {', '.join(result.stripped_phantom_tags)}",
                trace_id=trace_id or get_current_trace_id(),
                metadata={
                    "stripped_tags": list(result.stripped_phantom_tags),
                    "payload_sha256": result.audit_entry.payload_sha256,
                    "verification_duration_ms": result.verification_duration_ms,
                    "workspace_slug": workspace_id,
                    "turn_id": turn_id,
                },
            )
            try:
                recorded_id = await sink.record_entry(entry)
                persisted_audit = PhantomCitationAuditEntry(
                    audit_id=recorded_id,
                    workspace_id=result.audit_entry.workspace_id,
                    user_id=result.audit_entry.user_id,
                    stripped_tags=result.audit_entry.stripped_tags,
                    verification_duration_ms=result.audit_entry.verification_duration_ms,
                    payload_sha256=result.audit_entry.payload_sha256,
                )
                return CitationVerificationResult(
                    sanitized_text=result.sanitized_text,
                    valid_tags=result.valid_tags,
                    stripped_phantom_tags=result.stripped_phantom_tags,
                    verification_duration_ms=result.verification_duration_ms,
                    audit_entry=persisted_audit,
                    evidence_table=result.evidence_table,
                )
            except Exception as exc:
                logger.warning(
                    "assistant_phantom_citation_audit_persist_failed",
                    workspace_id=workspace_id,
                    error_type=type(exc).__name__,
                )
        return result

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
