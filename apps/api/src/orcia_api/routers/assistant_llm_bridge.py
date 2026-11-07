"""Live Async LLM Orchestration Bridge for `Mon Assistant` (`/api/v1/assistant/three-speed/*`)."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Request

from orcia_api.dependencies import get_or_create_shared_db_engine
from orcia_api.routers.assistant_llm_prompts import (
    build_assistant_system_instructions,
    build_multi_turn_messages,
    build_workspace_tools_schema,
    detect_adaptive_thinking_steps_for_question,
    resolve_5_layers_and_ontology_from_request,
    resolve_request_locale,
)
from orcia_api.routers.assistant_llm_providers import (
    ResolvedLiveLlmEndpoint,
    build_legacy_local_chat_url,
    build_provider_headers,
    build_provider_request_body,
    extract_thinking_and_clean_content,
    invoke_provider_chat_async,
    is_anthropic_provider,
    is_safe_llm_endpoint_url,
    logger,
    normalize_chat_completions_url,
    stream_provider_chat_sse_async,
)


@dataclass(frozen=True, slots=True)
class LiveLlmTurnOutcome:
    """Outcome of a live async LLM turn."""

    response_text: str
    step_label: str
    latency_ms: float
    thinking_text: str | None = None
    invoked_tool_names: tuple[str, ...] = ()


def _extract_tier_endpoint_from_dict(item: dict[str, Any]) -> ResolvedLiveLlmEndpoint | None:
    model_name = str(item.get("primaryModel") or item.get("model") or "").strip()
    endpoint_uri = str(item.get("endpointUrl") or item.get("endpoint_uri") or "").strip()
    if not model_name or not is_safe_llm_endpoint_url(endpoint_uri):
        return None
    provider = str(item.get("modelFamily") or item.get("provider") or "OpenAI").strip()
    auth_mode = str(item.get("authMode") or "api_key").strip()
    tier_key = str(item.get("tier") or item.get("tierKey") or "medium").strip().lower()
    raw_key = item.get("apiKey")
    api_key = str(raw_key).strip() if isinstance(raw_key, str) and raw_key.strip() else None
    return ResolvedLiveLlmEndpoint(
        provider=provider,
        model_name=model_name,
        endpoint_uri=endpoint_uri.rstrip("/"),
        auth_mode=auth_mode,
        tier=tier_key or "medium",
        api_key=api_key,
    )


def _select_endpoint_from_tiers(
    llm_tiers: list[Any],
    requested_tier: str | None = None,
) -> ResolvedLiveLlmEndpoint | None:
    target = (requested_tier or "").strip().lower()
    valid_endpoints = [
        resolved
        for item in llm_tiers
        if isinstance(item, dict)
        and (resolved := _extract_tier_endpoint_from_dict(item)) is not None
    ]
    if not valid_endpoints:
        return None
    if target and target != "auto":
        for ep in valid_endpoints:
            if ep.tier == target:
                return ep
    return valid_endpoints[0]


async def resolve_configured_llm_endpoint(
    request: Request,
    *,
    requested_tier: str | None = None,
) -> ResolvedLiveLlmEndpoint | None:
    """Resolve the active configured LLM endpoint asynchronously without blocking ASGI loop."""
    if os.environ.get("ORCIA_USE_CASSETTE_LLM", "").strip().lower() in ("1", "true", "yes"):
        return None

    snap = getattr(request.app.state, "platform_setup_snapshot", None)
    if snap is not None and getattr(snap, "llm_tiers", None):
        chosen = _select_endpoint_from_tiers(list(snap.llm_tiers), requested_tier)
        if chosen is not None:
            return chosen

    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        t0 = time.perf_counter()
        try:
            import orcia_core.bootstrap as bm

            engine = get_or_create_shared_db_engine(request)
            db_snap = await bm.load_platform_setup_state_from_postgres18(engine, orcia_env="local")
            if db_snap is not None:
                request.app.state.platform_setup_snapshot = db_snap
                return _select_endpoint_from_tiers(list(db_snap.llm_tiers), requested_tier)
        except Exception as exc:
            logger.warning(
                "llm_endpoint_pg_resolution_failed",
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                error_type=type(exc).__name__,
            )
    return None


def _get_or_create_async_http_client(request: Request) -> httpx.AsyncClient:
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


async def invoke_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    workspace_id: str = "ws-claims-alpha",
    user_id: str = "u-anonymous",
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str | None = None,
) -> LiveLlmTurnOutcome | None:
    """Asynchronously invoke the configured LLM endpoint with 5-layer prompt, history & tools."""
    client_host = getattr(getattr(request, "client", None), "host", "") or ""
    if client_host == "testclient" and os.environ.get("ORCIA_FORCE_LIVE_LLM_IN_TESTS") != "1":
        return None

    ep = await resolve_configured_llm_endpoint(request, requested_tier=requested_tier)
    if ep is None:
        return None

    resolved_locale = resolve_request_locale(request, locale)
    effort = (thinking_effort or "").strip().lower() or (
        "deep"
        if speed_mode == "SPEED_3_DEEP_AUDIT"
        else "balanced"
        if speed_mode == "SPEED_2_AGENT_TOOLS"
        else "fast"
    )
    effort_label = (
        ("High Thinking" if effort == "deep" else "Standard Thinking")
        if resolved_locale == "en"
        else ("Réflexion Élevée" if effort == "deep" else "Réflexion Standard")
    )
    assembled_5_layers, ontology_summary = resolve_5_layers_and_ontology_from_request(
        request, workspace_id=workspace_id, user_id=user_id, hat=hat
    )
    system_msg = build_assistant_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier or ep.tier,
        thinking_effort=effort,
        system_instructions_override=system_instructions_override,
        assembled_5_layers_prompt=assembled_5_layers,
        ontology_concepts_summary=ontology_summary,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=resolved_locale,
    )
    default_thinking = " · ".join(
        f"{t}: {s}"
        for t, s in detect_adaptive_thinking_steps_for_question(user_prompt, locale=resolved_locale)
    )
    step_label = f"💬 Modèle IA {ep.model_name} ({ep.provider} · {effort_label}) — réponse générée"
    messages = build_multi_turn_messages(
        system_msg=system_msg, user_prompt=user_prompt, conversation_history=conversation_history
    )
    tools = build_workspace_tools_schema(request, speed_mode)
    http_client = _get_or_create_async_http_client(request)

    outcome = await invoke_provider_chat_async(
        http_client, ep=ep, messages=messages, tools=tools or None
    )
    if outcome is None:
        return None

    invoked_tools = tuple(tc.get("name", "") for tc in outcome.tool_calls if tc.get("name"))
    content = outcome.content
    if not content and invoked_tools:
        followup_msgs = [
            *messages,
            {
                "role": "user",
                "content": (
                    f"[Tool Execution Results for {', '.join(invoked_tools)}]: "
                    f"Workspace context verified for '{user_prompt.strip()}'. Synthesize answer."
                ),
            },
        ]
        second = await invoke_provider_chat_async(
            http_client, ep=ep, messages=followup_msgs, tools=None
        )
        if second is not None and second.content:
            content = second.content

    if not content:
        return None
    return LiveLlmTurnOutcome(
        response_text=content,
        step_label=step_label,
        latency_ms=outcome.latency_ms,
        thinking_text=outcome.thinking_text or default_thinking,
        invoked_tool_names=invoked_tools,
    )


async def stream_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    workspace_id: str = "ws-claims-alpha",
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
) -> AsyncIterator[dict[str, Any]]:
    """True async SSE token streamer (`resp.aiter_lines()`) preserving Markdown indentation."""
    t0 = time.perf_counter()
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
        await resolve_configured_llm_endpoint(request, requested_tier=requested_tier)
        if can_call_live
        else None
    )

    if ep is not None:
        assembled_5_layers, ontology_summary = resolve_5_layers_and_ontology_from_request(
            request, workspace_id=workspace_id, user_id=user_id, hat=hat
        )
        system_msg = build_assistant_system_instructions(
            hat=hat,
            speed_mode=speed_mode,
            requested_tier=requested_tier or ep.tier,
            thinking_effort=thinking_effort,
            assembled_5_layers_prompt=assembled_5_layers,
            ontology_concepts_summary=ontology_summary,
            response_tone=response_tone,
            response_format=response_format,
            personal_instructions=personal_instructions,
            workspace_instructions=workspace_instructions,
            folder_pinned_notes=folder_pinned_notes,
            locale=resolved_locale,
        )
        messages = build_multi_turn_messages(
            system_msg=system_msg,
            user_prompt=user_prompt,
            conversation_history=conversation_history,
        )
        tools = build_workspace_tools_schema(request, speed_mode)
        http_client = _get_or_create_async_http_client(request)

        emitted_tokens = False
        async for evt in stream_provider_chat_sse_async(
            http_client, ep=ep, messages=messages, tools=tools or None
        ):
            if evt["event"] == "token_delta":
                emitted_tokens = True
            yield evt
        if emitted_tokens:
            return
        if client_host != "testclient":
            yield {
                "event": "stream_error",
                "data": {
                    "message": (
                        f"Le modèle IA {ep.model_name} ({ep.endpoint_uri}) n'a renvoyé aucun "
                        "jeton de réponse. Vérifiez que le fournisseur IA est bien démarré."
                    )
                },
            }
            return

    yield {
        "event": "thinking_delta",
        "data": {
            "step_code": "NODE_5_SINGLE_STREAM_LLM",
            "thinking_text": default_thinking,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        },
    }
    full_text = fallback_response_text or ""
    accumulated: list[str] = []
    for line_chunk in full_text.splitlines(keepends=True) or ([full_text] if full_text else []):
        accumulated.append(line_chunk)
        yield {
            "event": "token_delta",
            "data": {"delta": line_chunk, "accumulated_text": "".join(accumulated)},
        }
    yield {
        "event": "turn_completed",
        "data": {
            "response_text": full_text,
            "thinking_text": default_thinking,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        },
    }


__all__ = [
    "LiveLlmTurnOutcome",
    "ResolvedLiveLlmEndpoint",
    "_extract_tier_endpoint_from_dict",
    "_select_endpoint_from_tiers",
    "build_assistant_system_instructions",
    "build_legacy_local_chat_url",
    "build_multi_turn_messages",
    "build_provider_headers",
    "build_provider_request_body",
    "build_workspace_tools_schema",
    "detect_adaptive_thinking_steps_for_question",
    "extract_thinking_and_clean_content",
    "invoke_configured_llm_for_assistant_turn",
    "is_anthropic_provider",
    "is_safe_llm_endpoint_url",
    "normalize_chat_completions_url",
    "resolve_5_layers_and_ontology_from_request",
    "resolve_configured_llm_endpoint",
    "resolve_request_locale",
    "stream_configured_llm_for_assistant_turn",
]
