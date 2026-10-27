"""Centralized RFC 9457 error registry package for `apps/api` (`AD-12`, `AD-19`)."""

from __future__ import annotations

from orcia_api.errors.registry import (
    DOMAIN_ERROR_CLASSES,
    ERROR_CATALOG,
    ERROR_CLASS_REGISTRY,
    ERROR_CODE_REGISTRY,
    ErrorHttpMapping,
    OrciaDomainError,
    get_localized_error_text,
    resolve_domain_error_mapping,
    resolve_locale,
)

__all__ = [
    "DOMAIN_ERROR_CLASSES",
    "ERROR_CATALOG",
    "ERROR_CLASS_REGISTRY",
    "ERROR_CODE_REGISTRY",
    "ErrorHttpMapping",
    "OrciaDomainError",
    "get_localized_error_text",
    "resolve_domain_error_mapping",
    "resolve_locale",
]
