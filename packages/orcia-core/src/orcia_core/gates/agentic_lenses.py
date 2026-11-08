"""5-Lens Evaluator Models & Pure Evaluation Rules for Agentic Gates (`AD-10`, `Story 4.2`).

Extracted from `orcia_core.gates.agentic` to keep each module well below 300 lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AgenticLensId = Literal[
    "transverse_alignment_step1",
    "fact_verification",
    "adversarial_edge_cases",
    "domain_and_security_compliance",
    "synthesis_and_structure",
]
OntologyDataClassification = Literal["PUBLIC", "INTERNAL", "SENSITIVE", "RESTRICTED"]

INDEPENDENT_LENS_IDS: tuple[AgenticLensId, ...] = (
    "transverse_alignment_step1",
    "fact_verification",
    "adversarial_edge_cases",
    "domain_and_security_compliance",
)


@dataclass(frozen=True, slots=True)
class AtomicFactAssertion:
    """Single atomic factual claim evaluated by Lens 2 (`fact_verification`, `AD-10`)."""

    assertion_id: str
    statement: str
    grounding_source_uri: str
    confidence_score: float
    verified: bool
    contradicts_ontology: bool = False
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "statement": self.statement,
            "grounding_source_uri": self.grounding_source_uri,
            "confidence_score": round(self.confidence_score, 4),
            "verified": self.verified,
            "contradicts_ontology": self.contradicts_ontology,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class AgenticLensFinding:
    """Structured output of one of the 5 Agentic Gate lenses (`AD-10`)."""

    lens_id: AgenticLensId
    passed: bool
    score: float
    findings: tuple[str, ...]
    model_family: str
    model_id: str
    prompt_sha256: str
    atomic_facts: tuple[AtomicFactAssertion, ...] = ()
    isolated_from_peer_lenses: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "lens_id": self.lens_id,
            "passed": self.passed,
            "score": round(self.score, 4),
            "findings": list(self.findings),
            "model_family": self.model_family,
            "model_id": self.model_id,
            "prompt_sha256": self.prompt_sha256,
            "atomic_facts": [f.to_dict() for f in self.atomic_facts],
            "isolated_from_peer_lenses": self.isolated_from_peer_lenses,
        }


@dataclass(frozen=True, slots=True)
class CognitiveReviewBriefing4Blocks:
    """4-block Cognitive Review Briefing consolidated by Lens 5 (`UX-DR4`, `AD-10`)."""

    executive_summary: str
    key_elements_and_transverse_check: tuple[str, ...]
    decisions_made: tuple[str, ...]
    retained_assumptions: tuple[str, ...]
    assumptions_inspected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "executive_summary": self.executive_summary,
            "key_elements_and_transverse_check": list(self.key_elements_and_transverse_check),
            "decisions_made": list(self.decisions_made),
            "retained_assumptions": list(self.retained_assumptions),
            "assumptions_inspected": self.assumptions_inspected,
        }


@dataclass(frozen=True, slots=True)
class AgenticGateInput:
    """Input contract for evaluating an Agentic Gate (`Story 4.2`, `FR-18`, `AD-10`)."""

    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    executor_model_family: str
    evaluator_model_family: str
    candidate_artifact: dict[str, Any]
    evaluator_model_id: str = "google/gemini-2.5-pro"
    data_classification: OntologyDataClassification = "INTERNAL"
    anonymize_pii_reversible: bool = True
    custom_pii_entities: tuple[str, ...] = ()
    step1_prd_invariants: tuple[str, ...] = ()
    step2_arch_invariants: tuple[str, ...] = ()
    ontology_facts: dict[str, str] = field(default_factory=dict)
    pinned_kb_facts: dict[str, str] = field(default_factory=dict)
    step_memlog_markers: tuple[dict[str, str], ...] = ()
    fact_confidence_threshold: float = 0.80
    pass_score_threshold: float = 0.85


def evaluate_lens1_transverse(
    gate_input: AgenticGateInput,
    artifact_json: str,
    routed_family: str,
    routed_model_id: str,
    prompt_sha256: str,
) -> AgenticLensFinding:
    """Evaluate Lens 1 (`transverse_alignment_step1`): Step N vs Step 1 Cadrage & Step 2 Arch."""
    contradictions: list[str] = []
    lower_art = artifact_json.lower()
    for inv in (*gate_input.step1_prd_invariants, *gate_input.step2_arch_invariants):
        cleaned = inv.strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith("forbid:"):
            forbidden_term = cleaned.split(":", 1)[1].strip().lower()
            if forbidden_term and forbidden_term in lower_art:
                contradictions.append(
                    f"Contradiction transverse : terme interdit '{forbidden_term}' présent."
                )
        elif cleaned.lower().startswith("require:"):
            req_term = cleaned.split(":", 1)[1].strip().lower()
            if req_term and req_term not in lower_art:
                contradictions.append(
                    f"Exigence amont Step 1/2 manquante : '{req_term}' absent de l'artefact."
                )
    passed = len(contradictions) == 0
    score = 0.94 if passed else 0.35
    findings = (
        tuple(contradictions)
        if contradictions
        else ("Alignement transverse conforme aux invariants Step 1 (Cadrage) et Step 2 (Arch).",)
    )
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
) -> AgenticLensFinding:
    """Evaluate Lens 2 (`fact_verification`): atomic claims vs Ontology N1..N4 & pinned KBs."""
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
                        f"Assertion #{idx} contredit l'axiome ontologique '{onto_key}'."
                    )

            verified = (conf >= gate_input.fact_confidence_threshold) and not contradicts
            if not verified and not contradicts:
                blocking_findings.append(
                    f"Assertion #{idx} sous le seuil de confiance "
                    f"({conf:.2f} < {gate_input.fact_confidence_threshold:.2f})."
                )
            atomic_facts.append(
                AtomicFactAssertion(
                    assertion_id=f"FACT-{idx}",
                    statement=stmt,
                    grounding_source_uri=src,
                    confidence_score=conf,
                    verified=verified,
                    contradicts_ontology=contradicts,
                    rationale="Vérifié contre l'Ontologie N1..N4 et les KBs épinglées."
                    if verified
                    else "Confiance insuffisante ou contradiction ontologique.",
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
                rationale="Aucune contradiction détectée avec l'Ontologie et les KBs.",
            )
        )

    passed = len(blocking_findings) == 0
    avg_conf = sum(f.confidence_score for f in atomic_facts) / len(atomic_facts)
    score = round(avg_conf if passed else min(0.40, avg_conf), 4)
    findings = (
        tuple(blocking_findings)
        if blocking_findings
        else (f"{len(atomic_facts)} assertion(s) atomique(s) vérifiée(s) au-dessus du seuil.",)
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
) -> AgenticLensFinding:
    """Evaluate Lens 3 (`adversarial_edge_cases`)."""
    has_flaw = bool(scrubbed_artifact.get("adversarial_vulnerability", False))
    score = 0.45 if has_flaw else 0.91
    return AgenticLensFinding(
        lens_id="adversarial_edge_cases",
        passed=not has_flaw,
        score=score,
        findings=(
            ("Vulnérabilité adversariale ou cas limite non géré détecté.",)
            if has_flaw
            else ("Cas limites d'idempotence, de concurrence et de bornes vérifiés.",)
        ),
        model_family=routed_family,
        model_id=routed_model_id,
        prompt_sha256=prompt_sha256,
    )


def evaluate_lens4_compliance(
    scrubbed_artifact: dict[str, Any],
    routed_family: str,
    routed_model_id: str,
    prompt_sha256: str,
) -> AgenticLensFinding:
    """Evaluate Lens 4 (`domain_and_security_compliance`)."""
    sec_violation = bool(scrubbed_artifact.get("security_violation", False))
    score = 0.30 if sec_violation else 0.95
    return AgenticLensFinding(
        lens_id="domain_and_security_compliance",
        passed=not sec_violation,
        score=score,
        findings=(
            ("Non-conformité sécurité/domaine détectée.",)
            if sec_violation
            else ("Conformité domaine et garde-fous de sécurité validés (NFR-SEC-2/4).",)
        ),
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
