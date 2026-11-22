"""Async Turn Producer Task Execution, Liveness Heartbeat & FinOps Flush (`Story 26.3`)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import httpx

from orcia_api.routers._assistant_turn_producer_helpers import (
    emit_stream_error_and_outbox,
    flush_turn_telemetry_and_finops,
    handle_turn_cancelled,
    handle_turn_failure,
    watch_liveness_and_stop,
)
from orcia_api.routers._assistant_usage_telemetry import resolve_usage_with_fallback
from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.orchestration.llm_streaming_sse_utils import delta_to_sse_dict
from orcia_core.orchestration.redis_rate_limiter import RedisAssistantRateLimiter
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)

logger = get_logger("orcia.assistant.llm")


async def execute_turn_producer_task(
    *,
    registry: RedisAssistantTurnRegistry,
    rate_limiter: RedisAssistantRateLimiter,
    initial_record: AssistantTurnRecord,
    lease_token: str,
    liveness_ttl_s: int,
    t0: float,
    default_thinking: str,
    fallback_response_text: str | None,
    ep: LlmEndpointConfig | None,
    http_client_getter: Callable[[], httpx.AsyncClient],
    messages_builder: Callable[[], list[dict[str, Any]]],
    tools_builder: Callable[[], list[dict[str, Any]]],
    conversation_history_count: int,
    folder_pinned_notes: str | None,
    llm_port: LlmStreamingPort | None,
    user_email: str | None,
    user_display_name: str | None,
    audit_ledger_sink: Any | None,
    locale: str,
    instance: str,
    outbox_emitter: Any | None = None,
) -> None:
    """Execute background LLM turn, push events to Redis Stream, and flush FinOps in `finally`."""
    record = initial_record
    turn_id = record.turn_id
    current_task = asyncio.current_task()
    assert current_task is not None
    watcher = asyncio.create_task(
        watch_liveness_and_stop(
            registry, turn_id=turn_id, liveness_ttl_s=liveness_ttl_s, producer_task=current_task
        )
    )
    obs_in, obs_out, saw_usage, obs_lat = 0, 0, False, 0.0
    streamed_text, thinking_text, emitted_tokens = "", "", False
    flushed = False
    model_label = ep.model_name if ep is not None else "Polyvalent"

    async def _flush_once(rec: AssistantTurnRecord) -> None:
        nonlocal flushed
        if flushed:
            return
        flushed = True
        await flush_turn_telemetry_and_finops(
            record=rec,
            t0=t0,
            streamed_text=streamed_text,
            thinking_text=thinking_text,
            obs_in=obs_in,
            obs_out=obs_out,
            saw_usage=saw_usage,
            obs_lat=obs_lat,
            model_label=model_label,
            conversation_history_count=conversation_history_count,
            folder_pinned_notes=folder_pinned_notes,
            audit_ledger_sink=audit_ledger_sink,
            user_email=user_email,
            user_display_name=user_display_name,
            outbox_emitter=outbox_emitter,
        )

    try:
        active_port = llm_port
        use_streaming_port = ep is not None or (
            active_port is not None
            and getattr(active_port, "is_cassette_adapter", False)
            and not fallback_response_text
        )
        if use_streaming_port:
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
            pending_completed_data: dict[str, Any] | None = None
            async for delta in active_port.stream_chat_sse(req):
                evt = delta_to_sse_dict(delta)
                raw_data = evt.get("data")
                data_dict: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
                data_dict["trace_id"] = record.trace_id
                if evt["event"] == "thinking_delta":
                    thinking_text = str(data_dict.get("thinking_text") or "")
                elif evt["event"] == "token_delta":
                    emitted_tokens = True
                    streamed_text = str(data_dict.get("accumulated_text") or "")
                elif evt["event"] == "stream_error":
                    await emit_stream_error_and_outbox(
                        registry=registry,
                        record=record,
                        t0=t0,
                        error_code=str(data_dict.get("error_code") or "ERR_INTERNAL_SERVER_ERROR"),
                        status=int(data_dict.get("status") or 502),
                        detail_override=str(data_dict.get("message") or ""),
                        thinking_text=thinking_text,
                        streamed_text=streamed_text,
                        instance=instance,
                        locale=locale,
                        outbox_emitter=outbox_emitter,
                    )
                    return
                elif evt["event"] == "turn_completed":
                    data_dict["turn_id"] = turn_id
                    data_dict["assembled_system_prompt"] = record.assembled_system_prompt
                    obs_in = int(data_dict.get("input_tokens") or 0)
                    obs_out = int(data_dict.get("output_tokens") or 0)
                    saw_usage = str(data_dict.get("usage_source") or "") == "provider"
                    obs_lat = float(data_dict.get("latency_ms") or 0.0)
                    streamed_text = str(data_dict.get("response_text") or streamed_text)
                    thinking_text = str(data_dict.get("thinking_text") or thinking_text)
                    pending_completed_data = data_dict
                    continue
                await registry.append_event(turn_id, event=evt["event"], data=data_dict)
            if emitted_tokens:
                record = replace(
                    record,
                    status="COMPLETED",
                    thinking_text=thinking_text,
                    streamed_text=streamed_text,
                    elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                )
                await _flush_once(record)
                await registry.set_stream_ttl(turn_id, ttl_seconds=1800)
                if pending_completed_data is not None:
                    await registry.append_event(
                        turn_id,
                        event="turn_completed",
                        data=pending_completed_data,
                        ttl_seconds=1800,
                    )
                await registry.update_turn(record)
                return
            await emit_stream_error_and_outbox(
                registry=registry,
                record=record,
                t0=t0,
                error_code="ERR_INTERNAL_SERVER_ERROR",
                status=502,
                detail_override=(
                    f"AI model {stream_ep.model_name} ({stream_ep.endpoint_uri}) "
                    "returned zero tokens. Verify provider availability."
                ),
                thinking_text=thinking_text,
                streamed_text=streamed_text,
                instance=instance,
                locale=locale,
                outbox_emitter=outbox_emitter,
            )
            return

        thinking_text = default_thinking
        await registry.append_event(
            turn_id,
            event="thinking_delta",
            data={
                "step_code": "NODE_5_SINGLE_STREAM_LLM",
                "thinking_text": default_thinking,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "trace_id": record.trace_id,
            },
        )
        full_text = fallback_response_text or ""
        acc: list[str] = []
        for chunk in full_text.splitlines(keepends=True) or ([full_text] if full_text else []):
            acc.append(chunk)
            streamed_text = "".join(acc)
            emitted_tokens = True
            await registry.append_event(
                turn_id,
                event="token_delta",
                data={
                    "delta": chunk,
                    "accumulated_text": streamed_text,
                    "trace_id": record.trace_id,
                },
            )
        fb_in, fb_out, fb_src = resolve_usage_with_fallback(
            prompt_text=f"{record.assembled_system_prompt}\n{record.user_prompt}",
            reply_text=f"{full_text}\n{default_thinking}",
        )
        obs_in, obs_out, saw_usage = fb_in, fb_out, fb_src == "provider"
        obs_lat = round((time.perf_counter() - t0) * 1000.0, 2)
        record = replace(
            record,
            status="COMPLETED",
            thinking_text=thinking_text,
            streamed_text=streamed_text,
            elapsed_ms=obs_lat,
        )
        await _flush_once(record)
        await registry.set_stream_ttl(turn_id, ttl_seconds=1800)
        await registry.append_event(
            turn_id,
            event="turn_completed",
            data={
                "turn_id": turn_id,
                "response_text": full_text,
                "thinking_text": default_thinking,
                "assembled_system_prompt": record.assembled_system_prompt,
                "latency_ms": obs_lat,
                "input_tokens": fb_in,
                "output_tokens": fb_out,
                "usage_source": fb_src,
                "trace_id": record.trace_id,
            },
        )
        await registry.update_turn(record)
    except asyncio.CancelledError:
        record = await handle_turn_cancelled(
            registry=registry,
            record=record,
            t0=t0,
            streamed_text=streamed_text,
            thinking_text=thinking_text,
            obs_in=obs_in,
            obs_out=obs_out,
            saw_usage=saw_usage,
            outbox_emitter=outbox_emitter,
            flush_before_emit=_flush_once,
        )
    except Exception as exc:
        logger.warning(
            "background_turn_producer_failed",
            turn_id=turn_id,
            error_type=type(exc).__name__,
            error=scrub_sensitive_text(str(exc)),
        )
        record = await handle_turn_failure(
            registry=registry,
            record=record,
            exc=exc,
            t0=t0,
            thinking_text=thinking_text,
            streamed_text=streamed_text,
            instance=instance,
            locale=locale,
            outbox_emitter=outbox_emitter,
        )
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await watcher
        if not flushed and (record.status in ("COMPLETED", "STOPPED") or emitted_tokens):
            await _flush_once(record)
        await registry.clear_liveness(turn_id)
        await registry.set_stream_ttl(turn_id, ttl_seconds=1800)
        await rate_limiter.release_concurrency_slot(record.user_id, lease_token)
