"""RAG & Knowledge Base localized RFC 9457 error catalog (`AD-19`, `Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

RAG_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Données transactionnelles interdites dans le RAG DB (DDL uniquement)",
            "Le régime DB_DDL_ONLY n'autorise que les schémas DDL (CREATE TABLE) et interdit "
            "toute indexation de lignes transactionnelles.",
        ),
        "en": LocalizedErrorCopy(
            "Transactional data forbidden in DB RAG (DDL only)",
            "The DB_DDL_ONLY regime only allows DDL schema definitions (CREATE TABLE) and "
            "forbids indexing transactional rows.",
        ),
    },
    "ERR_EMPTY_OR_UNREADABLE_DOCUMENT": {
        "fr": LocalizedErrorCopy(
            "Document vide ou PDF scanné illisible (0 caractère exploitable)",
            "L'extraction texte du document a produit 0 caractère exploitable. Le fichier est "
            "rejeté avant toute vectorisation (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Empty or unreadable scanned document (0 usable characters)",
            "Text extraction produced 0 usable characters. The document was rejected before "
            "any vectorization (AD-21).",
        ),
    },
    "ERR_EMBEDDING_DIMENSION_MISMATCH": {
        "fr": LocalizedErrorCopy(
            "Dimension du modèle d'embedding incompatible (1024 requise)",
            "Le modèle d'embedding a retourné un vecteur de dimension incompatible. "
            "La dimension exacte imposée pour le corpus vectoriel ORCIA est de 1024.",
        ),
        "en": LocalizedErrorCopy(
            "Incompatible embedding model dimension (1024 required)",
            "The embedding model returned a vector with an incompatible dimension. "
            "The exact dimension required for ORCIA vector corpus is 1024.",
        ),
    },
    "ERR_EMBEDDING_GENERATION_FAILED": {
        "fr": LocalizedErrorCopy(
            "Échec de génération des embeddings sémantiques",
            "L'appel au fournisseur d'embeddings a échoué (erreur réseau, authentification, "
            "dépassement de quota ou réponse invalide).",
        ),
        "en": LocalizedErrorCopy(
            "Semantic embedding generation failed",
            "Call to embedding provider failed (network error, authentication, "
            "rate limit or invalid response).",
        ),
    },
    "ERR_EMBEDDING_PROVIDER_UNSUPPORTED": {
        "fr": LocalizedErrorCopy(
            "Fournisseur non compatible avec l'usage embedding",
            "Le fournisseur ou protocole sélectionné ne propose aucune API d'embeddings "
            "(ex. Anthropic). Choisissez un fournisseur compatible "
            "(OpenAI, Mistral, Gemini, Ollama).",
        ),
        "en": LocalizedErrorCopy(
            "Provider unsupported for embedding usage",
            "The selected provider or protocol does not offer a native embedding API "
            "(e.g. Anthropic). Choose a compatible provider (OpenAI, Mistral, Gemini, Ollama).",
        ),
    },
    "ERR_EMBEDDING_ANTHROPIC_UNSUPPORTED": {
        "fr": LocalizedErrorCopy(
            "Fournisseur non compatible avec l'usage embedding",
            "Le fournisseur Anthropic ne propose aucune API native d'embeddings sémantiques. "
            "Sélectionnez un fournisseur compatible (OpenAI, Mistral, Gemini, Ollama, vLLM).",
        ),
        "en": LocalizedErrorCopy(
            "Provider unsupported for embedding usage",
            "Anthropic does not provide a native semantic embeddings API. Select a compatible "
            "provider (OpenAI, Mistral, Gemini, Ollama, vLLM).",
        ),
    },
    "ERR_NO_ACTIVE_EMBEDDING_MODEL": {
        "fr": LocalizedErrorCopy(
            "Aucun modèle d'embedding actif configuré",
            "La plateforme ne dispose d'aucun modèle d'embedding actif au niveau global. "
            "Configurez et activez un modèle d'embedding dans /settings/ai-models.",
        ),
        "en": LocalizedErrorCopy(
            "No active embedding model configured",
            "The platform has no active embedding model configured globally. "
            "Configure and activate an embedding model in /settings/ai-models.",
        ),
    },
    "ERR_NO_ACTIVE_EMBEDDING_MODEL_VECTORIZE": {
        "fr": LocalizedErrorCopy(
            "Aucun modèle d'embedding actif configuré",
            "Aucun modèle d'embedding actif configuré pour vectoriser la requête.",
        ),
        "en": LocalizedErrorCopy(
            "No active embedding model configured",
            "No active embedding model is configured to vectorize the query.",
        ),
    },
    "ERR_NO_ACTIVE_EMBEDDING_MODEL_INGEST": {
        "fr": LocalizedErrorCopy(
            "Aucun modèle d'embedding actif configuré",
            "Aucun modèle d'embedding actif configuré. Ingestion documentaire bloquée.",
        ),
        "en": LocalizedErrorCopy(
            "No active embedding model configured",
            "No active embedding model is configured. Document ingestion is blocked.",
        ),
    },
    "ERR_RAG_REINDEX_IN_PROGRESS": {
        "fr": LocalizedErrorCopy(
            "Réindexation sémantique en cours",
            "Une réindexation globale du corpus vectoriel est actuellement en cours. "
            "La recherche documentaire et l'ingestion RAG sont temporairement indisponibles.",
        ),
        "en": LocalizedErrorCopy(
            "Semantic reindexing in progress",
            "A global reindexing of the vector corpus is currently in progress. "
            "Document search and RAG ingestion are temporarily unavailable.",
        ),
    },
    "ERR_RAG_REINDEX_PROGRESS_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Réindexation sémantique en cours",
            "Réindexation sémantique en cours ({progress_percentage}%). "
            "La recherche documentaire et l'ingestion RAG sont temporairement indisponibles.",
        ),
        "en": LocalizedErrorCopy(
            "Semantic reindexing in progress",
            "Semantic reindexing in progress ({progress_percentage}%). "
            "Document search and RAG ingestion are temporarily unavailable.",
        ),
    },
    "ERR_RAG_REINDEX_FAILED_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Échec de la réindexation sémantique",
            "La réindexation sémantique a échoué ({error_message}). "
            "Veuillez relancer la réindexation dans /settings/ai-models.",
        ),
        "en": LocalizedErrorCopy(
            "Semantic reindexing failed",
            "Semantic reindexing failed ({error_message}). "
            "Please restart reindexing in /settings/ai-models.",
        ),
    },
}

__all__ = ["RAG_ERROR_CATALOG"]
