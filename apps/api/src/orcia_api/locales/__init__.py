"""Localized message bundles and sanitization templates for `apps/api` (`Story 27.7`)."""

from __future__ import annotations

from orcia_api.locales._assistant_sanitization_locales import (
    CODE_INTENT_RE,
    DECISION_INTENT_RE,
    DOC_INTENT_RE,
    STEP_TEMPLATES_BY_LOCALE,
)
from orcia_api.locales._router_locale_messages import (
    ROUTER_LOCALE_MESSAGES,
    RouterLocaleCopy,
    get_router_copy,
)

__all__ = [
    "CODE_INTENT_RE",
    "DECISION_INTENT_RE",
    "DOC_INTENT_RE",
    "ROUTER_LOCALE_MESSAGES",
    "RouterLocaleCopy",
    "STEP_TEMPLATES_BY_LOCALE",
    "get_router_copy",
]
