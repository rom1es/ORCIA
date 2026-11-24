"""Catalog domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_core.catalog._error_catalog import CATALOG_ERROR_CATALOG
from orcia_kernel.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(CATALOG_ERROR_CATALOG)

__all__ = [
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
