"""Bootstrap domain errors (`AD-19`, `Story 3.2a`, `Story 9.2`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    HumanAnchorRequiredError,
    LocalizedErrorCopy,
    ModelOrthogonalityViolationError,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(
    {
        "ERR_INVALID_BOOTSTRAP_TOKEN": {
            "fr": LocalizedErrorCopy(
                "Jeton d'amorçage Jour 0 invalide ou manquant",
                "Pour tout environnement hors 'local', le jeton ORCIA_BOOTSTRAP_TOKEN "
                "généré au démarrage est obligatoire pour initialiser le premier administrateur.",
            ),
            "en": LocalizedErrorCopy(
                "Invalid or missing Day-0 bootstrap token",
                "For any non-'local' environment, the startup ORCIA_BOOTSTRAP_TOKEN "
                "is required to initialize the first platform administrator.",
            ),
        },
        "ERR_FIRST_USER_ALREADY_INITIALIZED": {
            "fr": LocalizedErrorCopy(
                "Premier administrateur déjà initialisé",
                "La table users contient déjà au moins un compte ; "
                "le parcours /welcome-setup est verrouillé contre toute reprise de contrôle.",
            ),
            "en": LocalizedErrorCopy(
                "First administrator already initialized",
                "The users table already contains at least one account; "
                "/welcome-setup is locked against first-user takeover.",
            ),
        },
    }
)


class InvalidBootstrapTokenError(OrciaDomainError):
    """Raised when `ORCIA_BOOTSTRAP_TOKEN` is invalid or missing on `ORCIA_ENV != 'local'`."""

    error_code = "ERR_INVALID_BOOTSTRAP_TOKEN"
    http_status = 403
    type_slug = "invalid-bootstrap-token"


class FirstUserAlreadyInitializedError(OrciaDomainError):
    """Raised when `COUNT(*) FROM users > 0` under `LOCK TABLE users IN EXCLUSIVE MODE`."""

    error_code = "ERR_FIRST_USER_ALREADY_INITIALIZED"
    http_status = 409
    type_slug = "first-user-already-initialized"


__all__ = [
    "FirstUserAlreadyInitializedError",
    "HumanAnchorRequiredError",
    "InvalidBootstrapTokenError",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
