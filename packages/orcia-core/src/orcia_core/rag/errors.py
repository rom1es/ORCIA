"""RAG & Knowledge Base domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import (
    LocalizedErrorCopy,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

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
    "ERR_RAG_REINDEX_IN_PROGRESS": {
        "fr": LocalizedErrorCopy(
            "Réindexation sémantique en cours",
            "Une réindexation globale du corpus vectoriel est actuellement en cours. "
            "La recherche documentaire et Mon Assistant sont temporairement indisponibles.",
        ),
        "en": LocalizedErrorCopy(
            "Semantic reindexing in progress",
            "A global reindexing of the vector corpus is currently in progress. "
            "Document search and My Assistant are temporarily unavailable.",
        ),
    },
}

register_domain_error_catalog(RAG_ERROR_CATALOG)


class DdlOnlyTransactionalDataError(OrciaDomainError):
    error_code = "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN"
    http_status, type_slug = 422, "ddl-only-transactional-data-forbidden"


class EmptyOrUnreadableDocumentError(OrciaDomainError):
    error_code = "ERR_EMPTY_OR_UNREADABLE_DOCUMENT"
    http_status, type_slug = 422, "empty-or-unreadable-document"


class EmbeddingDimensionMismatchError(OrciaDomainError):
    error_code = "ERR_EMBEDDING_DIMENSION_MISMATCH"
    http_status, type_slug = 422, "embedding-dimension-mismatch"


class EmbeddingGenerationFailedError(OrciaDomainError):
    error_code = "ERR_EMBEDDING_GENERATION_FAILED"
    http_status, type_slug = 502, "embedding-generation-failed"


class EmbeddingProviderUnsupportedError(OrciaDomainError):
    error_code = "ERR_EMBEDDING_PROVIDER_UNSUPPORTED"
    http_status, type_slug = 422, "embedding-provider-unsupported"


class NoActiveEmbeddingModelError(OrciaDomainError):
    error_code = "ERR_NO_ACTIVE_EMBEDDING_MODEL"
    http_status, type_slug = 422, "no-active-embedding-model"


class RagReindexInProgressError(OrciaDomainError):
    error_code = "ERR_RAG_REINDEX_IN_PROGRESS"
    http_status, type_slug = 503, "rag-reindex-in-progress"

    def __init__(
        self,
        *,
        progress_percentage: int = 0,
        job_id: str | None = None,
        detail_override: str | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        self.progress_percentage = progress_percentage
        self.job_id = job_id
        super().__init__(
            detail_override=detail_override,
            instance=instance,
            permission_broker_hint=permission_broker_hint,
        )


__all__ = [
    "DdlOnlyTransactionalDataError",
    "EmptyOrUnreadableDocumentError",
    "EmbeddingDimensionMismatchError",
    "EmbeddingGenerationFailedError",
    "EmbeddingProviderUnsupportedError",
    "NoActiveEmbeddingModelError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "RagReindexInProgressError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
