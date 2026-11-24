"""Ontology domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_core.ontology._error_catalog import ONTOLOGY_ERROR_CATALOG
from orcia_kernel.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)


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
    "ONTOLOGY_ERROR_CATALOG",
    "ObserverModeReadOnlyError",
    "OntologyConflictError",
    "OntologyScopeConflictError",
    "OrciaDomainError",
    "PromotionLevelJumpError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
