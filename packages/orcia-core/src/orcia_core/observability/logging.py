"""Unified 12-factor JSON stdout logging (`structlog` + stdlib) & W3C `trace_id` (`AD-23`)."""

from __future__ import annotations

import contextlib
import contextvars
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any

import structlog
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context

from orcia_core.observability._internal.ecs_formatter import (
    HealthProbeLogFilter,
    build_json_processor_formatter,
    clear_sensitive_secret_values,
    mask_secrets_processor,
    register_sensitive_secret_value,
    resolve_environment,
    resolve_log_level,
    resolve_version,
    scrub_sensitive_dict,
    scrub_sensitive_text,
)
from orcia_kernel.ids import new_uuid7

HEX_32_RE = re.compile(r"^[0-9a-f]{32}$")
TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")

_UNIFIED_THIRD_PARTY_LOGGERS: tuple[str, ...] = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "dramatiq",
    "dbos",
    "sqlalchemy",
)


def generate_trace_id() -> str:
    """Generate a valid 32-hex lowercase W3C OpenTelemetry trace identifier from UUIDv7."""
    return new_uuid7().hex


def generate_span_id() -> str:
    """Generate a 16-hex W3C OpenTelemetry span identifier from UUIDv7."""
    return new_uuid7().hex[:16]


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Immutable telemetry correlation context bound per request/task (`NFR-OBS-1`, `ARCH-P9`)."""

    trace_id: str
    workspace_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    span_id: str = field(default_factory=generate_span_id)

    @property
    def traceparent(self) -> str:
        """Format W3C `traceparent` header (`00-<trace-id>-<span-id>-01`)."""
        return f"00-{self.trace_id}-{self.span_id}-01"


_trace_ctx_var: contextvars.ContextVar[TraceContext | None] = contextvars.ContextVar(
    "orcia_trace_context", default=None
)
_otel_token_var: contextvars.ContextVar[contextvars.Token[otel_context.Context] | None] = (
    contextvars.ContextVar("orcia_otel_context_token", default=None)
)
_LOGGING_CONFIGURED = False


def resolve_or_create_trace_id(
    traceparent: str | None = None,
    x_trace_id: str | None = None,
) -> str:
    """Extract a valid 32-hex `trace_id` from W3C `traceparent` or `X-Trace-Id`, or generate one."""
    if traceparent:
        match = TRACEPARENT_RE.match(traceparent.strip().lower())
        if match:
            candidate = match.group(1)
            parent_id = match.group(2)
            if candidate != "0" * 32 and parent_id != "0" * 16:
                return candidate

    if x_trace_id:
        candidate = x_trace_id.strip().lower()
        if HEX_32_RE.match(candidate) and candidate != "0" * 32:
            return candidate

    active_otel_span = otel_trace.get_current_span()
    active_otel_ctx = active_otel_span.get_span_context() if active_otel_span else None
    if active_otel_ctx is not None and active_otel_ctx.is_valid:
        return f"{active_otel_ctx.trace_id:032x}"

    return generate_trace_id()


def bind_trace_context(
    trace_id: str | None = None,
    *,
    workspace_id: str | None = None,
    run_id: str | None = None,
    step_id: str | None = None,
    span_id: str | None = None,
) -> TraceContext:
    """Bind `trace_id`, `workspace_id`, `run_id`, and `step_id` to contextvars, structlog & OTel."""
    active_otel_span = otel_trace.get_current_span()
    active_otel_ctx = active_otel_span.get_span_context() if active_otel_span else None
    has_recording_otel_span = bool(
        active_otel_span is not None
        and active_otel_span.is_recording()
        and active_otel_ctx is not None
        and active_otel_ctx.is_valid
    )

    if has_recording_otel_span and active_otel_ctx is not None and trace_id is None:
        normalized = f"{active_otel_ctx.trace_id:032x}"
        resolved_span_id = span_id or f"{active_otel_ctx.span_id:016x}"
    else:
        normalized = resolve_or_create_trace_id(x_trace_id=trace_id)
        resolved_span_id = span_id or (
            f"{active_otel_ctx.span_id:016x}"
            if has_recording_otel_span and active_otel_ctx is not None
            else generate_span_id()
        )

    ctx = TraceContext(
        trace_id=normalized,
        workspace_id=workspace_id,
        run_id=run_id,
        step_id=step_id,
        span_id=resolved_span_id,
    )
    _trace_ctx_var.set(ctx)

    if has_recording_otel_span and active_otel_span is not None:
        if workspace_id:
            active_otel_span.set_attribute("orcia.workspace_id", workspace_id)
        if run_id:
            active_otel_span.set_attribute("orcia.run_id", run_id)
        if step_id:
            active_otel_span.set_attribute("orcia.step_id", step_id)
    else:
        prev_token = _otel_token_var.get()
        if prev_token is not None:
            with contextlib.suppress(Exception):
                otel_context.detach(prev_token)
        otel_span_ctx = SpanContext(
            trace_id=int(normalized, 16),
            span_id=int(resolved_span_id, 16),
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        token = otel_context.attach(set_span_in_context(NonRecordingSpan(otel_span_ctx)))
        _otel_token_var.set(token)

    structlog.contextvars.clear_contextvars()
    bound_fields: dict[str, str] = {"trace_id": ctx.trace_id, "span_id": ctx.span_id}
    if ctx.workspace_id:
        bound_fields["workspace_id"] = ctx.workspace_id
    if ctx.run_id:
        bound_fields["run_id"] = ctx.run_id
    if ctx.step_id:
        bound_fields["step_id"] = ctx.step_id
    structlog.contextvars.bind_contextvars(**bound_fields)
    return ctx


def clear_trace_context() -> None:
    """Clear active trace contextvars and OpenTelemetry span context."""
    prev_token = _otel_token_var.get()
    if prev_token is not None:
        with contextlib.suppress(Exception):
            otel_context.detach(prev_token)
        _otel_token_var.set(None)
    _trace_ctx_var.set(None)
    structlog.contextvars.clear_contextvars()


def get_current_trace_context() -> TraceContext:
    """Return active `TraceContext`, lazily creating one if unset."""
    current = _trace_ctx_var.get()
    if current is None:
        return bind_trace_context(generate_trace_id())
    return current


def get_current_trace_id() -> str:
    """Return the active 32-hex `trace_id`."""
    return get_current_trace_context().trace_id


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
        trace_ctx_getter=_trace_ctx_var.get,
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
