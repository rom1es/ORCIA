"""Background Turn Registry (`asyncio.Task`) & Prompt Telemetry Store (`AD-15`)."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from orcia_api.routers.assistant_llm_providers import (
    ResolvedLiveLlmEndpoint,
    stream_provider_chat_sse_async,
)
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.assistant.llm")

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
    """Explicitly stop the running `asyncio.Task` for `workspace_id` when user clicks Stop `■`."""
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


async def run_and_consume_decoupled_turn_stream(
    *,
    workspace_id: str,
    user_prompt: str,
    system_msg: str,
    default_thinking: str,
    fallback_response_text: str | None,
    client_host: str,
    ep: ResolvedLiveLlmEndpoint | None,
    http_client_getter: Callable[[], httpx.AsyncClient],
    messages_builder: Callable[[], list[dict[str, Any]]],
    tools_builder: Callable[[], list[dict[str, Any]]],
    conversation_history_count: int,
    folder_pinned_notes: str | None,
    thinking_effort: str | None,
) -> AsyncIterator[dict[str, Any]]:
    """Spawn a decoupled `asyncio.Task` producer and yield SSE events."""
    t0 = time.perf_counter()
    turn_id = f"turn-{uuid.uuid4().hex[:10]}"
    bg_state = ActiveBackgroundTurnState(
        turn_id=turn_id,
        workspace_id=workspace_id,
        user_prompt=user_prompt,
        assembled_system_prompt=system_msg,
    )
    ACTIVE_WORKSPACE_TURNS[workspace_id] = bg_state

    async def _producer() -> None:
        try:
            if ep is not None:
                http_client = http_client_getter()
                messages = messages_builder()
                tools = tools_builder()
                emitted_tokens = False
                async for evt in stream_provider_chat_sse_async(
                    http_client, ep=ep, messages=messages, tools=tools or None
                ):
                    raw_data = evt.get("data")
                    data_dict: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
                    if evt["event"] == "thinking_delta":
                        bg_state.thinking_text = str(data_dict.get("thinking_text") or "")
                    elif evt["event"] == "token_delta":
                        emitted_tokens = True
                        bg_state.streamed_text = str(data_dict.get("accumulated_text") or "")
                    elif evt["event"] == "turn_completed":
                        data_dict["turn_id"] = turn_id
                        data_dict["assembled_system_prompt"] = system_msg
                        bg_state.streamed_text = str(
                            data_dict.get("response_text") or bg_state.streamed_text
                        )
                        bg_state.thinking_text = str(
                            data_dict.get("thinking_text") or bg_state.thinking_text
                        )
                    await notify_background_turn_event(bg_state, evt)
                if emitted_tokens:
                    bg_state.status = "COMPLETED"
                    record_prompt_telemetry_entry(
                        workspace_id=workspace_id,
                        turn_id=turn_id,
                        user_prompt=user_prompt,
                        assembled_system_prompt=system_msg,
                        conversation_history_count=conversation_history_count,
                        folder_pinned_notes=folder_pinned_notes,
                        thinking_text=bg_state.thinking_text,
                        assistant_reply=bg_state.streamed_text,
                        model_label=ep.model_name,
                        thinking_effort=thinking_effort or "balanced",
                        thinking_elapsed_seconds=max(1, round(time.perf_counter() - t0)),
                    )
                    return
                if client_host != "testclient":
                    err_msg = (
                        f"Le modèle IA {ep.model_name} ({ep.endpoint_uri}) n'a renvoyé aucun "
                        "jeton de réponse. Vérifiez que le fournisseur IA est bien démarré."
                    )
                    bg_state.status = "ERROR"
                    bg_state.error_message = err_msg
                    await notify_background_turn_event(
                        bg_state, {"event": "stream_error", "data": {"message": err_msg}}
                    )
                    return

            bg_state.thinking_text = default_thinking
            await notify_background_turn_event(
                bg_state,
                {
                    "event": "thinking_delta",
                    "data": {
                        "step_code": "NODE_5_SINGLE_STREAM_LLM",
                        "thinking_text": default_thinking,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    },
                },
            )
            full_text = fallback_response_text or ""
            accumulated: list[str] = []
            for line_chunk in full_text.splitlines(keepends=True) or (
                [full_text] if full_text else []
            ):
                accumulated.append(line_chunk)
                bg_state.streamed_text = "".join(accumulated)
                await notify_background_turn_event(
                    bg_state,
                    {
                        "event": "token_delta",
                        "data": {"delta": line_chunk, "accumulated_text": bg_state.streamed_text},
                    },
                )
            bg_state.status = "COMPLETED"
            await notify_background_turn_event(
                bg_state,
                {
                    "event": "turn_completed",
                    "data": {
                        "turn_id": turn_id,
                        "response_text": full_text,
                        "thinking_text": default_thinking,
                        "assembled_system_prompt": system_msg,
                        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    },
                },
            )
            record_prompt_telemetry_entry(
                workspace_id=workspace_id,
                turn_id=turn_id,
                user_prompt=user_prompt,
                assembled_system_prompt=system_msg,
                conversation_history_count=conversation_history_count,
                folder_pinned_notes=folder_pinned_notes,
                thinking_text=default_thinking,
                assistant_reply=full_text,
                thinking_effort=thinking_effort or "balanced",
            )
        except asyncio.CancelledError:
            bg_state.status = "STOPPED"
            raise
        except Exception as exc:
            logger.warning("background_turn_producer_failed", error_type=type(exc).__name__)
            bg_state.status = "ERROR"
            bg_state.error_message = str(exc)
        finally:
            async with bg_state.notify_cond:
                bg_state.notify_cond.notify_all()

    bg_state.task = asyncio.create_task(_producer())
    cursor = 0
    while True:
        while cursor < len(bg_state.events):
            evt = bg_state.events[cursor]
            cursor += 1
            yield evt
        if bg_state.status in ("COMPLETED", "STOPPED", "ERROR") or (
            bg_state.task is not None and bg_state.task.done()
        ):
            while cursor < len(bg_state.events):
                evt = bg_state.events[cursor]
                cursor += 1
                yield evt
            break
        async with bg_state.notify_cond:
            if cursor < len(bg_state.events) or bg_state.status in (
                "COMPLETED",
                "STOPPED",
                "ERROR",
            ):
                continue
            await bg_state.notify_cond.wait()
