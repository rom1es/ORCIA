"""Catalog domain localized RFC 9457 error catalog (`AD-19`, `Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

CATALOG_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_HELP_ARTICLE_NOT_FOUND_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "Aucune fiche d'aide trouvée pour route={route} ({lang}).",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "No contextual help article found for route={route} ({lang}).",
        ),
    },
    "ERR_HELP_ARTICLE_ID_NOT_FOUND_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "Fiche d'aide introuvable : {resource_id}.",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "Contextual help article not found: {resource_id}.",
        ),
    },
    "ERR_HELP_ARTICLE_PREVIOUS_VERSION_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "Aucune version antérieure @v(N-1) disponible pour {resource_id}.",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "No previous version @v(N-1) available for {resource_id}.",
        ),
    },
}

__all__ = ["CATALOG_ERROR_CATALOG"]
