"""Bilingual seed strings for deterministic ontology service fixtures (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class OntologySeedCopy:
    """Localized ontology fixture copy for a target locale."""

    l1_term: str
    l1_definition: str
    l1_synonyms: tuple[str, ...]
    l1_banned_terms: tuple[str, ...]
    l1_profile_translations: dict[str, str]
    l2_term: str
    l2_definition: str
    l2_synonyms: tuple[str, ...]
    l2_profile_translations: dict[str, str]
    l3_parent_definition: str
    l3_parent_synonyms: tuple[str, ...]
    l3_subteam_definition: str
    l3_subteam_synonyms: tuple[str, ...]
    l3_ws_term: str
    l3_ws_definition: str
    l4_active_definition: str
    l4_obsolete_term: str
    l4_obsolete_definition: str
    prop_l4_change: str


ONTOLOGY_SEED_LOCALES: dict[SupportedLocale, OntologySeedCopy] = {
    "fr": OntologySeedCopy(
        l1_term="Actif Stratégique",
        l1_definition="Actif critique du SI Groupe soumis aux exigences d'audit PCI-DSS/DORA.",
        l1_synonyms=("Critical Asset", "Brique Critique Groupe"),
        l1_banned_terms=("Projet Legacy Non Gouverné",),
        l1_profile_translations={
            "EXECUTIVE": "Actif Stratégique (ROI & Risque Réglementaire DORA/PCI-DSS)",
            "PM_BUSINESS": "Produit Cœur Métier à SLA Critique (99.99%)",
            "ARCHITECT": "Composant Tier-1 sous contrat Architecture Spine immuable",
            "TECH_LEAD": "Service Tier-1 (Couverture >= 90%, 0-diff OpenAPI)",
            "DEVELOPER": "Module critique sous garde-fous CI/CD stricts",
            "SECOPS": "Périmètre régulé PCI-DSS / Audit Ledger Append-Only",
        },
        l2_term="Grand Livre de Paiement",
        l2_definition="Journal comptable immuable des transactions de la BU Digital & Paiements.",
        l2_synonyms=("Payment Ledger", "Journal Transactionnel"),
        l2_profile_translations={
            "EXECUTIVE": "Grand Livre Financier Consolidé BU",
            "ARCHITECT": "Event-Sourced Ledger Append-Only (PostgreSQL 18)",
        },
        l3_parent_definition="Actif Stratégique décliné par l'Équipe Parente Architecture.",
        l3_parent_synonyms=("Plateforme Agentique Core",),
        l3_subteam_definition="Actif Stratégique spécialisé par la Sous-Équipe Checkout.",
        l3_subteam_synonyms=("Microservice Tier-1", "Tunnel Checkout Critique"),
        l3_ws_term="Clé d'Idempotence Paiement",
        l3_ws_definition="Jeton UUIDv7 garantissant l'exécution unique d'une capture PSP.",
        l4_active_definition=(
            "Règle d'exemption Transaction Risk Analysis découverte durant le Run."
        ),
        l4_obsolete_term="Terme Branche Obsolète Replay",
        l4_obsolete_definition=(
            "Concept issu d'un snapshot annulé après Replay (ne doit jamais fuiter)."
        ),
        prop_l4_change="Promote Exemption 3DS Frictionless TRA to 3_WORKSPACE",
    ),
    "en": OntologySeedCopy(
        l1_term="Strategic Asset",
        l1_definition=(
            "Critical Group information-system asset subject to PCI-DSS/DORA audit requirements."
        ),
        l1_synonyms=("Critical Asset", "Group Core Building Block"),
        l1_banned_terms=("Ungoverned Legacy Project",),
        l1_profile_translations={
            "EXECUTIVE": "Strategic Asset (ROI & DORA/PCI-DSS Regulatory Risk)",
            "PM_BUSINESS": "Core Business Product with Critical SLA (99.99%)",
            "ARCHITECT": "Tier-1 Component under Immutable Architecture Spine Contract",
            "TECH_LEAD": "Tier-1 Service (Coverage >= 90%, 0-diff OpenAPI)",
            "DEVELOPER": "Critical module under strict CI/CD guardrails",
            "SECOPS": "PCI-DSS Regulated Scope / Append-Only Audit Ledger",
        },
        l2_term="Payment Ledger",
        l2_definition="Immutable accounting journal of Digital & Payments BU transactions.",
        l2_synonyms=("Payment Ledger", "Transactional Journal"),
        l2_profile_translations={
            "EXECUTIVE": "Consolidated BU Financial Ledger",
            "ARCHITECT": "Append-Only Event-Sourced Ledger (PostgreSQL 18)",
        },
        l3_parent_definition="Strategic Asset refined by the Parent Architecture Team.",
        l3_parent_synonyms=("Core Agentic Platform",),
        l3_subteam_definition="Strategic Asset specialized by the Checkout Sub-Team.",
        l3_subteam_synonyms=("Tier-1 Microservice", "Critical Checkout Funnel"),
        l3_ws_term="Payment Idempotency Key",
        l3_ws_definition="UUIDv7 token guaranteeing single execution of a PSP capture.",
        l4_active_definition="Transaction Risk Analysis exemption rule discovered during the run.",
        l4_obsolete_term="Obsolete Replay Branch Term",
        l4_obsolete_definition=(
            "Concept originating from a snapshot cancelled after Replay (must never leak)."
        ),
        prop_l4_change="Promote Exemption 3DS Frictionless TRA to 3_WORKSPACE",
    ),
}


def get_ontology_seed_bundle(locale: SupportedLocale = DEFAULT_LOCALE) -> OntologySeedCopy:
    """Return localized seed strings for the requested locale."""
    return ONTOLOGY_SEED_LOCALES.get(locale, ONTOLOGY_SEED_LOCALES[DEFAULT_LOCALE])


__all__ = ["ONTOLOGY_SEED_LOCALES", "OntologySeedCopy", "get_ontology_seed_bundle"]
