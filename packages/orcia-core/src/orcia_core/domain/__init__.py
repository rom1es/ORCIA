"""Pure hexagonal domain primitives re-exported from `orcia_kernel` (AD-19).

Note: Domain-specific exceptions live in `orcia_core.<domaine>.errors` (never in a catch-all
`domain/exceptions.py`). Base error contracts and common errors live in `orcia_kernel.errors`.
"""

from __future__ import annotations

from orcia_kernel.errors import (
    ERROR_CATALOG,
    OrciaDomainError,
    ResourceNotFoundError,
    SupportedLocale,
    ValidationDomainError,
    get_localized_error_text,
    register_domain_error_catalog,
    resolve_locale,
)
from orcia_kernel.ids import (
    compute_bytes_sha256,
    extract_uuid7_timestamp_ms,
    is_valid_uuid7,
    new_uuid7,
    new_uuid7_str,
)

__all__ = [
    "ERROR_CATALOG",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "SupportedLocale",
    "ValidationDomainError",
    "compute_bytes_sha256",
    "extract_uuid7_timestamp_ms",
    "get_localized_error_text",
    "is_valid_uuid7",
    "new_uuid7",
    "new_uuid7_str",
    "register_domain_error_catalog",
    "resolve_locale",
]
