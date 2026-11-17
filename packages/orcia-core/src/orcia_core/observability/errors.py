"""Observability & LogSink domain errors mapped to RFC 9457 (`AD-19`, `AD-23`, `Story 7.0b`)."""

from __future__ import annotations

from orcia_core.kernel.errors import (
    LocalizedErrorCopy,
    OrciaDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(
    {
        "ERR_UNSAFE_LOG_SINK_URL": {
            "fr": LocalizedErrorCopy(
                "URL de puits de logs rejetée par la politique de sécurité",
                "L'URL configurée pour le puits de logs ou le collecteur OTLP est invalide ou "
                "interdite par le garde-fou anti-SSRF.",
            ),
            "en": LocalizedErrorCopy(
                "Unsafe log sink endpoint URL rejected",
                "The configured log sink or OTLP collector URL is invalid or blocked by SSRF "
                "policy.",
            ),
        },
        "ERR_UNSUPPORTED_LOG_SINK_BACKEND": {
            "fr": LocalizedErrorCopy(
                "Backend de puits de logs non supporté",
                "Le paramètre LOG_SINK_BACKEND demandé n'est pas disponible dans cette "
                "configuration.",
            ),
            "en": LocalizedErrorCopy(
                "Unsupported log sink backend",
                "The requested LOG_SINK_BACKEND value is not supported in this runtime.",
            ),
        },
        "ERR_LOG_SINK_QUERY_FAILED": {
            "fr": LocalizedErrorCopy(
                "Échec d'interrogation du puits de logs",
                "Le puits de logs distant n'a pas pu répondre à la requête dans les délais "
                "impartis.",
            ),
            "en": LocalizedErrorCopy(
                "Log sink query failed",
                "The remote log sink failed to respond cleanly within the configured timeout.",
            ),
        },
    }
)


class UnsafeLogSinkUrlError(OrciaDomainError):
    """Raised when a LogSink or OTLP endpoint URL fails SSRF validation (`NFR-SEC-1`)."""

    error_code = "ERR_UNSAFE_LOG_SINK_URL"
    http_status = 422
    type_slug = "unsafe-log-sink-url"


class UnsupportedLogSinkBackendError(OrciaDomainError):
    """Raised when `LOG_SINK_BACKEND` specifies an unknown or unimplemented driver (`AD-23`)."""

    error_code = "ERR_UNSUPPORTED_LOG_SINK_BACKEND"
    http_status = 422
    type_slug = "unsupported-log-sink-backend"


class LogSinkQueryFailedError(OrciaDomainError):
    """Raised when querying the remote log sink fails or returns a non-2xx error (`AD-23`)."""

    error_code = "ERR_LOG_SINK_QUERY_FAILED"
    http_status = 502
    type_slug = "log-sink-query-failed"


__all__ = [
    "LogSinkQueryFailedError",
    "UnsafeLogSinkUrlError",
    "UnsupportedLogSinkBackendError",
]
