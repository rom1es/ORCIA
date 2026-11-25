"""Pure deterministic citation table & phantom-tag sanitization helpers (`<= 300 L`)."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

from orcia_core.orchestration._assistant_locales import get_assistant_node_copy
from orcia_core.orchestration.assistant_citations_models import (
    CitationVerificationResult,
    EvidenceGlossaryCitation,
    EvidenceSourceCitation,
    EvidenceTable,
    EvidenceToolCitation,
    PhantomCitationAuditEntry,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
)
from orcia_kernel.ids import new_uuid7_str

UNVERIFIED_CITATION_BADGE: str = get_assistant_node_copy()["unverified_citation"]
_CITATION_TAG_RE = re.compile(r"\[([SGO]\d+)\]")
_EMPTY_SHA256_HEX = hashlib.sha256(b"").hexdigest()
_EMPTY_SHA256_RE = re.compile(
    rf"(?:sha256\s*:\s*)?`?{_EMPTY_SHA256_HEX}`?",
    re.IGNORECASE,
)
_UNGROUNDED_ORCIA_URI_RE = re.compile(
    r"`?orcia://[A-Za-z0-9_./:@?=&%-]+`?",
    re.IGNORECASE,
)
_DANGLING_PARENS_RE = re.compile(r"\(\s*[,;:\-–—]*\s*\)|\[\s*[,;:\-–—]*\s*\]")
_ORPHAN_PROOF_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:preuve(?:\s+de\s+conformit[e\u00e9])?|proof(?:\s+of\s+compliance)?|"
    r"source|r[e\u00e9]f[e\u00e9]rence|hash|sha-?256|uri)\s*[:\-–—.\s]*$",
    re.IGNORECASE,
)


def _scrub_empty_evidence_artifacts(text: str, *, had_phantom_tags: bool) -> str:
    """Remove fabricated empty-string SHA-256 digests and ungrounded `orcia://` proof tokens."""
    if (
        not had_phantom_tags
        and not _EMPTY_SHA256_RE.search(text)
        and not _UNGROUNDED_ORCIA_URI_RE.search(text)
    ):
        return text
    out_lines: list[str] = []
    for raw_line in text.splitlines():
        line_dirty = (
            bool(_EMPTY_SHA256_RE.search(raw_line))
            or bool(_UNGROUNDED_ORCIA_URI_RE.search(raw_line))
            or _ORPHAN_PROOF_LINE_RE.match(raw_line) is not None
        )
        if not line_dirty and not had_phantom_tags:
            out_lines.append(raw_line)
            continue
        cleaned_line = _EMPTY_SHA256_RE.sub("", raw_line)
        cleaned_line = _UNGROUNDED_ORCIA_URI_RE.sub("", cleaned_line)
        cleaned_line = _DANGLING_PARENS_RE.sub("", cleaned_line)
        if line_dirty:
            cleaned_line = re.sub(r"[ \t]{2,}", " ", cleaned_line).rstrip()
            cleaned_line = re.sub(r"\s+([,.;:!?])", r"\1", cleaned_line)
        if _ORPHAN_PROOF_LINE_RE.match(cleaned_line):
            continue
        out_lines.append(cleaned_line)
    result = "\n".join(out_lines).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def build_evidence_table_impl(
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
    s_count, g_count = len(numbered_sources), len(numbered_glossary)
    s_range = f"([S1]..[S{s_count}])" if s_count > 1 else ("([S1])" if s_count == 1 else "()")
    g_range = f"([G1]..[G{g_count}])" if g_count > 1 else ("([G1])" if g_count == 1 else "()")
    footer_line = get_assistant_node_copy()["evidence_footer"].format(
        s_count=s_count, s_range=s_range, g_count=g_count, g_range=g_range
    )
    return EvidenceTable(
        sources=numbered_sources,
        glossary_items=numbered_glossary,
        tool_outputs=numbered_tools,
        footer_summary_line=footer_line,
        citation_map_emitted_at_ms=round((time.perf_counter() - t0) * 1000.0, 3),
    )


def verify_and_sanitize_citations_impl(
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
        return UNVERIFIED_CITATION_BADGE if known_tags else ""

    sanitized = _CITATION_TAG_RE.sub(_replace_match, response_text)
    if not known_tags:
        sanitized = _scrub_empty_evidence_artifacts(
            sanitized, had_phantom_tags=bool(stripped_found)
        )
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

    return CitationVerificationResult(
        sanitized_text=sanitized,
        valid_tags=tuple(valid_found),
        stripped_phantom_tags=tuple(stripped_found),
        verification_duration_ms=elapsed_ms,
        audit_entry=audit_entry,
        evidence_table=evidence_table,
    )


def evaluate_tool_v5_and_human_anchor_guard_impl(
    *,
    tool_name: str,
    is_si_write: bool = False,
    human_authored_required: bool = False,
    target_uri: str | None = None,
    section_key: str | None = None,
) -> dict[str, Any] | None:
    """Deterministic tool-level Lock V5 & Human-Anchor check replacing lexical heuristics."""
    clean_section = (section_key or "").strip().lower()
    protected = {
        "intention-metier",
        "business-intent",
        "architecture-decision-rationale",
        "human-anchor",
        "primary-anchor",
    }
    anchor_hit = human_authored_required or clean_section in protected
    external_target = bool(
        target_uri
        and "://" in target_uri
        and not target_uri.startswith(("orcia://", "local://", "pack://"))
    )
    if not anchor_hit and not (is_si_write or external_target):
        return None
    code = (
        "ERR_HUMAN_ANCHOR_REQUIRED" if anchor_hit else "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"
    )
    return {
        "transition_action": "CONTINUE_IN_PROCESS",
        "reason_code": code,
        "tool_name": tool_name,
        "target_uri": target_uri or "",
        "human_authored_required": anchor_hit,
        "is_si_write": bool(is_si_write or external_target),
    }
