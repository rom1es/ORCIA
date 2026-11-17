"""OpenTelemetry OTLP distributed tracing & runtime instrumentation (`AD-23`, `Story 7.0b`).

Strictly emits traces only (`TracerProvider` + `OTLPSpanExporter`). Never instantiates
`LoggerProvider` or `OTLPLogExporter` — 100 % of logs flow exclusively via `stdout` JSON.
"""

from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace as otel_trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from orcia_core.observability._internal.ecs_formatter import resolve_environment, resolve_version
from orcia_core.observability._internal.url_guard import validate_safe_log_sink_url
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.observability.tracing")

_GLOBAL_TRACER_PROVIDER: TracerProvider | None = None
_HTTPX_INSTRUMENTED: bool = False


def _resolve_otlp_traces_url(endpoint: str) -> str:
    normalized = validate_safe_log_sink_url(endpoint)
    if normalized.endswith("/v1/traces"):
        return normalized
    return f"{normalized}/v1/traces"


def configure_tracing(
    service_name: str,
    otlp_endpoint: str | None = None,
    exporter_mode: str | None = None,
    *,
    headers: dict[str, str] | None = None,
    set_global: bool = True,
) -> TracerProvider | None:
    """Configure OpenTelemetry `TracerProvider` for OTLP HTTP, console, or disabled (`none`)."""
    global _GLOBAL_TRACER_PROVIDER

    raw_mode = (
        (exporter_mode if exporter_mode is not None else os.environ.get("OTEL_TRACES_EXPORTER", ""))
        .strip()
        .lower()
    )
    raw_endpoint = (
        otlp_endpoint
        if otlp_endpoint is not None
        else os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    ).strip()

    if raw_mode == "none":
        return None
    if not raw_mode:
        if not raw_endpoint:
            return None
        raw_mode = "otlp"

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": resolve_version(),
            "deployment.environment.name": resolve_environment(),
        }
    )
    provider = TracerProvider(resource=resource)

    if raw_mode == "otlp":
        if not raw_endpoint:
            return None
        traces_url = _resolve_otlp_traces_url(raw_endpoint)
        exporter = OTLPSpanExporter(endpoint=traces_url, headers=headers)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    elif raw_mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        logger.warning("otel_traces_exporter_unsupported", exporter_mode=raw_mode)
        return None

    if set_global:
        if _GLOBAL_TRACER_PROVIDER is None:
            otel_trace.set_tracer_provider(provider)
            _GLOBAL_TRACER_PROVIDER = provider
        else:
            return _GLOBAL_TRACER_PROVIDER
    return provider


def instrument_runtime(
    app: Any = None,
    engine: Any = None,
    *,
    instrument_httpx: bool = True,
) -> dict[str, bool]:
    """Idempotently instrument FastAPI, SQLAlchemy, and HTTPX with OpenTelemetry."""
    global _HTTPX_INSTRUMENTED
    instrumented = {"fastapi": False, "sqlalchemy": False, "httpx": False}

    if app is not None:
        app_state = getattr(app, "state", None)
        already = bool(getattr(app_state, "_otel_fastapi_instrumented", False))
        if not already:
            FastAPIInstrumentor.instrument_app(app)
            if app_state is not None:
                app_state._otel_fastapi_instrumented = True
        instrumented["fastapi"] = True

    if engine is not None:
        sync_engine = getattr(engine, "sync_engine", engine)
        info = getattr(sync_engine, "info", None)
        already_sa = isinstance(info, dict) and bool(info.get("_otel_sa_instrumented"))
        if not already_sa:
            SQLAlchemyInstrumentor().instrument(engine=sync_engine)
            if isinstance(info, dict):
                info["_otel_sa_instrumented"] = True
        instrumented["sqlalchemy"] = True

    if instrument_httpx:
        if not _HTTPX_INSTRUMENTED:
            HTTPXClientInstrumentor().instrument()
            _HTTPX_INSTRUMENTED = True
        instrumented["httpx"] = True

    return instrumented


def shutdown_tracing(provider: TracerProvider | None = None) -> None:
    """Flush and shut down the given or global OpenTelemetry `TracerProvider` cleanly."""
    global _GLOBAL_TRACER_PROVIDER
    target = provider or _GLOBAL_TRACER_PROVIDER
    if target is None:
        return
    try:
        target.shutdown()
    except Exception as exc:
        logger.warning(
            "otel_tracer_shutdown_failed",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
    finally:
        if target is _GLOBAL_TRACER_PROVIDER:
            _GLOBAL_TRACER_PROVIDER = None


__all__ = [
    "configure_tracing",
    "instrument_runtime",
    "shutdown_tracing",
]
