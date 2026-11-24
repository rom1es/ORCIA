"""Pure Evaluation Rules for the 5-Lens Agentic Gate (`AD-10`, `Story 4.2`)."""

from __future__ import annotations

from typing import Any

from orcia_core.gates._agentic_models import (
    INDEPENDENT_LENS_IDS,
    AgenticGateInput,
    AgenticLensFinding,
    AgenticLensId,
    AtomicFactAssertion,
    CognitiveReviewBriefing4Blocks,
    OntologyDataClassification,
)
from orcia_core.gates._gate_locales import get_gate_locale_bundle
from orcia_kernel.enums import DEFAULT_LOCALE


def evaluate_lens1_transverse(
    gate_input: AgenticGateInput,
    artifact_json: str,
    routed_family: str,
    routed_model_id: str,
    prompt_sha256: str,
    *,
    locale: str = DEFAULT_LOCALE,
) -> AgenticLensFinding:
    """Evaluate Lens 1 (`transverse_alignment_step1`): Step N vs Step 1 Cadrage & Step 2 Arch."""
    bundle = get_gate_locale_bundle(locale)
    contradictions: list[str] = []
    lower_art = artifact_json.lower()
    for inv in (*gate_input.step1_prd_invariants, *gate_input.step2_arch_invariants):
        cleaned = inv.strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith("forbid:"):
            forbidden_term = cleaned.split(":", 1)[1].strip().lower()
            if forbidden_term and forbidden_term in lower_art:
                contradictions.append(bundle.lens1_forbidden_tpl.format(term=forbidden_term))
        elif cleaned.lower().startswith("require:"):
            req_term = cleaned.split(":", 1)[1].strip().lower()
            if req_term and req_term not in lower_art:
                contradictions.append(bundle.lens1_required_tpl.format(term=req_term))
    passed = len(contradictions) == 0
    score = 0.94 if passed else 0.35
    findings = tuple(contradictions) if contradictions else (bundle.lens1_pass,)
    return AgenticLensFinding(
        lens_id="transverse_alignment_step1",
        passed=passed,
        score=score,
        findings=findings,
        model_family=routed_family,
        model_id=routed_model_id,
        prompt_sha256=prompt_sha256,
    )


