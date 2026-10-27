"""Permissions & Auth domain errors (`AD-19`, `Story 3.2a`).

Inherits from `orcia_kernel.errors.OrciaDomainError` and registers localized FR/EN copy.
"""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import (
    LocalizedErrorCopy,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

PERMISSIONS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_AUTH_INVALID_CREDENTIALS": {
        "fr": LocalizedErrorCopy(
            "Identifiants d'authentification invalides",
            "L'adresse e-mail, le mot de passe ou le jeton OIDC fourni est invalide.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid authentication credentials",
            "The supplied email, password, or OIDC token is invalid.",
        ),
    },
    "ERR_AUTH_MFA_INVALID": {
        "fr": LocalizedErrorCopy(
            "Code MFA TOTP invalide ou manquant",
            "Le code d'authentification multifacteur TOTP est requis ou incorrect.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid or missing TOTP MFA code",
            "A valid TOTP multi-factor authentication code is required.",
        ),
    },
    "ERR_AUTH_TOKEN_REVOKED": {
        "fr": LocalizedErrorCopy(
            "Session expirée ou révoquée",
            "Le jeton de session ou de rafraîchissement a expiré ou a été révoqué.",
        ),
        "en": LocalizedErrorCopy(
            "Session expired or revoked",
            "The session or refresh token has expired or has been revoked.",
        ),
    },
    "ERR_PERMISSION_BROKER_INTERCEPTED": {
        "fr": LocalizedErrorCopy(
            "Accès externe intercepté par le Permission Broker",
            "L'accès à la ressource externe a été refusé (401/403). Consultez la carte "
            "Permission Broker pour demander le rôle requis dans Jira.",
        ),
        "en": LocalizedErrorCopy(
            "External access intercepted by Permission Broker",
            "External resource access was denied (401/403). Inspect the Permission Broker "
            "card to request the required role in Jira.",
        ),
    },
    "ERR_CONFUSED_DEPUTY_BLOCKED": {
        "fr": LocalizedErrorCopy(
            "Élévation de privilèges Service Principal bloquée",
            "L'exécution en mode service_principal est interdite sans approbation explicite "
            "d'un administrateur (protection anti-Confused Deputy).",
        ),
        "en": LocalizedErrorCopy(
            "Service Principal privilege escalation blocked",
            "Execution in service_principal mode is forbidden without explicit administrator "
            "approval (anti-Confused Deputy protection).",
        ),
    },
}

register_domain_error_catalog(PERMISSIONS_ERROR_CATALOG)


class InvalidCredentialsError(OrciaDomainError):
    error_code = "ERR_AUTH_INVALID_CREDENTIALS"
    http_status, type_slug = 401, "auth-invalid-credentials"


class InvalidMfaCodeError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_MFA_INVALID", 401, "auth-mfa-invalid"


class RevokedTokenError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_TOKEN_REVOKED", 401, "auth-token-revoked"


class PermissionBrokerDeniedError(OrciaDomainError):
    error_code = "ERR_PERMISSION_BROKER_INTERCEPTED"
    http_status, type_slug = 403, "permission-broker-intercepted"


class ConfusedDeputyBlockedError(OrciaDomainError):
    error_code = "ERR_CONFUSED_DEPUTY_BLOCKED"
    http_status, type_slug = 403, "confused-deputy-blocked"


__all__ = [
    "ConfusedDeputyBlockedError",
    "InvalidCredentialsError",
    "InvalidMfaCodeError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "PermissionBrokerDeniedError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "RevokedTokenError",
    "ScopeAccessDeniedError",
    "ValidationDomainError",
]
