"""Governed Multi-Step Tool Loop Executor for Background Turn Producer (`Story 26.6b`)."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from orcia_api.routers._assistant_tool_loop_rounds import (
    build_approval_proposal_text,
    execute_governed_round_with_outcomes,
)
from orcia_api.routers._assistant_tool_loop_rounds import (
    execute_sync_tool_followup as execute_sync_tool_followup,
)
from orcia_core.orchestration.assistant_loop_budgets import (
    AssistantLoopBudgetController,
    resolve_loop_budget_for_speed,
)
from orcia_core.orchestration.llm_streaming_sse_utils import delta_to_sse_dict
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutorPort,
    AuthorizedToolDescriptor,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)


async def execute_governed_tool_calls_round(
    *,
    tool_router: AssistantToolExecutorPort,
    catalog: Sequence[AuthorizedToolDescriptor],
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    iteration: int,
    tool_calls: Sequence[dict[str, Any]],
    user_email: str | None,
    user_display_name: str | None,
    locale: str,
    user_identity: Any | None = None,
    active_hat: str = "ARCHITECT",
) -> list[dict[str, Any]]:
    """Route every LLM tool call through `GovernedAssistantToolRouter` and emit SSE events."""
    messages, _ = await execute_governed_round_with_outcomes(
        tool_router=tool_router,
        catalog=catalog,
        registry=registry,
        record=record,
        iteration=iteration,
        tool_calls=tool_calls,
        user_email=user_email,
        user_display_name=user_display_name,
        locale=locale,
        user_identity=user_identity,
        active_hat=active_hat,
    )
    return messages


def _finalize_completed_payload(
    *,
    round_completed: dict[str, Any] | None,
    record: AssistantTurnRecord,
    streamed_text: str,
    thinking_text: str,
    obs_in: int,
    obs_out: int,
    obs_lat: float,
    approval_required: bool = False,
) -> dict[str, Any]:
    data = dict(round_completed or {})
    data["turn_id"] = record.turn_id
    data["assembled_system_prompt"] = record.assembled_system_prompt
    data["response_text"] = streamed_text
    data["thinking_text"] = thinking_text
    data["input_tokens"] = obs_in
    data["output_tokens"] = obs_out
    data["latency_ms"] = obs_lat
    if approval_required:
        data["approval_required"] = True
    return data


async def run_streaming_tool_loop(
    *,
    active_port: LlmStreamingPort,
    stream_ep: LlmEndpointConfig,
    initial_messages: list[dict[str, Any]],
    tools: tuple[dict[str, Any], ...],
    tool_catalog: tuple[AuthorizedToolDescriptor, ...],
    tool_router: AssistantToolExecutorPort | None,
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    user_email: str | None,
    user_display_name: str | None,
    locale: str,
    t0: float,
    user_identity: Any | None = None,
    active_hat: str = "ARCHITECT",
) -> dict[str, Any]:
    """Stream LLM deltas and execute multi-step governed tool loops within profile budgets."""
    policy = resolve_loop_budget_for_speed(record.speed_mode)
    controller = AssistantLoopBudgetController(policy)
    working_msgs: list[dict[str, Any]] = [dict(m) for m in initial_messages]
    thinking_text, streamed_text = "", ""
    obs_in, obs_out, saw_usage, obs_lat = 0, 0, False, 0.0
    emitted_tokens = False
    has_approval_required = False
    pending_completed_data: dict[str, Any] | None = None
    stream_error_data: dict[str, Any] | None = None

    while True:
        check = controller.check_budget()
        active_tools = tools if (check.can_continue and stream_ep.supports_tools) else ()
        if not check.can_continue:
            working_msgs.append(
                {
                    "role": "user",
                    "content": (
                        "Execution budget reached. Synthesize a concise final answer from the "
                        "tool results already gathered without calling additional tools."
                    ),
                }
            )
        req = LlmStreamRequest(
            endpoint=stream_ep,
            messages=tuple(working_msgs),
            tools=active_tools,
            include_thoughts=True,
        )
        round_completed: dict[str, Any] | None = None
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
                stream_error_data = data_dict
                break
            elif evt["event"] == "turn_completed":
                round_completed = data_dict
                continue
            await registry.append_event(record.turn_id, event=evt["event"], data=data_dict)

        if stream_error_data is not None:
            return {
                "stream_error": stream_error_data,
                "thinking_text": thinking_text,
                "streamed_text": streamed_text,
            }

        round_in = int((round_completed or {}).get("input_tokens") or 0)
        round_out = int((round_completed or {}).get("output_tokens") or 0)
        obs_in += round_in
        obs_out += round_out
        saw_usage = saw_usage or (
            str((round_completed or {}).get("usage_source") or "") == "provider"
        )
        obs_lat = round((time.perf_counter() - t0) * 1000.0, 2)
        if round_completed is not None:
            streamed_text = str(round_completed.get("response_text") or streamed_text)
            thinking_text = str(round_completed.get("thinking_text") or thinking_text)

        raw_tcs = (round_completed or {}).get("tool_calls") or ()
        tool_calls = [tc for tc in raw_tcs if isinstance(tc, dict)]
        controller.record_usage(round_in, round_out, increment_iteration=bool(active_tools))

        if not tool_calls or tool_router is None or not tool_catalog or not check.can_continue:
            pending_completed_data = _finalize_completed_payload(
                round_completed=round_completed,
                record=record,
                streamed_text=streamed_text,
                thinking_text=thinking_text,
                obs_in=obs_in,
                obs_out=obs_out,
                obs_lat=obs_lat,
            )
            break

        iteration = controller.iterations_used
        working_msgs.append(
            {
                "role": "assistant",
                "content": str((round_completed or {}).get("response_text") or ""),
                "tool_calls": tool_calls,
            }
        )
        tool_msgs, approval_outcomes = await execute_governed_round_with_outcomes(
            tool_router=tool_router,
            catalog=tool_catalog,
            registry=registry,
            record=record,
            iteration=iteration,
            tool_calls=tool_calls,
            user_email=user_email,
            user_display_name=user_display_name,
            locale=locale,
            user_identity=user_identity,
            active_hat=active_hat,
        )
        working_msgs.extend(tool_msgs)
        if approval_outcomes:
            has_approval_required = True
            proposal = build_approval_proposal_text(approval_outcomes, locale=locale)
            if not streamed_text:
                streamed_text = proposal
                emitted_tokens = True
                await registry.append_event(
                    record.turn_id,
                    event="token_delta",
                    data={
                        "delta": proposal,
                        "accumulated_text": streamed_text,
                        "trace_id": record.trace_id,
                    },
                )
            pending_completed_data = _finalize_completed_payload(
                round_completed=round_completed,
                record=record,
                streamed_text=streamed_text,
                thinking_text=thinking_text,
                obs_in=obs_in,
                obs_out=obs_out,
                obs_lat=obs_lat,
                approval_required=True,
            )
            break

    return {
        "emitted_tokens": emitted_tokens,
        "has_approval_required": has_approval_required,
        "thinking_text": thinking_text,
        "streamed_text": streamed_text,
        "obs_in": obs_in,
        "obs_out": obs_out,
        "saw_usage": saw_usage,
        "obs_lat": obs_lat,
        "pending_completed_data": pending_completed_data,
    }


__all__ = [
    "execute_governed_tool_calls_round",
    "execute_sync_tool_followup",
    "run_streaming_tool_loop",
]
