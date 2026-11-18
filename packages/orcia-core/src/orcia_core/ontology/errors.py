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
    "ERR_ONTOLOGY_PROMOTION_STEP_INVALID": {
        "fr": LocalizedErrorCopy(
            "Transition de promotion ontologique invalide",
            "La promotion doit cibler le palier immédiatement supérieur (L4 -> L3 -> L2 -> L1).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid ontology promotion transition",
            "Promotion must target the immediate next governance level (L4 -> L3 -> L2 -> L1).",
        ),
    },
}

register_domain_error_catalog(ONTOLOGY_ERROR_CATALOG)


class OntologyConflictError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_ONTOLOGY_CONFLICT", 422, "ontology-conflict"


class OntologyScopeConflictError(OntologyConflictError):
    """Cross-scope ontology key collision (`HTTP 409 ERR_ONTOLOGY_CONFLICT`)."""

    error_code, http_status, type_slug = "ERR_ONTOLOGY_CONFLICT", 409, "ontology-scope-conflict"


class PromotionLevelJumpError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ONTOLOGY_PROMOTION_STEP_INVALID",
        422,
        "ontology-promotion-step-invalid",
    )


__all__ = [
    "ObserverModeReadOnlyError",
    "OntologyConflictError",
    "OntologyScopeConflictError",
    "OrciaDomainError",
    "PromotionLevelJumpError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
