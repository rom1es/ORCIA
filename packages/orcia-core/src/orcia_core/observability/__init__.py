"""Structured JSON logging (`structlog`) and W3C OpenTelemetry trace context propagation."""

from orcia_core.observability.logging import (
    TraceContext,
    bind_trace_context,
    clear_sensitive_secret_values,
    clear_trace_context,
    configure_structlog,
    generate_trace_id,
    get_current_trace_context,
    get_current_trace_id,
    get_logger,
    mask_secrets_processor,
    register_sensitive_secret_value,
    resolve_or_create_trace_id,
    scrub_sensitive_dict,
    scrub_sensitive_text,
)

__all__ = [
    "TraceContext",
    "bind_trace_context",
    "clear_sensitive_secret_values",
    "clear_trace_context",
    "configure_structlog",
    "generate_trace_id",
    "get_current_trace_context",
    "get_current_trace_id",
    "get_logger",
    "mask_secrets_processor",
    "register_sensitive_secret_value",
    "resolve_or_create_trace_id",
    "scrub_sensitive_dict",
    "scrub_sensitive_text",
]
