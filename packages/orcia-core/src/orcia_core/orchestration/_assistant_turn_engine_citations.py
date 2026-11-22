"""Server Citation Verification, EvidenceTable Merge & SSE `citation_map` Builders (`AD-25`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.assistant_citations_models import (
    CitationVerificationResult,
    EvidenceTable,
    EvidenceToolCitation,
    RawToolOutputCandidate,
)
from orcia_core.orchestration.assistant_evidence_table import (
    evidence_table_to_citation_map_dict,
)


def is_low_evidence_table(table: EvidenceTable) -> bool:
    """Return True deterministically when server `EvidenceTable` contains zero evidence entries."""
    return (
        len(table.sources) == 0 and len(table.glossary_items) == 0 and len(table.tool_outputs) == 0
    )


def merge_tool_outputs_into_evidence_table(
    citation_guard: AssistantCitationAndV5GuardService,
    *,
    base_table: EvidenceTable | None,
    tool_outputs: Sequence[RawToolOutputCandidate] = (),
) -> EvidenceTable:
    """Append N3 tool outputs (`[O1..On]`) without altering `[Sn]`/`[Gn]` or masked entries."""
    if base_table is None:
        return citation_guard.build_evidence_table(
            sources=(), glossary_items=(), tool_outputs=tuple(tool_outputs)
        )
    if not tool_outputs:
        return base_table

    start_idx = len(base_table.tool_outputs) + 1
    appended_tools = tuple(
        EvidenceToolCitation(
            tag=f"O{idx}",
            index=idx,
            tool_name=t.tool_name,
            connector_uri=t.connector_uri,
            summary=t.summary,
        )
        for idx, t in enumerate(tool_outputs, start=start_idx)
    )
    return EvidenceTable(
        sources=base_table.sources,
        glossary_items=base_table.glossary_items,
        tool_outputs=(*base_table.tool_outputs, *appended_tools),
        footer_summary_line=base_table.footer_summary_line,
        citation_map_emitted_at_ms=base_table.citation_map_emitted_at_ms,
    )


def build_citation_map_sse_payload(
    verification: CitationVerificationResult,
    *,
    turn_id: str,
    trace_id: str,
) -> dict[str, Any]:
    """Build canonical SSE v2 `citation_map` payload from server `CitationVerificationResult`."""
    table = verification.evidence_table
    citations_index: dict[str, dict[str, Any]] = {}
    for src in table.sources:
        citations_index[src.tag] = {
            "label": src.title,
            "source_uri": src.uri,
            "authority_tier": src.authority_tier,
            "freshness": src.freshness,
            "stale_warning": src.freshness == "STALE_WARNING",
            "excerpt_verified": not src.restricted_access and bool(src.snippet),
            "restricted_access": src.restricted_access,
            "display_pill": src.display_pill,
            "request_access_uri": src.request_access_uri,
        }
    for glossary in table.glossary_items:
        citations_index[glossary.tag] = {
            "label": glossary.label,
            "source_uri": f"ontology://{glossary.ontology_level}/{glossary.term_or_axiom_id}",
            "authority_tier": "REFERENCE",
            "freshness": "FRESH",
            "stale_warning": False,
            "excerpt_verified": True,
            "ontology_level": glossary.ontology_level,
            "definition": glossary.definition,
        }
    for tool_out in table.tool_outputs:
        citations_index[tool_out.tag] = {
            "label": tool_out.tool_name,
            "source_uri": tool_out.connector_uri,
            "authority_tier": "ACTIVE",
            "freshness": "FRESH",
            "stale_warning": False,
            "excerpt_verified": True,
            "summary": tool_out.summary,
        }

    base_map = evidence_table_to_citation_map_dict(table)
    base_map["tool_outputs"] = [
        {
            "tag": t.tag,
            "index": t.index,
            "tool_name": t.tool_name,
            "connector_uri": t.connector_uri,
            "summary": t.summary,
        }
        for t in table.tool_outputs
    ]
    base_map["valid_tags"] = list(verification.valid_tags)
    base_map["stripped_phantom_tags"] = list(verification.stripped_phantom_tags)
    return {
        "turn_id": turn_id,
        "trace_id": trace_id,
        "citations": citations_index,
        "purged_phantom_count": len(verification.stripped_phantom_tags),
        "valid_tags": list(verification.valid_tags),
        "stripped_phantom_tags": list(verification.stripped_phantom_tags),
        "verification_duration_ms": verification.verification_duration_ms,
        "audit_id": verification.audit_entry.audit_id if verification.audit_entry else None,
        "sources": base_map["sources"],
        "glossary_items": base_map["glossary_items"],
        "tool_outputs": base_map["tool_outputs"],
        "footer_summary_line": table.footer_summary_line,
        "sanitized_response_text": verification.sanitized_text,
        "citation_map_dict": base_map,
    }


async def verify_turn_citations_with_guard_async(
    citation_guard: AssistantCitationAndV5GuardService,
    *,
    response_text: str,
    evidence_table: EvidenceTable,
    workspace_id: str,
    user_id: str,
    user_email: str | None = None,
    user_display_name: str | None = None,
    turn_id: str | None = None,
    trace_id: str = "",
) -> tuple[CitationVerificationResult, dict[str, Any], bool]:
    """Run server `CitationGuard` before `turn_completed` and emit `citation_map` payload."""
    verification = await citation_guard.verify_and_sanitize_citations_async(
        response_text=response_text,
        evidence_table=evidence_table,
        workspace_id=workspace_id,
        user_id=user_id,
        user_email=user_email,
        user_display_name=user_display_name,
        turn_id=turn_id,
        trace_id=trace_id or None,
    )
    payload = build_citation_map_sse_payload(
        verification,
        turn_id=turn_id or "",
        trace_id=trace_id,
    )
    return verification, payload, is_low_evidence_table(evidence_table)


__all__ = [
    "build_citation_map_sse_payload",
    "is_low_evidence_table",
    "merge_tool_outputs_into_evidence_table",
    "verify_turn_citations_with_guard_async",
]
