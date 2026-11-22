"""Assistant Turn State Serialization, App State Lookup & Prompt Telemetry (`Story 26.3`)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from orcia_core.orchestration.redis_rate_limiter import RedisAssistantRateLimiter
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord

TurnStatus = Literal["IDLE", "RUNNING", "COMPLETED", "STOPPED", "ERROR"]
PROMPT_TELEMETRY_LOG: dict[str, list[dict[str, object]]] = {}


@dataclass
class ActiveBackgroundTurnState:
    """Serialized snapshot for a decoupled background LLM turn."""

    turn_id: str
    workspace_id: str
    user_prompt: str
    assembled_system_prompt: str
    status: TurnStatus = "RUNNING"
    thinking_text: str = ""
    streamed_text: str = ""
    started_at_ms: float = field(default_factory=lambda: round(time.time() * 1000.0, 2))
    elapsed_ms: float = 0.0
    error_message: str | None = None


def turn_record_to_background_state(record: AssistantTurnRecord) -> ActiveBackgroundTurnState:
    """Convert a Redis `AssistantTurnRecord` into `ActiveBackgroundTurnState`."""
    return ActiveBackgroundTurnState(
        turn_id=record.turn_id,
        workspace_id=record.workspace_id,
        user_prompt=record.user_prompt,
        assembled_system_prompt=record.assembled_system_prompt,
        status=record.status,
        thinking_text=record.thinking_text,
        streamed_text=record.streamed_text,
        started_at_ms=record.started_at_ms,
        elapsed_ms=record.elapsed_ms,
        error_message=record.error_message,
    )


def get_turn_registry_from_request(request: Any | None) -> RedisAssistantTurnRegistry:
    """Resolve `app.state.assistant_turn_registry` or return an isolated fallback instance."""
    state = getattr(getattr(request, "app", None), "state", None)
    reg = getattr(state, "assistant_turn_registry", None)
    if isinstance(reg, RedisAssistantTurnRegistry):
        return reg
    fallback = RedisAssistantTurnRegistry(redis_client=getattr(state, "redis_client", None))
    if state is not None:
        state.assistant_turn_registry = fallback
    return fallback


def get_rate_limiter_from_request(request: Any | None) -> RedisAssistantRateLimiter:
    """Resolve `app.state.assistant_rate_limiter` or return an isolated fallback instance."""
    state = getattr(getattr(request, "app", None), "state", None)
    lim = getattr(state, "assistant_rate_limiter", None)
    if isinstance(lim, RedisAssistantRateLimiter):
        return lim
    fallback = RedisAssistantRateLimiter(redis_client=getattr(state, "redis_client", None))
    if state is not None:
        state.assistant_rate_limiter = fallback
    return fallback


def get_tracked_turn_tasks_from_request(request: Any | None) -> set[asyncio.Task[Any]]:
    """Resolve `app.state.assistant_turn_tasks` tracked task set (`add_done_callback`)."""
    state = getattr(getattr(request, "app", None), "state", None)
    tasks = getattr(state, "assistant_turn_tasks", None)
    if isinstance(tasks, set):
        return tasks
    created: set[asyncio.Task[Any]] = set()
    if state is not None:
        state.assistant_turn_tasks = created
    return created


def record_prompt_telemetry_entry(
    *,
    workspace_id: str,
    turn_id: str | None,
    user_prompt: str,
    assembled_system_prompt: str,
    conversation_history_count: int = 0,
    folder_title: str | None = None,
    folder_pinned_notes: str | None = None,
    thinking_text: str = "",
    assistant_reply: str = "",
    model_label: str = "Polyvalent",
    thinking_effort: str = "balanced",
    thinking_elapsed_seconds: int = 1,
    user_feedback: Literal["LIKE", "DISLIKE"] | None = None,
    timestamp_iso: str | None = None,
) -> dict[str, object]:
    """Upsert a prompt telemetry & feedback record for `workspace_id`."""
    resolved_id = (turn_id or "").strip() or f"turn-{uuid.uuid4().hex[:10]}"
    now_iso = timestamp_iso or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    bucket = PROMPT_TELEMETRY_LOG.setdefault(workspace_id, [])
    for existing in bucket:
        if existing.get("turn_id") == resolved_id:
            if user_prompt:
                existing["user_prompt"] = user_prompt
            if assembled_system_prompt:
                existing["assembled_system_prompt"] = assembled_system_prompt
            if assistant_reply:
                existing["assistant_reply"] = assistant_reply
            if thinking_text:
                existing["thinking_text"] = thinking_text
            existing["user_feedback"] = user_feedback
            return existing
    entry: dict[str, object] = {
        "turn_id": resolved_id,
        "workspace_id": workspace_id,
        "timestamp_iso": now_iso,
        "user_prompt": user_prompt,
        "assembled_system_prompt": assembled_system_prompt,
        "conversation_history_count": conversation_history_count,
        "folder_title": folder_title,
        "folder_pinned_notes": folder_pinned_notes,
        "thinking_text": thinking_text,
        "assistant_reply": assistant_reply,
        "model_label": model_label,
        "thinking_effort": thinking_effort,
        "thinking_elapsed_seconds": thinking_elapsed_seconds,
        "user_feedback": user_feedback,
    }
    bucket.insert(0, entry)
    del bucket[100:]
    return entry


async def get_active_turn_for_workspace(
    workspace_id: str, *, request: Any | None = None, user_id: str = "u-anonymous"
) -> ActiveBackgroundTurnState | None:
    """Return latest turn state for `(workspace_id, user_id)` from Redis."""
    reg = get_turn_registry_from_request(request)
    rec = await reg.get_latest_turn(workspace_id, user_id)
    return turn_record_to_background_state(rec) if rec is not None else None


async def stop_assistant_turn_by_id(
    turn_id: str, *, request: Any | None = None, stopped_by_user_id: str
) -> ActiveBackgroundTurnState | None:
    """Propagate stop via Redis and wait briefly for producer `finally` flush."""
    reg = get_turn_registry_from_request(request)
    rec = await reg.get_turn_by_id(turn_id)
    if rec is None:
        return None
    await reg.request_stop(turn_id, stopped_by_user_id=stopped_by_user_id)
    for _ in range(30):
        latest = await reg.get_turn_by_id(turn_id)
        if latest is not None and latest.status in ("STOPPED", "COMPLETED", "ERROR"):
            return turn_record_to_background_state(latest)
        await asyncio.sleep(0.05)
    latest = await reg.get_turn_by_id(turn_id)
    if latest is not None and latest.status == "RUNNING":
        forced = replace(latest, status="STOPPED", stopped_by_user_id=stopped_by_user_id)
        await reg.update_turn(forced, ttl_seconds=1800)
        return turn_record_to_background_state(forced)
    return turn_record_to_background_state(latest) if latest is not None else None


async def stop_active_turn_for_workspace(
    workspace_id: str,
    *,
    request: Any | None = None,
    user_id: str = "u-anonymous",
    turn_id: str | None = None,
) -> ActiveBackgroundTurnState | None:
    """Stop either explicit `turn_id` or the latest active turn for `(workspace_id, user_id)`."""
    reg = get_turn_registry_from_request(request)
    target_id = turn_id
    if not target_id:
        latest = await reg.get_latest_turn(workspace_id, user_id)
        if latest is None:
            return None
        target_id = latest.turn_id
    return await stop_assistant_turn_by_id(target_id, request=request, stopped_by_user_id=user_id)
