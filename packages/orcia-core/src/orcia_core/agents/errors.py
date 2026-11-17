"""Domain errors for `orcia_core.agents` (`AD-19`, `Story 16.2`)."""

from __future__ import annotations

from orcia_core.kernel.enums import SupportedLocale
from orcia_core.kernel.errors import (
    LocalizedErrorCopy,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    PolicyDeniedError,
    ResourceNotFoundError,
    ValidationDomainError,
    register_domain_error_catalog,
)

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
}

register_domain_error_catalog(AGENTS_ERROR_CATALOG)


class ReflexiveSessionExpiredError(ValidationDomainError):
    """Raised when attempting to resume a `ReflexiveSessionSnapshot` past its 24h TTL."""


class ReflexiveInvalidStateError(ValidationDomainError):
    """Raised when an execution transition does not match the expected session status."""


__all__ = [
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "PolicyDeniedError",
    "ReflexiveInvalidStateError",
    "ReflexiveSessionExpiredError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
