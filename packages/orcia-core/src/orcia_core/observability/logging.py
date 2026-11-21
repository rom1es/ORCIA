"""Unified 12-factor JSON stdout logging (`structlog` + stdlib) & W3C `trace_id` (`AD-23`)."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from orcia_core.observability._internal.ecs_formatter import (
    clear_sensitive_secret_values,
    mask_secrets_processor,
    register_sensitive_secret_value,
    resolve_environment,
    resolve_log_level,
    resolve_version,
    scrub_sensitive_dict,
    scrub_sensitive_text,
)
from orcia_core.observability._internal.ecs_normalizer import (
    HealthProbeLogFilter,
    build_json_processor_formatter,
)
from orcia_core.observability._internal.trace_context import (
    HEX_32_RE,
    TRACEPARENT_RE,
    TraceContext,
    bind_trace_context,
    clear_trace_context,
    generate_span_id,
    generate_trace_id,
    get_current_trace_context,
    get_current_trace_id,
    get_trace_ctx_var,
    resolve_or_create_trace_id,
)

_UNIFIED_THIRD_PARTY_LOGGERS: tuple[str, ...] = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "dramatiq",
    "dbos",
    "sqlalchemy",
)
_LOGGING_CONFIGURED = False


class _DynamicStdoutStream:
    """Stream proxy forwarding writes to current `sys.stdout` (supports pytest `capsys`)."""

    def write(self, msg: str) -> int:
        stream = sys.stdout
        if stream is None:  # pragma: no cover
            return 0
        return stream.write(msg)

    def flush(self) -> None:
        stream = sys.stdout
        if stream is not None:
            stream.flush()

    def isatty(self) -> bool:
        stream = sys.stdout
        return bool(stream is not None and stream.isatty())

    @property
    def encoding(self) -> str:
        stream = sys.stdout
        return str(getattr(stream, "encoding", "utf-8") or "utf-8")


def configure_logging(
    service: str = "api",
    log_level: str | None = None,
    env: str | None = None,
    version: str = "0.1.0",
) -> None:
    """Configure unified 12-factor JSON stdout logging for structlog and stdlib (`AD-23`)."""
    global _LOGGING_CONFIGURED
    resolved_level = resolve_log_level(log_level)
    resolved_env = resolve_environment(env)
    resolved_version = resolve_version(version)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            mask_secrets_processor,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=False,
    )

    formatter = build_json_processor_formatter(
        service=service,
        env=resolved_env,
        version=resolved_version,
        trace_ctx_getter=get_trace_ctx_var,
    )
    handler: logging.StreamHandler[Any] = logging.StreamHandler(_DynamicStdoutStream())
    handler.setLevel(resolved_level)
    handler.setFormatter(formatter)
    handler.addFilter(HealthProbeLogFilter())

    root_logger = logging.getLogger()
    root_logger.disabled = False
    preserved_capture_handlers = [
        existing
        for existing in root_logger.handlers
        if type(existing).__name__ == "LogCaptureHandler"
    ]
    root_logger.handlers = [*preserved_capture_handlers, handler]
    root_logger.setLevel(resolved_level)

    # Alembic / framework `fileConfig(..., disable_existing_loggers=True)` can leave
    # previously created loggers disabled; re-enable managed hierarchies explicitly.
    for existing_name, existing_obj in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(existing_obj, logging.Logger) and (
            existing_name == "orcia"
            or existing_name.startswith(("orcia.", "uvicorn", "dramatiq", "dbos", "sqlalchemy"))
        ):
            existing_obj.disabled = False
            if existing_name not in _UNIFIED_THIRD_PARTY_LOGGERS and existing_name.startswith(
                ("uvicorn.", "dramatiq.", "dbos.", "sqlalchemy.")
            ):
                existing_obj.setLevel(logging.NOTSET)

    for logger_name in _UNIFIED_THIRD_PARTY_LOGGERS:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.disabled = False
        third_party_logger.handlers = [handler]
        third_party_logger.setLevel(resolved_level)
        third_party_logger.propagate = False

    _LOGGING_CONFIGURED = True


def ensure_logging_configured(
    service: str = "worker",
    log_level: str | None = None,
    env: str | None = None,
    version: str = "0.1.0",
) -> None:
    """Idempotently configure logging once if not yet initialized in the current process."""
    if not _LOGGING_CONFIGURED:
        configure_logging(service=service, log_level=log_level, env=env, version=version)


def configure_structlog() -> None:
    """Backward-compatible alias configuring unified 12-factor JSON stdout logging."""
    configure_logging(service="api")


def get_logger(name: str = "orcia") -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to `name`."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


__all__ = [
    "HEX_32_RE",
    "HealthProbeLogFilter",
    "TRACEPARENT_RE",
    "TraceContext",
    "bind_trace_context",
    "clear_sensitive_secret_values",
    "clear_trace_context",
    "configure_logging",
    "configure_structlog",
    "ensure_logging_configured",
    "generate_span_id",
    "generate_trace_id",
    "get_current_trace_context",
    "get_current_trace_id",
    "get_logger",
    "mask_secrets_processor",
    "register_sensitive_secret_value",
    "resolve_log_level",
    "resolve_or_create_trace_id",
    "scrub_sensitive_dict",
    "scrub_sensitive_text",
]
