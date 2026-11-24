"""Localized RFC 9457 error catalog for the bootstrap domain (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

BOOTSTRAP_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_INVALID_BOOTSTRAP_TOKEN": {
        "fr": LocalizedErrorCopy(
            "Jeton d'amorçage Jour 0 invalide ou manquant",
            "Pour tout environnement hors 'local', le jeton ORCIA_BOOTSTRAP_TOKEN "
            "généré au démarrage est obligatoire pour initialiser le premier administrateur.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid or missing Day-0 bootstrap token",
            "For any non-'local' environment, the startup ORCIA_BOOTSTRAP_TOKEN "
            "is required to initialize the first platform administrator.",
        ),
    },
    "ERR_FIRST_USER_ALREADY_INITIALIZED": {
        "fr": LocalizedErrorCopy(
            "Premier administrateur déjà initialisé",
            "La table users contient déjà au moins un compte ; "
            "le parcours /welcome-setup est verrouillé contre toute reprise de contrôle.",
        ),
        "en": LocalizedErrorCopy(
            "First administrator already initialized",
            "The users table already contains at least one account; "
            "/welcome-setup is locked against first-user takeover.",
        ),
    },
    "ERR_NO_ACTIVE_EMBEDDING_MODEL_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Modèle d'indexation sémantique absent",
            "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
            "L'ajout ou la synchronisation de sources documentaires RAG nécessite "
            "un modèle d'indexation sémantique (/settings/ai-models).",
        ),
        "en": LocalizedErrorCopy(
            "No active semantic embedding model",
            "No active embedding model is configured at GLOBAL level. "
            "Adding or synchronizing RAG document sources requires a semantic indexing model "
            "(/settings/ai-models).",
        ),
    },
    "ERR_NO_ACTIVE_EMBEDDING_MODEL_SYNC_BLOCKED": {
        "fr": LocalizedErrorCopy(
            "Modèle d'indexation sémantique absent",
            "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
            "Ingestion documentaire bloquée.",
        ),
        "en": LocalizedErrorCopy(
            "No active semantic embedding model",
            "No active embedding model is configured at GLOBAL level. "
            "Document ingestion is blocked.",
        ),
    },
    "ERR_RAG_REINDEX_DOC_SYNC_QUEUED": {
        "fr": LocalizedErrorCopy(
            "Réindexation sémantique en cours",
            "Réindexation sémantique en cours ({progress}%). "
            "Synchronisation documentaire mise en attente.",
        ),
        "en": LocalizedErrorCopy(
            "Semantic reindexing in progress",
            "Semantic reindexing is in progress ({progress}%). Document sync queued.",
        ),
    },
    "ERR_LITELLM_MISSING_SECRET_REF": {
        "fr": LocalizedErrorCopy(
            "Référence de secret LLM manquante",
            "Aucune SecretRef configurée pour LiteLLMAdapter "
            "(DEC-SEC-01 : les clés par défaut en dur sont interdites).",
        ),
        "en": LocalizedErrorCopy(
            "Missing LLM SecretRef",
            "No SecretRef configured for LiteLLMAdapter "
            "(DEC-SEC-01: hardcoded default API keys are forbidden).",
        ),
    },
    "ERR_LITELLM_GOVERNED_CALL_FAILED": {
        "fr": LocalizedErrorCopy(
            "Échec de l'appel gouverné LLM",
            "Échec de l'appel gouverné via ConnectorInvoker : status={status}, code={code}",
        ),
        "en": LocalizedErrorCopy(
            "Governed LLM call failed",
            "Governed call failed via ConnectorInvoker: status={status}, code={code}",
        ),
    },
    "ERR_IAM_ACCOUNT_EMPTY_DISPLAY_NAME": {
        "fr": LocalizedErrorCopy(
            "Nom affiché invalide",
            "Le nom affiché du compte ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid display name",
            "The account display name cannot be empty.",
        ),
    },
    "ERR_ORG_ONTOLOGY_LEAD_BU_ONLY": {
        "fr": LocalizedErrorCopy(
            "Affectation de référent glossaire invalide",
            "Les référents glossaire (ONTOLOGY_LEAD) ne peuvent être affectés "
            "qu'à une Direction (BU).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid glossary lead assignment",
            "Glossary stewards (ONTOLOGY_LEAD) can only be assigned to a Business Unit (BU).",
        ),
    },
    "ERR_ORG_UNIT_EMPTY_NAME": {
        "fr": LocalizedErrorCopy(
            "Nom d'unité invalide",
            "Le nom de l'unité ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid unit name",
            "The organizational unit name cannot be empty.",
        ),
    },
    "ERR_ORG_UNIT_NOT_FOUND_REF": {
        "fr": LocalizedErrorCopy(
            "Unité organisationnelle introuvable",
            "Unité organisationnelle introuvable : '{unit_ref}'.",
        ),
        "en": LocalizedErrorCopy(
            "Organizational unit not found",
            "Organizational unit not found: '{unit_ref}'.",
        ),
    },
    "ERR_WIZARD_USER_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Utilisateur introuvable",
            "Utilisateur '{user_id}' introuvable dans PostgreSQL 18 "
            "pour démarrer une session wizard.",
        ),
        "en": LocalizedErrorCopy(
            "User not found",
            "User '{user_id}' not found in PostgreSQL 18 to start a wizard session.",
        ),
    },
    "ERR_WORKSPACE_INVALID_SLUG": {
        "fr": LocalizedErrorCopy(
            "Slug d'espace invalide",
            "Slug d'espace invalide : '{slug}'. "
            "Utilisez uniquement minuscules, chiffres et tirets (`^[a-z0-9-]+$`).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid space slug",
            "Invalid space slug: '{slug}'. "
            "Use only lowercase letters, digits, and hyphens (`^[a-z0-9-]+$`).",
        ),
    },
    "ERR_WORKSPACE_DERIVED_SLUG_INVALID": {
        "fr": LocalizedErrorCopy(
            "Slug d'espace impossible à dériver",
            "Impossible de dériver un slug valide depuis le nom de l'espace.",
        ),
        "en": LocalizedErrorCopy(
            "Cannot derive valid space slug",
            "Unable to derive a valid slug from the space name.",
        ),
    },
    "ERR_WORKSPACE_EMPTY_NAME": {
        "fr": LocalizedErrorCopy(
            "Nom d'espace vide",
            "Le nom de l'espace ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Empty space name",
            "The space name cannot be empty.",
        ),
    },
    "ERR_WORKSPACE_SLUG_EXISTS": {
        "fr": LocalizedErrorCopy(
            "Conflit de slug d'espace",
            "Un espace avec le slug '{slug}' existe déjà.",
        ),
        "en": LocalizedErrorCopy(
            "Space slug already exists",
            "A space with slug '{slug}' already exists.",
        ),
    },
}

register_domain_error_catalog(BOOTSTRAP_ERROR_CATALOG)

__all__ = ["BOOTSTRAP_ERROR_CATALOG"]
