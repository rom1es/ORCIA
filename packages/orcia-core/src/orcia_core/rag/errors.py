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
}

register_domain_error_catalog(RAG_ERROR_CATALOG)


class DdlOnlyTransactionalDataError(OrciaDomainError):
    error_code = "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN"
    http_status, type_slug = 422, "ddl-only-transactional-data-forbidden"


class EmptyOrUnreadableDocumentError(OrciaDomainError):
    error_code = "ERR_EMPTY_OR_UNREADABLE_DOCUMENT"
    http_status, type_slug = 422, "empty-or-unreadable-document"


__all__ = [
    "DdlOnlyTransactionalDataError",
    "EmptyOrUnreadableDocumentError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
