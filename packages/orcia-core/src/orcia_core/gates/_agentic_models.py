"""Dataclasses and type aliases for the 5-Lens Agentic Gate (`AD-10`, `Story 4.2`)."""

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
    evaluator_model_id: str
    candidate_artifact: dict[str, Any]
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
