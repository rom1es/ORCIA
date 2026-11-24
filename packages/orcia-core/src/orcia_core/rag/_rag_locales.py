"""Bilingual FR/EN locale bundle for RAG ingestion, tripartite audit & federated search."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class RagLocaleBundle:
    """Localized strings for RAG diagnostics, tripartite findings, and search."""

    connector_nominal: str
    connector_healthy_tpl: str
    connector_degraded_tpl: str
    connector_unreachable_tpl: str
    reciprocity_query_tpl: str
    reciprocity_response_tpl: str
    tripartite_aligned: str
    tripartite_obsolete_tpl: str
    tripartite_bug_tpl: str
    semantic_badge: str
    default_concept_label: str
    search_cand_folder_title: str
    search_cand_folder_snippet: str
    search_cand_proc_title: str
    search_cand_proc_snippet: str
    search_cand_help_title: str
    search_cand_help_snippet: str
    search_cand_agents_title: str
    search_cand_agents_snippet: str


RAG_LOCALES: dict[SupportedLocale, RagLocaleBundle] = {
    "fr": RagLocaleBundle(
        connector_nominal="Connectivité nominale",
        connector_healthy_tpl="Connexion vérifiée avec succès sur {uri} (< 5 s).",
        connector_degraded_tpl="Connectivité dégradée ou secret manquant sur {uri}.",
        connector_unreachable_tpl="Échec de connexion fail-fast (< 5 s) vers {uri}.",
        reciprocity_query_tpl="Synthétiser le contenu vérifié de {title}",
        reciprocity_response_tpl=(
            "Réponse vérifiée pour **{title}** : {excerpt} (Source : `{uri}#{chunk_id}`)"
        ),
        tripartite_aligned="La spécification Confluence et le symbole Git AST sont alignés.",
        tripartite_obsolete_tpl=(
            "Divergence Confluence ({doc_summary}) vs Git ({code_summary}) "
            "justifiée par le ticket Jira Done ({jira_key})."
        ),
        tripartite_bug_tpl=(
            "Divergence non justifiée par un ticket Jira : Confluence spécifie "
            "'{doc_summary}' tandis que le code applique '{code_summary}'."
        ),
        semantic_badge="✨ Passage proche",
        default_concept_label="Général",
        search_cand_folder_title="Dossier Architecture Paiement & Rapprochement",
        search_cand_folder_snippet=(
            "Synthèse des discussions d'architecture avec citations [S1] et [G1]."
        ),
        search_cand_proc_title="Processus sdlc/ticket-to-tech-spec",
        search_cand_proc_snippet=(
            "Génération gouvernée de spécification technique depuis un ticket Jira."
        ),
        search_cand_help_title="Guide d'aide : Arbitrer un Tie-Break ou ouvrir l'atelier Fokus",
        search_cand_help_snippet=(
            "Comment trancher en 1 clic sur le Cockpit ou acquérir le verrou Redis."
        ),
        search_cand_agents_title="Catalogue des Agents spécialisés & Compétences métiers",
        search_cand_agents_snippet=(
            "Créer, qualifier et exécuter des agents et compétences (skills) gouvernés."
        ),
    ),
    "en": RagLocaleBundle(
        connector_nominal="Nominal connectivity",
        connector_healthy_tpl="Connection successfully verified on {uri} (< 5 s).",
        connector_degraded_tpl="Degraded connectivity or missing secret on {uri}.",
        connector_unreachable_tpl="Fail-fast connection error (< 5 s) to {uri}.",
        reciprocity_query_tpl="Summarize verified content for {title}",
        reciprocity_response_tpl=(
            "Verified response for **{title}**: {excerpt} (Source: `{uri}#{chunk_id}`)"
        ),
        tripartite_aligned="The Confluence specification and Git AST symbol are aligned.",
        tripartite_obsolete_tpl=(
            "Confluence ({doc_summary}) vs Git ({code_summary}) divergence "
            "justified by Done Jira ticket ({jira_key})."
        ),
        tripartite_bug_tpl=(
            "Divergence not justified by a Jira ticket: Confluence specifies "
            "'{doc_summary}' while code applies '{code_summary}'."
        ),
        semantic_badge="✨ Near match",
        default_concept_label="General",
        search_cand_folder_title="Payment & Reconciliation Architecture Folder",
        search_cand_folder_snippet=(
            "Synthesis of architecture discussions with [S1] and [G1] citations."
        ),
        search_cand_proc_title="Process sdlc/ticket-to-tech-spec",
        search_cand_proc_snippet="Governed technical specification generation from a Jira ticket.",
        search_cand_help_title="Help guide: Arbitrate a Tie-Break or open Focus review",
        search_cand_help_snippet="How to arbitrate in 1 click on the Cockpit or acquire a lock.",
        search_cand_agents_title="Specialized Agents & Business Skills Catalog",
        search_cand_agents_snippet="Create, qualify, and execute governed agents and skills.",
    ),
}


def get_rag_locale_bundle(locale: str = DEFAULT_LOCALE) -> RagLocaleBundle:
    """Return the localized `RagLocaleBundle` (`en` or `fr`, defaulting to `fr`)."""
    norm = (locale or DEFAULT_LOCALE).strip().lower()
    return RAG_LOCALES["en"] if norm.startswith("en") else RAG_LOCALES["fr"]


__all__ = ["RAG_LOCALES", "RagLocaleBundle", "get_rag_locale_bundle"]
