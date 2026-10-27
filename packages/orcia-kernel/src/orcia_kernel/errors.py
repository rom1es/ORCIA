"""Kernel base exception `OrciaDomainError` and localized RFC 9457 error registry (`AD-19`).

Pure kernel module — zero framework or business domain dependencies. Each domain in
`packages/orcia-core` defines its own `<domaine>/errors.py` inheriting from `OrciaDomainError`
and registers its localized FR/EN copy via `register_domain_error_catalog()`.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class LocalizedErrorCopy:
    """Localized title and detail template for an invariant machine error code."""

    title: str
    detail: str


ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_OBSERVER_MODE_READ_ONLY": {
        "fr": LocalizedErrorCopy(
            "Mode observateur en lecture seule",
            "Cette action de modification est interdite en mode READ_ONLY_OBSERVER.",
        ),
        "en": LocalizedErrorCopy(
            "Read-only observer mode",
            "This mutation action is forbidden while in READ_ONLY_OBSERVER mode.",
        ),
    },
    "ERR_HUMAN_ANCHOR_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Ancrage humain obligatoire requis",
            "La section marquée human_authored_required exige une rédaction et une "
            "signature humaine explicites.",
        ),
        "en": LocalizedErrorCopy(
            "Mandatory human anchor required",
            "A section marked human_authored_required requires explicit human authoring "
            "and signature.",
        ),
    },
    "ERR_READ_SOURCE_DENIED": {
        "fr": LocalizedErrorCopy(
            "Accès au code source masqué refusé",
            "La permission READ_SOURCE est requise pour inspecter le contenu interne "
            "de cette ressource.",
        ),
        "en": LocalizedErrorCopy(
            "Read source access denied",
            "READ_SOURCE permission is required to inspect the internal source of this item.",
        ),
    },
    "ERR_MODEL_ORTHOGONALITY_VIOLATION": {
        "fr": LocalizedErrorCopy(
            "Violation d'orthogonalité des modèles",
            "La famille du modèle évaluateur doit être distincte de celle de l'exécuteur.",
        ),
        "en": LocalizedErrorCopy(
            "Model orthogonality violation",
            "The evaluator model family must differ from the executor model family.",
        ),
    },
    "ERR_RESOURCE_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "La ressource ou la route demandée n'existe pas sur la plateforme ORCIA.",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "The requested resource or route does not exist on the ORCIA platform.",
        ),
    },
    "ERR_VALIDATION_FAILED": {
        "fr": LocalizedErrorCopy(
            "Erreur de validation de la requête",
            "Les paramètres fournis ne respectent pas le contrat attendu.",
        ),
        "en": LocalizedErrorCopy(
            "Request validation failed",
            "The supplied parameters do not satisfy the expected schema contract.",
        ),
    },
    "ERR_INTERNAL_SERVER_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur interne de la plateforme",
            "Une erreur inattendue est survenue lors du traitement de la requête.",
        ),
        "en": LocalizedErrorCopy(
            "Internal platform error",
            "An unexpected error occurred while processing the request.",
        ),
    },
    "ERR_SCOPE_ACCESS_DENIED": {
        "fr": LocalizedErrorCopy(
            "Accès au périmètre ou module refusé",
            "Votre rôle RBAC ne vous autorise pas à accéder à ce périmètre ou module.",
        ),
        "en": LocalizedErrorCopy(
            "Scope or module access denied",
            "Your RBAC role does not grant access to this scope or module.",
        ),
    },
}


def register_domain_error_catalog(
    entries: dict[str, dict[SupportedLocale, LocalizedErrorCopy]],
) -> None:
    """Register domain-specific localized error descriptions into the kernel error catalog."""
    ERROR_CATALOG.update(entries)


def resolve_locale(accept_language: str | None) -> SupportedLocale:
    """Resolve `Accept-Language` header value to `'fr'` (default) or `'en'` (`;q=` weights)."""
    if not accept_language:
        return DEFAULT_LOCALE
    candidates: list[tuple[float, int, str]] = []
    for index, token in enumerate(accept_language.split(",")):
        parts = [part.strip() for part in token.split(";") if part.strip()]
        if not parts:
            continue
        lang_tag, q, valid_q = parts[0].lower(), 1.0, True
        for param in parts[1:]:
            if param.lower().startswith("q="):
                try:
                    q = float(param[2:].strip())
                except ValueError:
                    valid_q = False
                    break
        if valid_q and 0.0 < q <= 1.0:
            candidates.append((q, index, lang_tag.split("-")[0]))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    for _q, _index, primary in candidates:
        if primary in ("en", "fr"):
            return "en" if primary == "en" else "fr"
    return DEFAULT_LOCALE


def get_localized_error_text(
    error_code: str, locale: SupportedLocale = DEFAULT_LOCALE, detail_override: str | None = None
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
        return f"https://orcia.io/problems/{self.type_slug}"

    def localize(self, locale: SupportedLocale = DEFAULT_LOCALE) -> LocalizedErrorCopy:
        return get_localized_error_text(self.error_code, locale, self.detail_override)


class ObserverModeReadOnlyError(OrciaDomainError):
    error_code = "ERR_OBSERVER_MODE_READ_ONLY"
    http_status, type_slug = 403, "observer-mode-read-only"


class HumanAnchorRequiredError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_HUMAN_ANCHOR_REQUIRED", 422, "human-anchor-required"


class ReadSourceDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_READ_SOURCE_DENIED", 403, "read-source-denied"


class ModelOrthogonalityViolationError(OrciaDomainError):
    error_code = "ERR_MODEL_ORTHOGONALITY_VIOLATION"
    http_status, type_slug = 422, "model-orthogonality-violation"


class ResourceNotFoundError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_RESOURCE_NOT_FOUND", 404, "resource-not-found"


class ValidationDomainError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_VALIDATION_FAILED", 422, "validation-failed"


class ScopeAccessDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_SCOPE_ACCESS_DENIED", 403, "scope-access-denied"


__all__ = [
    "DEFAULT_LOCALE",
    "ERROR_CATALOG",
    "HumanAnchorRequiredError",
    "LocalizedErrorCopy",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "SupportedLocale",
    "ValidationDomainError",
    "get_localized_error_text",
    "register_domain_error_catalog",
    "resolve_locale",
]
