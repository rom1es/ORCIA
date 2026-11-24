"""RAG & Knowledge Base domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from collections.abc import Mapping

from orcia_core.rag._error_catalog import RAG_ERROR_CATALOG
from orcia_kernel.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

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
        detail_code: str | None = None,
        detail_params: Mapping[str, object] | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        self.progress_percentage = progress_percentage
        self.job_id = job_id
        super().__init__(
            detail_override=detail_override,
            detail_code=detail_code,
            detail_params=detail_params,
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
    "RAG_ERROR_CATALOG",
    "RagReindexInProgressError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
