"""Google Gemini Native (`CAP-076`) & Anthropic request/response dialect helpers."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_THINK_TAG_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_RE = re.compile(r"<think>(.*)$", re.DOTALL | re.IGNORECASE)


def separate_think_tags(raw_content: str, explicit_reasoning: str = "") -> tuple[str, str]:
    """Separate `<think>...</think>` blocks and explicit reasoning from clean content."""
    thinking_parts = [explicit_reasoning.strip()] if explicit_reasoning.strip() else []
    text = raw_content or ""
    for match in _THINK_TAG_RE.finditer(text):
        if extracted := match.group(1).strip():
            thinking_parts.append(extracted)
    cleaned = _THINK_TAG_RE.sub("", text)
    if (unclosed := _UNCLOSED_THINK_RE.search(cleaned)) is not None:
        if partial := unclosed.group(1).strip():
            thinking_parts.append(partial)
        cleaned = cleaned[: unclosed.start()]
    return cleaned.strip(), "\n\n".join(thinking_parts).strip()


def is_google_gemini_native_provider(endpoint_uri: str, provider: str = "") -> bool:
    """Return True when targeting Google Gemini Native API (`/v1beta`), False for Mode A."""
    u, p = endpoint_uri.strip().lower().rstrip("/"), provider.strip().lower()
    if "/openai" in u or u.endswith("/chat/completions"):
        return False
    return (
        "generativelanguage.googleapis.com" in u
        or ":generatecontent" in u
        or ":streamgeneratecontent" in u
        or "google" in p
        or "gemini" in p
    )


def build_gemini_native_url(endpoint_uri: str, model_name: str, *, stream: bool = False) -> str:
    """Construct Google Gemini Native `:generateContent` or `:streamGenerateContent?alt=sse` URL."""
    base = endpoint_uri.strip().rstrip("/")
    cleaned_name = (model_name or "").strip()
    if not cleaned_name:
        raise ValueError("model_name is mandatory and cannot be empty")
    model_id = cleaned_name.removeprefix("models/").strip()
    if not model_id:
        raise ValueError("model_name is mandatory and cannot be empty")
    action = "streamGenerateContent?alt=sse" if stream else "generateContent"
    if ":generateContent" in base or ":streamGenerateContent" in base:
        prefix = base.split(":generateContent")[0].split(":streamGenerateContent")[0]
        return f"{prefix}:{action}"
    parsed = urlparse(base)
    if not parsed.path or parsed.path == "/":
        base = f"{base}/v1beta"
    if base.endswith(f"/models/{model_id}"):
        return f"{base}:{action}"
    if base.endswith("/models"):
        return f"{base}/{model_id}:{action}"
    return f"{base}/models/{model_id}:{action}"


def build_gemini_native_headers(api_key: str | None) -> dict[str, str]:
    """Build headers for Google Gemini Native API (`x-goog-api-key`)."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key and api_key.strip():
        headers["x-goog-api-key"] = api_key.strip()
    return headers


def build_gemini_native_request_body(
    messages: list[dict[str, Any]],
    *,
    include_thoughts: bool = True,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build Google Gemini Native `:generateContent` JSON body with `thinkingConfig`."""
    sys_blocks = [
        str(m.get("content") or "").strip()
        for m in messages
        if m.get("role") == "system" and str(m.get("content") or "").strip()
    ]
    contents = [
        {
            "role": "model" if m.get("role") == "assistant" else "user",
            "parts": [{"text": str(m.get("content") or "")}],
        }
        for m in messages
        if m.get("role") != "system"
    ]
    body: dict[str, Any] = {
        "contents": contents or [{"role": "user", "parts": [{"text": "Hello"}]}]
    }
    if sys_blocks:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(sys_blocks)}]}
    if include_thoughts:
        body["generationConfig"] = {"thinkingConfig": {"includeThoughts": True}}
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
            body["tools"] = [{"functionDeclarations": decls}]
    return body


def parse_gemini_native_response(
    data: dict[str, Any],
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Extract `(clean_content, thinking_text, tool_calls)` from Gemini `candidates[0].content`."""
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return "", "", ()
    content_obj = candidates[0].get("content")
    if not isinstance(content_obj, dict) or not isinstance(content_obj.get("parts"), list):
        return "", "", ()
    thinking_parts, content_parts, tool_calls = [], [], []
    for idx, part in enumerate(content_obj["parts"]):
        if not isinstance(part, dict):
            continue
        if part.get("thought") is True and (t_txt := str(part.get("text") or "")):
            thinking_parts.append(t_txt)
        elif "text" in part and (txt := str(part.get("text") or "")):
            content_parts.append(txt)
        if isinstance(part.get("functionCall"), dict):
            fc = part["functionCall"]
            tool_calls.append(
                {
                    "id": str(fc.get("id") or f"gemini_call_{idx + 1}"),
                    "name": str(fc.get("name") or ""),
                    "arguments": fc.get("args") if isinstance(fc.get("args"), dict) else {},
                }
            )
    explicit_thinking = "\n\n".join(t.strip() for t in thinking_parts if t.strip())
    clean, think = separate_think_tags("".join(content_parts), explicit_thinking)
    return clean, think, tuple(tool_calls)


def extract_gemini_stream_chunk_deltas(chunk: dict[str, Any]) -> tuple[str, str]:
    """Return `(content_delta, reasoning_delta)` from a Gemini SSE `candidates` chunk."""
    candidates = chunk.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return "", ""
    content_obj = candidates[0].get("content")
    if not isinstance(content_obj, dict) or not isinstance(content_obj.get("parts"), list):
        return "", ""
    c_deltas: list[str] = []
    r_deltas: list[str] = []
    for part in content_obj["parts"]:
        if isinstance(part, dict) and (txt := str(part.get("text") or "")):
            (r_deltas if part.get("thought") is True else c_deltas).append(txt)
    return "".join(c_deltas), "".join(r_deltas)


def build_anthropic_native_request_body(
    model_name: str,
    messages: list[dict[str, Any]],
    *,
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build Anthropic `/v1/messages` JSON request body."""
    sys_blocks = [str(m.get("content") or "") for m in messages if m.get("role") == "system"]
    conv_msgs = [
        {
            "role": "assistant" if m.get("role") == "assistant" else "user",
            "content": str(m.get("content") or ""),
        }
        for m in messages
        if m.get("role") != "system"
    ]
    body: dict[str, Any] = {
        "model": model_name,
        "max_tokens": 4096,
        "messages": conv_msgs or [{"role": "user", "content": "Hello"}],
        "stream": stream,
    }
    if sys_blocks:
        body["system"] = "\n\n".join(sys_blocks)
    if tools:
        body["tools"] = [
            {
                "name": t.get("function", {}).get("name", "tool"),
                "description": t.get("function", {}).get("description", ""),
                "input_schema": t.get("function", {}).get("parameters", {"type": "object"}),
            }
            for t in tools
            if isinstance(t, dict)
        ]
    return body
