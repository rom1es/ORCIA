"""Structured JSON logging (`structlog`), `LogSinkQueryPort` adapters & OTel OTLP tracing."""

from orcia_core.observability._internal.elasticsearch_sink import ElasticsearchLogSinkAdapter
from orcia_core.observability.fingerprint import (
    compute_error_fingerprint_sha256,
    extract_top_frame,
)
from orcia_core.observability.log_sink_factory import build_log_sink_from_env
from orcia_core.observability.logging import (
    HealthProbeLogFilter,
    TraceContext,
    bind_trace_context,
    clear_sensitive_secret_values,
    clear_trace_context,
    configure_logging,
    configure_structlog,
    ensure_logging_configured,
    generate_trace_id,
    get_current_trace_context,
    get_current_trace_id,
    get_logger,
    mask_secrets_processor,
    register_sensitive_secret_value,
    resolve_log_level,
    resolve_or_create_trace_id,
    scrub_sensitive_dict,
    scrub_sensitive_text,
)
from orcia_core.observability.tracing import (
    configure_tracing,
    instrument_runtime,
    shutdown_tracing,
)

__all__ = [
    "ElasticsearchLogSinkAdapter",
    "HealthProbeLogFilter",
    "TraceContext",
    "bind_trace_context",
    "build_log_sink_from_env",
    "clear_sensitive_secret_values",
    "clear_trace_context",
    "compute_error_fingerprint_sha256",
    "configure_logging",
    "configure_structlog",
    "configure_tracing",
    "ensure_logging_configured",
    "extract_top_frame",
    "generate_trace_id",
    "get_current_trace_context",
    "get_current_trace_id",
    "get_logger",
    "instrument_runtime",
    "mask_secrets_processor",
    "register_sensitive_secret_value",
    "resolve_log_level",
    "resolve_or_create_trace_id",
    "scrub_sensitive_dict",
    "scrub_sensitive_text",
    "shutdown_tracing",
]
