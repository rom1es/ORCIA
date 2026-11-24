"""Bilingual orchestration sub-workflow YAML constants (`Story 27.7`)."""

from __future__ import annotations

FR_LEAF_YAML = """uri: "orcia://workflows/sub-verify-regression-suite"
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

EN_LEAF_YAML = """uri: "orcia://workflows/sub-verify-regression-suite"
title: "Regression Suite Verification Sub-Workflow"
description: "Runs isolated regression tests in a networkless sandbox (Depth 2)."
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
    title: "Sandbox pytest Execution"
    step_type: "SKILL"
    skill_uri: "orcia://skills/sandbox-pytest-runner@1.0.0"
    instructions: "Execute unit suite inside an isolated networkless sandbox."
    declares_intention: true
    tags:
      - "sdlc.declares_intention"
"""

FR_CHILD_YAML = """uri: "orcia://workflows/sub-remediate-and-verify"
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

EN_CHILD_YAML = """uri: "orcia://workflows/sub-remediate-and-verify"
title: "Governed Diagnosis & Fix Sub-Workflow"
description: "States remediation intent, applies the patch, and runs regression checks."
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
    title: "Fix Intent Specification"
    step_type: "AGENT"
    agent_uri: "orcia://agents/architect-investigator@1.0.0"
    template_key: "tpl-architecture-decision-record"
    instructions: "Author formal remediation intent before any code edit."
    declares_intention: true
    tags:
      - "sdlc.declares_intention"
  - step_key: "implement-code-fix"
    title: "Fix Implementation & Unit Tests"
    step_type: "AGENT"
    agent_uri: "orcia://agents/senior-dev-implementer@1.0.0"
    depends_on:
      - "declare-remediation-intent"
    instructions: "Implement the fix strictly matching the approved intent."
    tags:
      - "sdlc.writes_code"
    policies:
      - "sdlc.fr13_intention_before_code"
  - step_key: "invoke-regression-subworkflow"
    title: "Invoke Regression Sub-Workflow"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/sub-verify-regression-suite"
    depends_on:
      - "implement-code-fix"
    input_mapping:
      patch_ref: "steps.implement-code-fix.artifact"
    output_mapping:
      regression_report: "steps.run-sandbox-tests.report"
    instructions: "Delegate sandbox verification to the dedicated sub-workflow."
"""

__all__ = ["EN_CHILD_YAML", "EN_LEAF_YAML", "FR_CHILD_YAML", "FR_LEAF_YAML"]
