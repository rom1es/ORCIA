"""Localized RFC 9457 error catalog for `apps/api` router & guard messages (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

API_EXTRA_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_RAG_REINDEX_IN_PROGRESS_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Réindexation sémantique en cours",
            "Réindexation sémantique en cours ({progress}%). "
            "La recherche documentaire et l'ingestion RAG sont temporairement indisponibles.",
        ),
        "en": LocalizedErrorCopy(
            "Semantic reindexing in progress",
            "Semantic reindexing in progress ({progress}%). "
            "Document search and RAG ingestion are temporarily unavailable.",
        ),
    },
    "ERR_RAG_NO_ACTIVE_EMBEDDING_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Aucun modèle d'embedding actif",
            "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
            "Veuillez en configurer un dans /settings/ai-models.",
        ),
        "en": LocalizedErrorCopy(
            "No active embedding model configured",
            "No active embedding model is configured at GLOBAL level. "
            "Please configure one in /settings/ai-models.",
        ),
    },
    "ERR_RAG_REINDEX_NO_EMBEDDING_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Modèle d'embedding actif requis",
            "Impossible de lancer la réindexation : aucun modèle d'embedding actif configuré "
            "au niveau GLOBAL. Activez un modèle dans /settings/ai-models.",
        ),
        "en": LocalizedErrorCopy(
            "Active embedding model required",
            "Cannot start reindexing: no active embedding model is configured at GLOBAL level. "
            "Enable a model in /settings/ai-models.",
        ),
    },
    "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Aucun modèle IA de dialogue configuré",
            "Aucun modèle IA de dialogue (chat) actif n'est configuré. "
            "Veuillez configurer un modèle chat dans /settings/ai-models.",
        ),
        "en": LocalizedErrorCopy(
            "No active chat AI model configured",
            "No active chat AI model is configured. "
            "Please configure a chat model in /settings/ai-models.",
        ),
    },
    "ERR_IAM_PLATFORM_ADMIN_ONLY_ROLE": {
        "fr": LocalizedErrorCopy(
            "Privilège PLATFORM_ADMIN requis",
            "Seul un Administrateur Plateforme peut attribuer ou retirer le rôle PLATFORM_ADMIN.",
        ),
        "en": LocalizedErrorCopy(
            "PLATFORM_ADMIN privilege required",
            "Only a Platform Administrator can assign or revoke the PLATFORM_ADMIN role.",
        ),
    },
    "ERR_ONTOLOGY_PROMOTION_ALREADY_PROCESSED": {
        "fr": LocalizedErrorCopy(
            "Proposition déjà traitée",
            "La proposition de promotion '{proposal_id}' a déjà été traitée.",
        ),
        "en": LocalizedErrorCopy(
            "Promotion proposal already processed",
            "Promotion proposal '{proposal_id}' has already been processed.",
        ),
    },
    "ERR_ORG_UNIT_NAME_EMPTY": {
        "fr": LocalizedErrorCopy(
            "Nom d'unité organisationnelle vide",
            "Le nom de l'unité ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Empty organization unit name",
            "The organization unit name cannot be empty.",
        ),
    },
    "ERR_ORG_PG_SCHEMA_OUTDATED": {
        "fr": LocalizedErrorCopy(
            "Schéma PostgreSQL organisation incompatible",
            "Schéma PostgreSQL de l'organisation obsolète ou incompatible lors de '{op}' "
            "({exc}). Une migration Alembic est requise.",
        ),
        "en": LocalizedErrorCopy(
            "Outdated PostgreSQL organization schema",
            "PostgreSQL organization schema is outdated or incompatible during '{op}' "
            "({exc}). An Alembic migration is required.",
        ),
    },
    "ERR_EXEC_TRACE_NOT_INITIALIZED": {
        "fr": LocalizedErrorCopy(
            "Exécution non initialisée",
            "L'exécution '{execution_id}' est introuvable ou non initialisée.",
        ),
        "en": LocalizedErrorCopy(
            "Execution not initialized",
            "Execution '{execution_id}' was not found or is not initialized.",
        ),
    },
    "ERR_EXEC_STEP_MISMATCH": {
        "fr": LocalizedErrorCopy(
            "Étape d'exécution incohérente",
            "L'étape '{step_key}' ne correspond pas à '{execution_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Execution step mismatch",
            "Step '{step_key}' does not match '{execution_id}'.",
        ),
    },
    "ERR_ORG_PG_UNAVAILABLE_WORKSPACE": {
        "fr": LocalizedErrorCopy(
            "PostgreSQL 18 indisponible",
            "PostgreSQL 18 indisponible pour la création d'espace.",
        ),
        "en": LocalizedErrorCopy(
            "PostgreSQL 18 unavailable",
            "PostgreSQL 18 is unavailable for workspace creation.",
        ),
    },
    "ERR_INVITATION_FULL_NAME_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Nom complet requis",
            "Le nom complet de l'utilisateur invité est requis.",
        ),
        "en": LocalizedErrorCopy(
            "Full name required",
            "The invited user's full name is required.",
        ),
    },
    "ERR_INVITATION_INVALID_EMAIL": {
        "fr": LocalizedErrorCopy(
            "Adresse e-mail invalide",
            "Adresse e-mail invalide pour l'invitation utilisateur.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid email address",
            "Invalid email address for user invitation.",
        ),
    },
    "ERR_IAM_PLATFORM_ADMIN_ONLY_DELETE": {
        "fr": LocalizedErrorCopy(
            "Privilège PLATFORM_ADMIN requis",
            "Seul un Administrateur Plateforme peut supprimer un compte PLATFORM_ADMIN.",
        ),
        "en": LocalizedErrorCopy(
            "PLATFORM_ADMIN privilege required",
            "Only a Platform Administrator can delete a PLATFORM_ADMIN account.",
        ),
    },
    "ERR_EXEC_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Exécution introuvable",
            "L'exécution '{execution_id}' est introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Execution not found",
            "Execution '{execution_id}' was not found.",
        ),
    },
    "ERR_IAM_TEMP_PW_HUMAN_ONLY": {
        "fr": LocalizedErrorCopy(
            "Compte humain requis",
            "Seuls les comptes humains avec adresse e-mail valide "
            "peuvent recevoir un mot de passe temporaire.",
        ),
        "en": LocalizedErrorCopy(
            "Human account required",
            "Only human accounts with a valid email address can receive a temporary password.",
        ),
    },
    "ERR_ONTOLOGY_CONCEPT_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Concept introuvable",
            "Concept '{concept_key}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Concept not found",
            "Concept '{concept_key}' not found.",
        ),
    },
    "ERR_WRITE_PREVIEW_MISMATCH": {
        "fr": LocalizedErrorCopy(
            "Aperçu d'écriture incohérent",
            "ERR_WRITE_PREVIEW_MISMATCH: preview_id '{preview_id}' "
            "ne correspond pas à '{expected_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Write preview mismatch",
            "ERR_WRITE_PREVIEW_MISMATCH: preview_id '{preview_id}' does not match '{expected_id}'.",
        ),
    },
}

register_domain_error_catalog(API_EXTRA_ERROR_CATALOG)

__all__ = ["API_EXTRA_ERROR_CATALOG"]
