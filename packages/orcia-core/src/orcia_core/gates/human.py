"""Story 4.3: Adaptive Human Gates, 4-Block Review Briefing, Chunked Validation & <15s Guard."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.gates.errors import (
    HumanGateNotFoundError,
    RubberStampingGuardTriggeredError,
    UnapprovedChunksRemainingError,
)
from orcia_kernel.events import GateEvaluated
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import OutboxRelayPort

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


def _extract_chunks_from_payload(
    *,
    gate_evaluation_id: str,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    artifact_payload: dict[str, Any],
) -> list[ChunkApprovalRecord]:
    """Split an artifact payload into `ChunkApprovalRecord` sections."""
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
        cleaned_parts = [markdown or "Section principale"]

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


class AdaptiveHumanGateService:
    """Service orchestrating Adaptive Human Gates, Chunked Approvals & Anti-Rubber-Stamping."""

    def __init__(self, *, outbox_relay: OutboxRelayPort | None = None) -> None:
        self._outbox_relay = outbox_relay
        self._outbox_events: list[GateEvaluated] = []
        self._evaluations: dict[str, HumanGateEvaluationRecord] = {}

    def list_outbox_events(self) -> list[GateEvaluated]:
        return list(self._outbox_events)

    def get_evaluation(self, gate_evaluation_id: str) -> HumanGateEvaluationRecord:
        record = self._evaluations.get(gate_evaluation_id)
        if record is None:
            raise HumanGateNotFoundError(
                detail_override=f"Human Gate evaluation '{gate_evaluation_id}' not found."
            )
        return record

    def list_evaluations(
        self, *, workspace_id: str | None = None
    ) -> list[HumanGateEvaluationRecord]:
        items = list(self._evaluations.values())
        if workspace_id is not None:
            items = [e for e in items if e.workspace_id == workspace_id]
        return items

    def evaluate_human_gate(
        self,
        *,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
        step_key: str,
        policy: HumanGatePolicy,
        artifact_payload: dict[str, Any],
        deterministic_status: str = "PASS",
        agentic_score: float = 0.92,
        ontology_conflicts: int = 0,
        stale_warnings: int = 0,
        briefing_4blocks_jsonb: dict[str, Any] | None = None,
        sampling_override: bool | None = None,
        trace_id: str | None = None,
    ) -> HumanGateEvaluationRecord:
        """Evaluate whether a Human Gate auto-passes or requires chunked human review (`AD-11`)."""
        eval_id = new_uuid7_str()
        chunks = _extract_chunks_from_payload(
            gate_evaluation_id=eval_id,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            artifact_payload=artifact_payload,
        )
        total_words = sum(c.word_count for c in chunks)
        has_human_anchor = any(c.human_authored_required for c in chunks) or bool(
            artifact_payload.get("human_authored_required", False)
        )

        eligible_for_auto_pass = (
            deterministic_status == "PASS"
            and agentic_score >= AUTO_PASS_MIN_AGENTIC_SCORE
            and ontology_conflicts == 0
            and stale_warnings == 0
            and not has_human_anchor
        )

        requires_human = True
        if policy == "mandatory_full":
            requires_human = True
        elif policy == "risk_or_exception_based":
            requires_human = not eligible_for_auto_pass
        elif policy == "sampling":
            if not eligible_for_auto_pass:
                requires_human = True
            elif sampling_override is not None:
                requires_human = sampling_override
            else:
                bucket = compute_sampling_bucket(run_id, step_execution_id)
                requires_human = bucket < SAMPLING_RATE_PERCENT

        default_briefing = briefing_4blocks_jsonb or {
            "block_1_executive_summary": {
                "title": "1. Résumé Exécutif",
                "summary": f"Synthèse de l'étape {step_key} ({len(chunks)} sections).",
            },
            "block_2_key_elements_and_transverse_check": {
                "title": "2. Éléments Clés & Contrôle Transverse",
                "step1_aligned": ontology_conflicts == 0,
                "stale_warnings": stale_warnings,
            },
            "block_3_decisions_taken": {
                "title": "3. Décisions Prises",
                "decisions": artifact_payload.get("decisions", ["Validation structurelle"]),
            },
            "block_4_retained_hypotheses": {
                "title": "4. Hypothèses Retenues",
                "requires_human_inspection": True,
                "amber_border_token": "--color-arbitration-amber",
                "hypotheses": artifact_payload.get(
                    "hypotheses",
                    ["Les contraintes amont du Cadrage et de l'Ontologie sont respectées."],
                ),
            },
        }

        status: Literal["PASS", "FAIL", "PENDING_HUMAN_REVIEW"] = (
            "PENDING_HUMAN_REVIEW" if requires_human else "PASS"
        )
        outbox_event_id: str | None = None
        if status == "PASS":
            for chunk in chunks:
                chunk.status = "APPROVED"
                chunk.reviewed_at = datetime.now(UTC)
            outbox_event_id = self._publish_gate_event(
                gate_evaluation_id=eval_id,
                workspace_id=workspace_id,
                run_id=run_id,
                passed=True,
                score=agentic_score,
            )

        record = HumanGateEvaluationRecord(
            id=eval_id,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            policy=policy,
            status=status,
            auto_passed=not requires_human,
            deterministic_status=deterministic_status,
            agentic_score=agentic_score,
            ontology_conflicts=ontology_conflicts,
            stale_warnings=stale_warnings,
            total_word_count=total_words,
            briefing_4blocks_jsonb=default_briefing,
            hypotheses_block_inspected=not requires_human,
            chunks=chunks,
            outbox_event_id=outbox_event_id,
        )
        self._evaluations[eval_id] = record
        return record

    def inspect_briefing_hypotheses(
        self, gate_evaluation_id: str, *, reviewer_user_id: str
    ) -> HumanGateEvaluationRecord:
        """Mark Block 4 (`Hypothèses Retenues`) of the 4-block briefing as inspected."""
        record = self.get_evaluation(gate_evaluation_id)
        record.hypotheses_block_inspected = True
        record.reviewer_user_id = reviewer_user_id
        block4 = record.briefing_4blocks_jsonb.get("block_4_retained_hypotheses")
        if isinstance(block4, dict):
            block4["requires_human_inspection"] = False
            block4["inspected_by"] = reviewer_user_id
        return record

    def decide_chunk(
        self,
        gate_evaluation_id: str,
        chunk_key: str,
        *,
        action: ChunkDecisionAction,
        reviewer_user_id: str,
        co_edited_content: str | None = None,
        challenge_reason: str | None = None,
    ) -> ChunkApprovalRecord:
        """Approve, co-edit (with SHA-256 signature), or challenge a single chunk (`UX-DR5`)."""
        record = self.get_evaluation(gate_evaluation_id)
        target: ChunkApprovalRecord | None = None
        for chunk in record.chunks:
            if chunk.chunk_key == chunk_key:
                target = chunk
                break
        if target is None:
            raise HumanGateNotFoundError(
                detail_override=(
                    f"Chunk '{chunk_key}' not found in Human Gate '{gate_evaluation_id}'."
                )
            )

        now = datetime.now(UTC)
        target.reviewer_user_id = reviewer_user_id
        target.reviewed_at = now
        if action == "APPROVE":
            target.status = "APPROVED"
        elif action == "CO_EDIT":
            updated_text = (
                co_edited_content if co_edited_content is not None else target.content_markdown
            )
            target.content_markdown = updated_text
            target.word_count = count_words(updated_text)
            target.status = "CO_EDITED"
            target.human_anchor_signature_id = new_uuid7_str()
            target.human_anchor_sha256 = hashlib.sha256(updated_text.encode("utf-8")).hexdigest()
            record.total_word_count = sum(c.word_count for c in record.chunks)
        elif action == "CHALLENGE":
            target.status = "CHALLENGED"
            target.challenge_reason = challenge_reason or "Section contestée vers l'étape amont."
            record.status = "FAIL"
        return target

    def finalize_human_gate(
        self,
        gate_evaluation_id: str,
        *,
        reviewer_user_id: str,
        review_duration_ms: int,
        explicit_hypotheses_confirmation: bool = False,
        trace_id: str | None = None,
    ) -> HumanGateEvaluationRecord:
        """Finalize Human Gate approval after checking all chunks and <15s guard (`AD-11`)."""
        _ = trace_id
        record = self.get_evaluation(gate_evaluation_id)
        if explicit_hypotheses_confirmation:
            record.hypotheses_block_inspected = True

        unapproved = [
            c.chunk_key for c in record.chunks if c.status not in ("APPROVED", "CO_EDITED")
        ]
        if unapproved or not record.hypotheses_block_inspected:
            raise UnapprovedChunksRemainingError(
                detail_override=(
                    f"Cannot finalize Human Gate '{gate_evaluation_id}': "
                    f"unapproved chunks={unapproved}, "
                    f"hypotheses_inspected={record.hypotheses_block_inspected}."
                )
            )

        record.review_duration_ms = max(0, review_duration_ms)
        record.reviewer_user_id = reviewer_user_id
        is_fast_on_large_artifact = (
            record.total_word_count > RUBBER_STAMPING_WORD_THRESHOLD
            and record.review_duration_ms < RUBBER_STAMPING_MIN_DURATION_MS
        )
        if is_fast_on_large_artifact:
            record.fast_approval_warning = True
            if not explicit_hypotheses_confirmation:
                raise RubberStampingGuardTriggeredError(
                    detail_override=(
                        f"Fast approval detected ({record.review_duration_ms} ms < "
                        f"{RUBBER_STAMPING_MIN_DURATION_MS} ms on "
                        f"{record.total_word_count} words). "
                        "Explicit confirmation of retained hypotheses is required."
                    )
                )

        record.status = "PASS"
        record.evaluated_at = datetime.now(UTC)
        record.outbox_event_id = self._publish_gate_event(
            gate_evaluation_id=record.id,
            workspace_id=record.workspace_id,
            run_id=record.run_id,
            passed=True,
            score=1.0,
        )
        return record

    def _publish_gate_event(
        self,
        *,
        gate_evaluation_id: str,
        workspace_id: str,
        run_id: str,
        passed: bool,
        score: float,
    ) -> str:
        outbox_evt = GateEvaluated.create(
            gate_evaluation_id=gate_evaluation_id,
            run_id=run_id,
            workspace_id=workspace_id,
            gate_type="HUMAN",
            passed=passed,
            score=score,
        )
        self._outbox_events.append(outbox_evt)
        if self._outbox_relay is not None:
            self._outbox_relay.enqueue_in_transaction(outbox_evt)
        return outbox_evt.event_id
