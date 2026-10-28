"""Bootstrap reference templates & workflow manifests (`DEC-SEED-01`, `AD-16`, `AD-20`).

Centralizes reference workflow YAML definitions and template seeds inside `bootstrap` so that
domain modules (`orchestration`, `rag`) contain zero demo datasets (`AD-20` Rule 5).
Zero imports from `orcia_core.orchestration` (`AD-19` Contract 2).
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LEAF_SUB_WORKFLOW_YAML = """uri: "orcia://workflows/sub-verify-regression-suite"
title: "Sous-Workflow Vérification Suite de Non-Régression"
description: "Exécute les tests de non-régression isolés en sandbox (Profondeur 2)."
version: "1.1.0"
criticality: "LOW_NON_CRITICAL"
execution_regime: "AUTONOMOUS_CONTRACT"
tie_break_policy: "ONTOLOGY_AXIOM_FIRST"
mode: "standard"
max_cost_usd: 2.5
datasources:
  - "git://claims/core-engine@main"
steps:
  - step_key: "run-sandbox-tests"
    title: "Exécution Sandbox pytest"
    step_type: "SKILL"
    skill_uri: "orcia://skills/sandbox-pytest-runner@1.0.0"
    instructions: "Exécuter la suite unitaire en sandbox isolée sans réseau."
    declares_intention: true
    tags:
      - "sdlc.declares_intention"
"""

DEFAULT_CHILD_SUB_WORKFLOW_YAML = """uri: "orcia://workflows/sub-remediate-and-verify"
title: "Sous-Workflow Diagnostic & Correctif Gouverné"
description: "Formule l'intention de remédiation, applique le patch et appelle la vérification."
version: "1.2.0"
criticality: "STANDARD"
execution_regime: "BACKGROUND_FAST_PATH"
tie_break_policy: "ONTOLOGY_AXIOM_FIRST"
mode: "standard"
max_cost_usd: 5.0
datasources:
  - "git://claims/core-engine@main"
steps:
  - step_key: "declare-remediation-intent"
    title: "Spécification de l'Intention de Correctif"
    step_type: "AGENT"
    agent_uri: "orcia://agents/architect-investigator@1.0.0"
    template_key: "tpl-architecture-decision-record"
    instructions: "Rédiger l'intention formelle du correctif avant toute modification de code."
    declares_intention: true
    tags:
      - "sdlc.declares_intention"
  - step_key: "implement-code-fix"
    title: "Implémentation du Correctif & Tests Unitaires"
    step_type: "AGENT"
    agent_uri: "orcia://agents/senior-dev-implementer@1.0.0"
    depends_on:
      - "declare-remediation-intent"
    instructions: "Implémenter le correctif conformément à l'intention validée."
    tags:
      - "sdlc.writes_code"
    policies:
      - "sdlc.fr13_intention_before_code"
  - step_key: "invoke-regression-subworkflow"
    title: "Appel Sous-Workflow de Non-Régression"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/sub-verify-regression-suite"
    depends_on:
      - "implement-code-fix"
    input_mapping:
      patch_ref: "steps.implement-code-fix.artifact"
    output_mapping:
      regression_report: "steps.run-sandbox-tests.report"
    instructions: "Déléguer la vérification sandbox au sous-workflow dédié."
"""

DEFAULT_ROOT_WORKFLOW_YAML = """uri: "orcia://workflows/claims-engineering-delivery"
title: "Workflow Gouverné Ingénierie & Livraison Sinistres (Intention -> Code)"
description: "Processus maître combinant Ancre Humaine, Sous-Workflow fractal (<= 3) et Gate."
version: "2.0.0"
criticality: "HIGH_CRITICAL"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
adaptive_gate_policy: "STRICT"
max_cost_usd: 15.0
datasources:
  - "git://claims/core-engine@main"
  - "confluence://CLAIMS/pages/101-spec-seuil-validation@v12"
steps:
  - step_key: "frame-architecture-intent"
    title: "Cadrage d'Intention & Ancre Humaine"
    step_type: "AGENT"
    agent_uri: "orcia://agents/product-architect@1.0.0"
    template_key: "tpl-architecture-decision-record"
    instructions: "Structurer l'intention d'architecture avec section humaine obligatoire."
    human_authored_required: true
    requires_human_gate: true
    declares_intention: true
    tags:
      - "sdlc.declares_intention"
  - step_key: "delegate-remediation-subworkflow"
    title: "Sous-Workflow Implémentation & Vérification"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/sub-remediate-and-verify"
    depends_on:
      - "frame-architecture-intent"
    input_mapping:
      architecture_intent: "steps.frame-architecture-intent.adr"
    output_mapping:
      verified_patch: "steps.invoke-regression-subworkflow.regression_report"
    instructions: "Exécuter le sous-workflow de remédiation et vérification."
  - step_key: "post-deploy-verification"
    title: "Vérification Post-Action du Puits de Logs"
    step_type: "POST_ACTION_VERIFICATION"
    depends_on:
      - "delegate-remediation-subworkflow"
    verification_window_seconds: 300
    instructions: "Observer le puits de logs après déploiement pour confirmer zéro régression."
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
    title="Gabarit Multi-Audience — Décision d'Architecture & Risque Sinistre",
    version="1.0.0",
    description="Double vue : Document Markdown Humain + JSON Schema typé par l'Ontologie.",
    required_variables=("project_name", "jira_key"),
    sections=(
        BootstrapTemplateSectionSeed(
            section_key="human_architecture_intent",
            title="1. Intention Stratégique & Arbitrage Humain",
            markdown_body_template=(
                "Intention directrice pour **{{ project_name }}** (Ticket `{{ jira_key }}`) : "
                "définir les invariants non négociables avant toute génération de code."
            ),
            ontology_concept_term="Actif Stratégique",
            human_authored_required=True,
            mandatory=True,
            max_words_chunk=400,
        ),
        BootstrapTemplateSectionSeed(
            section_key="loss_event_specification",
            title="2. Spécification Technique & Contrat Ontologique",
            markdown_body_template=(
                "Spécification formelle du flux **{{ project_name }}** liée à `{{ jira_key }}` "
                "et soumise à validation automatisée."
            ),
            ontology_concept_term="Clé d'Idempotence Paiement",
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
    "DEFAULT_LEAF_SUB_WORKFLOW_YAML",
    "DEFAULT_ROOT_WORKFLOW_YAML",
]
