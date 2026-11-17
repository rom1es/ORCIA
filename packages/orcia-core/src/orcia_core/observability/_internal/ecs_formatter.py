"""ECS 1-line JSON formatter, LOG_LEVEL resolver, probe filter, and secret scrubbing (`AD-23`)."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from opentelemetry import trace as otel_trace

from orcia_core.kernel.secret_ports import SecretRef

REDACTED_PLACEHOLDER = "[REDACTED_SECRET]"

_LOG_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_HEALTH_PROBE_PATH_RE = re.compile(
    r"(?:^|[\s\"']|https?://[^/\s]+)(?:/api/v1/health|/ready)(?:[?\"\s']|$)"
)
_HTTP_STATUS_RE = re.compile(r'(?:"HTTP/[0-9.]+"\s+|status[=:]\s*|\s)([1-5]\d{2})(?:\s|$|"|\))')

_SENSITIVE_KEY_RE = re.compile(
    r"(secret|password|passwd|pwd|api[_-]?key|apikey|authorization|bearer|"
    r"private[_-]?key|vault[_-]?ref|canary|access[_-]?token|refresh[_-]?token|"
    r"auth[_-]?token|api[_-]?token|bearer[_-]?token|bootstrap[_-]?token|"
    r"session[_-]?token|id[_-]?token|mcp[_-]?token|webhook[_-]?secret|"
    r"signing[_-]?secret|master[_-]?key|client[_-]?secret|encryption[_-]?key|"
    r"credentials?|^token$|^pat$|(?:^|_)pat(?:_|$)|(?:^|_)jwt(?:_|$))",
    re.IGNORECASE,
)

_INLINE_SECRET_RE = re.compile(
    r"(?i:Bearer\s+[A-Za-z0-9._~+/=-]+|Basic\s+[A-Za-z0-9+/=]{8,})|"
    r"eyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}|"
    r"eyJ[A-Za-z0-9_\-]{10,}|"
    r"sk-[A-Za-z0-9_\-]{6,}|"
    r"(?:ghp|gho|pat)_[A-Za-z0-9_\-]{6,}|"
    r"CANARY_SECRET_[A-Za-z0-9_\-]+|"
    r"SecretRef\([^)]*\)"
)

_INLINE_KV_SECRET_RE = re.compile(
    r"(?i)\b(ORCIA_BOOTSTRAP_TOKEN|password|passwd|secret|api_key|"
    r"bearer_token|access_token|refresh_token|auth_token|token|jwt|pat)"
    r"\s*([:=])\s*(['\"]?)([^\s'\",;)}\]]+)\3"
)

_REGISTERED_SECRET_VALUES: set[str] = set()

_ECS_RESERVED_KEYS: frozenset[str] = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "logger_name",
        "message",
        "event",
        "service",
        "env",
        "version",
        "trace_id",
        "span_id",
        "workspace_id",
        "run_id",
        "step_id",
        "exception",
        "ctx",
    }
)


def resolve_log_level(explicit_level: str | None = None) -> int:
    """Resolve `LOG_LEVEL` (`DEBUG|INFO|WARNING|ERROR|CRITICAL`, defaulting to `INFO`)."""
    raw = explicit_level if explicit_level is not None else os.environ.get("LOG_LEVEL", "INFO")
    normalized = (raw or "INFO").strip().upper()
    return _LOG_LEVEL_MAP.get(normalized, logging.INFO)


def resolve_environment(explicit_env: str | None = None) -> str:
    """Resolve deployment environment name for ECS `env` attribute."""
    if explicit_env and explicit_env.strip():
        return explicit_env.strip()
    for env_key in ("ORCIA_ENV", "ENVIRONMENT", "ENV"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    return "development"


def resolve_version(explicit_version: str = "0.1.0") -> str:
    """Resolve service version for ECS `version` attribute."""
    env_ver = os.environ.get("ORCIA_VERSION", "").strip()
    return env_ver or explicit_version


def register_sensitive_secret_value(secret_value: str) -> None:
    """Register a resolved secret value so `structlog` and scrubbers redact it (`DEC-SEC-01`)."""
    cleaned = secret_value.strip()
    if len(cleaned) >= 4:
        _REGISTERED_SECRET_VALUES.add(cleaned)


def clear_sensitive_secret_values() -> None:
    """Clear registered sensitive secret values (used in isolated tests)."""
    _REGISTERED_SECRET_VALUES.clear()


def scrub_sensitive_text(text: str) -> str:
    """Replace inline credentials, JWTs, PATs, SecretRef, or registered secrets."""
    redacted = _INLINE_SECRET_RE.sub(REDACTED_PLACEHOLDER, text)
    redacted = _INLINE_KV_SECRET_RE.sub(rf"\1\2{REDACTED_PLACEHOLDER}", redacted)
    for secret_val in tuple(_REGISTERED_SECRET_VALUES):
        if secret_val and secret_val in redacted:
            redacted = redacted.replace(secret_val, REDACTED_PLACEHOLDER)
    return redacted


def _scrub_value(val: object) -> object:
    if isinstance(val, SecretRef):
        return REDACTED_PLACEHOLDER
    if isinstance(val, dict):
        return scrub_sensitive_dict(val)
    if isinstance(val, (list, tuple)):
        return [_scrub_value(item) for item in val]
    if isinstance(val, str):
        return scrub_sensitive_text(val)
    return val


def scrub_sensitive_dict(
    payload: dict[str, object],
    *,
    allowed_keys: frozenset[str] | None = None,
) -> dict[str, object]:
    """Scrub secret keys/values recursively and optionally enforce an allowlist (`NFR-SEC-4`)."""
    sanitized: dict[str, object] = {}
    for key, val in payload.items():
        if allowed_keys is not None and key not in allowed_keys:
            continue
        if _SENSITIVE_KEY_RE.search(str(key)):
            sanitized[key] = REDACTED_PLACEHOLDER
        else:
            sanitized[key] = _scrub_value(val)
    return sanitized


def mask_secrets_processor(
    _logger: object,
    _method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    """Structlog processor masking secrets in `message`, `ctx`, `exception`, and top-level keys."""
    for key, val in list(event_dict.items()):
        if (key not in _ECS_RESERVED_KEYS and _SENSITIVE_KEY_RE.search(str(key))) or isinstance(
            val, SecretRef
        ):
            event_dict[key] = REDACTED_PLACEHOLDER
        elif isinstance(val, str):
            event_dict[key] = scrub_sensitive_text(val)
        elif isinstance(val, dict):
            event_dict[key] = scrub_sensitive_dict(val)
        elif isinstance(val, (list, tuple)):
            event_dict[key] = [_scrub_value(item) for item in val]
    return event_dict


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
        if explicit_msg is not None:
            message = str(explicit_msg)
        else:
            message = "" if event_val is None else str(event_val)

        svc = str(event_dict.pop("service", service))
        env_val = str(event_dict.pop("env", env))
        ver = str(event_dict.pop("version", version))

        ctx_trace, ctx_span, ctx_ws, ctx_run, ctx_step, is_recording_otel = (
            _resolve_active_trace_fields(trace_ctx_getter)
        )
        popped_trace = event_dict.pop("trace_id", None)
        popped_span = event_dict.pop("span_id", None)
        if is_recording_otel:
            trace_id = ctx_trace
            span_id = ctx_span
        else:
            trace_id = popped_trace if popped_trace is not None else ctx_trace
            span_id = popped_span if popped_span is not None else ctx_span
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
                service=service,
                env=env,
                version=version,
                trace_ctx_getter=trace_ctx_getter,
            ),
            structlog.processors.JSONRenderer(serializer=_json_dumps_single_line),
        ],
    )
