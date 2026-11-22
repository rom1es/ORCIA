"""Deterministic Multi-Step Tool Loop Budgets Controller (`Story 26.6a`, `AD-25`)."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.orchestration.assistant_turn_errors import TurnBudgetExceededError
from orcia_core.orchestration.llm_tool_dialects import format_tool_result_message
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)

BudgetLimitKind = Literal["iterations", "tokens", "wall_clock"]
ToolExecutorFn = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class AssistantLoopBudgetPolicy:
    """Profile budgets governing multi-step assistant tool loops."""

    max_iterations: int = 4
    max_total_tokens: int = 16_000
    max_wall_clock_seconds: float = 60.0
    force_synthesis_on_limit: bool = True


_SPEED_BUDGET_DEFAULTS: dict[str, tuple[int, int, float]] = {
    "SPEED_3_DEEP_AUDIT": (12, 48_000, 120.0),
    "SPEED_2_AGENT_TOOLS": (4, 16_000, 60.0),
}


def resolve_loop_budget_for_speed(
    speed_mode: str,
    *,
    max_iterations: int | None = None,
    max_total_tokens: int | None = None,
    max_wall_clock_seconds: float | None = None,
    force_synthesis_on_limit: bool = True,
) -> AssistantLoopBudgetPolicy:
    """Resolve default profile loop budgets for Speed 1, Speed 2, or Speed 3."""
    default_iter, default_tok, default_sec = _SPEED_BUDGET_DEFAULTS.get(
        speed_mode, (1, 8_000, 30.0)
    )
    return AssistantLoopBudgetPolicy(
        max_iterations=max(1, max_iterations) if max_iterations is not None else default_iter,
        max_total_tokens=max(1, max_total_tokens) if max_total_tokens is not None else default_tok,
        max_wall_clock_seconds=(
            max(0.01, float(max_wall_clock_seconds))
            if max_wall_clock_seconds is not None
            else default_sec
        ),
        force_synthesis_on_limit=force_synthesis_on_limit,
    )


@dataclass(frozen=True, slots=True)
class BudgetCheckResult:
    """Result of evaluating iteration, token, and wall-clock limits before a loop step."""

    can_continue: bool
    exceeded_kind: BudgetLimitKind | None = None
    detail: str = ""


class AssistantLoopBudgetController:
    """Deterministic budget tracker for iterations, cumulative tokens, and wall-clock time."""

    def __init__(
        self,
        policy: AssistantLoopBudgetPolicy,
        *,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._policy = policy
        self._clock = clock_fn
        self._started_at = self._clock()
        self.iterations_used = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @property
    def policy(self) -> AssistantLoopBudgetPolicy:
        return self._policy

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def elapsed_seconds(self) -> float:
        return max(0.0, float(self._clock()) - self._started_at)

    def record_usage(
        self, input_tokens: int, output_tokens: int, *, increment_iteration: bool = True
    ) -> None:
        """Accumulate iteration count and token usage."""
        if increment_iteration:
            self.iterations_used += 1
        self.total_input_tokens += max(0, int(input_tokens))
        self.total_output_tokens += max(0, int(output_tokens))

    def check_budget(self) -> BudgetCheckResult:
        """Check whether another tool-loop step is permitted under configured budgets."""
        p = self._policy
        if self.iterations_used >= p.max_iterations:
            msg = f"Iteration budget exhausted ({self.iterations_used}/{p.max_iterations})."
            return BudgetCheckResult(can_continue=False, exceeded_kind="iterations", detail=msg)
        if self.total_tokens >= p.max_total_tokens:
            msg = f"Token budget exhausted ({self.total_tokens}/{p.max_total_tokens})."
            return BudgetCheckResult(can_continue=False, exceeded_kind="tokens", detail=msg)
        elapsed = self.elapsed_seconds()
        if elapsed >= p.max_wall_clock_seconds:
            msg = f"Wall-clock budget exhausted ({elapsed:.2f}s/{p.max_wall_clock_seconds:.2f}s)."
            return BudgetCheckResult(can_continue=False, exceeded_kind="wall_clock", detail=msg)
        return BudgetCheckResult(can_continue=True)


@dataclass(frozen=True, slots=True)
class BoundedToolLoopResult:
    """Outcome of a bounded multi-step tool loop."""

    final_content: str
    thinking_text: str
    iterations_used: int
    total_input_tokens: int
    total_output_tokens: int
    elapsed_seconds: float
    executed_tool_calls: tuple[dict[str, Any], ...]
    forced_synthesis: bool = False
    limit_reached: BudgetLimitKind | None = None


def _build_loop_result(
    *,
    final_content: str,
    thinking_parts: Sequence[str],
    controller: AssistantLoopBudgetController,
    executed: Sequence[dict[str, Any]],
    forced_synthesis: bool = False,
    limit_reached: BudgetLimitKind | None = None,
) -> BoundedToolLoopResult:
    """Build normalized `BoundedToolLoopResult` from accumulated loop state."""
    return BoundedToolLoopResult(
        final_content=final_content,
        thinking_text="\n\n".join(thinking_parts),
        iterations_used=controller.iterations_used,
        total_input_tokens=controller.total_input_tokens,
        total_output_tokens=controller.total_output_tokens,
        elapsed_seconds=round(controller.elapsed_seconds(), 4),
        executed_tool_calls=tuple(executed),
        forced_synthesis=forced_synthesis,
        limit_reached=limit_reached,
    )


async def run_bounded_tool_loop(
    *,
    llm_port: LlmStreamingPort,
    endpoint: LlmEndpointConfig,
    messages: Sequence[dict[str, Any]],
    tools: Sequence[dict[str, Any]],
    tool_executor: ToolExecutorFn,
    policy: AssistantLoopBudgetPolicy,
    tool_choice: str | dict[str, Any] | None = None,
    clock_fn: Callable[[], float] = time.monotonic,
    instance: str = "/api/v1/assistant/turns",
) -> BoundedToolLoopResult:
    """Run bounded multi-step `LlmStreamingPort` tool loop with forced synthesis or error."""
    controller = AssistantLoopBudgetController(policy, clock_fn=clock_fn)
    working_msgs: list[dict[str, Any]] = [dict(m) for m in messages]
    executed: list[dict[str, Any]] = []
    thinking_parts: list[str] = []
    last_content = ""
    effective_tools = tuple(tools) if endpoint.supports_tools else ()

    while True:
        check = controller.check_budget()
        if not check.can_continue:
            kind = check.exceeded_kind or "iterations"
            if not policy.force_synthesis_on_limit:
                raise TurnBudgetExceededError(
                    limit_kind=kind, detail_override=check.detail, instance=instance
                )
            synth_msgs = [
                *working_msgs,
                {
                    "role": "user",
                    "content": (
                        "Execution budget reached. Synthesize a concise final answer from the "
                        "tool results already gathered without calling additional tools."
                    ),
                },
            ]
            synth = await llm_port.complete_chat(
                LlmStreamRequest(
                    endpoint=endpoint,
                    messages=tuple(synth_msgs),
                    tools=(),
                    stream=False,
                    include_thoughts=True,
                )
            )
            if synth is not None:
                controller.record_usage(
                    synth.input_tokens, synth.output_tokens, increment_iteration=False
                )
                if synth.thinking_text:
                    thinking_parts.append(synth.thinking_text)
                if synth.content:
                    last_content = synth.content
            return _build_loop_result(
                final_content=last_content,
                thinking_parts=thinking_parts,
                controller=controller,
                executed=executed,
                forced_synthesis=True,
                limit_reached=kind,
            )

        outcome = await llm_port.complete_chat(
            LlmStreamRequest(
                endpoint=endpoint,
                messages=tuple(working_msgs),
                tools=effective_tools,
                tool_choice=tool_choice if effective_tools else None,
                stream=False,
                include_thoughts=True,
            )
        )
        if outcome is None:
            break
        controller.record_usage(
            outcome.input_tokens, outcome.output_tokens, increment_iteration=True
        )
        if outcome.thinking_text:
            thinking_parts.append(outcome.thinking_text)
        if outcome.content:
            last_content = outcome.content
        if not outcome.tool_calls or not effective_tools:
            return _build_loop_result(
                final_content=outcome.content,
                thinking_parts=thinking_parts,
                controller=controller,
                executed=executed,
            )

        working_msgs.append(
            {
                "role": "assistant",
                "content": outcome.content,
                "tool_calls": list(outcome.tool_calls),
            }
        )
        for tc in outcome.tool_calls:
            executed.append(tc)
            result_str = await tool_executor(tc)
            working_msgs.append(
                format_tool_result_message(
                    tool_call_id=str(tc.get("id") or "call_1"),
                    name=str(tc.get("name") or "tool"),
                    content=str(result_str),
                )
            )

    return _build_loop_result(
        final_content=last_content,
        thinking_parts=thinking_parts,
        controller=controller,
        executed=executed,
    )


__all__ = [
    "AssistantLoopBudgetController",
    "AssistantLoopBudgetPolicy",
    "BoundedToolLoopResult",
    "BudgetCheckResult",
    "BudgetLimitKind",
    "ToolExecutorFn",
    "resolve_loop_budget_for_speed",
    "run_bounded_tool_loop",
]
