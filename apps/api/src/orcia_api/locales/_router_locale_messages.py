"""Bilingual (`fr`/`en`) router & helper message catalog for `apps/api` (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class RouterLocaleCopy:
    """Localized message templates for `apps/api` routers & bridges."""

    rag_reindex_initiated: str
    ai_test_audit_ok: str
    ai_test_audit_err: str
    tool_intercepted_write: str
    bootstrap_missing_model: str
    bootstrap_invalid_url: str
    bootstrap_missing_api_key: str
    bootstrap_connect_failed: str
    iam_created: str
    iam_updated: str
    iam_pw_reset: str
    mcp_ide_badge: str
    ontology_term_saved: str
    ontology_promo_proposed: str
    ontology_promo_decided: str
    thinking_deep: str
    thinking_std: str
    llm_step_label: str
    org_unit_created: str
    org_unit_updated: str
    org_unit_deleted: str
    invitation_summary: str
    connector_test_detail: str
    connector_status_on: str
    connector_status_off: str
    connector_disabled: str
    workflow_what_if_sample: str
    pack_sdlc_title: str
    pack_sdlc_domain: str
    pack_sdlc_desc: str
    pack_builder_title: str
    pack_builder_domain: str
    pack_builder_desc: str
    pack_custom_domain: str


ROUTER_LOCALE_MESSAGES: dict[SupportedLocale, RouterLocaleCopy] = {
    "fr": RouterLocaleCopy(
        rag_reindex_initiated="Réindexation globale du corpus vectoriel initiée avec succès.",
        ai_test_audit_ok="Test de connexion modèle IA {mapping_id}: {health}",
        ai_test_audit_err="Test de connexion modèle IA {mapping_id}: ERROR ({err_type})",
        tool_intercepted_write=(
            "L'exécution de `{tool_label}` a été interceptée (Verrou V5 / Process Write Gate) "
            "et convertie en proposition soumise à arbitrage humain."
        ),
        bootstrap_missing_model=(
            "❌ Échec du test : veuillez renseigner l'identifiant du modèle principal."
        ),
        bootstrap_invalid_url=(
            "❌ Échec du test : veuillez indiquer une URL d'API valide (https:// ou http://)."
        ),
        bootstrap_missing_api_key=(
            "❌ Échec du test : veuillez saisir votre clé d'API (jeton secret) ou « Sans clé »."
        ),
        bootstrap_connect_failed="❌ Échec du test de connexion : {err_msg}",
        iam_created="Création du compte IAM '{principal_id}'",
        iam_updated="Mise à jour du compte IAM '{principal_id}'",
        iam_pw_reset="Réinitialisation du mot de passe temporaire de '{principal_id}'",
        mcp_ide_badge="💻 Appelé via MCP (IDE)",
        ontology_term_saved="Terme « {term} » enregistré au niveau {level}",
        ontology_promo_proposed="Promotion proposée pour « {term} » ({src} -> {dst})",
        ontology_promo_decided="Promotion {decision} pour « {term} » -> {level}",
        thinking_deep="Réflexion Élevée",
        thinking_std="Réflexion Standard",
        llm_step_label="💬 Modèle IA {model} ({provider} · {effort}) — réponse générée",
        org_unit_created="Création de l'unité '{name}' ({kind})",
        org_unit_updated="Mise à jour de l'unité '{name}' ({kind})",
        org_unit_deleted="Suppression de l'unité '{name}' ({kind})",
        invitation_summary="Invitation de {name} ({email}) sur '{unit_name}'",
        connector_test_detail="Banc de test connecteur {protocol}: {status_label}",
        connector_status_on="Activé",
        connector_status_off="Refusé",
        connector_disabled="Connecteur '{name}' désactivé dans la configuration.",
        workflow_what_if_sample=(
            "{h}\nSimulation What-If isolée pour {title} avec section complète et détaillée."
        ),
        pack_sdlc_title="Ingénierie Logicielle & Cycle de Vie Produit",
        pack_sdlc_domain="INGÉNIERIE LOGICIELLE & PRODUIT",
        pack_sdlc_desc=(
            "Connecteurs Git, Jira, Confluence et Nexus, processus guidés de spécification "
            "et réalisation, revues croisées et suivi de cohérence documentaire."
        ),
        pack_builder_title="Atelier de Création & Gouvernance de Packs Métiers",
        pack_builder_domain="GOUVERNANCE & MÉTHODOLOGIE",
        pack_builder_desc=(
            "Conception guidée de nouveaux Packs métiers, simulation d'impact avant "
            "évolution, certification des règles métiers et génération de fiches d'aide."
        ),
        pack_custom_domain="PACK MÉTIER PERSONNALISÉ",
    ),
    "en": RouterLocaleCopy(
        rag_reindex_initiated="Global vector corpus reindexing initiated successfully.",
        ai_test_audit_ok="AI model connection test {mapping_id}: {health}",
        ai_test_audit_err="AI model connection test {mapping_id}: ERROR ({err_type})",
        tool_intercepted_write=(
            "Execution of `{tool_label}` was intercepted (Lock V5 / Process Write Gate) "
            "and converted into an explicit human-validation proposal."
        ),
        bootstrap_missing_model="❌ Test failed: please enter the primary model identifier.",
        bootstrap_invalid_url=(
            "❌ Test failed: please enter a valid API URL starting with https:// or http://."
        ),
        bootstrap_missing_api_key=(
            "❌ Test failed: please enter your API key (secret token) or select 'No key'."
        ),
        bootstrap_connect_failed="❌ Connection test failed: {err_msg}",
        iam_created="IAM account '{principal_id}' created",
        iam_updated="IAM account '{principal_id}' updated",
        iam_pw_reset="Temporary password reset for '{principal_id}'",
        mcp_ide_badge="💻 Called via MCP (IDE)",
        ontology_term_saved="Term « {term} » saved at level {level}",
        ontology_promo_proposed="Promotion proposed for « {term} » ({src} -> {dst})",
        ontology_promo_decided="Promotion {decision} for « {term} » -> {level}",
        thinking_deep="High Thinking",
        thinking_std="Standard Thinking",
        llm_step_label="💬 AI Model {model} ({provider} · {effort}) — reply generated",
        org_unit_created="Organization unit '{name}' ({kind}) created",
        org_unit_updated="Organization unit '{name}' ({kind}) updated",
        org_unit_deleted="Organization unit '{name}' ({kind}) deleted",
        invitation_summary="Invitation of {name} ({email}) to '{unit_name}'",
        connector_test_detail="Connector test bench {protocol}: {status_label}",
        connector_status_on="Enabled",
        connector_status_off="Denied",
        connector_disabled="Connector '{name}' is disabled in configuration.",
        workflow_what_if_sample=(
            "{h}\nIsolated What-If simulation for {title} with complete detailed section."
        ),
        pack_sdlc_title="Software Engineering & Product Lifecycle",
        pack_sdlc_domain="SOFTWARE ENGINEERING & PRODUCT",
        pack_sdlc_desc=(
            "Git, Jira, Confluence, and Nexus connectors, guided specification and delivery "
            "processes, cross-checked reviews, and documentation consistency tracking."
        ),
        pack_builder_title="Business Pack Authoring & Governance Studio",
        pack_builder_domain="GOVERNANCE & METHODOLOGY",
        pack_builder_desc=(
            "Guided creation of new Business Packs, impact simulation before evolution, "
            "business rule certification, and help article generation."
        ),
        pack_custom_domain="CUSTOM BUSINESS PACK",
    ),
}

SHELL_SCOPE_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "org_unit_name": "Sous-Équipe Checkout & Core Solutions",
        "scope_global": "Plateforme Globale ORCIA",
        "scope_bu": "BU Produits & Plateformes",
        "scope_team": "Équipe Architecture & Agentique",
        "scope_ws": "Workspace Solution ORCIA Core",
    },
    "en": {
        "org_unit_name": "Checkout & Core Solutions Sub-Team",
        "scope_global": "ORCIA Global Platform",
        "scope_bu": "Products & Platforms BU",
        "scope_team": "Architecture & Agentic Team",
        "scope_ws": "ORCIA Core Solution Workspace",
    },
}


def get_router_copy(locale: str | SupportedLocale = DEFAULT_LOCALE) -> RouterLocaleCopy:
    norm: SupportedLocale = "en" if str(locale).lower().startswith("en") else "fr"
    return ROUTER_LOCALE_MESSAGES[norm]


def get_shell_scope_copy(locale: str | SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    norm: SupportedLocale = "en" if str(locale).lower().startswith("en") else "fr"
    return SHELL_SCOPE_LOCALES[norm]


__all__ = [
    "ROUTER_LOCALE_MESSAGES",
    "RouterLocaleCopy",
    "SHELL_SCOPE_LOCALES",
    "get_router_copy",
    "get_shell_scope_copy",
]
