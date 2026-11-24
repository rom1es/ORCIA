"""Bilingual locale bundles for Workflow YAML/JSON loader and validator (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

YAML_VALIDATION_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "empty_manifest": "Le manifeste Workflow-as-Code YAML/JSON est vide.",
        "syntax_error": "Erreur de syntaxe YAML/JSON à la ligne {line}: {exc}",
        "root_mapping": "La racine du manifeste doit être un objet YAML/JSON.",
        "step_object": "Chaque étape doit être un objet YAML/JSON.",
        "step_key_required": "Le champ 'step_key' est obligatoire sur chaque étape.",
        "step_key_unique": "Doublon d'identifiant d'étape '{step_key}' à la ligne {line}.",
        "invalid_step_type": "Type d'étape invalide '{step_type}'.",
        "subwf_uri_required": "L'étape SUB_WORKFLOW '{step_key}' exige 'sub_workflow_uri'.",
        "bounded_retries": "Le champ 'max_agent_retries' doit être borné entre 1 et 10.",
        "unknown_policy": (
            "Ligne {line}: Politique de workflow inconnue '{policy}' sur l'étape '{step_key}'."
        ),
        "steps_non_empty": "Le manifeste doit contenir au moins une étape dans 'steps'.",
        "unknown_dep": "L'étape '{step_key}' dépend de '{dep}' introuvable.",
        "unknown_feedback": (
            "La boucle de rétroaction de '{step_key}' cible '{target}' introuvable."
        ),
        "dag_cycle": "Cycle de dépendances détecté à la ligne {line} impliquant: {keys}.",
        "subwf_cycle": "Ligne {line}: Cycle d'appels SUB_WORKFLOW détecté: {chain}.",
        "subwf_depth": "Ligne {line}: Profondeur SUB_WORKFLOW {depth} > {max_depth} pour '{uri}'.",
        "valid_uri_required": "Le champ 'uri' doit être une URI canonique valide.",
        "title_required": "Le champ 'title' est obligatoire.",
        "invalid_criticality": "Criticité invalide '{value}'.",
        "invalid_regime": "Régime d'exécution invalide '{value}'.",
        "invalid_tie_break": "Politique de départage invalide '{value}'.",
        "invalid_mode": "Mode invalide '{value}'.",
        "invalid_gate_policy": "Politique de Gate adaptative invalide '{value}'.",
        "unknown_root_policy": "Politique de workflow inconnue '{policy}'.",
        "high_critical_autonomous": (
            "Ligne {line}: Un workflow HIGH_CRITICAL ne peut pas utiliser "
            "execution_regime: AUTONOMOUS_CONTRACT (FR-29, AD-18)."
        ),
        "high_critical_gate": "Tout workflow HIGH_CRITICAL exige au moins une Gate/Ancre Humaine.",
    },
    "en": {
        "empty_manifest": "Workflow-as-Code YAML/JSON manifest is empty.",
        "syntax_error": "YAML/JSON syntax error on line {line}: {exc}",
        "root_mapping": "Manifest root must be a YAML/JSON mapping object.",
        "step_object": "Each step must be a YAML/JSON mapping object.",
        "step_key_required": "Field 'step_key' is required on every step.",
        "step_key_unique": "Duplicate step identifier '{step_key}' on line {line}.",
        "invalid_step_type": "Invalid step type '{step_type}'.",
        "subwf_uri_required": "SUB_WORKFLOW step '{step_key}' requires 'sub_workflow_uri'.",
        "bounded_retries": "Field 'max_agent_retries' must be bounded between 1 and 10.",
        "unknown_policy": "Line {line}: Unknown workflow policy '{policy}' on step '{step_key}'.",
        "steps_non_empty": "Manifest must define at least one step in 'steps'.",
        "unknown_dep": "Step '{step_key}' depends on unknown step '{dep}'.",
        "unknown_feedback": "Feedback loop from '{step_key}' targets unknown step '{target}'.",
        "dag_cycle": "Dependency cycle detected on line {line} involving: {keys}.",
        "subwf_cycle": "Line {line}: SUB_WORKFLOW call cycle detected: {chain}.",
        "subwf_depth": "Line {line}: SUB_WORKFLOW nesting depth {depth} > {max_depth} for '{uri}'.",
        "valid_uri_required": "Field 'uri' must be a valid canonical URI.",
        "title_required": "Field 'title' is required.",
        "invalid_criticality": "Invalid criticality '{value}'.",
        "invalid_regime": "Invalid execution regime '{value}'.",
        "invalid_tie_break": "Invalid tie-break policy '{value}'.",
        "invalid_mode": "Invalid mode '{value}'.",
        "invalid_gate_policy": "Invalid adaptive gate policy '{value}'.",
        "unknown_root_policy": "Unknown workflow policy '{policy}'.",
        "high_critical_autonomous": (
            "Line {line}: A HIGH_CRITICAL workflow cannot use "
            "execution_regime: AUTONOMOUS_CONTRACT (FR-29, AD-18)."
        ),
        "high_critical_gate": (
            "Every HIGH_CRITICAL workflow requires at least one Human Gate or Anchor."
        ),
    },
}


def get_yaml_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return YAML_VALIDATION_LOCALES.get(locale, YAML_VALIDATION_LOCALES[DEFAULT_LOCALE])


__all__ = ["YAML_VALIDATION_LOCALES", "get_yaml_copy"]
