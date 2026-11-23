"""Localized FR/EN internal prompts and messages for assistant turn producer."""

from __future__ import annotations


def _is_english_locale(locale: str) -> bool:
    return (locale or "fr").strip().lower().startswith("en")


def build_synthesize_now_prompt(locale: str) -> str:
    """Return the forced-synthesis prompt for `synthesize-now` in FR or EN."""
    if _is_english_locale(locale):
        return (
            "Early synthesis requested (`synthesize-now`). Synthesize a concise final "
            "answer now from gathered evidence without calling additional tools."
        )
    return (
        "Synthèse anticipée demandée (`synthesize-now`). Synthétise dès maintenant une "
        "réponse finale concise à partir des preuves déjà collectées, sans appeler "
        "d'outils supplémentaires."
    )


def build_budget_reached_prompt(locale: str) -> str:
    """Return the forced-synthesis prompt when tool-loop budget is reached."""
    if _is_english_locale(locale):
        return (
            "Execution budget reached. Synthesize a concise final answer from the "
            "tool results already gathered without calling additional tools."
        )
    return (
        "Budget d'exécution atteint. Synthétise une réponse finale concise à partir des "
        "résultats d'outils déjà collectés, sans appeler d'outils supplémentaires."
    )


def format_governed_tool_round_summary(tool_count: int, locale: str) -> str:
    """Return the localized reflexive step summary for a governed tool round."""
    if _is_english_locale(locale):
        return f"Executed {tool_count} governed tool call(s)"
    plural = "s" if tool_count > 1 else ""
    return f"{tool_count} appel{plural} d'outil gouverné{plural} exécuté{plural}"


def format_zero_tokens_error_detail(model_name: str, endpoint_uri: str, locale: str) -> str:
    """Return the localized zero-token provider failure message."""
    if _is_english_locale(locale):
        return (
            f"AI model {model_name} ({endpoint_uri}) "
            "returned zero tokens. Verify provider availability."
        )
    return (
        f"Le modèle IA {model_name} ({endpoint_uri}) n'a renvoyé aucun jeton. "
        "Vérifiez la disponibilité du fournisseur."
    )
