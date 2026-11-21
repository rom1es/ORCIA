"""Serialization, Liveness Config & RFC 9457 Stream Error Helpers for Redis Turn Registry."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from orcia_core.kernel.errors import get_localized_error_text
from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord

logger = get_logger("orcia.core.orchestration.redis_turn_registry")


def decode_redis_val(raw: Any) -> str:
    """Decode Redis bytes or string cleanly to UTF-8 string."""
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)


def record_to_json(rec: AssistantTurnRecord) -> str:
    """Serialize `AssistantTurnRecord` into canonical JSON."""
    return json.dumps(asdict(rec), ensure_ascii=False)


def record_from_json(raw: str | bytes | None) -> AssistantTurnRecord | None:
    """Deserialize JSON bytes/string back into `AssistantTurnRecord`."""
    if raw is None:
        return None
    try:
        data = json.loads(decode_redis_val(raw))
        if not isinstance(data, dict):
            return None
        return AssistantTurnRecord(**data)
    except Exception as exc:
        logger.warning("assistant_turn_record_decode_failed", error_type=type(exc).__name__)
        return None


def cursor_gt(candidate: str, anchor: str) -> bool:
    """Return True when Redis Stream ID `candidate` is strictly greater than `anchor`."""
    if anchor == "0-0":
        return True
    try:
        c_ms, c_seq = (int(p) for p in candidate.split("-", 1))
        a_ms, a_seq = (int(p) for p in anchor.split("-", 1))
        return (c_ms, c_seq) > (a_ms, a_seq)
    except ValueError:
        return candidate > anchor


def resolve_liveness_ttl_seconds() -> int:
    """Resolve liveness key TTL from `ORCIA_ASSISTANT_LIVENESS_TTL_S` (default 15s)."""
    import os

    try:
        return max(1, int(os.environ.get("ORCIA_ASSISTANT_LIVENESS_TTL_S", "15").strip()))
    except ValueError:
        return 15


def build_rfc9457_stream_error_payload(
    *,
    turn_id: str,
    seq: int,
    trace_id: str,
    error_code: str,
    status: int,
    detail_override: str | None = None,
    instance: str = "/api/v1/assistant/turns",
    locale: str = "fr",
) -> dict[str, Any]:
    """Build RFC 9457 Problem Details + W3C `trace_id` envelope for SSE `stream_error`."""
    loc: Any = "en" if locale == "en" else "fr"
    safe_detail = scrub_sensitive_text(detail_override) if detail_override else None
    copy = get_localized_error_text(error_code, locale=loc, detail_override=safe_detail)
    slug = error_code.removeprefix("ERR_").lower().replace("_", "-")
    return {
        "type": f"https://orcia.io/problems/{slug}",
        "title": copy.title,
        "status": status,
        "detail": copy.detail,
        "message": copy.detail,
        "instance": instance,
        "error_code": error_code,
        "trace_id": trace_id,
        "turn_id": turn_id,
        "seq": seq,
        "timestamp": datetime.now(UTC).isoformat(),
    }
