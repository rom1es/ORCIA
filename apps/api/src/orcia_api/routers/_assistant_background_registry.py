"""Background Turn In-Memory Registry & Prompt Telemetry Store (`AD-15`, `Story 26.1`)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

TurnStatus = Literal["IDLE", "RUNNING", "COMPLETED", "STOPPED", "ERROR"]


@dataclass
class ActiveBackgroundTurnState:
    """In-memory state for a decoupled background LLM turn surviving SSE disconnects."""

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
    events: list[dict[str, Any]] = field(default_factory=list)
    notify_cond: asyncio.Condition = field(default_factory=asyncio.Condition)
    task: asyncio.Task[None] | None = None


ACTIVE_WORKSPACE_TURNS: dict[str, ActiveBackgroundTurnState] = {}
PROMPT_TELEMETRY_LOG: dict[str, list[dict[str, object]]] = {}


def get_active_turn_for_workspace(workspace_id: str) -> ActiveBackgroundTurnState | None:
    """Return the latest background turn state for `workspace_id`, if any."""
    return ACTIVE_WORKSPACE_TURNS.get(workspace_id)


async def notify_background_turn_event(
    state: ActiveBackgroundTurnState, event: dict[str, Any]
) -> None:
    """Append an SSE event to `state.events` and wake any attached SSE consumers."""
    state.events.append(event)
    state.elapsed_ms = round(time.time() * 1000.0 - state.started_at_ms, 2)
    async with state.notify_cond:
        state.notify_cond.notify_all()


async def stop_active_turn_for_workspace(workspace_id: str) -> ActiveBackgroundTurnState | None:
    """Explicitly stop the running `asyncio.Task` for `workspace_id` when user clicks Stop."""
    state = ACTIVE_WORKSPACE_TURNS.get(workspace_id)
    if state is None:
        return None
    if state.task is not None and not state.task.done():
        state.task.cancel()
    state.status = "STOPPED"
    state.elapsed_ms = round(time.time() * 1000.0 - state.started_at_ms, 2)
    async with state.notify_cond:
        state.notify_cond.notify_all()
    return state


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
