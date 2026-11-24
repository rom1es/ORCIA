"""Domain errors for `orcia_core.agents` (`AD-19`, `Story 16.2`)."""

from __future__ import annotations

from orcia_core.agents._error_catalog import AGENTS_ERROR_CATALOG
from orcia_core.kernel.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    PolicyDeniedError,
    ResourceNotFoundError,
    ValidationDomainError,
)


class ReflexiveSessionExpiredError(ValidationDomainError):
    """Raised when attempting to resume a `ReflexiveSessionSnapshot` past its 24h TTL."""


class ReflexiveInvalidStateError(ValidationDomainError):
    """Raised when an execution transition does not match the expected session status."""


__all__ = [
    "AGENTS_ERROR_CATALOG",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "PolicyDeniedError",
    "ReflexiveInvalidStateError",
    "ReflexiveSessionExpiredError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
