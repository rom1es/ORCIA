"""Structured JSON logging (`structlog`) with W3C OpenTelemetry `trace_id` propagation."""

from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass

import structlog

from orcia_kernel.ids import new_uuid7

HEX_32_RE = re.compile(r"^[0-9a-f]{32}$")
TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Immutable telemetry correlation context bound per request/task (NFR-OBS-1)."""

    trace_id: str
    workspace_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None


_trace_ctx_var: contextvars.ContextVar[TraceContext | None] = contextvars.ContextVar(
    "orcia_trace_context", default=None
)


def generate_trace_id() -> str:
    """Generate a valid 32-hex lowercase W3C OpenTelemetry trace identifier from UUIDv7."""
    return new_uuid7().hex


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

    return generate_trace_id()


def bind_trace_context(
    trace_id: str,
    *,
    workspace_id: str | None = None,
    run_id: str | None = None,
    step_id: str | None = None,
) -> TraceContext:
    """Bind `trace_id`, `workspace_id`, `run_id`, and `step_id` to contextvars and structlog."""
    normalized = resolve_or_create_trace_id(x_trace_id=trace_id)
    ctx = TraceContext(
        trace_id=normalized,
        workspace_id=workspace_id,
        run_id=run_id,
        step_id=step_id,
    )
    _trace_ctx_var.set(ctx)
    structlog.contextvars.clear_contextvars()
    bound_fields: dict[str, str] = {"trace_id": ctx.trace_id}
    if ctx.workspace_id:
        bound_fields["workspace_id"] = ctx.workspace_id
    if ctx.run_id:
        bound_fields["run_id"] = ctx.run_id
    if ctx.step_id:
        bound_fields["step_id"] = ctx.step_id
    structlog.contextvars.bind_contextvars(**bound_fields)
    return ctx


def clear_trace_context() -> None:
    """Clear active trace contextvars."""
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
