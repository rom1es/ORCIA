"""Deterministic Tool-Calling Cassette Fixtures for OpenAI-Compatible & Anthropic Dialects."""

from __future__ import annotations

import json
from typing import Any

from orcia_core.ports.llm_streaming_port import LlmStreamRequest


def _extract_first_tool_name(request: LlmStreamRequest) -> str:
    for tool in request.tools:
        if isinstance(tool, dict):
            fn = tool.get("function")
            if isinstance(fn, dict) and fn.get("name"):
                return str(fn["name"])
            if tool.get("name"):
                return str(tool["name"])
    return "query_workspace_knowledge_and_glossary"


def _is_anthropic_endpoint(request: LlmStreamRequest) -> bool:
    ep = request.endpoint
    return ep.protocol_mode == "anthropic_messages" or "anthropic" in ep.provider.lower()


def resolve_cassette_tool_scenario(
    request: LlmStreamRequest,
) -> tuple[str, tuple[dict[str, Any], ...], str] | None:
    """Resolve `(content, tool_calls, finish_reason)` for deterministic tool-calling cassettes.

    Returns `None` when request should follow standard text cassette playback.
    """
    all_text = "\n".join(str(m.get("content") or "") for m in request.messages)
    has_tool_result = any(str(m.get("role") or "") == "tool" for m in request.messages)
    always_loop = "[CASSETTE_MULTI_STEP_LOOP]" in all_text
    tool_loop_trigger = "[CASSETTE_TOOL_LOOP]" in all_text or always_loop

    if not tool_loop_trigger:
        return None

    is_ant = _is_anthropic_endpoint(request)
    if not request.tools or (has_tool_result and not always_loop):
        tool_summaries = [
            str(m.get("content") or "")
            for m in request.messages
            if str(m.get("role") or "") == "tool"
        ]
        joined = " | ".join(tool_summaries) if tool_summaries else "no-tool-evidence"
        dialect_tag = "anthropic" if is_ant else "openai_compatible"
        finish_reason = "end_turn" if is_ant else "stop"
        return (
            f"DETERMINISTIC_TOOL_SYNTHESIS ({dialect_tag}): {joined}",
            (),
            finish_reason,
        )

    tool_name = _extract_first_tool_name(request)
    last_user = next(
        (
            str(m.get("content") or "")
            for m in reversed(request.messages)
            if str(m.get("role") or "") == "user"
        ),
        "query",
    )
    tc_id = "toolu_ant_cassette_1" if is_ant else "call_oai_cassette_1"
    finish_reason = "tool_use" if is_ant else "tool_calls"
    tc = {
        "id": tc_id,
        "name": tool_name,
        "arguments": {"query": last_user.replace("[CASSETTE_TOOL_LOOP]", "").strip() or "context"},
    }
    return "", (tc,), finish_reason


def build_cassette_tool_delta_fragments(tc: dict[str, Any]) -> tuple[str, str]:
    """Split serialized JSON arguments into two deterministic streaming fragments."""
    raw = json.dumps(tc.get("arguments") or {}, ensure_ascii=False)
    mid = max(1, len(raw) // 2)
    return raw[:mid], raw[mid:]


__all__ = ["build_cassette_tool_delta_fragments", "resolve_cassette_tool_scenario"]
