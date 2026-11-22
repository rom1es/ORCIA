"""Liveness Watchdog, Terminal Transition & FinOps Helpers for Turn Producer (`Story 26.3`)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

from orcia_api.routers._assistant_background_registry import record_prompt_telemetry_entry
from orcia_api.routers._assistant_usage_telemetry import (
    persist_assistant_turn_ledger_entry,
    resolve_usage_with_fallback,
)
from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.redis_turn_registry import (
    RedisAssistantTurnRegistry,
    build_rfc9457_stream_error_payload,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord

logger = get_logger("orcia.assistant.llm")


async def watch_liveness_and_stop(
    registry: RedisAssistantTurnRegistry,
    *,
    turn_id: str,
    liveness_ttl_s: int,
    producer_task: asyncio.Task[None],
) -> None:
    """Refresh turn liveness TTL and cancel `producer_task` on cross-worker Redis stop."""
    beat_s = min(1.0, max(0.2, liveness_ttl_s / 3.0))
    pubsub = None
    redis_cli = getattr(registry, "_redis", None)
    if redis_cli is not None:
        with contextlib.suppress(Exception):
            pubsub = redis_cli.pubsub()
            await pubsub.subscribe(registry.stop_channel(turn_id))
    try:
        while not producer_task.done():
            await registry.refresh_liveness(turn_id, ttl_seconds=liveness_ttl_s)
            if await registry.is_stop_requested(turn_id) is not None:
                producer_task.cancel()
                return
            if pubsub is not None:
                with contextlib.suppress(Exception):
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=beat_s)
                    if msg is not None:
                        producer_task.cancel()
                        return
                    continue
            await asyncio.sleep(beat_s)
    except asyncio.CancelledError:
        return
    finally:
        if pubsub is not None:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(registry.stop_channel(turn_id))
                await pubsub.aclose()


async def handle_turn_cancelled(
    *,
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    t0: float,
    streamed_text: str,
    thinking_text: str,
    obs_in: int,
    obs_out: int,
    saw_usage: bool,
    outbox_emitter: Any | None = None,
    flush_before_emit: Callable[[AssistantTurnRecord], Awaitable[None]] | None = None,
) -> AssistantTurnRecord:
    """Persist stopped turn, FinOps ledger, and Outbox before emitting `turn_stopped`."""
    turn_id = record.turn_id
    stopped_by = await registry.is_stop_requested(turn_id) or record.user_id
    in_tok, out_tok, u_src = resolve_usage_with_fallback(
        prompt_text=f"{record.assembled_system_prompt}\n{record.user_prompt}",
        reply_text=f"{streamed_text}\n{thinking_text}",
        observed_input_tokens=obs_in,
        observed_output_tokens=obs_out,
        saw_provider_usage=saw_usage,
    )
    updated = replace(
        record,
        status="STOPPED",
        stopped_by_user_id=stopped_by,
        thinking_text=thinking_text,
        streamed_text=streamed_text,
        input_tokens=in_tok,
        output_tokens=out_tok,
        usage_source=u_src,
        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
    )
    if flush_before_emit is not None:
        await flush_before_emit(updated)
    if outbox_emitter is not None:
        await outbox_emitter.emit_turn_stopped(
            turn_id=turn_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            stopped_by_user_id=stopped_by,
            trace_id=record.trace_id,
        )
    await registry.set_stream_ttl(turn_id, ttl_seconds=1800)
    await registry.append_event(
        turn_id,
        event="turn_stopped",
        data={
            "turn_id": turn_id,
            "stopped_by_user_id": stopped_by,
            "partial_usage": {"input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": 0.0},
            "trace_id": record.trace_id,
        },
        ttl_seconds=1800,
    )
    await registry.update_turn(updated, ttl_seconds=1800)
    return updated


async def handle_turn_failure(
    *,
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    exc: Exception,
    t0: float,
    thinking_text: str,
    streamed_text: str,
    instance: str,
    locale: str,
    outbox_emitter: Any | None = None,
) -> AssistantTurnRecord:
    """Log failure safely, record ERROR state, and append RFC 9457 `stream_error` event."""
    safe_err = scrub_sensitive_text(str(exc))
    logger.warning(
        "background_turn_producer_failed",
        turn_id=record.turn_id,
        error_type=type(exc).__name__,
        error=safe_err,
    )
    err_payload = build_rfc9457_stream_error_payload(
        turn_id=record.turn_id,
        seq=0,
        trace_id=record.trace_id,
        error_code="ERR_INTERNAL_SERVER_ERROR",
        status=500,
        detail_override=safe_err,
        instance=instance,
        locale=locale,
    )
    updated = replace(
        record,
        status="ERROR",
        error_code="ERR_INTERNAL_SERVER_ERROR",
        error_message=safe_err,
        thinking_text=thinking_text,
        streamed_text=streamed_text,
        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
    )
    if outbox_emitter is not None:
        await outbox_emitter.emit_turn_failed(
            turn_id=record.turn_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            error_code="ERR_INTERNAL_SERVER_ERROR",
            trace_id=record.trace_id,
        )
    await registry.set_stream_ttl(record.turn_id, ttl_seconds=1800)
    await registry.append_event(
        record.turn_id, event="stream_error", data=err_payload, ttl_seconds=1800
    )
    await registry.update_turn(updated, ttl_seconds=1800)
    return updated


async def flush_turn_telemetry_and_finops(
    *,
    record: AssistantTurnRecord,
    t0: float,
    streamed_text: str,
    thinking_text: str,
    obs_in: int,
    obs_out: int,
    saw_usage: bool,
    obs_lat: float,
    model_label: str,
    conversation_history_count: int,
    folder_pinned_notes: str | None,
    audit_ledger_sink: Any | None,
    user_email: str | None,
    user_display_name: str | None,
    outbox_emitter: Any | None = None,
) -> None:
    """Record prompt telemetry and idempotent `audit_ledger` FinOps row inside `finally`."""
    in_tok, out_tok, u_src = resolve_usage_with_fallback(
        prompt_text=f"{record.assembled_system_prompt}\n{record.user_prompt}",
        reply_text=f"{streamed_text}\n{thinking_text}",
        observed_input_tokens=obs_in,
        observed_output_tokens=obs_out,
        saw_provider_usage=saw_usage,
    )
    record_prompt_telemetry_entry(
        workspace_id=record.workspace_id,
        turn_id=record.turn_id,
        user_prompt=record.user_prompt,
        assembled_system_prompt=record.assembled_system_prompt,
        conversation_history_count=conversation_history_count,
        folder_pinned_notes=folder_pinned_notes,
        thinking_text=thinking_text,
        assistant_reply=streamed_text,
        model_label=model_label,
        thinking_effort=record.effort,
        thinking_elapsed_seconds=max(1, round(time.perf_counter() - t0)),
    )
    await persist_assistant_turn_ledger_entry(
        audit_ledger_sink=audit_ledger_sink,
        user_id=record.user_id,
        user_email=user_email,
        user_display_name=user_display_name,
        workspace_id=record.workspace_id,
        turn_id=record.turn_id,
        model_id=record.model_id,
        inference_tier=record.inference_tier,
        effort=record.effort,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=obs_lat or (time.perf_counter() - t0) * 1000.0,
        usage_source=u_src,
        trace_id=record.trace_id,
        speed_mode=record.speed_mode,
    )
    if outbox_emitter is not None and record.status == "COMPLETED":
        await outbox_emitter.emit_turn_completed(
            turn_id=record.turn_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            speed_mode=record.speed_mode,
            input_tokens=in_tok,
            output_tokens=out_tok,
            trace_id=record.trace_id,
        )


async def emit_stream_error_and_outbox(
    *,
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    t0: float,
    error_code: str,
    status: int,
    detail_override: str,
    thinking_text: str,
    streamed_text: str,
    instance: str,
    locale: str,
    outbox_emitter: Any | None = None,
) -> None:
    """Persist ERROR state, append RFC 9457 `stream_error` frame, and emit Outbox failure."""
    err_payload = build_rfc9457_stream_error_payload(
        turn_id=record.turn_id,
        seq=0,
        trace_id=record.trace_id,
        error_code=error_code,
        status=status,
        detail_override=detail_override,
        instance=instance,
        locale=locale,
    )
    updated = replace(
        record,
        status="ERROR",
        error_code=error_code,
        error_message=str(err_payload["detail"]),
        thinking_text=thinking_text,
        streamed_text=streamed_text,
        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
    )
    if outbox_emitter is not None:
        await outbox_emitter.emit_turn_failed(
            turn_id=record.turn_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            error_code=error_code,
            trace_id=record.trace_id,
        )
    await registry.set_stream_ttl(record.turn_id, ttl_seconds=1800)
    await registry.append_event(
        record.turn_id, event="stream_error", data=err_payload, ttl_seconds=1800
    )
    await registry.update_turn(updated)
