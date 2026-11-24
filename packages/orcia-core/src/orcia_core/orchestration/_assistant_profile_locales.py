"""Bilingual locale bundles for Assistant composer & profile adaptation (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale

COMPOSER_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "step1_title": "1. Cadrage & Objectif Métier (Ancre Humaine)",
        "step1_inst": "Définir l'objectif métier et les invariants de contrôle.",
        "step2_title": "2. Collecte & Vérification des Sources Fédérées",
        "step2_inst": "Collecter les tranches via ContextSourcePort.",
        "step3_title": "3. Contrôle Complémentaire Demandé",
        "step3_inst": "Exécuter le contrôle complémentaire demandé sur les sources collectées.",
        "step_final_title": "Vérification Post-Action & Synthèse",
        "step_final_inst": "Vérifier la cohérence finale des livrables produits.",
        "wf_title": "Audit Multi-Sources & Vérification de Conformité",
        "wf_desc": "Workflow générique de collecte multi-sources et vérification post-action.",
    },
    "en": {
        "step1_title": "1. Framing & Business Objective (Human Anchor)",
        "step1_inst": "Define the business objective and control invariants.",
        "step2_title": "2. Federated Source Collection & Verification",
        "step2_inst": "Collect context slices via ContextSourcePort.",
        "step3_title": "3. Requested Complementary Check",
        "step3_inst": "Run the requested complementary check across collected sources.",
        "step_final_title": "Post-Action Verification & Synthesis",
        "step_final_inst": "Verify final consistency of produced deliverables.",
        "wf_title": "Multi-Source Audit & Compliance Verification",
        "wf_desc": "Generic multi-source collection and post-action verification workflow.",
    },
}

PROFILE_LABELS_LOCALES: dict[SupportedLocale, dict[str, dict[str, object]]] = {
    "fr": {
        "EXECUTIVE": {
            "register": "Direction / BU — KPIs FinOps, ROI, TTM & Risques N1/N2",
            "indicators": ("Coût FinOps ($)", "Gain TTM (%)", "Indice de Risque BU", "ROI"),
            "prefix": "[Synthèse Direction N1/N2 — KPIs FinOps & TTM]",
        },
        "PM": {
            "register": "Product / Métier — Règles de Gestion & Invariants Fonctionnels",
            "indicators": (
                "Règles de Gestion",
                "Parcours Utilisateurs",
                "Critères d'Acceptation",
                "Ancres Humaines",
            ),
            "prefix": "[Synthèse Produit & Règles de Gestion Métier]",
        },
        "ARCHITECT": {
            "register": "Architecte — URIs Canoniques, Contrats OpenAPI & Hashes SHA-256 N3",
            "indicators": (
                "URI Canoniques orcia://",
                "Contrats OpenAPI 3.1",
                "Hashes CAS SHA-256",
                "Axiomes Ontologiques L1..L4",
            ),
            "prefix": "[Synthèse Architecture N3 — URIs, Contrats & SHA-256]",
        },
        "TECH_LEAD": {
            "register": "Tech Lead — Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3",
            "indicators": (
                "DAG Steps & Verrous run-lock.json",
                "Hashes CAS SHA-256",
                "Couverture & Dette Technique",
                "URIs orcia://",
            ),
            "prefix": "[Synthèse Tech Lead N3 — Topologie DAG & Hashes SHA-256]",
        },
        "DEVELOPER": {
            "register": "Développeur — Spécifications d'Étape, Entrées/Sorties & Contrats N3",
            "indicators": (
                "Pointeurs JIT d'Artefacts",
                "Schémas d'Entrée/Sortie",
                "Hashes CAS SHA-256",
                "URIs orcia://",
            ),
            "prefix": "[Synthèse Technique N3 — Contrats & Pointeurs d'Étape]",
        },
        "SECOPS": {
            "register": "SecOps — Preuves de Gates, Isolation Passthrough & Conformité",
            "indicators": (
                "Preuves de Gates",
                "Isolation Passthrough / Service Principal",
                "Politiques Permission Broker",
                "Intégrité Audit Ledger",
            ),
            "prefix": "[Synthèse SecOps — Preuves de Gates & Isolation Passthrough]",
        },
    },
    "en": {
        "EXECUTIVE": {
            "register": "Executive / BU — FinOps KPIs, ROI, TTM & N1/N2 Risks",
            "indicators": ("FinOps Cost ($)", "TTM Gain (%)", "BU Risk Index", "ROI"),
            "prefix": "[Executive Summary N1/N2 — FinOps KPIs & TTM]",
        },
        "PM": {
            "register": "Product / Business — Domain Rules & Functional Invariants",
            "indicators": (
                "Business Rules",
                "User Journeys",
                "Acceptance Criteria",
                "Human Anchors",
            ),
            "prefix": "[Product & Business Rules Summary]",
        },
        "ARCHITECT": {
            "register": "Architect — Canonical URIs, OpenAPI Contracts & SHA-256 Digests N3",
            "indicators": (
                "Canonical orcia:// URIs",
                "OpenAPI 3.1 Contracts",
                "CAS SHA-256 Digests",
                "Ontology Axioms L1..L4",
            ),
            "prefix": "[Architecture Summary N3 — URIs, Contracts & SHA-256]",
        },
        "TECH_LEAD": {
            "register": "Tech Lead — DAG Topology, Dependencies, SHA-256 & Execution N3",
            "indicators": (
                "DAG Steps & run-lock.json",
                "CAS SHA-256 Digests",
                "Coverage & Technical Debt",
                "orcia:// URIs",
            ),
            "prefix": "[Tech Lead Summary N3 — DAG Topology & SHA-256]",
        },
        "DEVELOPER": {
            "register": "Developer — Step Specifications, Input/Output Schemas & Contracts N3",
            "indicators": (
                "JIT Artifact Pointers",
                "Input/Output Schemas",
                "CAS SHA-256 Digests",
                "orcia:// URIs",
            ),
            "prefix": "[Technical Summary N3 — Contracts & Step Pointers]",
        },
        "SECOPS": {
            "register": "SecOps — Gate Evidence, Passthrough Isolation & Compliance",
            "indicators": (
                "Gate Evidence",
                "Passthrough / Service Principal Isolation",
                "Permission Broker Policies",
                "Audit Ledger Integrity",
            ),
            "prefix": "[SecOps Summary — Gate Evidence & Passthrough Isolation]",
        },
    },
}

PROFILE_LABELS_FR = PROFILE_LABELS_LOCALES["fr"]

INTENT_KEYWORDS_LOCALES: dict[SupportedLocale, dict[str, tuple[str, ...]]] = {
    "fr": {
        "refusal": ("remplis-le pour moi", "remplis la section humaine", "rédige l'ancre humaine"),
        "modify": ("modifie", "ajoute", "étape", "ajuste"),
        "compose": ("propose un workflow", "créer un workflow", "comparer", "rapprochement"),
        "launch": ("lance", "exécute"),
    },
    "en": {
        "refusal": ("write the human anchor for me", "fill the human anchor"),
        "modify": ("step", "modify", "add step"),
        "compose": ("workflow", "composer", "audit"),
        "launch": ("launch", "start run"),
    },
}

__all__ = [
    "COMPOSER_LOCALES",
    "INTENT_KEYWORDS_LOCALES",
    "PROFILE_LABELS_FR",
    "PROFILE_LABELS_LOCALES",
]
