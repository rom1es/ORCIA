"""Cursor-Reattachable Redis Streams Consumer & Pod Liveness Watchdog (`Story 26.3`)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from orcia_core.orchestration.redis_turn_registry import (
    RedisAssistantTurnRegistry,
    build_rfc9457_stream_error_payload,
)

_TERMINAL_EVENTS = frozenset({"turn_completed", "turn_stopped", "stream_error"})


async def stream_assistant_turn_events(
    registry: RedisAssistantTurnRegistry,
    *,
    turn_id: str,
    after_cursor: str = "0-0",
    trace_id: str = "",
    instance: str = "/api/v1/assistant/turns",
    locale: str = "fr",
    poll_block_ms: int = 250,
) -> AsyncIterator[dict[str, Any]]:
    """Replay and live-tail Redis Stream events strictly after `after_cursor` without duplicates."""
    cursor = (after_cursor or "0-0").strip() or "0-0"
    while True:
        batch = await registry.read_events(turn_id, after_cursor=cursor, block_ms=poll_block_ms)
        for item in batch:
            cursor = item.cursor
            yield {
                "cursor": item.cursor,
                "event": item.event,
                "data": item.data,
            }
            if item.event in _TERMINAL_EVENTS:
                return

        rec = await registry.get_turn_by_id(turn_id)
        if rec is None:
            return
        if rec.status in ("COMPLETED", "STOPPED", "ERROR"):
            # Drain any trailing event written concurrently with status transition
            tail = await registry.read_events(turn_id, after_cursor=cursor, block_ms=0)
            for item in tail:
                cursor = item.cursor
                yield {"cursor": item.cursor, "event": item.event, "data": item.data}
                if item.event in _TERMINAL_EVENTS:
                    return
            return

        # Active RUNNING turn: verify worker liveness key has not expired (pod crash detection)
        if not await registry.is_live(turn_id):
            err_payload = build_rfc9457_stream_error_payload(
                turn_id=turn_id,
                seq=0,
                trace_id=trace_id or rec.trace_id,
                error_code="ERR_ASSISTANT_TURN_INTERRUPTED",
                status=503,
                instance=instance,
                locale=locale,
            )
            err_cursor = await registry.append_event(
                turn_id, event="stream_error", data=err_payload, ttl_seconds=1800
            )
            updated = replace(
                rec,
                status="ERROR",
                error_code="ERR_ASSISTANT_TURN_INTERRUPTED",
                error_message=str(err_payload["detail"]),
            )
            await registry.update_turn(updated, ttl_seconds=1800)
            yield {"cursor": err_cursor, "event": "stream_error", "data": err_payload}
            return
