"""Kernel RFC 9457 localized error catalog and locale resolution (`AD-19`).

Pure kernel module with zero framework or business domain dependencies.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class LocalizedErrorCopy:
    """Localized title and detail template for an invariant machine error code."""

    title: str
    detail: str


class _SafeFormatDict(dict[str, object]):
    """Preserve unresolved placeholders safely during catalog template interpolation."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


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
    "ERR_MODEL_ORTHOGONALITY_VIOLATION_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Violation d'orthogonalité des modèles",
            "La famille du modèle évaluateur ('{evaluator_model_family}') doit être distincte "
            "de celle de l'exécuteur ('{executor_model_family}').",
        ),
        "en": LocalizedErrorCopy(
            "Model orthogonality violation",
            "The evaluator model family ('{evaluator_model_family}') must differ from "
            "the executor model family ('{executor_model_family}').",
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
    "ERR_TRANSIENT_INFRA_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur d'infrastructure transitoire",
            "Une défaillance réseau ou d'infrastructure temporaire est survenue ; "
            "nouvel essai planifié.",
        ),
        "en": LocalizedErrorCopy(
            "Transient infrastructure error",
            "A temporary network or infrastructure failure occurred; retry scheduled.",
        ),
    },
    "ERR_TRANSIENT_CONNECTOR_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur transitoire du connecteur (nouvel essai autorisé)",
            "Le connecteur externe a rencontré une indisponibilité temporaire ; "
            "une nouvelle tentative automatique est planifiée.",
        ),
        "en": LocalizedErrorCopy(
            "Transient connector error (retry allowed)",
            "The external connector encountered a temporary unavailability; "
            "an automatic retry is scheduled.",
        ),
    },
    "ERR_RATE_LIMITED": {
        "fr": LocalizedErrorCopy(
            "Quota d'appels amont atteint (429)",
            "Le connecteur externe a limité le débit d'appels ; "
            "nouvel essai différé selon Retry-After.",
        ),
        "en": LocalizedErrorCopy(
            "Upstream rate limit exceeded (429)",
            "The external connector rate-limited the request; retry delayed per Retry-After.",
        ),
    },
    "ERR_UPSTREAM_TIMEOUT": {
        "fr": LocalizedErrorCopy(
            "Délai d'attente amont dépassé",
            "Le service externe n'a pas répondu dans le délai imparti.",
        ),
        "en": LocalizedErrorCopy(
            "Upstream service timeout",
            "The external service did not respond within the configured timeout.",
        ),
    },
    "ERR_FUNCTIONAL_CONNECTOR_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur fonctionnelle du connecteur (non rejouable)",
            "L'action externe a été rejetée pour un motif métier ; escalade vers arbitrage humain.",
        ),
        "en": LocalizedErrorCopy(
            "Functional connector error (non-retryable)",
            "The external action was rejected for a business reason; "
            "escalated to human arbitration.",
        ),
    },
    "ERR_POLICY_DENIED": {
        "fr": LocalizedErrorCopy(
            "Action refusée par la politique de gouvernance",
            "La politique de sécurité ou d'autorisation interdit cette invocation de connecteur.",
        ),
        "en": LocalizedErrorCopy(
            "Action denied by governance policy",
            "Security or authorization policy forbids this connector invocation.",
        ),
    },
    "ERR_PERMANENT_INFRA_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur d'infrastructure permanente ou disjoncteur ouvert",
            "Le connecteur externe est indisponible de manière persistante ou "
            "son disjoncteur est ouvert.",
        ),
        "en": LocalizedErrorCopy(
            "Permanent infrastructure error or open circuit breaker",
            "The external connector is persistently unavailable or its circuit breaker is open.",
        ),
    },
    "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE": {
        "fr": LocalizedErrorCopy(
            "Workflow critique incompatible avec l'autonomie totale",
            "Tout workflow classé HIGH_CRITICAL exige au moins une Gate Humaine et ne peut pas "
            "être exécuté en régime AUTONOMOUS_CONTRACT.",
        ),
        "en": LocalizedErrorCopy(
            "Critical workflow requires human gate",
            "Any workflow classified as HIGH_CRITICAL requires at least one Human Gate and "
            "cannot run under AUTONOMOUS_CONTRACT regime.",
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
    error_code: str,
    locale: SupportedLocale = DEFAULT_LOCALE,
    detail_override: str | None = None,
    *,
    detail_code: str | None = None,
    detail_params: Mapping[str, object] | None = None,
) -> LocalizedErrorCopy:
    """Return localized `(title, detail)` for `error_code` with deterministic fallback."""
    catalog_entry = ERROR_CATALOG.get(error_code) or ERROR_CATALOG["ERR_INTERNAL_SERVER_ERROR"]
    localized = catalog_entry.get(locale) or catalog_entry[DEFAULT_LOCALE]
    if detail_override:
        return LocalizedErrorCopy(title=localized.title, detail=detail_override)
    detail_text = localized.detail
    if detail_code and detail_code in ERROR_CATALOG:
        detail_entry = ERROR_CATALOG[detail_code]
        detail_text = (detail_entry.get(locale) or detail_entry[DEFAULT_LOCALE]).detail
    if detail_params is not None:
        detail_text = detail_text.format_map(_SafeFormatDict(detail_params))
    return LocalizedErrorCopy(title=localized.title, detail=detail_text)


__all__ = [
    "ERROR_CATALOG",
    "LocalizedErrorCopy",
    "get_localized_error_text",
    "register_domain_error_catalog",
    "resolve_locale",
]
