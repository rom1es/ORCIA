"""Models, constants, and chunk extraction helpers for Adaptive Human Gates (`Story 4.3`)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.gates._gate_locales import get_gate_locale_bundle
from orcia_kernel.enums import DEFAULT_LOCALE
from orcia_kernel.ids import new_uuid7_str

HumanGatePolicy = Literal["mandatory_full", "risk_or_exception_based", "sampling"]
ChunkApprovalStatus = Literal["PENDING", "APPROVED", "CO_EDITED", "CHALLENGED"]
ChunkDecisionAction = Literal["APPROVE", "CO_EDIT", "CHALLENGE"]

RUBBER_STAMPING_WORD_THRESHOLD = 1000
RUBBER_STAMPING_MIN_DURATION_MS = 15000
AUTO_PASS_MIN_AGENTIC_SCORE = 0.85
SAMPLING_RATE_PERCENT = 20


def count_words(text: str) -> int:
    """Count words in a text or Markdown string."""
    return len(re.findall(r"\S+", text))


def compute_sampling_bucket(run_id: str, step_execution_id: str) -> int:
    """Return a deterministic integer in [0, 99] from `run_id:step_execution_id`."""
    digest = hashlib.sha256(f"{run_id}:{step_execution_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100


@dataclass(slots=True)
class ChunkApprovalRecord:
    """Single section/chunk approval state within a Human Gate (`chunk_approvals` table)."""

    id: str
    gate_evaluation_id: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    chunk_key: str
    section_title: str
    section_index: int
    content_markdown: str
    word_count: int
    human_authored_required: bool = False
    status: ChunkApprovalStatus = "PENDING"
    reviewer_user_id: str | None = None
    human_anchor_signature_id: str | None = None
    human_anchor_sha256: str | None = None
    challenge_reason: str | None = None
    reviewed_at: datetime | None = None


@dataclass(slots=True)
class HumanGateEvaluationRecord:
    """State of a Human Gate evaluation (`gate_evaluations` + `chunk_approvals`)."""

    id: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    policy: HumanGatePolicy
    status: Literal["PASS", "FAIL", "PENDING_HUMAN_REVIEW"]
    auto_passed: bool
    deterministic_status: str
    agentic_score: float
    ontology_conflicts: int
    stale_warnings: int
    total_word_count: int
    briefing_4blocks_jsonb: dict[str, Any]
    hypotheses_block_inspected: bool = False
    chunks: list[ChunkApprovalRecord] = field(default_factory=list)
    review_duration_ms: int = 0
    fast_approval_warning: bool = False
    reviewer_user_id: str | None = None
    outbox_event_id: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def extract_chunks_from_payload(
    *,
    gate_evaluation_id: str,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    artifact_payload: dict[str, Any],
    locale: str = DEFAULT_LOCALE,
) -> list[ChunkApprovalRecord]:
    """Split an artifact payload into `ChunkApprovalRecord` sections."""
    bundle = get_gate_locale_bundle(locale)
    raw_sections = artifact_payload.get("sections")
    chunks: list[ChunkApprovalRecord] = []
    if isinstance(raw_sections, list) and raw_sections:
        for idx, item in enumerate(raw_sections):
            if isinstance(item, dict):
                chunk_key = str(item.get("chunk_key") or item.get("key") or f"section-{idx + 1}")
                title = str(item.get("title") or f"Section {idx + 1}")
                content = str(item.get("content") or item.get("markdown") or "")
                human_req = bool(item.get("human_authored_required", False))
            else:
                chunk_key = f"section-{idx + 1}"
                title = f"Section {idx + 1}"
                content = str(item)
                human_req = False
            chunks.append(
                ChunkApprovalRecord(
                    id=new_uuid7_str(),
                    gate_evaluation_id=gate_evaluation_id,
                    workspace_id=workspace_id,
                    run_id=run_id,
                    step_execution_id=step_execution_id,
                    chunk_key=chunk_key,
                    section_title=title,
                    section_index=idx,
                    content_markdown=content,
                    word_count=count_words(content),
                    human_authored_required=human_req,
                )
            )
        return chunks

    markdown = str(artifact_payload.get("content") or artifact_payload.get("summary") or "")
    parts = re.split(r"(?m)^##\s+", markdown)
    cleaned_parts = [p.strip() for p in parts if p.strip()]
    if not cleaned_parts:
        cleaned_parts = [markdown or bundle.human_default_section_title]

    for idx, part in enumerate(cleaned_parts):
        lines = part.splitlines()
        title = lines[0].strip("# ").strip() if lines else f"Section {idx + 1}"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else part
        chunks.append(
            ChunkApprovalRecord(
                id=new_uuid7_str(),
                gate_evaluation_id=gate_evaluation_id,
                workspace_id=workspace_id,
                run_id=run_id,
                step_execution_id=step_execution_id,
                chunk_key=f"section-{idx + 1}",
                section_title=title[:255] or f"Section {idx + 1}",
                section_index=idx,
                content_markdown=body,
                word_count=count_words(part),
                human_authored_required=bool(
                    artifact_payload.get("human_authored_required", False) and idx == 0
                ),
            )
        )
    return chunks


def build_default_human_briefing(
    *,
    step_key: str,
    chunk_count: int,
    ontology_conflicts: int,
    stale_warnings: int,
    artifact_payload: dict[str, Any],
    locale: str = DEFAULT_LOCALE,
) -> dict[str, Any]:
    """Build the localized 4-block Human Gate review briefing."""
    bundle = get_gate_locale_bundle(locale)
    return {
        "block_1_executive_summary": {
            "title": bundle.human_block1_title,
            "summary": bundle.human_block1_summary_tpl.format(
                step_key=step_key, chunk_count=chunk_count
            ),
        },
        "block_2_key_elements_and_transverse_check": {
            "title": bundle.human_block2_title,
            "step1_aligned": ontology_conflicts == 0,
            "stale_warnings": stale_warnings,
        },
        "block_3_decisions_taken": {
            "title": bundle.human_block3_title,
            "decisions": artifact_payload.get("decisions", [bundle.human_block3_default_decision]),
        },
        "block_4_retained_hypotheses": {
            "title": bundle.human_block4_title,
            "requires_human_inspection": True,
            "amber_border_token": "--color-arbitration-amber",
            "hypotheses": artifact_payload.get(
                "hypotheses", [bundle.human_block4_default_hypothesis]
            ),
        },
    }
