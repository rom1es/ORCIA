"""Catalog domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)

__all__ = [
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
