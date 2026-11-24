"""Bilingual FR/EN locale helpers for contextual help resolution (`Story 27.7`)."""

from __future__ import annotations

from orcia_core.catalog.contextual_help_models import HelpLanguageCode

_ASSISTANT_PREFILL_TEMPLATES: dict[HelpLanguageCode, str] = {
    "fr": "Explique-moi comment utiliser l'écran {route} ({title})",
    "en": "Help me understand screen {route} ({title})",
}


def build_localized_assistant_prefill(route: str, title: str, lang: HelpLanguageCode) -> str:
    """Build localized contextual prompt prefill for the Ask-Assistant CTA."""
    tpl = _ASSISTANT_PREFILL_TEMPLATES.get(lang, _ASSISTANT_PREFILL_TEMPLATES["fr"])
    return tpl.format(route=route, title=title)
