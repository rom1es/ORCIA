"""Bootstrap domain errors (`AD-19`, `Story 3.2a`, `Story 9.2`)."""

from __future__ import annotations

from orcia_core.bootstrap._error_catalog import BOOTSTRAP_ERROR_CATALOG
from orcia_kernel.errors import (
    HumanAnchorRequiredError,
    ModelOrthogonalityViolationError,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)


class InvalidBootstrapTokenError(OrciaDomainError):
    """Raised when `ORCIA_BOOTSTRAP_TOKEN` is invalid or missing on `ORCIA_ENV != 'local'`."""

    error_code = "ERR_INVALID_BOOTSTRAP_TOKEN"
    http_status = 403
    type_slug = "invalid-bootstrap-token"


class FirstUserAlreadyInitializedError(OrciaDomainError):
    """Raised when `COUNT(*) FROM users > 0` under `LOCK TABLE users IN EXCLUSIVE MODE`."""

    error_code = "ERR_FIRST_USER_ALREADY_INITIALIZED"
    http_status = 409
    type_slug = "first-user-already-initialized"


__all__ = [
    "BOOTSTRAP_ERROR_CATALOG",
    "FirstUserAlreadyInitializedError",
    "HumanAnchorRequiredError",
    "InvalidBootstrapTokenError",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
