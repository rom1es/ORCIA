"""Async HTTPX Pinned Request, Protocol Switch & SSE Line Helpers (`Story 26.6a`)."""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx

from orcia_core.orchestration._llm_streaming_http_helpers import (
    build_gemini_interactions_fallback_request,
    build_openai_fallback_body,
    should_attempt_openai_404_fallback,
)
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.ai_models_urls import is_gemini_interactions_url
from orcia_core.orchestration.llm_gemini_dialect import is_google_gemini_native_provider
from orcia_core.orchestration.llm_gemini_interactions import (
    is_gemini_interactions_agent_field_required_error,
    is_gemini_interactions_api_required_error,
)
from orcia_core.ports.llm_streaming_port import LlmStreamRequest


async def post_pinned_json(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
) -> httpx.Response:
    """Execute pinned HTTPX POST JSON request."""
    p_url, p_headers, ext = await prepare_pinned_http_request(client, url, headers)
    return await client.post(p_url, json=body, headers=p_headers, extensions=ext)


async def post_chat_with_protocol_fallbacks(
    client: httpx.AsyncClient,
    request: LlmStreamRequest,
    *,
    target_url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    allow_legacy_fallback: bool,
) -> httpx.Response:
    """Post non-stream chat request with OpenAI 404 legacy and Gemini Interactions fallbacks."""
    ep = request.endpoint
    resp = await post_pinned_json(client, target_url, headers, body)
    fallback_url = should_attempt_openai_404_fallback(
        allow_legacy_fallback=allow_legacy_fallback,
        status_code=resp.status_code,
        ep=ep,
        target_url=target_url,
    )
    if fallback_url is not None:
        return await post_pinned_json(
            client, fallback_url, headers, build_openai_fallback_body(request, stream=False)
        )
    if not is_google_gemini_native_provider(target_url, ep.provider):
        return resp
    if not is_gemini_interactions_url(target_url) and is_gemini_interactions_api_required_error(
        resp.status_code, resp.text
    ):
        ia_url, ia_hdrs, ia_body = build_gemini_interactions_fallback_request(
            request, stream=False, use_agent_field=False
        )
        resp = await post_pinned_json(client, ia_url, ia_hdrs, ia_body)
        target_url = ia_url
    if is_gemini_interactions_url(target_url) and is_gemini_interactions_agent_field_required_error(
        resp.status_code, resp.text
    ):
        ia_url, ia_hdrs, ia_body = build_gemini_interactions_fallback_request(
            request, stream=False, use_agent_field=True
        )
        resp = await post_pinned_json(client, ia_url, ia_hdrs, ia_body)
    return resp


async def maybe_resolve_stream_switch(
    request: LlmStreamRequest,
    resp: httpx.Response,
    *,
    use_url: str,
    use_headers: dict[str, str],
    allow_legacy_fallback: bool,
    switched_to_agent: bool,
) -> tuple[str, dict[str, str], dict[str, Any], bool] | None:
    """Return `(new_url, new_headers, new_body, switched_to_agent)` for 404/Interactions retry."""
    ep = request.endpoint
    if resp.status_code == 404:
        fb = should_attempt_openai_404_fallback(
            allow_legacy_fallback=allow_legacy_fallback,
            status_code=404,
            ep=ep,
            target_url=use_url,
        )
        if fb is not None:
            fb_body = build_openai_fallback_body(request, stream=True)
            return fb, use_headers, fb_body, switched_to_agent
    if resp.status_code in (400, 404) and is_google_gemini_native_provider(use_url, ep.provider):
        err_text = (await resp.aread()).decode("utf-8", errors="replace")
        if not is_gemini_interactions_url(use_url) and is_gemini_interactions_api_required_error(
            resp.status_code, err_text
        ):
            ia_url, ia_hdrs, ia_body = build_gemini_interactions_fallback_request(
                request, stream=True, use_agent_field=False
            )
            return ia_url, ia_hdrs, ia_body, switched_to_agent
        if (
            is_gemini_interactions_url(use_url)
            and not switched_to_agent
            and is_gemini_interactions_agent_field_required_error(resp.status_code, err_text)
        ):
            ia_url, ia_hdrs, ia_body = build_gemini_interactions_fallback_request(
                request, stream=True, use_agent_field=True
            )
            return ia_url, ia_hdrs, ia_body, True
    return None


def parse_sse_json_line(raw_line: str) -> Literal["skip", "done"] | dict[str, Any]:
    """Parse a raw SSE/NDJSON line into `"skip"`, `"done"`, or a decoded JSON dict."""
    line = raw_line.strip()
    if not line or line.startswith((":", "event:")):
        return "skip"
    payload_str = line[5:].strip() if line.startswith("data:") else line
    if payload_str == "[DONE]":
        return "done"
    try:
        chunk = json.loads(payload_str)
    except json.JSONDecodeError:
        return "skip"
    return chunk if isinstance(chunk, dict) else "skip"
