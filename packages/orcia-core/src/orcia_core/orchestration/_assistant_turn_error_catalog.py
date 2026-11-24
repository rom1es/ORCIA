"""Assistant turn reliability, liveness, and rate-limit localized error catalog (`AD-25`)."""

from __future__ import annotations

from orcia_core.kernel.enums import SupportedLocale
from orcia_core.kernel.errors import LocalizedErrorCopy

ASSISTANT_TURN_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_ASSISTANT_TURN_INTERRUPTED": {
        "fr": LocalizedErrorCopy(
            "Tour d'assistant interrompu",
            "Le worker exécutant ce tour s'est arrêté de manière inattendue. "
            "Relancez votre demande pour continuer.",
        ),
        "en": LocalizedErrorCopy(
            "Assistant turn interrupted",
            "The worker executing this assistant turn terminated unexpectedly. "
            "Please submit a new request to continue.",
        ),
    },
    "ERR_ASSISTANT_RATE_LIMITED": {
        "fr": LocalizedErrorCopy(
            "Limite de débit de l'assistant atteinte",
            "Trop de requêtes assistant envoyées sur une courte période. "
            "Veuillez patienter quelques secondes avant de réessayer.",
        ),
        "en": LocalizedErrorCopy(
            "Assistant rate limit exceeded",
            "Too many assistant requests were submitted in a short window. "
            "Please wait a few seconds before retrying.",
        ),
    },
    "ERR_ASSISTANT_CONCURRENCY_LIMIT": {
        "fr": LocalizedErrorCopy(
            "Limite de tours simultanés atteinte",
            "Vous avez atteint le nombre maximal de tours d'assistant actifs simultanément.",
        ),
        "en": LocalizedErrorCopy(
            "Assistant concurrency limit exceeded",
            "You have reached the maximum number of concurrently running assistant turns.",
        ),
    },
    "ERR_ASSISTANT_TURN_BUDGET_EXCEEDED": {
        "fr": LocalizedErrorCopy(
            "Budget d'exécution du tour d'assistant dépassé",
            "La boucle d'outils de l'assistant a atteint sa limite autorisée "
            "(itérations, jetons ou durée maximale).",
        ),
        "en": LocalizedErrorCopy(
            "Assistant turn execution budget exceeded",
            "The assistant tool loop reached its configured limit "
            "(max iterations, token budget, or wall-clock duration).",
        ),
    },
}

__all__ = ["ASSISTANT_TURN_ERROR_CATALOG"]
