"""Bilingual FR/EN locale bundle for Agentic and Human Gate outputs (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class GateLocaleBundle:
    """Localized strings for Agentic and Human Gate evaluation outputs."""

    lens1_forbidden_tpl: str
    lens1_required_tpl: str
    lens1_pass: str
    lens2_axiom_contradiction_tpl: str
    lens2_low_confidence_tpl: str
    lens2_fact_verified: str
    lens2_fact_failed: str
    lens2_no_contradiction: str
    lens2_assertions_verified_tpl: str
    lens3_flaw_detected: str
    lens3_pass: str
    lens4_violation_detected: str
    lens4_pass: str
    default_decision: str
    default_assumption: str
    step_review_summary_tpl: str
    synthesis_consolidated: str
    human_block1_title: str
    human_block1_summary_tpl: str
    human_block2_title: str
    human_block3_title: str
    human_block3_default_decision: str
    human_block4_title: str
    human_block4_default_hypothesis: str
    human_default_section_title: str
    human_default_challenge_reason: str


GATE_LOCALES: dict[SupportedLocale, GateLocaleBundle] = {
    "fr": GateLocaleBundle(
        lens1_forbidden_tpl="Contradiction transverse : terme interdit '{term}' présent.",
        lens1_required_tpl="Exigence amont Step 1/2 manquante : '{term}' absent de l'artefact.",
        lens1_pass=(
            "Alignement transverse conforme aux invariants Step 1 (Cadrage) et Step 2 (Arch)."
        ),
        lens2_axiom_contradiction_tpl=(
            "Assertion #{idx} contredit l'axiome ontologique '{onto_key}'."
        ),
        lens2_low_confidence_tpl=(
            "Assertion #{idx} sous le seuil de confiance ({conf:.2f} < {threshold:.2f})."
        ),
        lens2_fact_verified="Vérifié contre l'Ontologie N1..N4 et les KBs épinglées.",
        lens2_fact_failed="Confiance insuffisante ou contradiction ontologique.",
        lens2_no_contradiction="Aucune contradiction détectée avec l'Ontologie et les KBs.",
        lens2_assertions_verified_tpl=(
            "{count} assertion(s) atomique(s) vérifiée(s) au-dessus du seuil."
        ),
        lens3_flaw_detected="Vulnérabilité adversariale ou cas limite non géré détecté.",
        lens3_pass="Cas limites d'idempotence, de concurrence et de bornes vérifiés.",
        lens4_violation_detected="Non-conformité sécurité/domaine détectée.",
        lens4_pass="Conformité domaine et garde-fous de sécurité validés (NFR-SEC-2/4).",
        default_decision="Architecture modulaire et contrats d'interface validés.",
        default_assumption=(
            "Hypothèse nominale de fraîcheur des sources épinglées dans run-lock.json."
        ),
        step_review_summary_tpl="Synthèse de revue de l'étape {step_key}",
        synthesis_consolidated="Briefing de revue en 4 blocs consolidé à partir des 4 lentilles.",
        human_block1_title="1. Résumé Exécutif",
        human_block1_summary_tpl="Synthèse de l'étape {step_key} ({chunk_count} sections).",
        human_block2_title="2. Éléments Clés & Contrôle Transverse",
        human_block3_title="3. Décisions Prises",
        human_block3_default_decision="Validation structurelle",
        human_block4_title="4. Hypothèses Retenues",
        human_block4_default_hypothesis=(
            "Les contraintes amont du Cadrage et de l'Ontologie sont respectées."
        ),
        human_default_section_title="Section principale",
        human_default_challenge_reason="Section contestée vers l'étape amont.",
    ),
    "en": GateLocaleBundle(
        lens1_forbidden_tpl="Cross-cutting contradiction: forbidden term '{term}' present.",
        lens1_required_tpl="Missing upstream Step 1/2 requirement: '{term}' absent from artifact.",
        lens1_pass="Cross-cutting alignment complies with Step 1 (Framing) and Step 2 (Arch).",
        lens2_axiom_contradiction_tpl=("Assertion #{idx} contradicts ontology axiom '{onto_key}'."),
        lens2_low_confidence_tpl=(
            "Assertion #{idx} below confidence threshold ({conf:.2f} < {threshold:.2f})."
        ),
        lens2_fact_verified="Verified against Ontology N1..N4 and pinned knowledge bases.",
        lens2_fact_failed="Insufficient confidence or ontology contradiction.",
        lens2_no_contradiction="No contradiction detected with Ontology and knowledge bases.",
        lens2_assertions_verified_tpl="{count} atomic assertion(s) verified above threshold.",
        lens3_flaw_detected="Adversarial vulnerability or unhandled edge case detected.",
        lens3_pass="Idempotency, concurrency, and boundary edge cases verified.",
        lens4_violation_detected="Security or domain compliance violation detected.",
        lens4_pass="Domain compliance and security guardrails validated (NFR-SEC-2/4).",
        default_decision="Modular architecture and interface contracts validated.",
        default_assumption="Nominal freshness assumption for sources pinned in run-lock.json.",
        step_review_summary_tpl="Review synthesis for step {step_key}",
        synthesis_consolidated="4-block review briefing consolidated from the 4 lenses.",
        human_block1_title="1. Executive Summary",
        human_block1_summary_tpl="Summary of step {step_key} ({chunk_count} sections).",
        human_block2_title="2. Key Elements & Cross-Cutting Check",
        human_block3_title="3. Decisions Taken",
        human_block3_default_decision="Structural validation",
        human_block4_title="4. Retained Hypotheses",
        human_block4_default_hypothesis=(
            "Upstream Framing and Ontology constraints are satisfied."
        ),
        human_default_section_title="Main section",
        human_default_challenge_reason="Section challenged back to the upstream step.",
    ),
}


def get_gate_locale_bundle(locale: str = DEFAULT_LOCALE) -> GateLocaleBundle:
    """Return the localized `GateLocaleBundle` (`en` or `fr`, defaulting to `fr`)."""
    norm = (locale or DEFAULT_LOCALE).strip().lower()
    return GATE_LOCALES["en"] if norm.startswith("en") else GATE_LOCALES["fr"]


__all__ = ["GATE_LOCALES", "GateLocaleBundle", "get_gate_locale_bundle"]
