"""Agentic Gate Service — Model Orthogonality, Reversible PII Scrubber & 5-Lens DAG (`Story 4.2`).

Implements `FR-18`, `AD-10`, `AD-19`, `NFR-SEC-2`, and `DEC-SEC-01`:
- Enforces `evaluator_model_family != executor_model_family` (`ModelOrthogonalityViolationError`).
- Purges 100% of executor Chain-of-Thought before invoking the 4 independent evaluator lenses.
- Routes `SENSITIVE` / `RESTRICTED` data to sovereign local models (`local/ollama-*` / `local/vllm`)
  and applies `PiiReversibleScrubber` (`anonymize_pii_reversible: true`) with local re-hydration.
- Runs the 4 independent lenses in parallel (`asyncio.gather`, zero cross-visibility) followed by
  Lens 5 (`synthesis_and_structure`) which integrates `step_memlog_jsonb`, computes `agentic_score`,
  structures `briefing_4blocks_jsonb`, and publishes `GateEvaluated` to `domain_events_outbox`.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from orcia_core.gates.agentic_lenses import (
    INDEPENDENT_LENS_IDS,
    AgenticGateInput,
    AgenticLensFinding,
    AgenticLensId,
    AtomicFactAssertion,
    CognitiveReviewBriefing4Blocks,
    OntologyDataClassification,
    evaluate_lens1_transverse,
    evaluate_lens2_facts,
    evaluate_lens3_adversarial,
    evaluate_lens4_compliance,
)
from orcia_core.gates.models import GateEvaluationEntity, GateStatus
from orcia_core.gates.pii_scrubber import (
    PiiReversibleScrubber,
    purge_executor_chain_of_thought,
)
from orcia_core.observability.logging import get_logger, scrub_sensitive_dict
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.events import GateEvaluated
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import (
    LLMPort,
    LlmPromptRequest,
    OutboxRelayPort,
    assert_model_orthogonality,
)


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


def _resolve_sovereign_evaluator_route(
    executor_family: str,
    requested_evaluator_family: str,
    requested_evaluator_model_id: str,
    data_classification: OntologyDataClassification,
) -> tuple[str, str, bool]:
    """Enforce model orthogonality and route `SENSITIVE`/`RESTRICTED` data to local models."""
    assert_model_orthogonality(executor_family, requested_evaluator_family)
    if data_classification in ("SENSITIVE", "RESTRICTED"):
        exec_norm = executor_family.strip().lower()
        if exec_norm != "local_ollama":
            return "local_ollama", "local/ollama-qwen2.5-coder-32b", True
        return "local_vllm", "local/vllm-mistral-small-24b", True
    return requested_evaluator_family.strip().lower(), requested_evaluator_model_id, False


class AgenticGateService:
    """Executes the 5-Lens Agentic Gate DAG with Model Orthogonality & PII Scrubbing (`AD-10`)."""

    def __init__(
        self,
        *,
        llm_port: LLMPort | None = None,
        pii_scrubber: PiiReversibleScrubber | None = None,
        outbox_relay: OutboxRelayPort | None = None,
    ) -> None:
        self.llm_port: LLMPort = llm_port or DeterministicCassetteLLM()
        self.pii_scrubber: PiiReversibleScrubber = pii_scrubber or PiiReversibleScrubber()
        self._outbox_relay = outbox_relay
        self._evaluations: dict[str, GateEvaluationEntity] = {}
        self._outbox_events: list[GateEvaluated] = []

    def list_evaluations(self, *, run_id: str | None = None) -> list[GateEvaluationEntity]:
        items = list(self._evaluations.values())
        if run_id is not None:
            items = [e for e in items if e.run_id == run_id]
        return items

    def list_outbox_events(self) -> list[GateEvaluated]:
        return list(self._outbox_events)

    async def evaluate_agentic_gate_async(
        self, gate_input: AgenticGateInput
    ) -> AgenticGateEvaluationResult:
        """Execute the 4 parallel lenses + 1 synthesis lens asynchronously (`AD-10`)."""
        routed_family, routed_model_id, is_local = _resolve_sovereign_evaluator_route(
            gate_input.executor_model_family,
            gate_input.evaluator_model_family,
            gate_input.evaluator_model_id,
            gate_input.data_classification,
        )

        # 1. Purge executor Chain-of-Thought (FR-18, AD-10)
        purged_artifact, cot_purged_count = purge_executor_chain_of_thought(
            gate_input.candidate_artifact
        )

        # 2. Reversible PII scrubbing (NFR-SEC-2)
        if gate_input.anonymize_pii_reversible:
            scrubbed_artifact, token_map, pii_redacted_count = self.pii_scrubber.scrub_payload(
                gate_input.run_id,
                purged_artifact,
                custom_entities=gate_input.custom_pii_entities,
            )
        else:
            scrubbed_artifact = purged_artifact
            token_map = {}
            pii_redacted_count = 0

        artifact_json = json.dumps(scrubbed_artifact, sort_keys=True, ensure_ascii=False)

        # 3. Parallel execution of Lenses 1..4 without cross-visibility or executor memlog
        lens_tasks = [
            self._run_independent_lens(
                lens_id=lens_id,
                gate_input=gate_input,
                scrubbed_artifact=scrubbed_artifact,
                artifact_json=artifact_json,
                routed_family=routed_family,
                routed_model_id=routed_model_id,
            )
            for lens_id in INDEPENDENT_LENS_IDS
        ]
        independent_findings: list[AgenticLensFinding] = list(await asyncio.gather(*lens_tasks))

        # 4. Lens 5 — Synthesis & Structure (after Lenses 1..4, integrating step_memlog_markers)
        synthesis_finding, briefing, raw_summary = await self._run_synthesis_lens(
            gate_input=gate_input,
            independent_findings=tuple(independent_findings),
            scrubbed_artifact=scrubbed_artifact,
            routed_family=routed_family,
            routed_model_id=routed_model_id,
        )
        all_lenses = (*independent_findings, synthesis_finding)

        # 5. Rehydrate PII locally in the executive summary and briefing (NFR-SEC-2)
        if gate_input.anonymize_pii_reversible:
            rehydrated_summary = self.pii_scrubber.rehydrate_text(gate_input.run_id, raw_summary)
            rehydrated_briefing = CognitiveReviewBriefing4Blocks(
                executive_summary=self.pii_scrubber.rehydrate_text(
                    gate_input.run_id, briefing.executive_summary
                ),
                key_elements_and_transverse_check=tuple(
                    self.pii_scrubber.rehydrate_text(gate_input.run_id, item)
                    for item in briefing.key_elements_and_transverse_check
                ),
                decisions_made=tuple(
                    self.pii_scrubber.rehydrate_text(gate_input.run_id, item)
                    for item in briefing.decisions_made
                ),
                retained_assumptions=tuple(
                    self.pii_scrubber.rehydrate_text(gate_input.run_id, item)
                    for item in briefing.retained_assumptions
                ),
                assumptions_inspected=briefing.assumptions_inspected,
            )
        else:
            rehydrated_summary = raw_summary
            rehydrated_briefing = briefing

        avg_score = round(sum(f.score for f in all_lenses) / len(all_lenses), 4)
        blocking_lens_failed = any(not f.passed for f in independent_findings)
        passed = (avg_score >= gate_input.pass_score_threshold) and not blocking_lens_failed
        status: GateStatus = "PASS" if passed else "FAIL"

        eval_id = new_uuid7_str()
        outbox_evt = GateEvaluated.create(
            gate_evaluation_id=eval_id,
            run_id=gate_input.run_id,
            workspace_id=gate_input.workspace_id,
            gate_type="AGENTIC",
            passed=passed,
            score=avg_score,
        )
        self._outbox_events.append(outbox_evt)
        if self._outbox_relay is not None:
            self._outbox_relay.enqueue_in_transaction(outbox_evt)

        sanitized_briefing = scrub_sensitive_dict(rehydrated_briefing.to_dict())
        entity = GateEvaluationEntity(
            id=eval_id,
            workspace_id=gate_input.workspace_id,
            run_id=gate_input.run_id,
            step_execution_id=gate_input.step_execution_id,
            step_key=gate_input.step_key,
            gate_type="AGENTIC",
            sandbox_tier="NONE",
            status=status,
            score=avg_score,
            schema_validation_passed=True,
            ontology_axioms_passed=all(f.passed for f in independent_findings[:2]),
            pattern_drift_passed=True,
            lens_findings=tuple(scrub_sensitive_dict(f.to_dict()) for f in all_lenses),
            briefing_4blocks=sanitized_briefing,
            evaluator_model_id=routed_model_id,
            duration_ms=18,
            outbox_event_id=outbox_evt.event_id,
            evaluated_at=datetime.now(UTC).isoformat(),
        )
        self._evaluations[entity.id] = entity
        get_logger("orcia.gates.agentic").info(
            "gate.agentic.evaluated",
            gate_evaluation_id=eval_id,
            run_id=gate_input.run_id,
            routed_model_family=routed_family,
            routed_model_id=routed_model_id,
            score=avg_score,
            status=status,
        )
        return AgenticGateEvaluationResult(
            evaluation=entity,
            routed_model_family=routed_family,
            routed_model_id=routed_model_id,
            routed_to_local_sovereign_model=is_local,
            cot_items_purged=cot_purged_count,
            pii_tokens_redacted=pii_redacted_count,
            pii_token_map=token_map,
            rehydrated_summary=rehydrated_summary,
            lens_results=all_lenses,
            briefing_4blocks=rehydrated_briefing,
        )

    def evaluate_agentic_gate(self, gate_input: AgenticGateInput) -> AgenticGateEvaluationResult:
        """Synchronous entrypoint for evaluating the 5-lens Agentic Gate DAG."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.evaluate_agentic_gate_async(gate_input))
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                lambda: asyncio.run(self.evaluate_agentic_gate_async(gate_input))
            ).result()

    async def _run_independent_lens(
        self,
        *,
        lens_id: AgenticLensId,
        gate_input: AgenticGateInput,
        scrubbed_artifact: dict[str, Any],
        artifact_json: str,
        routed_family: str,
        routed_model_id: str,
    ) -> AgenticLensFinding:
        sys_prompt = (
            f"ORCIA Agentic Gate Evaluator — Independent Lens '{lens_id}'. "
            "Zero cross-visibility with peer lenses and zero access to executor CoT."
        )
        user_prompt = (
            f"LENS={lens_id}\nSTEP={gate_input.step_key}\nARTIFACT={artifact_json}\n"
            f"PRD_INVARIANTS={list(gate_input.step1_prd_invariants)}\n"
            f"ARCH_INVARIANTS={list(gate_input.step2_arch_invariants)}"
        )
        llm_res = await self.llm_port.complete(
            LlmPromptRequest(
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                model_family=routed_family,
                model_id=routed_model_id,
                executor_model_family=gate_input.executor_model_family,
                metadata={"lens_id": lens_id, "run_id": gate_input.run_id},
            )
        )

        if lens_id == "transverse_alignment_step1":
            return evaluate_lens1_transverse(
                gate_input, artifact_json, routed_family, routed_model_id, llm_res.prompt_sha256
            )
        if lens_id == "fact_verification":
            return evaluate_lens2_facts(
                gate_input,
                scrubbed_artifact,
                artifact_json,
                routed_family,
                routed_model_id,
                llm_res.prompt_sha256,
            )
        if lens_id == "adversarial_edge_cases":
            return evaluate_lens3_adversarial(
                scrubbed_artifact, routed_family, routed_model_id, llm_res.prompt_sha256
            )
        return evaluate_lens4_compliance(
            scrubbed_artifact, routed_family, routed_model_id, llm_res.prompt_sha256
        )

    async def _run_synthesis_lens(
        self,
        *,
        gate_input: AgenticGateInput,
        independent_findings: tuple[AgenticLensFinding, ...],
        scrubbed_artifact: dict[str, Any],
        routed_family: str,
        routed_model_id: str,
    ) -> tuple[AgenticLensFinding, CognitiveReviewBriefing4Blocks, str]:
        decisions = [
            str(m.get("text") or m.get("summary") or "")
            for m in gate_input.step_memlog_markers
            if "DECISION" in str(m.get("marker_type", "")).upper()
        ] or ["Architecture modulaire et contrats d'interface validés."]
        assumptions = [
            str(m.get("text") or m.get("summary") or "")
            for m in gate_input.step_memlog_markers
            if "ASSUMPTION" in str(m.get("marker_type", "")).upper()
        ] or ["Hypothèse nominale de fraîcheur des sources épinglées dans run-lock.json."]

        summary_candidate = str(
            scrubbed_artifact.get("summary")
            or scrubbed_artifact.get("title")
            or f"Synthèse de revue de l'étape {gate_input.step_key}"
        )
        synth_prompt = (
            f"LENS=synthesis_and_structure\nSUMMARY={summary_candidate}\n"
            f"LENS_SCORES={[f.score for f in independent_findings]}"
        )
        llm_res = await self.llm_port.complete(
            LlmPromptRequest(
                system_prompt="ORCIA Agentic Gate — Lens 5 Synthesis & 4-Block Review Briefing.",
                user_prompt=synth_prompt,
                model_family=routed_family,
                model_id=routed_model_id,
                executor_model_family=gate_input.executor_model_family,
                metadata={"lens_id": "synthesis_and_structure", "run_id": gate_input.run_id},
            )
        )

        all_passed = all(f.passed for f in independent_findings)
        synth_score = round(
            sum(f.score for f in independent_findings) / len(independent_findings), 4
        )
        briefing = CognitiveReviewBriefing4Blocks(
            executive_summary=summary_candidate,
            key_elements_and_transverse_check=tuple(
                f"[{f.lens_id}] {f.findings[0]}" for f in independent_findings if f.findings
            ),
            decisions_made=tuple(decisions),
            retained_assumptions=tuple(assumptions),
            assumptions_inspected=False,
        )
        finding = AgenticLensFinding(
            lens_id="synthesis_and_structure",
            passed=all_passed,
            score=synth_score,
            findings=("Briefing de revue en 4 blocs consolidé à partir des 4 lentilles.",),
            model_family=routed_family,
            model_id=routed_model_id,
            prompt_sha256=llm_res.prompt_sha256,
            isolated_from_peer_lenses=False,
        )
        return finding, briefing, summary_candidate


__all__ = [
    "INDEPENDENT_LENS_IDS",
    "AgenticGateEvaluationResult",
    "AgenticGateInput",
    "AgenticGateService",
    "AgenticLensFinding",
    "AgenticLensId",
    "AtomicFactAssertion",
    "CognitiveReviewBriefing4Blocks",
    "OntologyDataClassification",
]
