"""Bilingual (`fr`/`en`) shell & organization scope display labels (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

SHELL_SCOPE_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "org_unit_name": "Sous-Équipe Checkout & Core Solutions",
        "scope_global": "Plateforme Globale ORCIA",
        "scope_bu": "BU Produits & Plateformes",
        "scope_team": "Équipe Architecture & Agentique",
        "scope_ws": "Workspace Solution ORCIA Core",
    },
    "en": {
        "org_unit_name": "Checkout & Core Solutions Sub-Team",
        "scope_global": "ORCIA Global Platform",
        "scope_bu": "Products & Platforms BU",
        "scope_team": "Architecture & Agentic Team",
        "scope_ws": "ORCIA Core Solution Workspace",
    },
}


def get_shell_scope_copy(locale: str | SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    """Return bilingual scope display labels for the requested locale."""
    norm: SupportedLocale = "en" if str(locale).lower().startswith("en") else "fr"
    return SHELL_SCOPE_LOCALES[norm]


__all__ = ["SHELL_SCOPE_LOCALES", "get_shell_scope_copy"]
