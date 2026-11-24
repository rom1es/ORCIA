"""Bilingual (`fr`/`en`) template copy for `SdlcDocVsCodeAuditAssistantTemplate`."""

from __future__ import annotations

from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale

SECURITY_MOD_KEYWORDS: tuple[str, ...] = (
    "secops",
    "sécurité",
    "security",
    "sonar",
    "étape",
    "step",
    "ajout",
    "add",
)

SDLC_DOC_VS_CODE_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "step1_title": "1. Cadrage & Périmètre d'Audit (Ancre Humaine)",
        "step1_instr": "Définir le périmètre de comparaison Confluence/Jira vs Git.",
        "step2_title": "2. Extraction Tripartite Confluence / Jira / Git",
        "step2_instr": "Extraire les arêtes tripartites et alertes de fraîcheur.",
        "step3_title": "3. Qualification des Écarts Doc vs Code",
        "step3_instr": "Qualifier chaque écart Doc vs Code.",
        "step4_title": "4. Contrôle de Conformité & Sécurité",
        "step4_instr": "Vérifier la conformité sécurité et gouvernance sur les écarts identifiés.",
        "final_title": "Vérification Post-Action & Rapport",
        "final_instr": "Vérifier la complétude du rapport d'audit tripartite.",
        "wf_title": "Audit Tripartite Documentation Confluence/Jira vs Codebase Git",
        "wf_desc": "Compare les spécifications Confluence/Jira à l'arbre AST Git (UJ-10).",
        "blueprint_desc": (
            "Compare les spécifications Confluence/Jira à l'arbre AST Git et qualifie "
            "les écarts ([DOC_OBSOLETE_SUSPECTED] vs [BUG_CODE_SUSPECTED])."
        ),
    },
    "en": {
        "step1_title": "1. Framing & Audit Scope (Human Anchor)",
        "step1_instr": "Define the Confluence/Jira vs Git comparison scope.",
        "step2_title": "2. Tripartite Confluence / Jira / Git Extraction",
        "step2_instr": "Extract tripartite links and freshness alerts.",
        "step3_title": "3. Doc vs Code Drift Qualification",
        "step3_instr": "Qualify each Doc vs Code drift finding.",
        "step4_title": "4. Security & Compliance Check",
        "step4_instr": "Verify security and governance compliance on identified drifts.",
        "final_title": "Post-Action Verification & Report",
        "final_instr": "Verify completeness of the tripartite audit report.",
        "wf_title": "Tripartite Confluence/Jira Documentation vs Git Codebase Audit",
        "wf_desc": "Compare Confluence/Jira specifications against the Git AST (UJ-10).",
        "blueprint_desc": (
            "Compare Confluence/Jira specifications against the Git AST and classify "
            "drifts ([DOC_OBSOLETE_SUSPECTED] vs [BUG_CODE_SUSPECTED])."
        ),
    },
}


def get_sdlc_doc_vs_code_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return SDLC_DOC_VS_CODE_LOCALES.get(locale, SDLC_DOC_VS_CODE_LOCALES[DEFAULT_LOCALE])
