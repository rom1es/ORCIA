"""Background Turn Lifecycle, Rate-Limiting & Cross-Worker Stop (`Story 26.3`, `R1`)."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx

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
    get_rate_limiter_from_request,
    get_tracked_turn_tasks_from_request,
    get_turn_registry_from_request,
)
from orcia_api.routers._assistant_background_registry import (
    record_prompt_telemetry_entry as record_prompt_telemetry_entry,
)
from orcia_api.routers._assistant_background_registry import (
    stop_active_turn_for_workspace as stop_active_turn_for_workspace,
)
from orcia_api.routers._assistant_background_registry import (
    stop_assistant_turn_by_id as stop_assistant_turn_by_id,
)
from orcia_api.routers._assistant_turn_consumer import stream_assistant_turn_events
from orcia_api.routers._assistant_turn_producer import execute_turn_producer_task
from orcia_api.routers._assistant_usage_telemetry import resolve_assistant_outbox_emitter
from orcia_core.orchestration.assistant_turn_errors import (
    AssistantConcurrencyLimitError,
    AssistantRateLimitExceededError,
)
from orcia_core.orchestration.redis_rate_limiter import (
    RedisAssistantRateLimiter,
    resolve_rate_limit_settings,
)
from orcia_core.orchestration.redis_turn_registry import (
    RedisAssistantTurnRegistry,
    resolve_liveness_ttl_seconds,
)
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutorPort,
    AuthorizedToolDescriptor,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamingPort


async def enforce_assistant_rate_and_concurrency(
    rate_limiter: RedisAssistantRateLimiter,
    *,
    user_id: str,
    workspace_id: str,
    instance: str,
) -> str:
    """Enforce Redis sliding-window rate limit + per-user concurrency semaphore (`HTTP 429`)."""
    max_req, window_s, max_conc = resolve_rate_limit_settings()
    allowed, retry_after = await rate_limiter.check_and_record_turn_rate(
        user_id, workspace_id, window_seconds=window_s, max_requests=max_req
    )
    if not allowed:
        raise AssistantRateLimitExceededError(retry_after_s=retry_after, instance=instance)
    lease = await rate_limiter.acquire_concurrency_slot(user_id, limit=max_conc, ttl_seconds=180)
    if lease is None:
        raise AssistantConcurrencyLimitError(instance=instance)
    return lease


async def start_background_assistant_turn(
    *,
    registry: RedisAssistantTurnRegistry,
    rate_limiter: RedisAssistantRateLimiter,
    task_set: set[asyncio.Task[Any]],
    workspace_id: str,
    user_id: str,
    user_prompt: str,
    system_msg: str,
    default_thinking: str,
    fallback_response_text: str | None,
    ep: LlmEndpointConfig | None,
    http_client_getter: Callable[[], httpx.AsyncClient],
    messages_builder: Callable[[], list[dict[str, Any]]],
    tools_builder: Callable[[], list[dict[str, Any]]],
    conversation_history_count: int = 0,
    folder_pinned_notes: str | None = None,
    thinking_effort: str | None = None,
    llm_port: LlmStreamingPort | None = None,
    user_email: str | None = None,
    user_display_name: str | None = None,
    model_tier: str | None = None,
    audit_ledger_sink: Any | None = None,
    outbox_emitter: Any | None = None,
    trace_id: str | None = None,
    speed_mode: str | None = None,
    locale: str = "fr",
    instance: str = "/api/v1/assistant/turns",
    pre_acquired_lease: str | None = None,
    thread_id: str | None = None,
    parent_turn_id: str | None = None,
    citation_map: dict[str, Any] | None = None,
    prompt_assembly_latency_ms: float = 0.0,
    thread_messages_repo: Any | None = None,
    tool_router: AssistantToolExecutorPort | None = None,
    tool_catalog: tuple[AuthorizedToolDescriptor, ...] = (),
    user_identity: Any | None = None,
    active_hat: str = "ARCHITECT",
) -> str:
    """Register a Redis-tracked turn and launch its bounded `asyncio.Task` producer."""
    resolved_trace = trace_id or "00000000000000000000000000000000"
    lease_token = pre_acquired_lease or await enforce_assistant_rate_and_concurrency(
        rate_limiter, user_id=user_id, workspace_id=workspace_id, instance=instance
    )
    t0 = time.perf_counter()
    turn_id = f"turn-{uuid.uuid4().hex[:10]}"
    liveness_ttl_s = resolve_liveness_ttl_seconds()
    record = AssistantTurnRecord(
        turn_id=turn_id,
        workspace_id=workspace_id,
        user_id=user_id,
        status="RUNNING",
        user_prompt=user_prompt,
        assembled_system_prompt=system_msg,
        started_at_ms=round(time.time() * 1000.0, 2),
        trace_id=resolved_trace,
        speed_mode=speed_mode or "SPEED_1_FAST",
        model_id=ep.model_name if ep is not None else "assistant-router",
        inference_tier=model_tier or (ep.tier if ep is not None else None),
        effort=thinking_effort or "balanced",
        thread_id=thread_id,
        parent_turn_id=parent_turn_id,
        citation_map=dict(citation_map or {}),
        prompt_assembly_latency_ms=prompt_assembly_latency_ms,
    )
    await registry.register_turn(record)
    await registry.refresh_liveness(turn_id, ttl_seconds=liveness_ttl_s)
    if outbox_emitter is not None:
        await outbox_emitter.emit_turn_started(
            turn_id=turn_id,
            workspace_id=workspace_id,
            user_id=user_id,
            speed_mode=record.speed_mode,
            trace_id=resolved_trace,
        )

    task = asyncio.create_task(
        execute_turn_producer_task(
            registry=registry,
            rate_limiter=rate_limiter,
            initial_record=record,
            lease_token=lease_token,
            liveness_ttl_s=liveness_ttl_s,
            t0=t0,
            default_thinking=default_thinking,
            fallback_response_text=fallback_response_text,
            ep=ep,
            http_client_getter=http_client_getter,
            messages_builder=messages_builder,
            tools_builder=tools_builder,
            conversation_history_count=conversation_history_count,
            folder_pinned_notes=folder_pinned_notes,
            llm_port=llm_port,
            user_email=user_email,
            user_display_name=user_display_name,
            audit_ledger_sink=audit_ledger_sink,
            locale=locale,
            instance=instance,
            outbox_emitter=outbox_emitter,
            thread_messages_repo=thread_messages_repo,
            tool_router=tool_router,
            tool_catalog=tool_catalog,
            user_identity=user_identity,
            active_hat=active_hat,
        )
    )
    task_set.add(task)
    task.add_done_callback(task_set.discard)
    return turn_id


async def run_and_consume_decoupled_turn_stream(
    *,
    request: Any | None = None,
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
    pre_acquired_lease: str | None = None,
    thread_id: str | None = None,
    parent_turn_id: str | None = None,
    citation_map: dict[str, Any] | None = None,
    prompt_assembly_latency_ms: float = 0.0,
    thread_messages_repo: Any | None = None,
    tool_router: AssistantToolExecutorPort | None = None,
    tool_catalog: tuple[AuthorizedToolDescriptor, ...] = (),
    user_identity: Any | None = None,
    active_hat: str = "ARCHITECT",
) -> AsyncIterator[dict[str, Any]]:
    """Launch tracked background turn on Redis and stream ordered events."""
    reg = get_turn_registry_from_request(request)
    lim = get_rate_limiter_from_request(request)
    tasks = get_tracked_turn_tasks_from_request(request)
    turn_id = await start_background_assistant_turn(
        registry=reg,
        rate_limiter=lim,
        task_set=tasks,
        workspace_id=workspace_id,
        user_id=user_id or "u-anonymous",
        user_prompt=user_prompt,
        system_msg=system_msg,
        default_thinking=default_thinking,
        fallback_response_text=fallback_response_text,
        ep=ep,
        http_client_getter=http_client_getter,
        messages_builder=messages_builder,
        tools_builder=tools_builder,
        conversation_history_count=conversation_history_count,
        folder_pinned_notes=folder_pinned_notes,
        thinking_effort=thinking_effort,
        llm_port=llm_port,
        user_email=user_email,
        user_display_name=user_display_name,
        model_tier=model_tier,
        audit_ledger_sink=audit_ledger_sink,
        outbox_emitter=resolve_assistant_outbox_emitter(request),
        trace_id=trace_id,
        speed_mode=speed_mode,
        pre_acquired_lease=pre_acquired_lease,
        thread_id=thread_id,
        parent_turn_id=parent_turn_id,
        citation_map=citation_map,
        prompt_assembly_latency_ms=prompt_assembly_latency_ms,
        thread_messages_repo=thread_messages_repo,
        tool_router=tool_router,
        tool_catalog=tool_catalog,
        user_identity=user_identity,
        active_hat=active_hat,
    )
    async for evt in stream_assistant_turn_events(reg, turn_id=turn_id, trace_id=trace_id or ""):
        yield evt
