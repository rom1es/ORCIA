"""Localized RFC 9457 error catalog for Observability & LogSink (`Story 7.0b`, `Story 27.7`)."""

from __future__ import annotations

from orcia_core.kernel.errors import LocalizedErrorCopy, register_domain_error_catalog
from orcia_kernel.enums import SupportedLocale

OBSERVABILITY_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_UNSAFE_LOG_SINK_URL": {
        "fr": LocalizedErrorCopy(
            "URL de puits de logs rejetée par la politique de sécurité",
            "L'URL configurée pour le puits de logs ou le collecteur OTLP est invalide ou "
            "interdite par le garde-fou anti-SSRF.",
        ),
        "en": LocalizedErrorCopy(
            "Unsafe log sink endpoint URL rejected",
            "The configured log sink or OTLP collector URL is invalid or blocked by SSRF policy.",
        ),
    },
    "ERR_UNSUPPORTED_LOG_SINK_BACKEND": {
        "fr": LocalizedErrorCopy(
            "Backend de puits de logs non supporté",
            "Le paramètre LOG_SINK_BACKEND demandé n'est pas disponible dans cette configuration.",
        ),
        "en": LocalizedErrorCopy(
            "Unsupported log sink backend",
            "The requested LOG_SINK_BACKEND value is not supported in this runtime.",
        ),
    },
    "ERR_LOG_SINK_QUERY_FAILED": {
        "fr": LocalizedErrorCopy(
            "Échec d'interrogation du puits de logs",
            "Le puits de logs distant n'a pas pu répondre à la requête dans les délais impartis.",
        ),
        "en": LocalizedErrorCopy(
            "Log sink query failed",
            "The remote log sink failed to respond cleanly within the configured timeout.",
        ),
    },
}

register_domain_error_catalog(OBSERVABILITY_ERROR_CATALOG)

__all__ = ["OBSERVABILITY_ERROR_CATALOG"]
