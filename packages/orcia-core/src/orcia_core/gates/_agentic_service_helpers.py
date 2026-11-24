"""Pure routing and PII rehydration helpers for `AgenticGateService` (`Story 4.2`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.gates.agentic_lenses import (
    AgenticGateInput,
    AgenticLensFinding,
    CognitiveReviewBriefing4Blocks,
    OntologyDataClassification,
)
from orcia_core.gates.models import GateEvaluationEntity
from orcia_core.gates.pii_scrubber import PiiReversibleScrubber
from orcia_kernel.ports import assert_model_orthogonality


@dataclass(frozen=True, slots=True)
class AgenticGateEvaluationResult:
    """Full outcome of an Agentic Gate 5-lens DAG evaluation (`Story 4.2`)."""

    evaluation: GateEvaluationEntity
    routed_model_family: str
    routed_model_id: str
    routed_to_local_sovereign_model: bool
    cot_items_purged: int
    pii_tokens_redacted: int
    pii_token_map: dict[str, str]
    rehydrated_summary: str
    lens_results: tuple[AgenticLensFinding, ...]
    briefing_4blocks: CognitiveReviewBriefing4Blocks


def resolve_sovereign_evaluator_route(
    executor_family: str,
    requested_evaluator_family: str,
    requested_evaluator_model_id: str,
    data_classification: OntologyDataClassification,
) -> tuple[str, str, bool]:
    """Enforce model orthogonality and route `SENSITIVE`/`RESTRICTED` data to local models."""
    assert_model_orthogonality(executor_family, requested_evaluator_family)
    is_local = (
        "local" in requested_evaluator_family.lower()
        or "sovereign" in requested_evaluator_family.lower()
        or "vllm" in requested_evaluator_family.lower()
    )
    if data_classification in ("SENSITIVE", "RESTRICTED"):
        if is_local:
            return requested_evaluator_family.strip().lower(), requested_evaluator_model_id, True
        exec_norm = executor_family.strip().lower()
        eval_fam = "local_vllm" if exec_norm == "local_engine" else "local_engine"
        routed_model = (
            requested_evaluator_model_id
            if requested_evaluator_model_id.startswith("local/")
            else f"local/{requested_evaluator_model_id}"
        )
        return eval_fam, routed_model, True
    return requested_evaluator_family.strip().lower(), requested_evaluator_model_id, is_local


def rehydrate_briefing_and_summary(
    *,
    pii_scrubber: PiiReversibleScrubber,
    gate_input: AgenticGateInput,
    raw_summary: str,
    briefing: CognitiveReviewBriefing4Blocks,
) -> tuple[str, CognitiveReviewBriefing4Blocks]:
    """Rehydrate PII placeholders locally in summary and 4-block briefing (`NFR-SEC-2`)."""
    if not gate_input.anonymize_pii_reversible:
        return raw_summary, briefing
    rehydrated_summary = pii_scrubber.rehydrate_text(gate_input.run_id, raw_summary)
    rehydrated_briefing = CognitiveReviewBriefing4Blocks(
        executive_summary=pii_scrubber.rehydrate_text(
            gate_input.run_id, briefing.executive_summary
        ),
        key_elements_and_transverse_check=tuple(
            pii_scrubber.rehydrate_text(gate_input.run_id, item)
            for item in briefing.key_elements_and_transverse_check
        ),
        decisions_made=tuple(
            pii_scrubber.rehydrate_text(gate_input.run_id, item) for item in briefing.decisions_made
        ),
        retained_assumptions=tuple(
            pii_scrubber.rehydrate_text(gate_input.run_id, item)
            for item in briefing.retained_assumptions
        ),
        assumptions_inspected=briefing.assumptions_inspected,
    )
    return rehydrated_summary, rehydrated_briefing
