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
            "register": "Direction / BU — Pilotage KPIs, ROI, Délais & Risques",
            "indicators": ("Coût & Budget", "Délais (TTM)", "Risques métier", "ROI"),
            "prefix": "[Synthèse Direction — KPIs & Risques]",
        },
        "PM": {
            "register": "Produit / Métier — Règles de Gestion & Priorités Fonctionnelles",
            "indicators": (
                "Règles de Gestion",
                "Parcours Utilisateurs",
                "Critères d'Acceptation",
                "Décisions Métier",
            ),
            "prefix": "[Synthèse Produit & Règles de Gestion]",
        },
        "ARCHITECT": {
            "register": (
                "Architecte — Conception Système, Contrats d'Interface & Cohérence Technique"
            ),
            "indicators": (
                "Architecture Cible",
                "Contrats d'API",
                "Décisions Techniques",
                "Principes Métier",
            ),
            "prefix": "[Synthèse Architecture — Conception & Contrats]",
        },
        "TECH_LEAD": {
            "register": (
                "Référent Technique — Architecture Applicative, Dépendances, "
                "Qualité & Plan d'Exécution"
            ),
            "indicators": (
                "Dépendances & Séquence",
                "Qualité & Tests",
                "Risques & Dette Technique",
                "Faisabilité d'Exécution",
            ),
            "prefix": "[Synthèse Référent Technique — Qualité & Exécution]",
        },
        "DEVELOPER": {
            "register": (
                "Développeur — Implémentation, Schémas d'Entrée/Sortie & Contrats Techniques"
            ),
            "indicators": (
                "Points d'Entrée & Fichiers",
                "Schémas d'Entrée/Sortie",
                "Cas Limites & Tests",
                "Contraintes Techniques",
            ),
            "prefix": "[Synthèse Technique — Implémentation & Contrats]",
        },
        "SECOPS": {
            "register": "SecOps — Contrôles de Sécurité, Isolation des Accès & Conformité",
            "indicators": (
                "Contrôles & Validations",
                "Isolation des Accès",
                "Gouvernance des Permissions",
                "Traçabilité d'Audit",
            ),
            "prefix": "[Synthèse SecOps — Sécurité & Conformité]",
        },
    },
    "en": {
        "EXECUTIVE": {
            "register": "Executive / BU — KPIs, ROI, Delivery & Risks",
            "indicators": ("Cost & Budget", "Time-to-Market", "Business Risks", "ROI"),
            "prefix": "[Executive Summary — KPIs & Risks]",
        },
        "PM": {
            "register": "Product / Business — Business Rules & Functional Priorities",
            "indicators": (
                "Business Rules",
                "User Journeys",
                "Acceptance Criteria",
                "Business Decisions",
            ),
            "prefix": "[Product & Business Rules Summary]",
        },
        "ARCHITECT": {
            "register": "Architect — System Design, Interface Contracts & Technical Coherence",
            "indicators": (
                "Target Architecture",
                "API Contracts",
                "Technical Decisions",
                "Domain Principles",
            ),
            "prefix": "[Architecture Summary — Design & Contracts]",
        },
        "TECH_LEAD": {
            "register": (
                "Technical Lead — Application Architecture, Dependencies, Quality & Delivery Plan"
            ),
            "indicators": (
                "Dependencies & Sequencing",
                "Quality & Testing",
                "Risks & Technical Debt",
                "Delivery Feasibility",
            ),
            "prefix": "[Technical Lead Summary — Quality & Delivery]",
        },
        "DEVELOPER": {
            "register": ("Developer — Implementation, Input/Output Schemas & Technical Contracts"),
            "indicators": (
                "Entry Points & Files",
                "Input/Output Schemas",
                "Edge Cases & Tests",
                "Technical Constraints",
            ),
            "prefix": "[Technical Summary — Implementation & Contracts]",
        },
        "SECOPS": {
            "register": "SecOps — Security Controls, Access Isolation & Compliance",
            "indicators": (
                "Validation Controls",
                "Access Isolation",
                "Permission Governance",
                "Audit Traceability",
            ),
            "prefix": "[SecOps Summary — Security & Compliance]",
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
