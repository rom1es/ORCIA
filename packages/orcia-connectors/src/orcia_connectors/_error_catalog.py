"""Localized RFC 9457 error catalog for `orcia_connectors` (`AD-19`, `Story 27.8`).

Registers connector and surgical-exploration `detail_code` entries in `orcia_core.kernel`
so `OrciaDomainError` and FastAPI RFC 9457 responses localize both `title` and `detail`
dynamically via `Accept-Language: fr` / `en`.
"""

from __future__ import annotations

from orcia_core.kernel.enums import SupportedLocale
from orcia_core.kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

CONNECTOR_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_SURGICAL_URI_EMPTY": {
        "fr": LocalizedErrorCopy(
            "Paramètre URI requis",
            "Le paramètre `uri` ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Required URI parameter",
            "The `uri` parameter cannot be empty.",
        ),
    },
    "ERR_SURGICAL_NULL_BYTE": {
        "fr": LocalizedErrorCopy(
            "URI invalide",
            "Octet nul interdit dans l'URI.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid URI",
            "Null bytes are forbidden in the URI.",
        ),
    },
    "ERR_SURGICAL_FILE_SCHEME_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Schéma d'URI interdit",
            "Le schéma `file://` est interdit.",
        ),
        "en": LocalizedErrorCopy(
            "Forbidden URI scheme",
            "The `file://` URI scheme is forbidden.",
        ),
    },
    "ERR_SURGICAL_SSRF_BLOCKED": {
        "fr": LocalizedErrorCopy(
            "Cible réseau protégée bloquée",
            "Cible SSRF bloquée par la gouvernance : `{host}`.",
        ),
        "en": LocalizedErrorCopy(
            "Protected network target blocked",
            "SSRF target blocked by governance policy: `{host}`.",
        ),
    },
    "ERR_SURGICAL_NETWORK_SCHEME_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "URL réseau directe interdite",
            "Les URL réseau directes ne sont pas autorisées en exploration.",
        ),
        "en": LocalizedErrorCopy(
            "Direct network URL forbidden",
            "Direct network URLs are not allowed during surgical exploration.",
        ),
    },
    "ERR_SURGICAL_UNSUPPORTED_SCHEME": {
        "fr": LocalizedErrorCopy(
            "Schéma d'URI non supporté",
            "Schéma d'URI non supporté : `{scheme}://`.",
        ),
        "en": LocalizedErrorCopy(
            "Unsupported URI scheme",
            "Unsupported URI scheme: `{scheme}://`.",
        ),
    },
    "ERR_SURGICAL_PATH_TRAVERSAL": {
        "fr": LocalizedErrorCopy(
            "Traversée de chemin interdite",
            "Traversée de chemin `..` strictement interdite.",
        ),
        "en": LocalizedErrorCopy(
            "Path traversal forbidden",
            "Path traversal `..` is strictly forbidden.",
        ),
    },
    "ERR_SURGICAL_PACK_URI_OUT_OF_BOUNDS": {
        "fr": LocalizedErrorCopy(
            "URI de pack hors périmètre",
            "URI `pack://` hors périmètre autorisé.",
        ),
        "en": LocalizedErrorCopy(
            "Pack URI out of bounds",
            "The `pack://` URI is outside the authorized directory.",
        ),
    },
    "ERR_SURGICAL_PATH_OUT_OF_BOUNDS": {
        "fr": LocalizedErrorCopy(
            "Chemin hors des racines autorisées",
            "Chemin `{uri}` hors des racines autorisées ({roots}).",
        ),
        "en": LocalizedErrorCopy(
            "Path outside authorized roots",
            "Path `{uri}` is outside the authorized roots ({roots}).",
        ),
    },
    "ERR_SURGICAL_UNKNOWN_PRIMITIVE": {
        "fr": LocalizedErrorCopy(
            "Primitive d'exploration inconnue",
            "Primitive inconnue : `{primitive}`.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown exploration primitive",
            "Unknown surgical primitive: `{primitive}`.",
        ),
    },
    "ERR_SURGICAL_INVALID_LINE_RANGE": {
        "fr": LocalizedErrorCopy(
            "Bornes de lignes invalides",
            "Bornes de lignes invalides (`start_line={start_line}`, `end_line={end_line}`).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid line bounds",
            "Invalid line bounds (`start_line={start_line}`, `end_line={end_line}`).",
        ),
    },
    "ERR_SURGICAL_INVALID_QUERY": {
        "fr": LocalizedErrorCopy(
            "Requête de recherche invalide",
            "La requête `query` doit contenir entre 1 et 256 caractères.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid search query",
            "The `query` parameter must contain between 1 and 256 characters.",
        ),
    },
    "ERR_SURGICAL_SEARCH_SCOPE_DENIED": {
        "fr": LocalizedErrorCopy(
            "Périmètre de recherche non autorisé",
            "Périmètre de recherche `{scope}` non autorisé.",
        ),
        "en": LocalizedErrorCopy(
            "Unauthorized search scope",
            "Search scope `{scope}` is not authorized.",
        ),
    },
    "ERR_SURGICAL_RESOURCE_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "Ressource introuvable : `{uri}`.",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "Resource not found: `{uri}`.",
        ),
    },
}

register_domain_error_catalog(CONNECTOR_ERROR_CATALOG)

__all__ = ["CONNECTOR_ERROR_CATALOG"]
