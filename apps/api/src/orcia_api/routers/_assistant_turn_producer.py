"""Async Turn Producer Task Execution, Liveness Heartbeat & FinOps Flush (`Story 26.3`)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from typing import Any

import httpx

from orcia_api.routers._assistant_turn_finalizer import (
    emit_fallback_response_events_async,
    finalize_and_emit_turn_completion_async,
)
from orcia_api.routers._assistant_turn_producer_helpers import (
    emit_stream_error_and_outbox,
    flush_turn_telemetry_and_finops,
    handle_turn_cancelled,
    handle_turn_failure,
    watch_liveness_and_stop,
)
from orcia_api.routers._assistant_turn_producer_tool_loop import run_streaming_tool_loop
from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.assistant_citations_models import EvidenceTable
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.orchestration.redis_rate_limiter import RedisAssistantRateLimiter
from orcia_core.orchestration.redis_thread_lock import RedisThreadTurnLock
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutorPort,
    AuthorizedToolDescriptor,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamingPort

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
    thread_messages_repo: Any | None = None,
    tool_router: AssistantToolExecutorPort | None = None,
    tool_catalog: tuple[AuthorizedToolDescriptor, ...] = (),
    user_identity: Any | None = None,
    active_hat: str = "ARCHITECT",
    turn_engine: AssistantTurnEngine | None = None,
    base_evidence_table: EvidenceTable | None = None,
    thread_lock: RedisThreadTurnLock | None = None,
) -> None:
    """Execute background LLM turn, push events to Redis Stream, and flush FinOps in `finally`."""
    record = initial_record
    turn_id = record.turn_id
    current_task = asyncio.current_task()
    watcher = (
        asyncio.create_task(
            watch_liveness_and_stop(
                registry, turn_id=turn_id, liveness_ttl_s=liveness_ttl_s, producer_task=current_task
            )
        )
        if current_task is not None
        else None
    )
    obs_in, obs_out, saw_usage, obs_lat = 0, 0, False, 0.0
    streamed_text, thinking_text, emitted_tokens = "", "", False
    flushed, lock_released = False, False
    model_label = ep.model_name if ep is not None else "Polyvalent"

    async def _release_lock_once() -> None:
        nonlocal lock_released
        if (
            lock_released
            or thread_lock is None
            or not record.thread_id
            or not record.thread_lock_token
        ):
            return
        lock_released = True
        await thread_lock.release_async(
            thread_id=record.thread_id, user_id=record.user_id, token=record.thread_lock_token
        )

    async def _flush_once(rec: AssistantTurnRecord, reply_override: str | None = None) -> None:
        nonlocal flushed
        if flushed:
            return
        flushed = True
        final_reply = reply_override if reply_override is not None else streamed_text
        await flush_turn_telemetry_and_finops(
            record=rec,
            t0=t0,
            streamed_text=final_reply,
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
            thread_messages_repo=thread_messages_repo,
        )
        await _release_lock_once()

    try:
        if turn_engine is not None:
            await turn_engine.start_assistant_reflexive_session_async(
                turn_id=turn_id,
                workspace_id=record.workspace_id,
                user_id=record.user_id,
                user_prompt=record.user_prompt,
                speed_mode=record.speed_mode,  # type: ignore[arg-type]
                locale=locale,
            )
        active_port = llm_port
        use_streaming_port = ep is not None or (
            active_port is not None
            and getattr(active_port, "is_cassette_adapter", False)
            and not fallback_response_text
        )
        stream_ep: LlmEndpointConfig | None = ep
        if use_streaming_port:
            stream_ep = ep or LlmEndpointConfig(
                provider="cassette",
                model_name="cassette-deterministic",
                endpoint_uri="http://localhost",
                auth_mode="none",
                supports_tools=True,
            )
            if active_port is None:
                active_port = HttpxMultiProviderLlmStreamingAdapter(
                    http_client=http_client_getter()
                )
            loop_out = await run_streaming_tool_loop(
                active_port=active_port,
                stream_ep=stream_ep,
                initial_messages=messages_builder(),
                tools=tuple(tools_builder()),
                tool_catalog=tool_catalog,
                tool_router=tool_router,
                registry=registry,
                record=record,
                user_email=user_email,
                user_display_name=user_display_name,
                locale=locale,
                t0=t0,
                user_identity=user_identity,
                active_hat=active_hat,
                turn_engine=turn_engine,
            )
            if "stream_error" in loop_out:
                err_data = loop_out["stream_error"]
                await _release_lock_once()
                await emit_stream_error_and_outbox(
                    registry=registry,
                    record=record,
                    t0=t0,
                    error_code=str(err_data.get("error_code") or "ERR_INTERNAL_SERVER_ERROR"),
                    status=int(err_data.get("status") or 502),
                    detail_override=str(err_data.get("message") or ""),
                    thinking_text=str(loop_out.get("thinking_text") or ""),
                    streamed_text=str(loop_out.get("streamed_text") or ""),
                    instance=instance,
                    locale=locale,
                    outbox_emitter=outbox_emitter,
                )
                return
            emitted_tokens = bool(loop_out["emitted_tokens"])
            thinking_text = str(loop_out["thinking_text"])
            streamed_text = str(loop_out["streamed_text"])
            obs_in = int(loop_out["obs_in"])
            obs_out = int(loop_out["obs_out"])
            saw_usage = bool(loop_out["saw_usage"])
            obs_lat = float(loop_out["obs_lat"])
            pending_completed_data = loop_out["pending_completed_data"]
            if not emitted_tokens and not bool(loop_out.get("has_approval_required")):
                await _release_lock_once()
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
            tool_outputs = loop_out.get("tool_outputs") or ()
        else:
            stream_ep = ep
            thinking_text = default_thinking
            streamed_text, emitted_tokens = await emit_fallback_response_events_async(
                registry=registry,
                record=record,
                default_thinking=default_thinking,
                fallback_response_text=fallback_response_text,
                t0=t0,
            )
            obs_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            tool_outputs, pending_completed_data = (), None

        record = await finalize_and_emit_turn_completion_async(
            turn_engine=turn_engine,
            base_evidence_table=base_evidence_table,
            tool_outputs=tool_outputs,
            pending_completed_data=pending_completed_data,
            record=record,
            stream_ep=stream_ep,
            thinking_text=thinking_text,
            streamed_text=streamed_text,
            obs_in=obs_in,
            obs_out=obs_out,
            saw_usage=saw_usage,
            obs_lat=obs_lat,
            t0=t0,
            user_email=user_email,
            user_display_name=user_display_name,
            registry=registry,
            flush_before_emit=_flush_once,
        )
        streamed_text = record.streamed_text
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
            turn_engine=turn_engine,
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
            turn_engine=turn_engine,
        )
    finally:
        if watcher is not None:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await watcher
        if not flushed and (record.status in ("COMPLETED", "STOPPED") or emitted_tokens):
            await _flush_once(record)
        await registry.clear_liveness(turn_id)
        await registry.set_stream_ttl(turn_id, ttl_seconds=1800)
        await rate_limiter.release_concurrency_slot(record.user_id, lease_token)
        await _release_lock_once()
