"""ECS 1-line JSON formatter helpers, LOG_LEVEL resolver, and secret scrubbing (`AD-23`)."""

from __future__ import annotations

import logging
import os
import re
import threading
from collections import OrderedDict

import structlog

from orcia_core.kernel.secret_ports import SecretRef

REDACTED_PLACEHOLDER = "[REDACTED_SECRET]"
MAX_REGISTERED_SECRET_VALUES = 2048

_LOG_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

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

_REGISTERED_SECRET_VALUES: OrderedDict[str, None] = OrderedDict()
_SECRET_VALUES_LOCK = threading.Lock()

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
    """Register a resolved secret value in a bounded LRU (max 2048) for redaction."""
    cleaned = secret_value.strip()
    if len(cleaned) < 4:
        return
    with _SECRET_VALUES_LOCK:
        if cleaned in _REGISTERED_SECRET_VALUES:
            _REGISTERED_SECRET_VALUES.move_to_end(cleaned)
            return
        _REGISTERED_SECRET_VALUES[cleaned] = None
        while len(_REGISTERED_SECRET_VALUES) > MAX_REGISTERED_SECRET_VALUES:
            _REGISTERED_SECRET_VALUES.popitem(last=False)


def clear_sensitive_secret_values() -> None:
    """Clear registered sensitive secret values (used in isolated tests)."""
    with _SECRET_VALUES_LOCK:
        _REGISTERED_SECRET_VALUES.clear()


def scrub_sensitive_text(text: str) -> str:
    """Replace inline credentials, JWTs, PATs, SecretRef, or registered secrets."""
    redacted = _INLINE_SECRET_RE.sub(REDACTED_PLACEHOLDER, text)
    redacted = _INLINE_KV_SECRET_RE.sub(rf"\1\2{REDACTED_PLACEHOLDER}", redacted)
    with _SECRET_VALUES_LOCK:
        registered_snapshot = tuple(_REGISTERED_SECRET_VALUES.keys())
    for secret_val in registered_snapshot:
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


def __getattr__(name: str) -> object:
    """Re-export normalizer symbols lazily without circular import."""
    if name in (
        "HealthProbeLogFilter",
        "build_ecs_normalizer",
        "build_json_processor_formatter",
    ):
        from orcia_core.observability._internal import ecs_normalizer

        return getattr(ecs_normalizer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
