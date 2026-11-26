"""Localized RFC 9457 error catalog for `orcia_core.agents` (`Story 27.7`)."""

from __future__ import annotations

from orcia_core.kernel.enums import SupportedLocale
from orcia_core.kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

AGENTS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_REFLEXIVE_SESSION_EXPIRED": {
        "fr": LocalizedErrorCopy(
            "Session d'exécution expirée (délai de 24h dépassé)",
            "La session en attente de validation d'écriture a dépassé sa durée de validité.",
        ),
        "en": LocalizedErrorCopy(
            "Reflexive execution session expired (24h TTL exceeded)",
            "The paused write-preview session exceeded its 24-hour validity window.",
        ),
    },
    "ERR_REFLEXIVE_STATE_INVALID": {
        "fr": LocalizedErrorCopy(
            "Transition d'état d'exécution invalide",
            "L'action demandée n'est pas compatible avec le statut courant de l'exécution.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid execution state transition",
            "The requested action is incompatible with the current execution status.",
        ),
    },
    "ERR_AGENTS_WRITE_GATE_MISSING": {
        "fr": LocalizedErrorCopy(
            "Port de gouvernance d'écriture manquant",
            "Aucun port de gouvernance d'écriture n'est configuré.",
        ),
        "en": LocalizedErrorCopy(
            "Write governance port missing",
            "No write-governance port is configured.",
        ),
    },
    "ERR_WRITE_PREVIEW_APPROVAL_REQUIRED_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Jeton d'approbation d'écriture requis",
            "ERR_WRITE_PREVIEW_APPROVAL_REQUIRED: Jeton signé requis.",
        ),
        "en": LocalizedErrorCopy(
            "Write preview approval token required",
            "ERR_WRITE_PREVIEW_APPROVAL_REQUIRED: Signed approval token required.",
        ),
    },
    "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Aucun modèle IA actif configuré",
            "Aucun modèle IA de dialogue (chat) actif n'est configuré pour cet espace. "
            "Veuillez configurer un modèle dans /settings/ai-models.",
        ),
        "en": LocalizedErrorCopy(
            "No active AI chat model configured",
            "No active chat AI model is configured for this workspace. "
            "Please configure a model in /settings/ai-models.",
        ),
    },
    "ERR_PROCESS_DATASOURCES_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Sources de données ou entrées requises pour ce processus",
            "Aucune source de données n'est attachée à cet espace et aucune entrée "
            "explicite n'a été fournie. Attachez au moins une source à l'espace ou "
            "fournissez des paramètres d'exécution.",
        ),
        "en": LocalizedErrorCopy(
            "Datasources or explicit inputs required for process run",
            "No datasources are attached to this workspace and no explicit step inputs "
            "were provided. Attach at least one workspace datasource or provide run inputs.",
        ),
    },
}

register_domain_error_catalog(AGENTS_ERROR_CATALOG)

__all__ = ["AGENTS_ERROR_CATALOG"]
