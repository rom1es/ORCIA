"""Bilingual locale strings for `DeterministicCassetteLLM` (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

CASSETTE_DEFAULT_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "fast_path_assumption": "[ASSUMPTION] Option par défaut retenue en mode Fast-Path.",
    },
    "en": {
        "fast_path_assumption": "[ASSUMPTION] Default option retained in Fast-Path mode.",
    },
}


def get_cassette_default_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return CASSETTE_DEFAULT_LOCALES.get(locale, CASSETTE_DEFAULT_LOCALES[DEFAULT_LOCALE])


__all__ = ["CASSETTE_DEFAULT_LOCALES", "get_cassette_default_copy"]
