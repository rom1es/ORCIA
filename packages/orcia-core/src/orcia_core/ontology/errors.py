"""Ontology domain errors (`AD-19`, `Story 3.2a`)."""

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

ONTOLOGY_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_ONTOLOGY_CONFLICT": {
        "fr": LocalizedErrorCopy(
            "Conflit d'axiome ontologique immuable",
            "La spécialisation ou surcharge viole un axiome parent marqué immutable: true.",
        ),
        "en": LocalizedErrorCopy(
            "Immutable ontology axiom conflict",
            "The specialization or override violates a parent axiom marked immutable: true.",
        ),
    },
}

register_domain_error_catalog(ONTOLOGY_ERROR_CATALOG)


class OntologyConflictError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_ONTOLOGY_CONFLICT", 422, "ontology-conflict"


__all__ = [
    "ObserverModeReadOnlyError",
    "OntologyConflictError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
