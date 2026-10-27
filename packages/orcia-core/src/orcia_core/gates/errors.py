"""Gates domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    ModelOrthogonalityViolationError,
    OrciaDomainError,
    ValidationDomainError,
)

__all__ = [
    "ModelOrthogonalityViolationError",
    "OrciaDomainError",
    "ValidationDomainError",
]
