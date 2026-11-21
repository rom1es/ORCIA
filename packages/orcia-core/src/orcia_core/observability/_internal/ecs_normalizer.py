"""ECS Log Record Normalizer & Formatter Builder (`AD-23`, `Story 26.1`)."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from opentelemetry import trace as otel_trace

from orcia_core.observability._internal.ecs_formatter import (
    mask_secrets_processor,
    scrub_sensitive_dict,
    scrub_sensitive_text,
)

_HEALTH_PROBE_PATH_RE = re.compile(
    r"(?:^|[\s\"']|https?://[^/\s]+)(?:/api/v1/health|/api/v1/ready|/ready)(?:[?\"\s']|$)"
)
_HTTP_STATUS_RE = re.compile(r'(?:"HTTP/[0-9.]+"\s+|status[=:]\s*|\s)([1-5]\d{2})(?:\s|$|"|\))')


class HealthProbeLogFilter(logging.Filter):
    """Filter out regular HTTP `< 400` health probe logs (`/api/v1/health`, `/ready`)."""

    @staticmethod
    def _extract_status(record: logging.LogRecord, rendered_message: str) -> int | None:
        if isinstance(record.msg, dict):
            raw_status = record.msg.get("status") or record.msg.get("status_code")
            if isinstance(raw_status, int):
                return raw_status
        if isinstance(record.args, tuple) and len(record.args) >= 5:
            last_arg = record.args[-1]
            if isinstance(last_arg, int) and 100 <= last_arg <= 599:
                return last_arg
        match = _HTTP_STATUS_RE.search(rendered_message)
        if match:
            return int(match.group(1))
        return None

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False for non-error access logs targeting `/api/v1/health` or `/ready`."""
        if isinstance(record.msg, dict):
            rendered = " ".join(
                str(part)
                for part in (
                    record.msg.get("path", ""),
                    record.msg.get("event", ""),
                    record.msg.get("message", ""),
                )
                if part
            )
        else:
            rendered = record.getMessage()

        if not _HEALTH_PROBE_PATH_RE.search(rendered):
            return True
        if record.levelno >= logging.WARNING:
            return True
        status = self._extract_status(record, rendered)
        return status is not None and status >= 400


def _resolve_active_trace_fields(
    trace_ctx_getter: Callable[[], Any],
) -> tuple[str | None, str | None, str | None, str | None, str | None, bool]:
    active_ctx = trace_ctx_getter()
    active_otel_span = otel_trace.get_current_span()
    otel_ctx = active_otel_span.get_span_context() if active_otel_span else None
    is_recording_otel = bool(
        active_otel_span is not None
        and active_otel_span.is_recording()
        and otel_ctx is not None
        and otel_ctx.is_valid
    )
    if is_recording_otel and otel_ctx is not None:
        return (
            f"{otel_ctx.trace_id:032x}",
            f"{otel_ctx.span_id:016x}",
            active_ctx.workspace_id if active_ctx is not None else None,
            active_ctx.run_id if active_ctx is not None else None,
            active_ctx.step_id if active_ctx is not None else None,
            True,
        )
    if active_ctx is not None:
        return (
            active_ctx.trace_id,
            active_ctx.span_id,
            active_ctx.workspace_id,
            active_ctx.run_id,
            active_ctx.step_id,
            False,
        )
    if otel_ctx is not None and otel_ctx.is_valid:
        return (f"{otel_ctx.trace_id:032x}", f"{otel_ctx.span_id:016x}", None, None, None, False)
    return (None, None, None, None, None, False)


def build_ecs_normalizer(
    *,
    service: str,
    env: str,
    version: str,
    trace_ctx_getter: Callable[[], Any],
) -> Callable[[object, str, structlog.typing.EventDict], structlog.typing.EventDict]:
    """Create a structlog processor normalizing every record into the canonical ECS schema."""

    def _normalize_to_ecs(
        _logger: object,
        _method_name: str,
        event_dict: structlog.typing.EventDict,
    ) -> structlog.typing.EventDict:
        timestamp = event_dict.pop("timestamp", None)
        if not timestamp:
            timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        level = str(event_dict.pop("level", "info")).lower()
        logger_name = str(
            event_dict.pop("logger", None) or event_dict.pop("logger_name", None) or "orcia"
        )
        event_val = event_dict.pop("event", None)
        explicit_msg = event_dict.pop("message", None)
        message = (
            str(explicit_msg)
            if explicit_msg is not None
            else ("" if event_val is None else str(event_val))
        )
        svc = str(event_dict.pop("service", service))
        env_val = str(event_dict.pop("env", env))
        ver = str(event_dict.pop("version", version))

        ctx_trace, ctx_span, ctx_ws, ctx_run, ctx_step, is_recording_otel = (
            _resolve_active_trace_fields(trace_ctx_getter)
        )
        popped_trace = event_dict.pop("trace_id", None)
        popped_span = event_dict.pop("span_id", None)
        trace_id = (
            ctx_trace
            if is_recording_otel
            else (popped_trace if popped_trace is not None else ctx_trace)
        )
        span_id = (
            ctx_span
            if is_recording_otel
            else (popped_span if popped_span is not None else ctx_span)
        )
        workspace_id = event_dict.pop("workspace_id", ctx_ws)
        run_id = event_dict.pop("run_id", ctx_run)
        step_id = event_dict.pop("step_id", ctx_step)
        exception_val = event_dict.pop("exception", None)
        existing_ctx = event_dict.pop("ctx", None)

        ctx_payload: dict[str, object] = {}
        if isinstance(existing_ctx, dict):
            ctx_payload.update(existing_ctx)
        if explicit_msg is not None and event_val is not None and str(event_val) != message:
            ctx_payload["event"] = event_val
        for rem_key, rem_val in list(event_dict.items()):
            event_dict.pop(rem_key)
            if not str(rem_key).startswith("_"):
                ctx_payload[str(rem_key)] = rem_val

        normalized: dict[str, Any] = {
            "timestamp": timestamp,
            "level": level,
            "logger": logger_name,
            "message": scrub_sensitive_text(message),
            "service": svc,
            "env": env_val,
            "version": ver,
            "trace_id": trace_id,
            "span_id": span_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "step_id": step_id,
            "ctx": scrub_sensitive_dict(ctx_payload),
        }
        if exception_val is not None:
            normalized["exception"] = scrub_sensitive_text(str(exception_val))
        return normalized

    return _normalize_to_ecs


def _json_dumps_single_line(obj: object, **_kwargs: Any) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False)


def build_json_processor_formatter(
    *,
    service: str,
    env: str,
    version: str,
    trace_ctx_getter: Callable[[], Any],
) -> structlog.stdlib.ProcessorFormatter:
    """Build `structlog.stdlib.ProcessorFormatter` rendering 1-line ECS JSON on stdout."""
    foreign_pre_chain: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=foreign_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            mask_secrets_processor,
            build_ecs_normalizer(
                service=service, env=env, version=version, trace_ctx_getter=trace_ctx_getter
            ),
            structlog.processors.JSONRenderer(serializer=_json_dumps_single_line),
        ],
    )
