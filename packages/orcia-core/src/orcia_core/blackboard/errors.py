"""Blackboard domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_core.blackboard._error_catalog import BLACKBOARD_ERROR_CATALOG
from orcia_kernel.errors import (
    OrciaDomainError,
    ResourceNotFoundError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(BLACKBOARD_ERROR_CATALOG)


class BlackboardAppendOnlyViolationError(OrciaDomainError):
    error_code = "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION"
    http_status, type_slug = 409, "blackboard-append-only-violation"


__all__ = [
    "BlackboardAppendOnlyViolationError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
