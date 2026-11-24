"""Bilingual orchestration workflow & ADR template seed bundles (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.bootstrap._bootstrap_orchestration_yaml_locales import (
    EN_CHILD_YAML,
    EN_LEAF_YAML,
    FR_CHILD_YAML,
    FR_LEAF_YAML,
)
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class BootstrapOrchestrationSeedCopy:
    """Localized bootstrap YAML workflow & ADR template copy."""

    leaf_sub_workflow_yaml: str
    child_sub_workflow_yaml: str
    root_workflow_yaml: str
    adr_title: str
    adr_description: str
    sec1_title: str
    sec1_body: str
    sec1_concept: str
    sec2_title: str
    sec2_body: str
    sec2_concept: str


_FR_ROOT_HEADER = """uri: "orcia://workflows/claims-engineering-delivery"
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

_EN_ROOT_HEADER = """uri: "orcia://workflows/claims-engineering-delivery"
title: "Governed Claims Engineering & Delivery Workflow (Intent -> Code)"
description: "Master process combining Human Anchor, fractal Sub-Workflow (<= 3), and Gate."
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
    title: "Intent Framing & Human Anchor"
    step_type: "AGENT"
    agent_uri: "orcia://agents/product-architect@1.0.0"
    template_key: "tpl-architecture-decision-record"
    instructions: "Structure architectural intent with a mandatory human-authored section."
    human_authored_required: true
    requires_human_gate: true
    declares_intention: true
    tags:
      - "sdlc.declares_intention"
  - step_key: "delegate-remediation-subworkflow"
    title: "Implementation & Verification Sub-Workflow"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/sub-remediate-and-verify"
    depends_on:
      - "frame-architecture-intent"
    input_mapping:
      architecture_intent: "steps.frame-architecture-intent.adr"
    output_mapping:
      verified_patch: "steps.invoke-regression-subworkflow.regression_report"
    instructions: "Execute remediation and verification sub-workflow."
  - step_key: "post-deploy-verification"
    title: "Post-Action Log Sink Verification"
    step_type: "POST_ACTION_VERIFICATION"
    depends_on:
      - "delegate-remediation-subworkflow"
    verification_window_seconds: 300
    instructions: "Monitor the log sink after deployment to confirm zero regression."
"""

BOOTSTRAP_ORCHESTRATION_SEED_LOCALES: dict[SupportedLocale, BootstrapOrchestrationSeedCopy] = {
    "fr": BootstrapOrchestrationSeedCopy(
        leaf_sub_workflow_yaml=FR_LEAF_YAML,
        child_sub_workflow_yaml=FR_CHILD_YAML,
        root_workflow_yaml=_FR_ROOT_HEADER,
        adr_title="Gabarit Multi-Audience — Décision d'Architecture & Risque Sinistre",
        adr_description="Double vue : Document Markdown Humain + JSON Schema typé par l'Ontologie.",
        sec1_title="1. Intention Stratégique & Arbitrage Humain",
        sec1_body=(
            "Intention directrice pour **{{ project_name }}** (Ticket `{{ jira_key }}`) : "
            "définir les invariants non négociables avant toute génération de code."
        ),
        sec1_concept="Actif Stratégique",
        sec2_title="2. Spécification Technique & Contrat Ontologique",
        sec2_body=(
            "Spécification formelle du flux **{{ project_name }}** liée à `{{ jira_key }}` "
            "et soumise à validation automatisée."
        ),
        sec2_concept="Clé d'Idempotence Paiement",
    ),
    "en": BootstrapOrchestrationSeedCopy(
        leaf_sub_workflow_yaml=EN_LEAF_YAML,
        child_sub_workflow_yaml=EN_CHILD_YAML,
        root_workflow_yaml=_EN_ROOT_HEADER,
        adr_title="Multi-Audience Template — Architecture Decision & Claim Risk",
        adr_description="Dual view: Human Markdown Document + Ontology-typed JSON Schema.",
        sec1_title="1. Strategic Intent & Human Arbitration",
        sec1_body=(
            "Guiding intent for **{{ project_name }}** (Ticket `{{ jira_key }}`): "
            "define non-negotiable invariants before any code generation."
        ),
        sec1_concept="Strategic Asset",
        sec2_title="2. Technical Specification & Ontology Contract",
        sec2_body=(
            "Formal flow specification for **{{ project_name }}** linked to `{{ jira_key }}` "
            "and subject to automated gate validation."
        ),
        sec2_concept="Payment Idempotency Key",
    ),
}


def get_bootstrap_orchestration_seed_copy(
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> BootstrapOrchestrationSeedCopy:
    """Return localized orchestration seed manifests and template strings."""
    return BOOTSTRAP_ORCHESTRATION_SEED_LOCALES.get(
        locale, BOOTSTRAP_ORCHESTRATION_SEED_LOCALES[DEFAULT_LOCALE]
    )


__all__ = [
    "BOOTSTRAP_ORCHESTRATION_SEED_LOCALES",
    "BootstrapOrchestrationSeedCopy",
    "get_bootstrap_orchestration_seed_copy",
]
