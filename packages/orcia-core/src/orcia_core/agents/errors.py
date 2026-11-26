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


class ProcessModelNotConfiguredError(OrciaDomainError):
    """Raised when no active workspace/platform LLM is configured for live execution."""

    error_code = "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL"
    http_status = 422
    type_slug = "process-model-not-configured"


class ProcessDatasourcesRequiredError(OrciaDomainError):
    """Raised when a live process execution lacks attached workspace datasources or inputs."""

    error_code = "ERR_PROCESS_DATASOURCES_REQUIRED"
    http_status = 422
    type_slug = "process-datasources-required"


__all__ = [
    "AGENTS_ERROR_CATALOG",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "PolicyDeniedError",
    "ProcessDatasourcesRequiredError",
    "ProcessModelNotConfiguredError",
    "ReflexiveInvalidStateError",
    "ReflexiveSessionExpiredError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
