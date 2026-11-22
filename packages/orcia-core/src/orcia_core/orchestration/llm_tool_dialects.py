"""Native Tool-Calling Parsing & Message Formatting for 2 Dialects (`D5 + R7`, `Story 26.6a`).

Supports strictly:
- `openai_compatible` (OpenAI, vLLM, Ollama `/v1`, Azure): `delta.tool_calls` + `role: "tool"`
- `anthropic_messages` (Anthropic `/v1/messages`): `tool_use` / `input_json_delta` + `tool_result`
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from orcia_core.ports.llm_streaming_port import ToolCallDelta


def parse_json_arguments(raw: Any) -> dict[str, Any]:
    """Parse tool-call JSON arguments deterministically without crashing on partial text."""
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except json.JSONDecodeError:
            return {"_raw": text}
    return {}


def format_tool_result_message(
    *,
    tool_call_id: str,
    name: str,
    content: str,
) -> dict[str, Any]:
    """Build canonical provider-agnostic tool result turn message."""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": content,
    }


def _to_openai_tool_call_entry(tc: dict[str, Any], idx: int) -> dict[str, Any]:
    args_val = tc.get("arguments")
    if isinstance(args_val, str):
        args_json = args_val
    else:
        args_json = json.dumps(args_val if isinstance(args_val, dict) else {}, ensure_ascii=False)
    return {
        "id": str(tc.get("id") or f"call_{idx + 1}"),
        "type": "function",
        "function": {
            "name": str(tc.get("name") or ""),
            "arguments": args_json,
        },
    }


def format_messages_for_dialect(
    messages: Sequence[dict[str, Any]],
    *,
    dialect: str,
) -> list[dict[str, Any]]:
    """Format canonical conversation messages (`tool_calls` & `tool` results) per dialect."""
    if dialect == "anthropic_messages":
        formatted: list[dict[str, Any]] = []
        for msg in messages:
            role = str(msg.get("role") or "user").strip().lower()
            if role == "system":
                continue
            if role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": str(msg.get("tool_call_id") or "toolu_1"),
                    "content": str(msg.get("content") or ""),
                }
                if (
                    formatted
                    and formatted[-1].get("role") == "user"
                    and isinstance(formatted[-1].get("content"), list)
                ):
                    formatted[-1]["content"].append(block)
                else:
                    formatted.append({"role": "user", "content": [block]})
                continue
            raw_tcs = msg.get("tool_calls")
            if role == "assistant" and isinstance(raw_tcs, (list, tuple)) and raw_tcs:
                blocks: list[dict[str, Any]] = []
                txt = str(msg.get("content") or "")
                if txt:
                    blocks.append({"type": "text", "text": txt})
                for idx, tc in enumerate(raw_tcs):
                    if not isinstance(tc, dict):
                        continue
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": str(tc.get("id") or f"toolu_{idx + 1}"),
                            "name": str(tc.get("name") or ""),
                            "input": parse_json_arguments(tc.get("arguments")),
                        }
                    )
                formatted.append({"role": "assistant", "content": blocks})
                continue
            formatted.append(
                {
                    "role": "assistant" if role == "assistant" else "user",
                    "content": msg.get("content")
                    if isinstance(msg.get("content"), list)
                    else str(msg.get("content") or ""),
                }
            )
        return formatted

    out: list[dict[str, Any]] = []
    for msg in messages:
        role = str(msg.get("role") or "user").strip().lower()
        if role == "tool":
            entry: dict[str, Any] = {
                "role": "tool",
                "tool_call_id": str(msg.get("tool_call_id") or "call_1"),
                "content": str(msg.get("content") or ""),
            }
            if msg.get("name"):
                entry["name"] = str(msg["name"])
            out.append(entry)
            continue
        raw_tcs = msg.get("tool_calls")
        if role == "assistant" and isinstance(raw_tcs, (list, tuple)) and raw_tcs:
            oai_tcs = [
                _to_openai_tool_call_entry(tc, idx)
                for idx, tc in enumerate(raw_tcs)
                if isinstance(tc, dict)
            ]
            out.append(
                {
                    "role": "assistant",
                    "content": str(msg.get("content") or ""),
                    "tool_calls": oai_tcs,
                }
            )
            continue
        base: dict[str, Any] = {"role": role, "content": str(msg.get("content") or "")}
        if msg.get("name"):
            base["name"] = str(msg["name"])
        out.append(base)
    return out


class ToolCallAccumulator:
    """Stateful SSE tool-call fragment accumulator for OpenAI-compatible and Anthropic dialects."""

    def __init__(self) -> None:
        self._slots: dict[int, dict[str, Any]] = {}
        self.finish_reason: str | None = None

    def process_chunk(self, chunk: dict[str, Any]) -> list[ToolCallDelta]:
        """Extract `ToolCallDelta` events and update finish/stop reason from one SSE chunk."""
        emitted: list[ToolCallDelta] = []
        ev_type = chunk.get("type")
        if ev_type == "content_block_start" and isinstance(chunk.get("content_block"), dict):
            cb = chunk["content_block"]
            if cb.get("type") == "tool_use":
                idx = int(chunk.get("index") or 0)
                tc_id = str(cb.get("id") or f"toolu_{idx + 1}")
                tc_name = str(cb.get("name") or "")
                slot = self._slots.setdefault(
                    idx, {"index": idx, "id": tc_id, "name": tc_name, "arg_chunks": []}
                )
                slot["id"] = tc_id
                if tc_name:
                    slot["name"] = tc_name
                if isinstance(cb.get("input"), dict) and cb["input"]:
                    slot["arg_chunks"].append(json.dumps(cb["input"], ensure_ascii=False))
                emitted.append(
                    ToolCallDelta(
                        index=idx,
                        tool_call_id=slot["id"],
                        name=slot["name"],
                        arguments_delta="",
                    )
                )
            return emitted

        if ev_type == "content_block_delta" and isinstance(chunk.get("delta"), dict):
            delta = chunk["delta"]
            if delta.get("type") == "input_json_delta":
                idx = int(chunk.get("index") or 0)
                slot = self._slots.setdefault(
                    idx, {"index": idx, "id": f"toolu_{idx + 1}", "name": "", "arg_chunks": []}
                )
                partial = str(delta.get("partial_json") or "")
                if partial:
                    slot["arg_chunks"].append(partial)
                emitted.append(
                    ToolCallDelta(
                        index=idx,
                        tool_call_id=slot["id"],
                        name=slot["name"],
                        arguments_delta=partial,
                    )
                )
            return emitted

        if ev_type == "message_delta" and isinstance(chunk.get("delta"), dict):
            if sr := chunk["delta"].get("stop_reason"):
                self.finish_reason = str(sr)
            return emitted

        choices = chunk.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            c0 = choices[0]
            if fr := c0.get("finish_reason"):
                self.finish_reason = str(fr)
            delta = c0.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("tool_calls"), list):
                for raw_tc in delta["tool_calls"]:
                    if not isinstance(raw_tc, dict):
                        continue
                    idx = int(raw_tc.get("index") or 0)
                    slot = self._slots.setdefault(
                        idx, {"index": idx, "id": "", "name": "", "arg_chunks": []}
                    )
                    if raw_tc.get("id"):
                        slot["id"] = str(raw_tc["id"])
                    fn = raw_tc.get("function")
                    arg_delta = ""
                    if isinstance(fn, dict):
                        if fn.get("name"):
                            slot["name"] = (
                                f"{slot['name']}{fn['name']}" if slot["name"] else str(fn["name"])
                            )
                        if fn.get("arguments") is not None:
                            arg_delta = str(fn["arguments"])
                            slot["arg_chunks"].append(arg_delta)
                    emitted.append(
                        ToolCallDelta(
                            index=idx,
                            tool_call_id=slot["id"] or f"call_{idx + 1}",
                            name=slot["name"],
                            arguments_delta=arg_delta,
                        )
                    )
        return emitted

    def finalize_tool_calls(self) -> tuple[dict[str, Any], ...]:
        """Reassemble accumulated tool-call fragments deterministically by `(index, id)`."""
        ordered = sorted(self._slots.items(), key=lambda kv: (kv[0], str(kv[1].get("id") or "")))
        result: list[dict[str, Any]] = []
        for idx, slot in ordered:
            raw_args = "".join(slot["arg_chunks"])
            result.append(
                {
                    "id": str(slot.get("id") or f"call_{idx + 1}"),
                    "name": str(slot.get("name") or ""),
                    "arguments": parse_json_arguments(raw_args),
                }
            )
        return tuple(result)


__all__ = [
    "ToolCallAccumulator",
    "format_messages_for_dialect",
    "format_tool_result_message",
    "parse_json_arguments",
]
