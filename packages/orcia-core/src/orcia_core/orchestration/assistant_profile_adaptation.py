"""Profile Adaptation & Constitutional Prompt Layer Sanitizers (`Story 3.3`, `Story 26.2`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from orcia_core.orchestration.assistant_prompt_locales import (
    CONSTITUTIONAL_LAYER_1_TEXT_EN,
    CONSTITUTIONAL_LAYER_1_TEXT_FR,
)

AssistantLayerId = Literal[
    "1_CONSTITUTIONAL_IMMUTABLE",
    "2_ONTOLOGY_AND_AXIOMS_L1_L4",
    "3_HUMAN_PROFILE_ADAPTATION",
    "4_FEDERATED_CONTEXT_FANOUT",
    "5_CONVERSATIONAL_INTENT_AND_COMPOSER",
]

AssistantIntentKind = Literal[
    "QA_COACHING",
    "WORKFLOW_COMPOSE",
    "WORKFLOW_MODIFY",
    "WORKFLOW_LAUNCH",
    "HUMAN_ANCHOR_WRITE_REFUSAL",
]

CONSTITUTIONAL_LAYER_1_TEXT: str = CONSTITUTIONAL_LAYER_1_TEXT_FR

_LAYER_OR_CONSTITUTIONAL_TAG_RE = re.compile(
    r"\[((?:LAYER|CONSTITUTIONAL|ONTOLOGY|HUMAN_PROFILE|ADAPTATION)(?:[_\s]+[^\]]*)?)\]",
    re.IGNORECASE,
)


def sanitize_layer_marker_tags(text: str | None) -> str:
    """Escape `[LAYER_*]` and `[CONSTITUTIONAL_*]` marker tags in untrusted text."""
    if not text:
        return ""
    return _LAYER_OR_CONSTITUTIONAL_TAG_RE.sub(r"(escaped:\1)", text.strip())


@dataclass(frozen=True, slots=True)
class ProfileAdaptationSpec:
    """Semantic adaptation descriptor for a `HumanProfileArchetype` (`FR-1`, `UX-DR12`)."""

    archetype: str
    register_label: str
    vocabulary_tier: Literal[
        "N1_N2_EXECUTIVE",
        "N2_PRODUCT_RULES",
        "N3_TECHNICAL_LINEAGE",
        "N3_SECOPS_GATES",
    ]
    highlighted_indicators: tuple[str, ...]
    response_prefix_fr: str
    register_label_en: str = ""
    highlighted_indicators_en: tuple[str, ...] = ()
    response_prefix_en: str = ""


PROFILE_ADAPTATION_MAP: dict[str, ProfileAdaptationSpec] = {
    "EXECUTIVE": ProfileAdaptationSpec(
        archetype="EXECUTIVE",
        register_label="Direction / BU — KPIs FinOps, ROI, TTM & Risques N1/N2",
        vocabulary_tier="N1_N2_EXECUTIVE",
        highlighted_indicators=("Coût FinOps ($)", "Gain TTM (%)", "Indice de Risque BU", "ROI"),
        response_prefix_fr="[Synthèse Direction N1/N2 — KPIs FinOps & TTM]",
        register_label_en="Executive / BU — FinOps KPIs, ROI, TTM & N1/N2 Risks",
        highlighted_indicators_en=("FinOps Cost ($)", "TTM Gain (%)", "BU Risk Index", "ROI"),
        response_prefix_en="[Executive Summary N1/N2 — FinOps KPIs & TTM]",
    ),
    "PM": ProfileAdaptationSpec(
        archetype="PM",
        register_label="Product / Métier — Règles de Gestion & Invariants Fonctionnels",
        vocabulary_tier="N2_PRODUCT_RULES",
        highlighted_indicators=(
            "Règles de Gestion",
            "Parcours Utilisateurs",
            "Critères d'Acceptation",
            "Ancres Humaines",
        ),
        response_prefix_fr="[Synthèse Produit & Règles de Gestion Métier]",
        register_label_en="Product / Business — Domain Rules & Functional Invariants",
        highlighted_indicators_en=(
            "Business Rules",
            "User Journeys",
            "Acceptance Criteria",
            "Human Anchors",
        ),
        response_prefix_en="[Product & Business Rules Summary]",
    ),
    "ARCHITECT": ProfileAdaptationSpec(
        archetype="ARCHITECT",
        register_label="Architecte — URIs Canoniques, Contrats OpenAPI & Hashes SHA-256 N3",
        vocabulary_tier="N3_TECHNICAL_LINEAGE",
        highlighted_indicators=(
            "URI Canoniques orcia://",
            "Contrats OpenAPI 3.1",
            "Hashes CAS SHA-256",
            "Axiomes Ontologiques L1..L4",
        ),
        response_prefix_fr="[Synthèse Architecture N3 — URIs, Contrats & SHA-256]",
        register_label_en="Architect — Canonical URIs, OpenAPI Contracts & SHA-256 Digests N3",
        highlighted_indicators_en=(
            "Canonical orcia:// URIs",
            "OpenAPI 3.1 Contracts",
            "CAS SHA-256 Digests",
            "Ontology Axioms L1..L4",
        ),
        response_prefix_en="[Architecture Summary N3 — URIs, Contracts & SHA-256]",
    ),
    "TECH_LEAD": ProfileAdaptationSpec(
        archetype="TECH_LEAD",
        register_label="Tech Lead — Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3",
        vocabulary_tier="N3_TECHNICAL_LINEAGE",
        highlighted_indicators=(
            "DAG Steps & Verrous run-lock.json",
            "Hashes CAS SHA-256",
            "Couverture & Dette Technique",
            "URIs orcia://",
        ),
        response_prefix_fr="[Synthèse Tech Lead N3 — Topologie DAG & Hashes SHA-256]",
        register_label_en="Tech Lead — DAG Topology, Dependencies, SHA-256 & Execution N3",
        highlighted_indicators_en=(
            "DAG Steps & run-lock.json",
            "CAS SHA-256 Digests",
            "Coverage & Technical Debt",
            "orcia:// URIs",
        ),
        response_prefix_en="[Tech Lead Summary N3 — DAG Topology & SHA-256]",
    ),
    "DEVELOPER": ProfileAdaptationSpec(
        archetype="DEVELOPER",
        register_label="Développeur — Spécifications d'Étape, Entrées/Sorties & Contrats N3",
        vocabulary_tier="N3_TECHNICAL_LINEAGE",
        highlighted_indicators=(
            "Pointeurs JIT d'Artefacts",
            "Schémas d'Entrée/Sortie",
            "Hashes CAS SHA-256",
            "URIs orcia://",
        ),
        response_prefix_fr="[Synthèse Technique N3 — Contrats & Pointeurs d'Étape]",
        register_label_en="Developer — Step Specifications, Input/Output Schemas & Contracts N3",
        highlighted_indicators_en=(
            "JIT Artifact Pointers",
            "Input/Output Schemas",
            "CAS SHA-256 Digests",
            "orcia:// URIs",
        ),
        response_prefix_en="[Technical Summary N3 — Contracts & Step Pointers]",
    ),
    "SECOPS": ProfileAdaptationSpec(
        archetype="SECOPS",
        register_label="SecOps — Preuves de Gates, Isolation Passthrough & Conformité",
        vocabulary_tier="N3_SECOPS_GATES",
        highlighted_indicators=(
            "Preuves de Gates",
            "Isolation Passthrough / Service Principal",
            "Politiques Permission Broker",
            "Intégrité Audit Ledger",
        ),
        response_prefix_fr="[Synthèse SecOps — Preuves de Gates & Isolation Passthrough]",
        register_label_en="SecOps — Gate Evidence, Passthrough Isolation & Compliance",
        highlighted_indicators_en=(
            "Gate Evidence",
            "Passthrough / Service Principal Isolation",
            "Permission Broker Policies",
            "Audit Ledger Integrity",
        ),
        response_prefix_en="[SecOps Summary — Gate Evidence & Passthrough Isolation]",
    ),
}


def resolve_profile_adaptation(archetype: str) -> ProfileAdaptationSpec:
    """Resolve `ProfileAdaptationSpec` for a user's `human_profile_archetype` (`UX-DR12`)."""
    norm = (archetype or "").strip().upper()
    return PROFILE_ADAPTATION_MAP.get(norm, PROFILE_ADAPTATION_MAP["ARCHITECT"])


def resolve_profile_copy_for_locale(
    spec: ProfileAdaptationSpec, *, locale: str = "fr"
) -> tuple[str, tuple[str, ...], str]:
    """Return `(register_label, highlighted_indicators, response_prefix)` in `locale`."""
    if (locale or "fr").strip().lower().startswith("en"):
        return (
            spec.register_label_en or spec.register_label,
            spec.highlighted_indicators_en or spec.highlighted_indicators,
            spec.response_prefix_en or spec.response_prefix_fr,
        )
    return spec.register_label, spec.highlighted_indicators, spec.response_prefix_fr


__all__ = [
    "CONSTITUTIONAL_LAYER_1_TEXT",
    "CONSTITUTIONAL_LAYER_1_TEXT_EN",
    "CONSTITUTIONAL_LAYER_1_TEXT_FR",
    "PROFILE_ADAPTATION_MAP",
    "AssistantIntentKind",
    "AssistantLayerId",
    "ProfileAdaptationSpec",
    "resolve_profile_adaptation",
    "resolve_profile_copy_for_locale",
    "sanitize_layer_marker_tags",
]
