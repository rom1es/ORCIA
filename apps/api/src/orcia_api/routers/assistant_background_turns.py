"""Background Turn Producer (`asyncio.Task`) & Stream Consumer (`AD-15`, `Story 26.2`)."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx

from orcia_api.routers._assistant_background_registry import (
    ACTIVE_WORKSPACE_TURNS as ACTIVE_WORKSPACE_TURNS,
)
from orcia_api.routers._assistant_background_registry import (
    PROMPT_TELEMETRY_LOG as PROMPT_TELEMETRY_LOG,
)
from orcia_api.routers._assistant_background_registry import (
    ActiveBackgroundTurnState as ActiveBackgroundTurnState,
)
from orcia_api.routers._assistant_background_registry import (
    TurnStatus as TurnStatus,
)
from orcia_api.routers._assistant_background_registry import (
    get_active_turn_for_workspace as get_active_turn_for_workspace,
)
from orcia_api.routers._assistant_background_registry import (
    notify_background_turn_event,
)
from orcia_api.routers._assistant_background_registry import (
    record_prompt_telemetry_entry as record_prompt_telemetry_entry,
)
from orcia_api.routers._assistant_background_registry import (
    stop_active_turn_for_workspace as stop_active_turn_for_workspace,
)
from orcia_api.routers._assistant_usage_telemetry import (
    persist_assistant_turn_ledger_entry,
    resolve_usage_with_fallback,
)
from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.orchestration.llm_streaming_sse_utils import delta_to_sse_dict
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)

logger = get_logger("orcia.assistant.llm")


async def run_and_consume_decoupled_turn_stream(
    *,
    workspace_id: str,
    user_prompt: str,
    system_msg: str,
    default_thinking: str,
    fallback_response_text: str | None,
    ep: LlmEndpointConfig | None,
    http_client_getter: Callable[[], httpx.AsyncClient],
    messages_builder: Callable[[], list[dict[str, Any]]],
    tools_builder: Callable[[], list[dict[str, Any]]],
    conversation_history_count: int,
    folder_pinned_notes: str | None,
    thinking_effort: str | None,
    llm_port: LlmStreamingPort | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    user_display_name: str | None = None,
    model_tier: str | None = None,
    audit_ledger_sink: Any | None = None,
    trace_id: str | None = None,
    speed_mode: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Spawn a decoupled `asyncio.Task` producer via `LlmStreamingPort` and yield SSE events."""
    t0 = time.perf_counter()
    turn_id = f"turn-{uuid.uuid4().hex[:10]}"
    bg_state = ActiveBackgroundTurnState(
        turn_id=turn_id,
        workspace_id=workspace_id,
        user_prompt=user_prompt,
        assembled_system_prompt=system_msg,
    )
    ACTIVE_WORKSPACE_TURNS[workspace_id] = bg_state

    async def _finalize(
        reply: str, thinking: str, obs_in_tok: int, obs_out_tok: int, saw_usage: bool, lat_ms: float
    ) -> None:
        record_prompt_telemetry_entry(
            workspace_id=workspace_id,
            turn_id=turn_id,
            user_prompt=user_prompt,
            assembled_system_prompt=system_msg,
            conversation_history_count=conversation_history_count,
            folder_pinned_notes=folder_pinned_notes,
            thinking_text=thinking,
            assistant_reply=reply,
            model_label=ep.model_name if ep is not None else "Polyvalent",
            thinking_effort=thinking_effort or "balanced",
            thinking_elapsed_seconds=max(1, round(time.perf_counter() - t0)),
        )
        in_tok, out_tok, u_src = resolve_usage_with_fallback(
            prompt_text=f"{system_msg}\n{user_prompt}",
            reply_text=f"{reply}\n{thinking}",
            observed_input_tokens=obs_in_tok,
            observed_output_tokens=obs_out_tok,
            saw_provider_usage=saw_usage,
        )
        await persist_assistant_turn_ledger_entry(
            audit_ledger_sink=audit_ledger_sink,
            user_id=user_id,
            user_email=user_email,
            user_display_name=user_display_name,
            workspace_id=workspace_id,
            turn_id=turn_id,
            model_id=ep.model_name if ep is not None else "assistant-router",
            inference_tier=model_tier or (ep.tier if ep is not None else None),
            effort=thinking_effort or "balanced",
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=lat_ms,
            usage_source=u_src,
            trace_id=trace_id,
            speed_mode=speed_mode,
        )

    async def _producer() -> None:
        try:
            active_port = llm_port
            if ep is not None or (
                active_port is not None
                and getattr(active_port, "is_cassette_adapter", False)
                and not fallback_response_text
            ):
                stream_ep = ep or LlmEndpointConfig(
                    provider="cassette",
                    model_name="cassette-deterministic",
                    endpoint_uri="http://localhost",
                    auth_mode="none",
                )
                if active_port is None:
                    active_port = HttpxMultiProviderLlmStreamingAdapter(
                        http_client=http_client_getter()
                    )
                req = LlmStreamRequest(
                    endpoint=stream_ep,
                    messages=tuple(messages_builder()),
                    tools=tuple(tools_builder()),
                    include_thoughts=True,
                )
                emitted_tokens = False
                obs_in, obs_out, obs_src, obs_lat = 0, 0, "estimated", 0.0
                async for delta in active_port.stream_chat_sse(req):
                    evt = delta_to_sse_dict(delta)
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
                        obs_in = int(data_dict.get("input_tokens") or 0)
                        obs_out = int(data_dict.get("output_tokens") or 0)
                        obs_src = str(data_dict.get("usage_source") or "estimated")
                        obs_lat = float(data_dict.get("latency_ms") or 0.0)
                        bg_state.streamed_text = str(
                            data_dict.get("response_text") or bg_state.streamed_text
                        )
                        bg_state.thinking_text = str(
                            data_dict.get("thinking_text") or bg_state.thinking_text
                        )
                    await notify_background_turn_event(bg_state, evt)
                if emitted_tokens:
                    bg_state.status = "COMPLETED"
                    await _finalize(
                        bg_state.streamed_text,
                        bg_state.thinking_text,
                        obs_in,
                        obs_out,
                        obs_src == "provider",
                        obs_lat or (time.perf_counter() - t0) * 1000.0,
                    )
                    return
                err_msg = scrub_sensitive_text(
                    f"AI model {stream_ep.model_name} ({stream_ep.endpoint_uri}) "
                    "returned zero tokens. Verify provider availability."
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
            fb_in, fb_out, fb_src = resolve_usage_with_fallback(
                prompt_text=f"{system_msg}\n{user_prompt}",
                reply_text=f"{full_text}\n{default_thinking}",
            )
            fb_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            await notify_background_turn_event(
                bg_state,
                {
                    "event": "turn_completed",
                    "data": {
                        "turn_id": turn_id,
                        "response_text": full_text,
                        "thinking_text": default_thinking,
                        "assembled_system_prompt": system_msg,
                        "latency_ms": fb_lat,
                        "input_tokens": fb_in,
                        "output_tokens": fb_out,
                        "usage_source": fb_src,
                    },
                },
            )
            await _finalize(full_text, default_thinking, 0, 0, False, fb_lat)
        except asyncio.CancelledError:
            bg_state.status = "STOPPED"
            raise
        except Exception as exc:
            safe_err = scrub_sensitive_text(str(exc))
            logger.warning(
                "background_turn_producer_failed",
                error_type=type(exc).__name__,
                error=safe_err,
            )
            bg_state.status = "ERROR"
            bg_state.error_message = safe_err
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
