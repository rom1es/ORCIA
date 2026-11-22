"""Deterministic Token Budget Trimmer for Multi-Turn Assistant Prompts (`Story 26.5`, `H-18`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_MESSAGE_OVERHEAD_TOKENS: int = 4
_DEFAULT_MAX_TOKENS_BUDGET: int = 8192


@dataclass(frozen=True, slots=True)
class TrimmedPromptBudgetResult:
    """Trimmed `[system, *history, user]` message list bounded within `max_tokens_budget`."""

    messages: tuple[dict[str, Any], ...]
    estimated_input_tokens: int
    max_tokens_budget: int
    dropped_history_count: int
    context_truncated: bool


def estimate_text_tokens(text: str) -> int:
    """Estimate token count deterministically (`max(1, len // 4)` when non-empty)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _estimate_message_tokens(message: dict[str, Any]) -> int:
    return estimate_text_tokens(str(message.get("content") or "")) + _MESSAGE_OVERHEAD_TOKENS


def _truncate_system_preserving_layer_1(system_msg: str, max_sys_tokens: int) -> tuple[str, bool]:
    if estimate_text_tokens(system_msg) <= max_sys_tokens:
        return system_msg, False
    char_limit = max(64, max_sys_tokens * 4)
    if len(system_msg) <= char_limit:
        return system_msg, False
    marker = "\n...[CONTEXT_BUDGET_TRIMMED]"
    keep = max(32, char_limit - len(marker))
    return system_msg[:keep].rstrip() + marker, True


def trim_messages_to_token_budget(
    *,
    system_msg: str,
    user_prompt: str,
    conversation_history: Sequence[dict[str, Any]] | None = None,
    max_tokens_budget: int = _DEFAULT_MAX_TOKENS_BUDGET,
    reserve_output_tokens: int | None = None,
) -> TrimmedPromptBudgetResult:
    """Trim oldest conversation turns so `[system, *history, user]` fits `max_tokens_budget`."""
    safe_budget = max(128, int(max_tokens_budget or _DEFAULT_MAX_TOKENS_BUDGET))
    reserved = (
        max(0, int(reserve_output_tokens))
        if reserve_output_tokens is not None
        else min(1024, safe_budget // 8)
    )
    input_budget = max(96, safe_budget - reserved)

    user_msg: dict[str, Any] = {"role": "user", "content": user_prompt}
    user_tokens = _estimate_message_tokens(user_msg)
    max_sys_tokens = max(64, input_budget - user_tokens)
    trimmed_sys, sys_truncated = _truncate_system_preserving_layer_1(system_msg, max_sys_tokens)
    sys_msg: dict[str, Any] = {"role": "system", "content": trimmed_sys}
    sys_tokens = _estimate_message_tokens(sys_msg)

    remaining_for_history = max(0, input_budget - sys_tokens - user_tokens)
    kept_reversed: list[dict[str, Any]] = []
    history_items = [dict(item) for item in (conversation_history or ())]
    used_history_tokens = 0
    for item in reversed(history_items):
        msg_tokens = _estimate_message_tokens(item)
        if used_history_tokens + msg_tokens > remaining_for_history:
            break
        kept_reversed.append(item)
        used_history_tokens += msg_tokens

    kept_history = list(reversed(kept_reversed))
    dropped = len(history_items) - len(kept_history)
    final_messages = tuple([sys_msg, *kept_history, user_msg])
    total_tokens = sys_tokens + used_history_tokens + user_tokens
    return TrimmedPromptBudgetResult(
        messages=final_messages,
        estimated_input_tokens=total_tokens,
        max_tokens_budget=safe_budget,
        dropped_history_count=dropped,
        context_truncated=sys_truncated or dropped > 0,
    )


__all__ = [
    "TrimmedPromptBudgetResult",
    "estimate_text_tokens",
    "trim_messages_to_token_budget",
]
