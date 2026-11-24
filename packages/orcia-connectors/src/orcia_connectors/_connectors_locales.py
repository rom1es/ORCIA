"""Bilingual (`fr`/`en`) locale bundles for `orcia_connectors` (`Story 27.8`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class SurgicalLocaleBundle:
    default_read_source_hint: str
    redacted_summary: str
    check_missing_label: str
    check_missing_summary: str
    check_ok_label: str
    check_ok_summary: str
    outline_summary: str
    inspect_empty_summary: str
    inspect_lines_summary: str
    search_matches_summary: str
    search_formatted_badge: str


SURGICAL_LOCALES: dict[SupportedLocale, SurgicalLocaleBundle] = {
    "fr": SurgicalLocaleBundle(
        default_read_source_hint=(
            "Demandez l'habilitation READ_SOURCE via le courtier de permissions de l'Espace."
        ),
        redacted_summary="Extrait protégé : habilitation READ_SOURCE requise.",
        check_missing_label="Vérification : {filename} (introuvable)",
        check_missing_summary="La ressource {filename} est absente du périmètre autorisé.",
        check_ok_label="Vérification : {filename} ({total_lines} lignes)",
        check_ok_summary="{filename} disponible ({total_lines} lignes).",
        outline_summary=(
            "Structure extraite de {filename} ({node_count} entrées sur {total_lines} lignes)."
        ),
        inspect_empty_summary=(
            "Aucune ligne dans la plage demandée sur {filename} ({total_lines} lignes)."
        ),
        inspect_lines_summary="Lu {count} ligne(s) de {filename} (#L{start_line}-{end_line}).",
        search_matches_summary="{count} extrait(s) trouvé(s) pour « {query} ».",
        search_formatted_badge="Recherché « {query} » ({count} résultat(s))",
    ),
    "en": SurgicalLocaleBundle(
        default_read_source_hint=(
            "Request READ_SOURCE permission through the Space permission broker."
        ),
        redacted_summary="Protected excerpt: READ_SOURCE permission is required.",
        check_missing_label="Check: {filename} (not found)",
        check_missing_summary="Resource {filename} is absent from the authorized scope.",
        check_ok_label="Check: {filename} ({total_lines} lines)",
        check_ok_summary="{filename} available ({total_lines} lines).",
        outline_summary=(
            "Extracted structure from {filename} ({node_count} entries across {total_lines} lines)."
        ),
        inspect_empty_summary="No lines in requested range for {filename} ({total_lines} lines).",
        inspect_lines_summary="Read {count} line(s) from {filename} (#L{start_line}-{end_line}).",
        search_matches_summary="{count} snippet(s) matched for '{query}'.",
        search_formatted_badge="Searched '{query}' ({count} matches)",
    ),
}


def get_surgical_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> SurgicalLocaleBundle:
    return SURGICAL_LOCALES.get(locale, SURGICAL_LOCALES[DEFAULT_LOCALE])


CODEGRAPH_MARKDOWN_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "heading": "### Rayon d'Impact Code Graph (`codegraph_calculate_blast_radius`)",
        "repo": "- **Dépôt** : `{repo_alias}`",
        "files": "- **Fichiers modifiés** : {files_str}",
        "score": "- **Score d'impact** : `{score}` (Risque : **{risk}**)",
        "drift": (
            "> [!WARNING] Dérive détectée (GRAPH_MOVED_SINCE_RUN_LOCK) : "
            "Le graphe de code a évolué (`{run_sha}` vs `{idx_sha}`)."
        ),
    },
    "en": {
        "heading": "### Code Graph Blast Radius (`codegraph_calculate_blast_radius`)",
        "repo": "- **Repository**: `{repo_alias}`",
        "files": "- **Modified files**: {files_str}",
        "score": "- **Impact score**: `{score}` (Risk: **{risk}**)",
        "drift": (
            "> [!WARNING] Drift detected (GRAPH_MOVED_SINCE_RUN_LOCK): "
            "The code graph moved (`{run_sha}` vs `{idx_sha}`)."
        ),
    },
}


def get_codegraph_markdown_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return CODEGRAPH_MARKDOWN_LOCALES.get(locale, CODEGRAPH_MARKDOWN_LOCALES[DEFAULT_LOCALE])


AUTONOMOUS_HELP_DEFAULTS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "title": "Aide mise à jour sous contrat",
        "purpose": "Aide générée sous contrat.",
        "step": "Vérifier l'exécution autonome.",
        "faq": "Consultable dans l'écran cible.",
    },
    "en": {
        "title": "Contract-updated contextual help",
        "purpose": "Contract-generated help.",
        "step": "Verify autonomous execution.",
        "faq": "Available in the target screen.",
    },
}

JIRA_ACCESS_REQUEST_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "summary": "[ORCIA Permission Broker] {required_role} sur {target_uri}",
        "description": (
            "Demande d'accès ({execution_identity}) pour l'étape {step_key} "
            "par {requester_email} — Approbateur: {approver_team}"
        ),
    },
    "en": {
        "summary": "[ORCIA Permission Broker] {required_role} on {target_uri}",
        "description": (
            "Access request ({execution_identity}) for step {step_key} "
            "by {requester_email} — Approver: {approver_team}"
        ),
    },
}

SDLC_POLICY_AND_MARKER_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "writes_code_without_intent": (
            "Ligne {line}: L'étape '{step_key}' modifie du code ('writes_code: true') "
            "sans étape amont déclarant l'intention ('declares_intention: true') (FR-13)."
        ),
        "reverse_doc_mode_forbidden": (
            "Ligne {line}: L'étape '{step_key}' active 'reverse_doc_from_code: true' "
            "uniquement autorisé en mode 'brownfield_bootstrap' (FR-13)."
        ),
        "assumption_summary": "[ASSUMPTION] Continuité d'audit en tâche de fond retenue",
        "assumption_details": "Hypothèse appliquée sans blocage worker: {note}",
        "bug_code_summary": "[BUG_CODE_SUSPECTED] Écart d'implémentation détecté dans le code",
        "doc_obsolete_summary": (
            "[DOC_OBSOLETE_SUSPECTED] Spécification Confluence possiblement obsolète"
        ),
    },
    "en": {
        "writes_code_without_intent": (
            "Line {line}: Step '{step_key}' modifies code ('writes_code: true') "
            "without an upstream intention declaration ('declares_intention: true') (FR-13)."
        ),
        "reverse_doc_mode_forbidden": (
            "Line {line}: Step '{step_key}' enables 'reverse_doc_from_code: true', "
            "which is allowed only in 'brownfield_bootstrap' mode (FR-13)."
        ),
        "assumption_summary": "[ASSUMPTION] Background audit continuity retained",
        "assumption_details": "Applied assumption without worker blocking: {note}",
        "bug_code_summary": "[BUG_CODE_SUSPECTED] Implementation drift detected in source code",
        "doc_obsolete_summary": "[DOC_OBSOLETE_SUSPECTED] Confluence specification may be obsolete",
    },
}

BOUNDED_WORKFLOW_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "default_remarks": "Corrections demandées en revue.",
        "goal_reentry_body": (
            "# {title}\n\n## Reprise adaptative (`iter-{iteration}`)\n"
            "Corrections demandées : {remarks}"
        ),
        "decisions_heading": "## Décisions",
        "substep_section": (
            "Section générée pour la sous-étape **{name}** (`{sub_id}`, "
            "itération `iter-{iteration}`). Entrées : `{inputs}`."
        ),
        "remarks_line": "Prise en compte des remarques de retour : {remarks}.",
        "mermaid_block": "```mermaid\nflowchart LR\n  Entree --> Analyse --> Livrable\n```",
        "validated_detail": " Détail complémentaire validé conformément au socle documentaire.",
        "fallback_artifact": "# {title}\n\nContenu validé.",
        "auto_remediated_line": "\n\n# {title}\nSection auto-remédiée (essai #{retry}). ",
        "compliant_detail": "Détail conforme. ",
        "autonomous_default_artifact": "# Livrable\n\nContenu validé.\n",
    },
    "en": {
        "default_remarks": "Corrections requested during review.",
        "goal_reentry_body": (
            "# {title}\n\n## Adaptive reentry (`iter-{iteration}`)\n"
            "Requested corrections: {remarks}"
        ),
        "decisions_heading": "## Decisions",
        "substep_section": (
            "Section generated for sub-step **{name}** (`{sub_id}`, "
            "iteration `iter-{iteration}`). Inputs: `{inputs}`."
        ),
        "remarks_line": "Incorporated review feedback: {remarks}.",
        "mermaid_block": "```mermaid\nflowchart LR\n  Input --> Analysis --> Deliverable\n```",
        "validated_detail": " Additional detail validated against the documentation baseline.",
        "fallback_artifact": "# {title}\n\nValidated content.",
        "auto_remediated_line": "\n\n# {title}\nAuto-remediated section (attempt #{retry}). ",
        "compliant_detail": "Compliant detail. ",
        "autonomous_default_artifact": "# Deliverable\n\nValidated content.\n",
    },
}

CONNECTOR_SEED_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "confluence_seed_title": "Dossier d'Étude d'Architecture CRL — Mon Compte",
        "confluence_seed_markdown": (
            "# Dossier d'Étude d'Architecture CRL\n\n## Contexte\nSocle CRL."
        ),
        "confluence_default_markdown": "# {page_id}\nContenu de référence Confluence.",
        "jira_paybuild_summary": "Implémenter le connecteur checkout idempotent",
        "jira_paysec_summary": "Revue SecOps habilitation IAM connecteur paiement",
        "git_verified_content": "// Contenu vérifié depuis {uri}@{ref}",
    },
    "en": {
        "confluence_seed_title": "CRL Architecture Study Dossier — My Account",
        "confluence_seed_markdown": "# CRL Architecture Study Dossier\n\n## Context\nCRL Baseline.",
        "confluence_default_markdown": "# {page_id}\nConfluence reference content.",
        "jira_paybuild_summary": "Implement idempotent checkout connector",
        "jira_paysec_summary": "SecOps IAM authorization review for payment connector",
        "git_verified_content": "// Verified content from {uri}@{ref}",
    },
}
