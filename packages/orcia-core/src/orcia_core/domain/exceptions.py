"""Domain exceptions and localized RFC 9457 error catalog (FR default, EN supported).

Pure domain module — zero framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SupportedLocale = Literal["fr", "en"]
DEFAULT_LOCALE: SupportedLocale = "fr"


@dataclass(frozen=True, slots=True)
class LocalizedErrorCopy:
    """Localized title and detail template for an invariant machine error code."""

    title: str
    detail: str


ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_OBSERVER_MODE_READ_ONLY": {
        "fr": LocalizedErrorCopy(
            title="Mode observateur en lecture seule",
            detail="Cette action de modification est interdite en mode READ_ONLY_OBSERVER.",
        ),
        "en": LocalizedErrorCopy(
            title="Read-only observer mode",
            detail="This mutation action is forbidden while in READ_ONLY_OBSERVER mode.",
        ),
    },
    "ERR_HUMAN_ANCHOR_REQUIRED": {
        "fr": LocalizedErrorCopy(
            title="Ancrage humain obligatoire requis",
            detail=(
                "La section marquée human_authored_required exige une rédaction et une "
                "signature humaine explicites."
            ),
        ),
        "en": LocalizedErrorCopy(
            title="Mandatory human anchor required",
            detail=(
                "A section marked human_authored_required requires explicit human authoring "
                "and signature."
            ),
        ),
    },
    "ERR_READ_SOURCE_DENIED": {
        "fr": LocalizedErrorCopy(
            title="Accès au code source masqué refusé",
            detail=(
                "La permission READ_SOURCE est requise pour inspecter le contenu interne "
                "de cette ressource."
            ),
        ),
        "en": LocalizedErrorCopy(
            title="Read source access denied",
            detail=(
                "READ_SOURCE permission is required to inspect the internal source of this item."
            ),
        ),
    },
    "ERR_MODEL_ORTHOGONALITY_VIOLATION": {
        "fr": LocalizedErrorCopy(
            title="Violation d'orthogonalité des modèles",
            detail="La famille du modèle évaluateur doit être distincte de celle de l'exécuteur.",
        ),
        "en": LocalizedErrorCopy(
            title="Model orthogonality violation",
            detail="The evaluator model family must differ from the executor model family.",
        ),
    },
    "ERR_RESOURCE_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            title="Ressource introuvable",
            detail="La ressource ou la route demandée n'existe pas sur la plateforme ORCIA.",
        ),
        "en": LocalizedErrorCopy(
            title="Resource not found",
            detail="The requested resource or route does not exist on the ORCIA platform.",
        ),
    },
    "ERR_VALIDATION_FAILED": {
        "fr": LocalizedErrorCopy(
            title="Erreur de validation de la requête",
            detail="Les paramètres fournis ne respectent pas le contrat attendu.",
        ),
        "en": LocalizedErrorCopy(
            title="Request validation failed",
            detail="The supplied parameters do not satisfy the expected schema contract.",
        ),
    },
    "ERR_INTERNAL_SERVER_ERROR": {
        "fr": LocalizedErrorCopy(
            title="Erreur interne de la plateforme",
            detail="Une erreur inattendue est survenue lors du traitement de la requête.",
        ),
        "en": LocalizedErrorCopy(
            title="Internal platform error",
            detail="An unexpected error occurred while processing the request.",
        ),
    },
    "ERR_AUTH_INVALID_CREDENTIALS": {
        "fr": LocalizedErrorCopy(
            title="Identifiants d'authentification invalides",
            detail="L'adresse e-mail, le mot de passe ou le jeton OIDC fourni est invalide.",
        ),
        "en": LocalizedErrorCopy(
            title="Invalid authentication credentials",
            detail="The supplied email, password, or OIDC token is invalid.",
        ),
    },
    "ERR_AUTH_MFA_INVALID": {
        "fr": LocalizedErrorCopy(
            title="Code MFA TOTP invalide ou manquant",
            detail="Le code d'authentification multifacteur TOTP est requis ou incorrect.",
        ),
        "en": LocalizedErrorCopy(
            title="Invalid or missing TOTP MFA code",
            detail="A valid TOTP multi-factor authentication code is required.",
        ),
    },
    "ERR_AUTH_TOKEN_REVOKED": {
        "fr": LocalizedErrorCopy(
            title="Session expirée ou révoquée",
            detail="Le jeton de session ou de rafraîchissement a expiré ou a été révoqué.",
        ),
        "en": LocalizedErrorCopy(
            title="Session expired or revoked",
            detail="The session or refresh token has expired or has been revoked.",
        ),
    },
    "ERR_SCOPE_ACCESS_DENIED": {
        "fr": LocalizedErrorCopy(
            title="Accès au périmètre ou module refusé",
            detail="Votre rôle RBAC ne vous autorise pas à accéder à ce périmètre ou module.",
        ),
        "en": LocalizedErrorCopy(
            title="Scope or module access denied",
            detail="Your RBAC role does not grant access to this scope or module.",
        ),
    },
}


def resolve_locale(accept_language: str | None) -> SupportedLocale:
    """Resolve `Accept-Language` header value to `'fr'` (default) or `'en'` (`;q=` weights)."""
    if not accept_language:
        return DEFAULT_LOCALE
    candidates: list[tuple[float, int, str]] = []
    for index, token in enumerate(accept_language.split(",")):
        parts = [part.strip() for part in token.split(";") if part.strip()]
        if not parts:
            continue
        lang_tag = parts[0].lower()
        q = 1.0
        valid_q = True
        for param in parts[1:]:
            if param.lower().startswith("q="):
                try:
                    q = float(param[2:].strip())
                except ValueError:
                    valid_q = False
                    break
        if not valid_q or q <= 0.0 or q > 1.0:
            continue
        primary = lang_tag.split("-")[0]
        candidates.append((q, index, primary))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    for _q, _index, primary in candidates:
        if primary == "en":
            return "en"
        if primary == "fr":
            return "fr"
    return DEFAULT_LOCALE


def get_localized_error_text(
    error_code: str,
    locale: SupportedLocale = DEFAULT_LOCALE,
    detail_override: str | None = None,
) -> LocalizedErrorCopy:
    """Return localized `(title, detail)` for `error_code` with safe fallback."""
    catalog_entry = ERROR_CATALOG.get(error_code) or ERROR_CATALOG["ERR_INTERNAL_SERVER_ERROR"]
    localized = catalog_entry.get(locale) or catalog_entry[DEFAULT_LOCALE]
    if detail_override:
        return LocalizedErrorCopy(title=localized.title, detail=detail_override)
    return localized


class OrciaDomainError(Exception):
    """Base class for all ORCIA domain errors mapped to RFC 9457 Problem Details."""

    error_code: str = "ERR_INTERNAL_SERVER_ERROR"
    http_status: int = 500
    type_slug: str = "internal-server-error"

    def __init__(
        self,
        *,
        detail_override: str | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        default_copy = get_localized_error_text(self.error_code, DEFAULT_LOCALE, detail_override)
        super().__init__(default_copy.detail)
        self.detail_override = detail_override
        self.instance = instance
        self.permission_broker_hint = permission_broker_hint

    @property
    def type_uri(self) -> str:
        """Canonical RFC 9457 problem type URI."""
        return f"https://orcia.io/problems/{self.type_slug}"

    def localize(self, locale: SupportedLocale = DEFAULT_LOCALE) -> LocalizedErrorCopy:
        """Return localized title and detail for the requested locale."""
        return get_localized_error_text(self.error_code, locale, self.detail_override)


class ObserverModeReadOnlyError(OrciaDomainError):
    """Raised when a caller in READ_ONLY_OBSERVER mode attempts a mutation (AD-4, AD-6)."""

    error_code = "ERR_OBSERVER_MODE_READ_ONLY"
    http_status = 403
    type_slug = "observer-mode-read-only"


class HumanAnchorRequiredError(OrciaDomainError):
    """Raised when an agent attempts to write a section requiring a human signature (AD-3)."""

    error_code = "ERR_HUMAN_ANCHOR_REQUIRED"
    http_status = 422
    type_slug = "human-anchor-required"


class ReadSourceDeniedError(OrciaDomainError):
    """Raised when inspecting black-box source without READ_SOURCE permission (AD-6)."""

    error_code = "ERR_READ_SOURCE_DENIED"
    http_status = 403
    type_slug = "read-source-denied"


class ModelOrthogonalityViolationError(OrciaDomainError):
    """Raised when evaluator and executor share the same LLM model family (AD-10)."""

    error_code = "ERR_MODEL_ORTHOGONALITY_VIOLATION"
    http_status = 422
    type_slug = "model-orthogonality-violation"


class ResourceNotFoundError(OrciaDomainError):
    """Raised when a requested entity or route does not exist."""

    error_code = "ERR_RESOURCE_NOT_FOUND"
    http_status = 404
    type_slug = "resource-not-found"


class ValidationDomainError(OrciaDomainError):
    """Raised when domain or request validation fails."""

    error_code = "ERR_VALIDATION_FAILED"
    http_status = 422
    type_slug = "validation-failed"


class InvalidCredentialsError(OrciaDomainError):
    """Raised when local password or OIDC token authentication fails (AD-6)."""

    error_code = "ERR_AUTH_INVALID_CREDENTIALS"
    http_status = 401
    type_slug = "auth-invalid-credentials"


class InvalidMfaCodeError(OrciaDomainError):
    """Raised when TOTP MFA code is missing or invalid (AD-6)."""

    error_code = "ERR_AUTH_MFA_INVALID"
    http_status = 401
    type_slug = "auth-mfa-invalid"


class RevokedTokenError(OrciaDomainError):
    """Raised when a session or refresh token is expired or revoked in Redis (AD-6)."""

    error_code = "ERR_AUTH_TOKEN_REVOKED"
    http_status = 401
    type_slug = "auth-token-revoked"


class ScopeAccessDeniedError(OrciaDomainError):
    """Raised when a caller attempts to access an unauthorized scope or module (AD-6)."""

    error_code = "ERR_SCOPE_ACCESS_DENIED"
    http_status = 403
    type_slug = "scope-access-denied"
