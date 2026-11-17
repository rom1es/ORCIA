"""Composition Root factory selecting `LogSinkQueryPort` from env (`AD-23`, `Story 7.0b`)."""

from __future__ import annotations

import os

import httpx

from orcia_core.kernel.log_sink_ports import LogSinkQueryPort, NoopLogSinkAdapter
from orcia_core.kernel.secret_ports import SecretProviderPort, SecretRef
from orcia_core.observability._internal.elasticsearch_sink import ElasticsearchLogSinkAdapter
from orcia_core.observability.errors import UnsupportedLogSinkBackendError


def build_log_sink_from_env(
    http_client: httpx.AsyncClient | None = None,
    *,
    secret_provider: SecretProviderPort | None = None,
) -> LogSinkQueryPort:
    """Instantiate the configured `LogSinkQueryPort` from `LOG_SINK_BACKEND` (default `none`)."""
    backend = os.environ.get("LOG_SINK_BACKEND", "none").strip().lower() or "none"
    if backend == "none":
        return NoopLogSinkAdapter()

    if backend in ("elasticsearch", "opensearch"):
        url = os.environ.get("ORCIA_LOG_SINK_URL", "").strip()
        if not url:
            raise UnsupportedLogSinkBackendError(
                detail_override=(
                    "ORCIA_LOG_SINK_URL must be configured when LOG_SINK_BACKEND=elasticsearch."
                )
            )
        index_pattern = os.environ.get("ORCIA_LOG_SINK_INDEX", "orcia-logs-*").strip()
        secret_uri = os.environ.get("ORCIA_LOG_SINK_SECRET_REF", "").strip()
        auth_ref = SecretRef(uri=secret_uri) if secret_uri else None
        return ElasticsearchLogSinkAdapter(
            url,
            index_pattern=index_pattern or "orcia-logs-*",
            http_client=http_client,
            secret_provider=secret_provider,
            auth_secret_ref=auth_ref,
        )

    if backend == "loki":
        raise UnsupportedLogSinkBackendError(
            detail_override=(
                "LokiLogSinkAdapter is deferred to P2 (OBS-LOGSINK-LOKI-01); "
                "use LOG_SINK_BACKEND=elasticsearch or none."
            )
        )

    raise UnsupportedLogSinkBackendError(
        detail_override=f"Unsupported LOG_SINK_BACKEND value: {backend!r}."
    )


__all__ = ["build_log_sink_from_env"]
