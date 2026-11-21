"""Assistant Turn Reliability, Liveness & Rate-Limit Domain Errors (`AD-19`, `AD-25`)."""

from __future__ import annotations

from orcia_core.kernel.enums import SupportedLocale
from orcia_core.kernel.errors import (
    LocalizedErrorCopy,
    OrciaDomainError,
    register_domain_error_catalog,
)

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
}

register_domain_error_catalog(ASSISTANT_TURN_ERROR_CATALOG)


class AssistantTurnInterruptedError(OrciaDomainError):
    """Raised/emitted when an active turn's worker liveness expires mid-stream (`R1`)."""

    error_code = "ERR_ASSISTANT_TURN_INTERRUPTED"
    http_status = 503
    type_slug = "assistant-turn-interrupted"


class AssistantRateLimitExceededError(OrciaDomainError):
    """Raised when sliding-window rate limit for assistant turns is exceeded (`HTTP 429`)."""

    error_code = "ERR_ASSISTANT_RATE_LIMITED"
    http_status = 429
    type_slug = "assistant-rate-limited"

    def __init__(
        self,
        *,
        retry_after_s: int = 1,
        detail_override: str | None = None,
        instance: str | None = None,
    ) -> None:
        self.retry_after_s = max(1, retry_after_s)
        super().__init__(detail_override=detail_override, instance=instance)


class AssistantConcurrencyLimitError(OrciaDomainError):
    """Raised when per-user concurrent active assistant turn semaphore is exhausted (`429`)."""

    error_code = "ERR_ASSISTANT_CONCURRENCY_LIMIT"
    http_status = 429
    type_slug = "assistant-concurrency-limit"


__all__ = [
    "ASSISTANT_TURN_ERROR_CATALOG",
    "AssistantConcurrencyLimitError",
    "AssistantRateLimitExceededError",
    "AssistantTurnInterruptedError",
]
