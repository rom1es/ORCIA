"""Structured JSON logging (`structlog`) with W3C OpenTelemetry `trace_id` (`AD-12`, `ARCH-P9`)."""

from __future__ import annotations

import contextlib
import contextvars
import re
from dataclasses import dataclass, field

import structlog
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context

from orcia_kernel.ids import new_uuid7

HEX_32_RE = re.compile(r"^[0-9a-f]{32}$")
TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")


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
    normalized = resolve_or_create_trace_id(x_trace_id=trace_id)
    resolved_span_id = span_id or generate_span_id()
    ctx = TraceContext(
        trace_id=normalized,
        workspace_id=workspace_id,
        run_id=run_id,
        step_id=step_id,
        span_id=resolved_span_id,
    )
    _trace_ctx_var.set(ctx)

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


def configure_structlog() -> None:
    """Configure `structlog` for deterministic JSON structured logging with contextvars."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str = "orcia") -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to `name`."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(logger_name=name)
    return logger