def evaluate_lens2_facts(
    gate_input: AgenticGateInput,
    scrubbed_artifact: dict[str, Any],
    artifact_json: str,
    routed_family: str,
    routed_model_id: str,
    prompt_sha256: str,
    *,
    locale: str = DEFAULT_LOCALE,
) -> AgenticLensFinding:
    """Evaluate Lens 2 (`fact_verification`): atomic claims vs Ontology N1..N4 & pinned KBs."""
    bundle = get_gate_locale_bundle(locale)
    raw_claims = scrubbed_artifact.get("claims") or scrubbed_artifact.get("assertions") or []
    atomic_facts: list[AtomicFactAssertion] = []
    blocking_findings: list[str] = []

    if isinstance(raw_claims, list) and raw_claims:
        for idx, item in enumerate(raw_claims, start=1):
            if isinstance(item, dict):
                stmt = str(item.get("statement", ""))
                src = str(item.get("source_uri", "orcia://ontology/layer-1"))
                conf = float(item.get("confidence", 0.92))
                contradicts = bool(item.get("contradicts_ontology", False))
            else:
                stmt = str(item)
                src = "orcia://ontology/layer-1"
                conf = 0.92
                contradicts = False

            for onto_key, onto_rule in gate_input.ontology_facts.items():
                if onto_rule.lower().startswith("forbid:") and (
                    onto_rule.split(":", 1)[1].strip().lower() in stmt.lower()
                ):
                    contradicts = True
                    conf = min(conf, 0.25)
                    blocking_findings.append(
                        bundle.lens2_axiom_contradiction_tpl.format(idx=idx, onto_key=onto_key)
                    )

            verified = (conf >= gate_input.fact_confidence_threshold) and not contradicts
            if not verified and not contradicts:
                blocking_findings.append(
                    bundle.lens2_low_confidence_tpl.format(
                        idx=idx, conf=conf, threshold=gate_input.fact_confidence_threshold
                    )
                )
            atomic_facts.append(
                AtomicFactAssertion(
                    assertion_id=f"FACT-{idx}",
                    statement=stmt,
                    grounding_source_uri=src,
                    confidence_score=conf,
                    verified=verified,
                    contradicts_ontology=contradicts,
                    rationale=bundle.lens2_fact_verified if verified else bundle.lens2_fact_failed,
                )
            )
    else:
        atomic_facts.append(
            AtomicFactAssertion(
                assertion_id="FACT-1",
                statement=artifact_json[:140],
                grounding_source_uri="orcia://ontology/layer-1",
                confidence_score=0.93,
                verified=True,
                contradicts_ontology=False,
                rationale=bundle.lens2_no_contradiction,
            )
        )

    passed = len(blocking_findings) == 0
    avg_conf = sum(f.confidence_score for f in atomic_facts) / len(atomic_facts)
    score = round(avg_conf if passed else min(0.40, avg_conf), 4)
    findings = (
        tuple(blocking_findings)
        if blocking_findings
        else (bundle.lens2_assertions_verified_tpl.format(count=len(atomic_facts)),)
    )
    return AgenticLensFinding(
        lens_id="fact_verification",
        passed=passed,
        score=score,
        findings=findings,
        model_family=routed_family,
        model_id=routed_model_id,
        prompt_sha256=prompt_sha256,
        atomic_facts=tuple(atomic_facts),
    )


def evaluate_lens3_adversarial(
    scrubbed_artifact: dict[str, Any],
    routed_family: str,
    routed_model_id: str,
    prompt_sha256: str,
    *,
    locale: str = DEFAULT_LOCALE,
) -> AgenticLensFinding:
    """Evaluate Lens 3 (`adversarial_edge_cases`)."""
    bundle = get_gate_locale_bundle(locale)
    has_flaw = bool(scrubbed_artifact.get("adversarial_vulnerability", False))
    score = 0.45 if has_flaw else 0.91
    return AgenticLensFinding(
        lens_id="adversarial_edge_cases",
        passed=not has_flaw,
        score=score,
        findings=(bundle.lens3_flaw_detected,) if has_flaw else (bundle.lens3_pass,),
        model_family=routed_family,
        model_id=routed_model_id,
        prompt_sha256=prompt_sha256,
    )


def evaluate_lens4_compliance(
    scrubbed_artifact: dict[str, Any],
    routed_family: str,
    routed_model_id: str,
    prompt_sha256: str,
    *,
    locale: str = DEFAULT_LOCALE,
) -> AgenticLensFinding:
    """Evaluate Lens 4 (`domain_and_security_compliance`)."""
    bundle = get_gate_locale_bundle(locale)
    sec_violation = bool(scrubbed_artifact.get("security_violation", False))
    score = 0.30 if sec_violation else 0.95
    return AgenticLensFinding(
        lens_id="domain_and_security_compliance",
        passed=not sec_violation,
        score=score,
        findings=(bundle.lens4_violation_detected,) if sec_violation else (bundle.lens4_pass,),
        model_family=routed_family,
        model_id=routed_model_id,
        prompt_sha256=prompt_sha256,
    )


__all__ = [
    "INDEPENDENT_LENS_IDS",
    "AgenticGateInput",
    "AgenticLensFinding",
    "AgenticLensId",
    "AtomicFactAssertion",
    "CognitiveReviewBriefing4Blocks",
    "OntologyDataClassification",
    "evaluate_lens1_transverse",
    "evaluate_lens2_facts",
    "evaluate_lens3_adversarial",
    "evaluate_lens4_compliance",
]
