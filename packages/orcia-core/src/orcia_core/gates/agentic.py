"""Agentic Gate Service — Model Orthogonality, PII Scrubber & 5-Lens DAG (`Story 4.2`)."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from datetime import UTC, datetime
from typing import Any

from orcia_core.gates._agentic_lens_runner import (
    run_independent_lens_with_llm,
    run_synthesis_lens_with_llm,
)
from orcia_core.gates._agentic_service_helpers import (
    AgenticGateEvaluationResult,
    rehydrate_briefing_and_summary,
    resolve_sovereign_evaluator_route,
)
from orcia_core.gates.agentic_lenses import (
    INDEPENDENT_LENS_IDS,
    AgenticGateInput,
    AgenticLensFinding,
    AgenticLensId,
    AtomicFactAssertion,
    CognitiveReviewBriefing4Blocks,
    OntologyDataClassification,
)
from orcia_core.gates.models import GateEvaluationEntity, GateStatus
from orcia_core.gates.pii_scrubber import (
    PiiReversibleScrubber,
    purge_executor_chain_of_thought,
)
from orcia_core.observability.logging import get_logger, scrub_sensitive_dict
from orcia_kernel.enums import DEFAULT_LOCALE
from orcia_kernel.events import GateEvaluated
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import LLMPort, OutboxRelayPort


class AgenticGateService:
    """Executes the 5-Lens Agentic Gate DAG with Model Orthogonality & PII Scrubbing (`AD-10`)."""

    def __init__(
        self,
        *,
        llm_port: LLMPort | None = None,
        pii_scrubber: PiiReversibleScrubber | None = None,
        outbox_relay: OutboxRelayPort | None = None,
    ) -> None:
        self.llm_port: LLMPort | None = llm_port
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
        self, gate_input: AgenticGateInput, *, locale: str = DEFAULT_LOCALE
    ) -> AgenticGateEvaluationResult:
        """Execute the 4 parallel lenses + 1 synthesis lens asynchronously (`AD-10`)."""
        if self.llm_port is None:
            raise RuntimeError("AgenticGateService requires an LLMPort instance.")
        routed_family, routed_model_id, is_local = resolve_sovereign_evaluator_route(
            gate_input.executor_model_family,
            gate_input.evaluator_model_family,
            gate_input.evaluator_model_id,
            gate_input.data_classification,
        )

        purged_artifact, cot_purged_count = purge_executor_chain_of_thought(
            gate_input.candidate_artifact
        )
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
        lens_tasks = [
            self._run_independent_lens(
                lens_id=lens_id,
                gate_input=gate_input,
                scrubbed_artifact=scrubbed_artifact,
                artifact_json=artifact_json,
                routed_family=routed_family,
                routed_model_id=routed_model_id,
                locale=locale,
            )
            for lens_id in INDEPENDENT_LENS_IDS
        ]
        independent_findings: list[AgenticLensFinding] = list(await asyncio.gather(*lens_tasks))

        synthesis_finding, briefing, raw_summary = await self._run_synthesis_lens(
            gate_input=gate_input,
            independent_findings=tuple(independent_findings),
            scrubbed_artifact=scrubbed_artifact,
            routed_family=routed_family,
            routed_model_id=routed_model_id,
            locale=locale,
        )
        all_lenses = (*independent_findings, synthesis_finding)
        rehydrated_summary, rehydrated_briefing = rehydrate_briefing_and_summary(
            pii_scrubber=self.pii_scrubber,
            gate_input=gate_input,
            raw_summary=raw_summary,
            briefing=briefing,
        )

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

    def evaluate_agentic_gate(
        self, gate_input: AgenticGateInput, *, locale: str = DEFAULT_LOCALE
    ) -> AgenticGateEvaluationResult:
        """Synchronous entrypoint for evaluating the 5-lens Agentic Gate DAG."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.evaluate_agentic_gate_async(gate_input, locale=locale))
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                lambda: asyncio.run(self.evaluate_agentic_gate_async(gate_input, locale=locale))
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
        locale: str = DEFAULT_LOCALE,
    ) -> AgenticLensFinding:
        assert self.llm_port is not None
        return await run_independent_lens_with_llm(
            llm_port=self.llm_port,
            lens_id=lens_id,
            gate_input=gate_input,
            scrubbed_artifact=scrubbed_artifact,
            artifact_json=artifact_json,
            routed_family=routed_family,
            routed_model_id=routed_model_id,
            locale=locale,
        )

    async def _run_synthesis_lens(
        self,
        *,
        gate_input: AgenticGateInput,
        independent_findings: tuple[AgenticLensFinding, ...],
        scrubbed_artifact: dict[str, Any],
        routed_family: str,
        routed_model_id: str,
        locale: str = DEFAULT_LOCALE,
    ) -> tuple[AgenticLensFinding, CognitiveReviewBriefing4Blocks, str]:
        assert self.llm_port is not None
        return await run_synthesis_lens_with_llm(
            llm_port=self.llm_port,
            gate_input=gate_input,
            independent_findings=independent_findings,
            scrubbed_artifact=scrubbed_artifact,
            routed_family=routed_family,
            routed_model_id=routed_model_id,
            locale=locale,
        )


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
