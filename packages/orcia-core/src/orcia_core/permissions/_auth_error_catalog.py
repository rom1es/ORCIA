"""Authentication & SSO localized RFC 9457 error catalog (`AD-19`, `Story 3.2a`).

Zero framework imports (`fastapi`, `sqlalchemy`, etc.).
"""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

AUTH_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
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
    "ERR_AUTH_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Authentification requise",
            "Connectez-vous pour accéder à cette ressource.",
        ),
        "en": LocalizedErrorCopy(
            "Authentication required",
            "Sign in to access this resource.",
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
    "ERR_AUTH_WEAK_PASSWORD": {
        "fr": LocalizedErrorCopy(
            "Politique de mot de passe non respectée",
            "Le mot de passe doit comporter au moins 12 caractères et contenir au moins "
            "une lettre minuscule, une lettre majuscule et un chiffre.",
        ),
        "en": LocalizedErrorCopy(
            "Weak password policy violation",
            "The password must be at least 12 characters long and contain at least one "
            "lowercase letter, one uppercase letter, and one digit.",
        ),
    },
    "ERR_AUTH_PASSWORD_UNCHANGED": {
        "fr": LocalizedErrorCopy(
            "Nouveau mot de passe identique à l'actuel",
            "Le nouveau mot de passe doit être différent du mot de passe actuel.",
        ),
        "en": LocalizedErrorCopy(
            "New password matches current password",
            "The new password must be different from the current password.",
        ),
    },
    "ERR_AUTH_CURRENT_PASSWORD_INVALID": {
        "fr": LocalizedErrorCopy(
            "Mot de passe actuel incorrect",
            "Le mot de passe actuel saisi est incorrect. Vérifiez votre saisie puis réessayez.",
        ),
        "en": LocalizedErrorCopy(
            "Incorrect current password",
            "The current password entered is incorrect. Please check your entry and try again.",
        ),
    },
    "ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY": {
        "fr": LocalizedErrorCopy(
            "Mot de passe géré par votre fournisseur SSO",
            "Ce compte est connecté via SSO (OIDC) : son mot de passe ne peut pas être "
            "modifié localement dans ORCIA.",
        ),
        "en": LocalizedErrorCopy(
            "Password managed by SSO provider",
            "This account is signed in via SSO (OIDC): its password cannot be changed "
            "locally in ORCIA.",
        ),
    },
    "ERR_LOCAL_AUTH_DISABLED": {
        "fr": LocalizedErrorCopy(
            "Connexion locale désactivée par la politique d'authentification",
            "L'administrateur de la plateforme a configuré l'authentification unique (SSO) "
            "comme mode exclusif d'accès à ORCIA.",
        ),
        "en": LocalizedErrorCopy(
            "Local authentication disabled by platform policy",
            "The platform administrator configured organization SSO as the exclusive sign-in mode.",
        ),
    },
    "ERR_SSO_AUTH_DISABLED": {
        "fr": LocalizedErrorCopy(
            "Connexion SSO désactivée par la politique d'authentification",
            "L'administrateur de la plateforme a configuré l'authentification locale "
            "(e-mail et mot de passe) comme mode exclusif d'accès à ORCIA.",
        ),
        "en": LocalizedErrorCopy(
            "SSO authentication disabled by platform policy",
            "The platform administrator configured local credentials as the exclusive mode.",
        ),
    },
    "ERR_SSO_CONFIG_INCOMPLETE": {
        "fr": LocalizedErrorCopy(
            "Configuration SSO OIDC incomplète",
            "L'URL de l'émetteur OIDC, l'identifiant client et l'URI de redirection sont requis "
            "pour activer le mode SSO exclusif.",
        ),
        "en": LocalizedErrorCopy(
            "Incomplete OIDC SSO configuration",
            "OIDC issuer URL, client ID, and redirect URI are required to enable SSO mode.",
        ),
    },
    "ERR_AUTH_SMTP_CONNECTOR_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Connecteur SMTP actif requis pour l'envoi de codes par e-mail",
            "Configurez et activez un connecteur SMTP (SMTP_MAIL) dans l'onglet Connecteurs avant "
            "d'activer la vérification à 6 chiffres par e-mail.",
        ),
        "en": LocalizedErrorCopy(
            "Active SMTP connector required for email OTP verification",
            "Configure and enable an SMTP connector (SMTP_MAIL) under the Connectors tab before "
            "enabling 6-digit verification codes by e-mail.",
        ),
    },
    "ERR_AUTH_CHALLENGE_INVALID": {
        "fr": LocalizedErrorCopy(
            "Jeton ou code de vérification expiré ou invalide",
            "Le challenge d'authentification à deux facteurs a expiré, a été consommé ou "
            "le code saisi est incorrect.",
        ),
        "en": LocalizedErrorCopy(
            "Expired or invalid verification challenge",
            "The two-factor challenge is expired, already consumed, or the code is invalid.",
        ),
    },
}

__all__ = ["AUTH_ERROR_CATALOG"]
