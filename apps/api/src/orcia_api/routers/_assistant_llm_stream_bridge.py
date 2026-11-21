"""Live Async LLM Streaming Bridge for `Mon Assistant` (`AD-15`, `Story 26.1`)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import Request

from orcia_api.routers._assistant_usage_telemetry import resolve_audit_ledger_sink
from orcia_api.routers.assistant_background_turns import run_and_consume_decoupled_turn_stream
from orcia_api.routers.assistant_llm_prompts import (
    build_multi_turn_messages,
    build_workspace_tools_schema,
    detect_adaptive_thinking_steps_for_question,
    resolve_request_locale,
)
from orcia_api.routers.assistant_llm_resolver import resolve_configured_llm_endpoint


def get_or_create_async_http_client(request: Request) -> httpx.AsyncClient:
    """Return shared `httpx.AsyncClient` from `request.app.state.http_client`."""
    shared: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if shared is not None and not getattr(shared, "is_closed", False):
        return shared
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(300.0, connect=10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    request.app.state.http_client = client
    return client


async def stream_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    workspace_id: str = "scope-global",
    user_id: str = "u-anonymous",
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str | None = None,
    fallback_response_text: str | None = None,
    user_email: str | None = None,
    user_display_name: str | None = None,
    audit_ledger_sink: Any | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """True async SSE token streamer decoupled via `ACTIVE_WORKSPACE_TURNS`."""
    from orcia_api.routers.assistant_llm_bridge import (
        resolve_assembled_system_instructions_for_turn,
    )

    resolved_locale = resolve_request_locale(request, locale)
    default_thinking = " · ".join(
        f"{t}: {s}"
        for t, s in detect_adaptive_thinking_steps_for_question(user_prompt, locale=resolved_locale)
    )
    client_host = getattr(getattr(request, "client", None), "host", "") or ""
    can_call_live = (
        client_host != "testclient" or os.environ.get("ORCIA_FORCE_LIVE_LLM_IN_TESTS") == "1"
    )
    ep = (
        await resolve_configured_llm_endpoint(
            request, requested_tier=requested_tier, workspace_id=workspace_id
        )
        if can_call_live
        else None
    )
    system_msg = resolve_assembled_system_instructions_for_turn(
        request,
        hat=hat,
        speed_mode=speed_mode,
        workspace_id=workspace_id,
        user_id=user_id,
        requested_tier=requested_tier or (ep.tier if ep is not None else "medium"),
        thinking_effort=thinking_effort,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=resolved_locale,
    )
    async for evt in run_and_consume_decoupled_turn_stream(
        workspace_id=workspace_id,
        user_prompt=user_prompt,
        system_msg=system_msg,
        default_thinking=default_thinking,
        fallback_response_text=fallback_response_text,
        client_host=client_host,
        ep=ep,
        http_client_getter=lambda: get_or_create_async_http_client(request),
        messages_builder=lambda: build_multi_turn_messages(
            system_msg=system_msg,
            user_prompt=user_prompt,
            conversation_history=conversation_history,
        ),
        tools_builder=lambda: build_workspace_tools_schema(request, speed_mode),
        conversation_history_count=len(conversation_history or []),
        folder_pinned_notes=folder_pinned_notes,
        thinking_effort=thinking_effort,
        user_id=user_id,
        user_email=user_email,
        user_display_name=user_display_name,
        model_tier=requested_tier or (ep.tier if ep is not None else "medium"),
        audit_ledger_sink=audit_ledger_sink or resolve_audit_ledger_sink(request),
        trace_id=getattr(getattr(request, "state", None), "trace_id", None),
        speed_mode=speed_mode,
    ):
        yield evt


__all__ = ["get_or_create_async_http_client", "stream_configured_llm_for_assistant_turn"]
