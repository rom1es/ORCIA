"""Bilingual locale bundles for HelpArticle validation & ORCIA docs workflow (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import SupportedLocale

HELP_MANDATORY_SECTIONS: dict[SupportedLocale, tuple[str, str, str]] = {
    "fr": (
        "## 1. À quoi sert cet écran ?",
        "## 2. Comment faire (Pas-à-pas)",
        "## 3. Questions fréquentes & Dépannage",
    ),
    "en": (
        "## 1. What is this screen for?",
        "## 2. How to use (Step-by-step)",
        "## 3. Frequently Asked Questions & Troubleshooting",
    ),
}

HELP_MARKDOWN_HEADINGS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "sec1": "## 1. À quoi sert cet écran ? {{#overview}}",
        "ui_prefix": "Composant UI",
        "sec2": "## 2. Comment faire (Pas-à-pas) {{#steps}}",
        "sec2_sub": "### Pas-à-pas",
        "sec3": "## 3. Questions fréquentes & Dépannage {{#faq}}",
        "sec3_sub": "### Questions fréquentes",
        "pack_overview_sec": "## 1. À quoi sert cet écran ?\nPack métier {title}.",
    },
    "en": {
        "sec1": "## 1. What is this screen for? {{#overview}}",
        "ui_prefix": "UI Component",
        "sec2": "## 2. How to use (Step-by-step) {{#steps}}",
        "sec2_sub": "### Step-by-step",
        "sec3": "## 3. Frequently Asked Questions & Troubleshooting {{#faq}}",
        "sec3_sub": "### Frequently Asked Questions",
        "pack_overview_sec": "## 1. What is this screen for?\nBusiness pack {title}.",
    },
}

HELP_VALIDATOR_VIOLATIONS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "missing_sections": "Sections obligatoires manquantes : {sections}",
        "unknown_components": "Composants @orcia/ui inexistants cités : {components}",
        "unknown_glossary": "Termes absents du Glossaire : {terms}",
        "secret_leak": (  # pragma: allowlist secret
            "Fuite de secret ou token détectée dans le corps HelpArticle."
        ),
    },
    "en": {
        "missing_sections": "Missing mandatory sections: {sections}",
        "unknown_components": "Unknown @orcia/ui components referenced: {components}",
        "unknown_glossary": "Terms missing from glossary: {terms}",
        "secret_leak": (  # pragma: allowlist secret
            "Secret or token leak detected inside HelpArticle body."
        ),
    },
}

ORCIA_DOCS_GLOSSARY_LOCALES: dict[SupportedLocale, list[str]] = {
    "fr": ["Espace de Travail", "Équipe", "Processus", "Pack Métier"],
    "en": ["Workspace", "Team", "Process", "Business Pack"],
}


@dataclass(frozen=True, slots=True)
class OrciaDocsCopy:
    """Localized ORCIA complete documentation workflow copy."""

    purpose: str
    steps: list[str]
    faq: list[str]
    doc_title: str
    step1_title: str
    step2_title: str
    step3_title: str
    step4_title: str
    step1_summary_tpl: str
    step2_summary: str
    step3_summary_tpl: str
    step4_summary_tpl: str
    present_word: str
    missing_word: str
    writer_handle: str
    certifier_handle: str


ORCIA_DOCS_WORKFLOW_LOCALES: dict[SupportedLocale, OrciaDocsCopy] = {
    "fr": OrciaDocsCopy(
        purpose=(
            "### Objectif\n"
            "Rassembler en un guide unifié la documentation fonctionnelle de chaque écran "
            "d'ORCIA, le modèle métier d'organisation (Directions, Équipes, Espaces de "
            "travail) et la FAQ d'accompagnement."
        ),
        steps=[
            (
                "**Guide Fonctionnel par Écran** : Piloter l'activité depuis le Cockpit "
                "(`/cockpit`), dialoguer avec Mon Assistant (`/assistant`), organiser ses "
                "sources et livrables dans Mes Espaces (`/workspaces`), configurer ses "
                "Agents (`/agents`) et orchestrer ses Processus (`/processes`)."
            ),
            (
                "**Architecture & Modèle Métier** : Structurer l'organisation en Directions "
                "(BU) et Équipes de facturation, puis rattacher chaque Espace de travail "
                "(collectif, privé ou confidentiel) avec héritage gouverné."
            ),
            (
                "**Synchronisation Documentaire** : Exécuter le processus "
                "`generate-orcia-documentation` pour vérifier et publier l'ensemble des "
                "guides FR/EN et le catalogue `/showcase`."
            ),
        ],
        faq=[
            (
                "**Questions Fréquentes (FAQ) — Quelle est la différence entre une Équipe "
                "et un Espace de travail ?** L'Équipe porte les membres et le rattachement "
                "budgétaire, tandis que l'Espace de travail isole les sources documentaires, "
                "le glossaire et les livrables d'un projet."
            ),
            (
                "**Questions Fréquentes (FAQ) — Comment mettre à jour l'aide contextuelle "
                "(`ⓘ`) d'un écran ?** Lancez le processus `generate-orcia-documentation` "
                "depuis `☍ Mes Processus` pour valider et rattacher à chaud les guides mis à jour."
            ),
        ],
        doc_title="Documentation Complète d'ORCIA — Guides Écrans, Architecture & FAQ",
        step1_title="Étape 1 — Inventaire du dépôt ORCIA",
        step2_title="Étape 2 — Génération & Enrichissement des Guides et de la FAQ",
        step3_title="Étape 3 — Contrôle Qualité Déterministe (validate_help_article)",
        step4_title="Étape 4 — Publication & Rattachement à Chaud (/showcase & docs/help/)",
        step1_summary_tpl=(
            "{routes_count} routes UI, {ui_components_count} primitives @orcia/ui, "
            "{help_files_count} fiches d'aide bilingues (FR/EN), FAQ d'architecture "
            "({faq_word}) et {tl_count} rapports Tech Lead recensés."
        ),
        step2_summary=(
            "Sections obligatoires structurées (Objectif, Guide Fonctionnel par Écran, "
            "Architecture & Modèle Métier, Questions Fréquentes FAQ) en français et en anglais."
        ),
        step3_summary_tpl=(
            "Validation FR/EN réussie ({route_count} routes vérifiées, sections "
            "obligatoires présentes, 0 secret ou jargon technique interne détecté)."
        ),
        step4_summary_tpl="Guides FR/EN publiés et rattachés à chaud ({targets}).",
        present_word="présente",
        missing_word="absente",
        writer_handle="@Rédacteur-Documentation-Orcia",
        certifier_handle="@Certificateur-Sécurité-et-Sandbox",
    ),
    "en": OrciaDocsCopy(
        purpose=(
            "### Objective\n"
            "Gather in a unified guide the functional documentation of every ORCIA screen, "
            "the organizational domain model (Business Units, Teams, Workspaces) and the "
            "support FAQ."
        ),
        steps=[
            (
                "**Functional Screen Guide**: Monitor activity from the Cockpit (`/cockpit`), "
                "interact with My Assistant (`/assistant`), organize sources and deliverables "
                "in My Spaces (`/workspaces`), configure Agents (`/agents`), and orchestrate "
                "Processes (`/processes`)."
            ),
            (
                "**Architecture & Domain Model**: Structure the organization into Business "
                "Units and Billing Teams, then attach each Workspace (shared, private, or "
                "confidential) with governed inheritance."
            ),
            (
                "**Documentation Synchronization**: Run the `generate-orcia-documentation` "
                "process to verify and publish all FR/EN guides and the `/showcase` catalog."
            ),
        ],
        faq=[
            (
                "**Frequently Asked Questions (FAQ) — What is the difference between a Team "
                "and a Workspace?** A Team holds members and billing ownership, whereas a "
                "Workspace isolates project sources, glossary terms, and deliverables."
            ),
            (
                "**Frequently Asked Questions (FAQ) — How do I update a screen's contextual "
                "help (`ⓘ`)?** Run the `generate-orcia-documentation` process from "
                "`☍ My Processes` to validate and hot-attach updated guides."
            ),
        ],
        doc_title="ORCIA Complete Documentation — Screen Guides, Architecture & FAQ",
        step1_title="Step 1 — ORCIA Repository Inventory",
        step2_title="Step 2 — Screen Guides & Architecture FAQ Generation",
        step3_title="Step 3 — Deterministic Quality Check (validate_help_article)",
        step4_title="Step 4 — Hot Attachment & Publication (/showcase & docs/help/)",
        step1_summary_tpl=(
            "{routes_count} UI routes, {ui_components_count} @orcia/ui primitives, "
            "{help_files_count} bilingual help files (FR/EN), architecture FAQ "
            "({faq_word}) and {tl_count} Tech Lead reports inventoried."
        ),
        step2_summary=(
            "Mandatory sections structured (Objective, Functional Screen Guide, "
            "Architecture & Domain Model, Frequently Asked Questions FAQ) in French and English."
        ),
        step3_summary_tpl=(
            "FR/EN validation passed ({route_count} bound routes verified, "
            "mandatory sections present, 0 secret or internal technical jargon detected)."
        ),
        step4_summary_tpl="FR/EN guides published and hot-attached ({targets}).",
        present_word="present",
        missing_word="missing",
        writer_handle="@Orcia-Documentation-Writer",
        certifier_handle="@Security-And-Sandbox-Certifier",
    ),
}

__all__ = [
    "HELP_MANDATORY_SECTIONS",
    "HELP_MARKDOWN_HEADINGS",
    "HELP_VALIDATOR_VIOLATIONS",
    "ORCIA_DOCS_GLOSSARY_LOCALES",
    "ORCIA_DOCS_WORKFLOW_LOCALES",
    "OrciaDocsCopy",
]
