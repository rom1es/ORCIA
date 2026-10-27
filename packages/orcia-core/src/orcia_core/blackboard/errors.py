"""Blackboard domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    LocalizedErrorCopy,
    OrciaDomainError,
    ResourceNotFoundError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(
    {
        "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION": {
            "fr": LocalizedErrorCopy(
                "Violation du Blackboard en ajout seul",
                "Les snapshots engagés dans blackboard_snapshots sont immuables.",
            ),
            "en": LocalizedErrorCopy(
                "Append-only Blackboard violation",
                "Committed snapshots in blackboard_snapshots are strictly immutable.",
            ),
        },
    }
)


class BlackboardAppendOnlyViolationError(OrciaDomainError):
    error_code = "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION"
    http_status, type_slug = 409, "blackboard-append-only-violation"


__all__ = [
    "BlackboardAppendOnlyViolationError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
