"""Observability & LogSink domain errors mapped to RFC 9457 (`AD-19`, `AD-23`, `Story 7.0b`)."""

from __future__ import annotations

from orcia_core.kernel.errors import OrciaDomainError, register_domain_error_catalog
from orcia_core.observability._error_catalog import OBSERVABILITY_ERROR_CATALOG

register_domain_error_catalog(OBSERVABILITY_ERROR_CATALOG)


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
