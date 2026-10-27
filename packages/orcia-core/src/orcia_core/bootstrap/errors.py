"""Bootstrap domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    HumanAnchorRequiredError,
    ModelOrthogonalityViolationError,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)

__all__ = [
    "HumanAnchorRequiredError",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
