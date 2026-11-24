"""Bootstrap reference templates & workflow manifests (`DEC-SEED-01`, `AD-16`, `AD-20`).

Centralizes reference workflow YAML definitions and template seeds inside `bootstrap` so that
domain modules (`orchestration`, `rag`) contain zero demo datasets (`AD-20` Rule 5).
Zero imports from `orcia_core.orchestration` (`AD-19` Contract 2).
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.bootstrap._bootstrap_orchestration_locales import (
    get_bootstrap_orchestration_seed_copy,
)

_FR_COPY = get_bootstrap_orchestration_seed_copy("fr")
DEFAULT_LEAF_SUB_WORKFLOW_YAML = _FR_COPY.leaf_sub_workflow_yaml
DEFAULT_CHILD_SUB_WORKFLOW_YAML = _FR_COPY.child_sub_workflow_yaml
DEFAULT_ROOT_WORKFLOW_YAML = _FR_COPY.root_workflow_yaml

DEFAULT_FOLDER_PILOT_WORKFLOW_YAML = """uri: "orcia://pack-sdlc/workflows/ticket-to-tech-spec"
title: "Pilot Process: Folder & Request to Governed Specification"
description: "Three-step governed pilot workflow with mandatory human anchor and verification."
version: "1.0.0"
criticality: "HIGH_CRITICAL"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
adaptive_gate_policy: "STRICT"
max_cost_usd: 10.0
datasources:
  - "git://claims/core-engine@main"
steps:
  - step_key: "frame-spec-human-anchor"
    title: "Human Intent & Anchor Framing"
    step_type: "AGENT"
    agent_uri: "orcia://agents/product-architect@1.0.0"
    template_key: "tpl-architecture-decision-record"
    instructions: "Author and sign the mandatory human intent anchor before downstream synthesis."
    human_authored_required: true
    requires_human_gate: true
    declares_intention: true
  - step_key: "synthesize-spec-artifact"
    title: "Synthesize Governed Specification"
    step_type: "AGENT"
    agent_uri: "orcia://agents/architect-investigator@1.0.0"
    depends_on:
      - "frame-spec-human-anchor"
    instructions: "Generate governed specification bound to the signed human anchor."
  - step_key: "post-spec-verification"
    title: "Post-Specification Verification"
    step_type: "POST_ACTION_VERIFICATION"
    depends_on:
      - "synthesize-spec-artifact"
    verification_window_seconds: 120
    instructions: "Verify specification invariants after generation."
"""


@dataclass(frozen=True, slots=True)
class BootstrapTemplateSectionSeed:
    """Section definition inside a reference bootstrap Artifact Template (`DEC-SEED-01`)."""

    section_key: str
    title: str
    markdown_body_template: str
    ontology_concept_term: str | None = None
    human_authored_required: bool = False
    mandatory: bool = True
    max_words_chunk: int = 600


@dataclass(frozen=True, slots=True)
class BootstrapTemplateSeed:
    """Reference Multi-Audience Artifact Template seed (`DEC-SEED-01`)."""

    template_key: str
    uri: str
    title: str
    version: str
    description: str
    required_variables: tuple[str, ...]
    sections: tuple[BootstrapTemplateSectionSeed, ...]


DEFAULT_ADR_TEMPLATE_SEED = BootstrapTemplateSeed(
    template_key="tpl-architecture-decision-record",
    uri="orcia://templates/tpl-architecture-decision-record@1.0.0",
    title=_FR_COPY.adr_title,
    version="1.0.0",
    description=_FR_COPY.adr_description,
    required_variables=("project_name", "jira_key"),
    sections=(
        BootstrapTemplateSectionSeed(
            section_key="human_architecture_intent",
            title=_FR_COPY.sec1_title,
            markdown_body_template=_FR_COPY.sec1_body,
            ontology_concept_term=_FR_COPY.sec1_concept,
            human_authored_required=True,
            mandatory=True,
            max_words_chunk=400,
        ),
        BootstrapTemplateSectionSeed(
            section_key="loss_event_specification",
            title=_FR_COPY.sec2_title,
            markdown_body_template=_FR_COPY.sec2_body,
            ontology_concept_term=_FR_COPY.sec2_concept,
            human_authored_required=False,
            mandatory=True,
            max_words_chunk=400,
        ),
    ),
)

__all__ = [
    "BootstrapTemplateSectionSeed",
    "BootstrapTemplateSeed",
    "DEFAULT_ADR_TEMPLATE_SEED",
    "DEFAULT_CHILD_SUB_WORKFLOW_YAML",
    "DEFAULT_FOLDER_PILOT_WORKFLOW_YAML",
    "DEFAULT_LEAF_SUB_WORKFLOW_YAML",
    "DEFAULT_ROOT_WORKFLOW_YAML",
]
