"""Google Gemini Interactions API (`/v1beta/interactions`) dialect helpers (`CAP-076`).

Pure Python module with zero external SDK imports (`AD-19`).
"""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.llm_gemini_dialect import separate_think_tags


def is_gemini_interactions_api_required_error(status_code: int, response_text: str) -> bool:
    """Return True when Gemini rejects `:generateContent` requiring the Interactions API."""
    return status_code == 400 and "interactions api" in (response_text or "").lower()


def is_gemini_interactions_agent_field_required_error(status_code: int, response_text: str) -> bool:
    """Return True when `/interactions` rejects `model` and expects `agent` instead."""
    low = (response_text or "").lower()
    return status_code in (400, 404) and (
        "agent" in low or "not found for api version" in low or "is not a valid model" in low
    )


def build_gemini_interactions_probe_body(
    model_name: str, *, use_agent_field: bool = False
) -> dict[str, Any]:
    """Build minimal connection test payload for `/v1beta/interactions`."""
    model_id = (model_name or "").strip().removeprefix("models/").strip()
    return {"agent" if use_agent_field else "model": model_id, "input": "ping"}


def build_gemini_interactions_request_body(
    model_name: str,
    messages: list[dict[str, Any]],
    *,
    stream: bool = False,
    tools: list[dict[str, Any]] | None = None,
    use_agent_field: bool = False,
) -> dict[str, Any]:
    """Build `/v1beta/interactions` JSON payload with `system_instruction` and `tools`."""
    model_id = (model_name or "").strip().removeprefix("models/").strip()
    sys_blocks = [
        str(m.get("content") or "").strip()
        for m in messages
        if m.get("role") == "system" and str(m.get("content") or "").strip()
    ]
    conv = [m for m in messages if m.get("role") != "system"]
    if len(conv) == 1:
        input_val: Any = str(conv[0].get("content") or "Hello")
    elif conv:
        input_val = [
            {
                "role": "model" if m.get("role") == "assistant" else "user",
                "content": str(m.get("content") or ""),
            }
            for m in conv
        ]
    else:
        input_val = "Hello"

    body: dict[str, Any] = {
        "agent" if use_agent_field else "model": model_id,
        "input": input_val,
    }
    if stream:
        body["stream"] = True
    if sys_blocks:
        body["system_instruction"] = "\n\n".join(sys_blocks)
    if tools:
        decls = [
            {
                "name": str(t.get("function", {}).get("name") or "tool"),
                "description": str(t.get("function", {}).get("description") or ""),
                "parameters": t.get("function", {}).get("parameters") or {"type": "object"},
            }
            for t in tools
            if isinstance(t, dict)
        ]
        if decls:
            body["tools"] = [{"function_declarations": decls}]
    return body


def _extract_parts_list(
    parts: list[Any],
    content_parts: list[str],
    thinking_parts: list[str],
) -> None:
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("thought") is True:
            if isinstance(part.get("text"), str) and part["text"]:
                thinking_parts.append(part["text"])
        elif isinstance(part.get("text"), str) and part["text"]:
            content_parts.append(part["text"])


def _extract_thought_text(item: dict[str, Any]) -> str:
    for key in ("thought", "text", "summary"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def parse_gemini_interactions_response(
    data: dict[str, Any],
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Extract `(clean_content, thinking_text, tool_calls)` from Interactions API JSON."""
    raw_inter = data.get("interaction")
    root: dict[str, Any] = raw_inter if isinstance(raw_inter, dict) else data
    items = root.get("outputs") or root.get("steps") or []
    content_parts: list[str] = []
    thinking_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    if isinstance(items, list):
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            itype = str(item.get("type") or "").lower()
            if itype in ("thought", "thought_summary") or item.get("thought") is True:
                if t_txt := _extract_thought_text(item):
                    thinking_parts.append(t_txt)
                continue
            fc = item.get("function_call") or item.get("functionCall")
            if itype in ("function_call", "tool_call") or isinstance(fc, dict):
                fc_dict = fc if isinstance(fc, dict) else item
                raw_args = fc_dict.get("arguments")
                if not isinstance(raw_args, dict):
                    raw_args = fc_dict.get("args") if isinstance(fc_dict.get("args"), dict) else {}
                tool_calls.append(
                    {
                        "id": str(fc_dict.get("id") or item.get("id") or f"gemini_call_{idx + 1}"),
                        "name": str(fc_dict.get("name") or ""),
                        "arguments": raw_args,
                    }
                )
                continue
            if (
                (itype in ("text", "content", "model_output") or "text" in item)
                and isinstance(item.get("text"), str)
                and item["text"]
            ):
                content_parts.append(item["text"])
            c_val = item.get("content")
            if isinstance(c_val, str) and c_val:
                content_parts.append(c_val)
            elif isinstance(c_val, list):
                _extract_parts_list(c_val, content_parts, thinking_parts)
            if isinstance(item.get("parts"), list):
                _extract_parts_list(item["parts"], content_parts, thinking_parts)

    if not content_parts:
        for fallback_key in ("output_text", "output"):
            val = root.get(fallback_key)
            if isinstance(val, str) and val:
                content_parts.append(val)
                break

    explicit_thinking = "\n\n".join(t.strip() for t in thinking_parts if t.strip())
    clean, think = separate_think_tags("".join(content_parts), explicit_thinking)
    return clean, think, tuple(tool_calls)


def extract_gemini_interactions_stream_deltas(chunk: dict[str, Any]) -> tuple[str, str]:
    """Return `(content_delta, reasoning_delta)` from a Gemini Interactions SSE chunk."""
    delta = chunk.get("delta")
    if not isinstance(delta, dict):
        return "", ""
    dtype = str(delta.get("type") or "").lower()
    if (
        dtype in ("thought", "thought_summary")
        or delta.get("thought") is True
        or isinstance(delta.get("thought"), str)
    ):
        text = (
            delta["thought"]
            if isinstance(delta.get("thought"), str)
            else str(delta.get("text") or delta.get("summary") or "")
        )
        return "", text
    return str(delta.get("text") or delta.get("content") or ""), ""


__all__ = [
    "build_gemini_interactions_probe_body",
    "build_gemini_interactions_request_body",
    "extract_gemini_interactions_stream_deltas",
    "is_gemini_interactions_agent_field_required_error",
    "is_gemini_interactions_api_required_error",
    "parse_gemini_interactions_response",
]
