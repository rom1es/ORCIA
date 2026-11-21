"""Profile Adaptation & Constitutional Prompt Layer Sanitizers (`Story 3.3`, `Story 26.1`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

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

CONSTITUTIONAL_LAYER_1_TEXT: str = (
    "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]\n"
    "1. [NO_HUMAN_ANCHOR_WRITE]: Interdiction absolue de rédiger, pré-remplir ou modifier toute "
    "section marquée `human_authored_required: true` (Human-Led Anchor Card). En cas de demande "
    "de rédaction à la place de l'humain, refuser poliment et engager un questionnement "
    "socratique.\n"
    "2. [NO_GATE_SELF_APPROVAL]: Interdiction absolue d'approuver ou de contourner une Gate "
    "Déterministe, Agentique ou Humaine.\n"
    "3. [EXPLICIT_PROVENANCE_URI]: Toute affirmation factuelle doit citer son URI canonique "
    "`orcia://` et son condensat `sha256:`."
)

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


PROFILE_ADAPTATION_MAP: dict[str, ProfileAdaptationSpec] = {
    "EXECUTIVE": ProfileAdaptationSpec(
        archetype="EXECUTIVE",
        register_label="Direction / BU — KPIs FinOps, ROI, TTM & Risques N1/N2",
        vocabulary_tier="N1_N2_EXECUTIVE",
        highlighted_indicators=("Coût FinOps ($)", "Gain TTM (%)", "Indice de Risque BU", "ROI"),
        response_prefix_fr="[Synthèse Direction N1/N2 — KPIs FinOps & TTM]",
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
    ),
}


def resolve_profile_adaptation(archetype: str) -> ProfileAdaptationSpec:
    """Resolve `ProfileAdaptationSpec` for a user's `human_profile_archetype` (`UX-DR12`)."""
    norm = archetype.strip().upper()
    return PROFILE_ADAPTATION_MAP.get(norm, PROFILE_ADAPTATION_MAP["ARCHITECT"])
