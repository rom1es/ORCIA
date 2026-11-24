"""Independent and synthesis lens execution helpers for `AgenticGateService` (`Story 4.2`)."""

from __future__ import annotations

from typing import Any

from orcia_core.gates._gate_locales import get_gate_locale_bundle
from orcia_core.gates.agentic_lenses import (
    AgenticGateInput,
    AgenticLensFinding,
    AgenticLensId,
    CognitiveReviewBriefing4Blocks,
    evaluate_lens1_transverse,
    evaluate_lens2_facts,
    evaluate_lens3_adversarial,
    evaluate_lens4_compliance,
)
from orcia_kernel.enums import DEFAULT_LOCALE
from orcia_kernel.ports import LLMPort, LlmPromptRequest


async def run_independent_lens_with_llm(
    *,
    llm_port: LLMPort,
    lens_id: AgenticLensId,
    gate_input: AgenticGateInput,
    scrubbed_artifact: dict[str, Any],
    artifact_json: str,
    routed_family: str,
    routed_model_id: str,
    locale: str = DEFAULT_LOCALE,
) -> AgenticLensFinding:
    """Execute one independent evaluator lens with zero peer visibility."""
    sys_prompt = (
        f"ORCIA Agentic Gate Evaluator — Independent Lens '{lens_id}'. "
        "Zero cross-visibility with peer lenses and zero access to executor CoT."
    )
    user_prompt = (
        f"LENS={lens_id}\nSTEP={gate_input.step_key}\nARTIFACT={artifact_json}\n"
        f"PRD_INVARIANTS={list(gate_input.step1_prd_invariants)}\n"
        f"ARCH_INVARIANTS={list(gate_input.step2_arch_invariants)}"
    )
    llm_res = await llm_port.complete(
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
            gate_input,
            artifact_json,
            routed_family,
            routed_model_id,
            llm_res.prompt_sha256,
            locale=locale,
        )
    if lens_id == "fact_verification":
        return evaluate_lens2_facts(
            gate_input,
            scrubbed_artifact,
            artifact_json,
            routed_family,
            routed_model_id,
            llm_res.prompt_sha256,
            locale=locale,
        )
    if lens_id == "adversarial_edge_cases":
        return evaluate_lens3_adversarial(
            scrubbed_artifact,
            routed_family,
            routed_model_id,
            llm_res.prompt_sha256,
            locale=locale,
        )
    return evaluate_lens4_compliance(
        scrubbed_artifact,
        routed_family,
        routed_model_id,
        llm_res.prompt_sha256,
        locale=locale,
    )


async def run_synthesis_lens_with_llm(
    *,
    llm_port: LLMPort,
    gate_input: AgenticGateInput,
    independent_findings: tuple[AgenticLensFinding, ...],
    scrubbed_artifact: dict[str, Any],
    routed_family: str,
    routed_model_id: str,
    locale: str = DEFAULT_LOCALE,
) -> tuple[AgenticLensFinding, CognitiveReviewBriefing4Blocks, str]:
    """Execute Lens 5 synthesis consolidating the 4-block review briefing."""
    bundle = get_gate_locale_bundle(locale)
    decisions = [
        str(m.get("text") or m.get("summary") or "")
        for m in gate_input.step_memlog_markers
        if "DECISION" in str(m.get("marker_type", "")).upper()
    ] or [bundle.default_decision]
    assumptions = [
        str(m.get("text") or m.get("summary") or "")
        for m in gate_input.step_memlog_markers
        if "ASSUMPTION" in str(m.get("marker_type", "")).upper()
    ] or [bundle.default_assumption]

    summary_candidate = str(
        scrubbed_artifact.get("summary")
        or scrubbed_artifact.get("title")
        or bundle.step_review_summary_tpl.format(step_key=gate_input.step_key)
    )
    synth_prompt = (
        f"LENS=synthesis_and_structure\nSUMMARY={summary_candidate}\n"
        f"LENS_SCORES={[f.score for f in independent_findings]}"
    )
    llm_res = await llm_port.complete(
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
    synth_score = round(sum(f.score for f in independent_findings) / len(independent_findings), 4)
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
        findings=(bundle.synthesis_consolidated,),
        model_family=routed_family,
        model_id=routed_model_id,
        prompt_sha256=llm_res.prompt_sha256,
        isolated_from_peer_lenses=False,
    )
    return finding, briefing, summary_candidate
