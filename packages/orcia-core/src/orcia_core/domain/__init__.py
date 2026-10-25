"""Pure hexagonal domain primitives: UUIDv7 identifiers and domain exceptions."""

from orcia_core.domain.exceptions import (
    ERROR_CATALOG,
    HumanAnchorRequiredError,
    ModelOrthogonalityViolationError,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    SupportedLocale,
    ValidationDomainError,
    get_localized_error_text,
    resolve_locale,
)
from orcia_core.domain.identifiers import (
    extract_uuid7_timestamp_ms,
    is_valid_uuid7,
    new_uuid7,
    new_uuid7_str,
)

__all__ = [
    "ERROR_CATALOG",
    "HumanAnchorRequiredError",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "SupportedLocale",
    "ValidationDomainError",
    "extract_uuid7_timestamp_ms",
    "get_localized_error_text",
    "is_valid_uuid7",
    "new_uuid7",
    "new_uuid7_str",
    "resolve_locale",
]
