"""Bilingual locale bundles for orchestration engine, step executors, JIT & human anchors."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

ENGINE_STEP_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "jit_summary": "Hydratation JIT de '{step_key}' ({count} items)",
        "jit_directive": "Directive exécutée: {directive}",
        "subwf_summary": "Sous-workflow '{uri}' engagé (profondeur {depth})",
        "subwf_details": "Sorties reversées via output_mapping: {keys}",
        "fast_path_div": (
            "Divergence détectée entre source documentaire (seuil 500€) "
            "et source opérationnelle (seuil 350€)"
        ),
        "default_audit_div": (
            "Écart seuil d'exemption TRA : source documentaire v12 indique 500€ "
            "vs source opérationnelle indique 350€"
        ),
        "template_section_desc": "Synthèse rédigée de la section '{title}'.",
        "fast_path_assumption_summary": "[ASSUMPTION] Continuité d'audit en tâche de fond retenue",
        "fast_path_assumption_details": "Hypothèse appliquée sans blocage worker: {note}",
        "fast_path_div_summary": "[DIVERGENCE] Écart détecté entre sources fédérées",
    },
    "en": {
        "jit_summary": "JIT hydration of '{step_key}' ({count} items)",
        "jit_directive": "Executed directive: {directive}",
        "subwf_summary": "Sub-workflow '{uri}' started (depth {depth})",
        "subwf_details": "Mapped outputs returned via output_mapping: {keys}",
        "fast_path_div": (
            "Divergence detected between documentary source (500€ threshold) "
            "and operational source (350€ threshold)"
        ),
        "default_audit_div": (
            "TRA exemption threshold divergence: documentary source v12 states 500€ "
            "vs operational source states 350€"
        ),
        "template_section_desc": "Authored synthesis for section '{title}'.",
        "fast_path_assumption_summary": "[ASSUMPTION] Background audit continuity retained",
        "fast_path_assumption_details": "Assumption applied without blocking worker: {note}",
        "fast_path_div_summary": "[DIVERGENCE] Gap detected between federated sources",
    },
}

STEP_EXECUTOR_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "subwf_summary": "Sous-workflow '{uri}' préparé pour '{step_key}'",
        "subwf_details": "Entrées hydratées: {keys}",
        "human_artifact_done": "Décision humaine enregistrée: {decision}",
        "human_report_done": "Tâche humaine {step_key} : VALIDÉE ({decision})",
        "human_summary_done": "Tâche humaine '{step_key}' résolue ({decision})",
        "human_details_done": "Décision appliquée: {decision}",
        "human_artifact_wait": "En attente de validation humaine sur {step_key}",
        "human_summary_wait": "Tâche humaine '{step_key}' mise en pause (attente arbitrage)",
        "human_details_wait": "Directive soumise à validation humaine: {directive}",
        "post_artifact": "Vérification post-action validée pour {step_key}",
        "post_report": "Rapport de vérification {step_key} : PASS ({count} entrées)",
        "post_summary": "Vérification post-action '{step_key}' : PASS",
        "post_details": "Entrées vérifiées: {keys} | Directive: {directive}",
        "gate_artifact": "Gate Déterministe {skill_uri} : {status}",
        "gate_report": "Rapport Gate {step_key} : {status}",
        "gate_summary": "Gate Déterministe '{skill_uri}' ({status})",
        "skill_artifact": "Exécution déterministe Skill {skill_uri} pour {step_key}",
        "skill_adr": "Validation technique Skill {step_key}",
        "skill_report": "Rapport Skill {step_key} : PASS",
        "skill_summary": "Skill '{skill_uri}' exécuté sur '{step_key}'",
        "skill_details": "Directive exécutée: {directive}",
        "agent_adr": "ADR [{sha}] pour {step_key}",
        "agent_report": "Rapport Agent {step_key} : PASS ({tag})",
        "agent_summary": "Agent '{step_key}' exécuté via LLMPort ({model_id})",
        "agent_details": "Prompt SHA-256: {sha} | Sortie: {content}",
    },
    "en": {
        "subwf_summary": "Sub-workflow '{uri}' prepared for '{step_key}'",
        "subwf_details": "Hydrated inputs: {keys}",
        "human_artifact_done": "Human decision recorded: {decision}",
        "human_report_done": "Human task {step_key}: VALIDATED ({decision})",
        "human_summary_done": "Human task '{step_key}' resolved ({decision})",
        "human_details_done": "Applied decision: {decision}",
        "human_artifact_wait": "Awaiting human validation on {step_key}",
        "human_summary_wait": "Human task '{step_key}' paused (awaiting arbitration)",
        "human_details_wait": "Directive submitted for human validation: {directive}",
        "post_artifact": "Post-action verification passed for {step_key}",
        "post_report": "Verification report {step_key}: PASS ({count} entries)",
        "post_summary": "Post-action verification '{step_key}': PASS",
        "post_details": "Verified inputs: {keys} | Directive: {directive}",
        "gate_artifact": "Deterministic Gate {skill_uri}: {status}",
        "gate_report": "Gate report {step_key}: {status}",
        "gate_summary": "Deterministic Gate '{skill_uri}' ({status})",
        "skill_artifact": "Deterministic Skill execution {skill_uri} for {step_key}",
        "skill_adr": "Skill technical validation {step_key}",
        "skill_report": "Skill report {step_key}: PASS",
        "skill_summary": "Skill '{skill_uri}' executed on '{step_key}'",
        "skill_details": "Executed directive: {directive}",
        "agent_adr": "ADR [{sha}] for {step_key}",
        "agent_report": "Agent report {step_key}: PASS ({tag})",
        "agent_summary": "Agent '{step_key}' executed via LLMPort ({model_id})",
        "agent_details": "Prompt SHA-256: {sha} | Output: {content}",
    },
}

HUMAN_ANCHOR_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "axiom_summary": "Départage par axiome ontologique '{axiom_key}' -> {opt_key}",
        "axiom_details": "Option '{opt_title}' retenue formellement par l'Ontologie.",
        "assumption_summary": (
            "[ASSUMPTION] Option par défaut '{opt_key}' ({opt_title}) retenue sur '{q}'"
        ),
        "assumption_details": (
            "Politique DEFER_AND_CONTINUE_WITH_ASSUMPTION appliquée. "
            "Impact SI: {si} | FinOps: {fin}"
        ),
        "escalate_summary": "Escalade vers Arbitrage Humain : {q}",
        "escalate_details": "{count} options comparées (outbox={event_id}).",
        "resolved_summary": "Arbitrage humain tranché : {opt_key} ({opt_title})",
        "resolved_no_note": "Option validée sans note additionnelle.",
        "signed_summary": "Ancre humaine signée sur '{section_key}' ({char_len} caractères)",
        "signed_details": "SHA-256={sha} par {display_name} ({user_id})",
    },
    "en": {
        "axiom_summary": "Tie-break by ontology axiom '{axiom_key}' -> {opt_key}",
        "axiom_details": "Option '{opt_title}' formally retained by the Ontology.",
        "assumption_summary": (
            "[ASSUMPTION] Default option '{opt_key}' ({opt_title}) retained on '{q}'"
        ),
        "assumption_details": (
            "DEFER_AND_CONTINUE_WITH_ASSUMPTION policy applied. SI impact: {si} | FinOps: {fin}"
        ),
        "escalate_summary": "Escalated to Human Arbitration: {q}",
        "escalate_details": "{count} options compared (outbox={event_id}).",
        "resolved_summary": "Human arbitration decided: {opt_key} ({opt_title})",
        "resolved_no_note": "Option validated without additional note.",
        "signed_summary": "Human anchor signed on '{section_key}' ({char_len} characters)",
        "signed_details": "SHA-256={sha} by {display_name} ({user_id})",
    },
}


def get_ops_copy(
    table: dict[SupportedLocale, dict[str, str]],
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> dict[str, str]:
    return table.get(locale, table[DEFAULT_LOCALE])


__all__ = [
    "ENGINE_STEP_LOCALES",
    "HUMAN_ANCHOR_LOCALES",
    "STEP_EXECUTOR_LOCALES",
    "get_ops_copy",
]
