"""Live Async LLM Orchestration Bridge for `Mon Assistant` (`/api/v1/assistant/three-speed/*`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request

from orcia_api.dependencies._llm_streaming_providers import get_llm_streaming_port
from orcia_api.routers._assistant_llm_stream_bridge import (
    get_or_create_async_http_client as _get_or_create_async_http_client,
)
from orcia_api.routers._assistant_llm_stream_bridge import (
    stream_configured_llm_for_assistant_turn as stream_configured_llm_for_assistant_turn,
)
from orcia_api.routers.assistant_background_turns import (
    ActiveBackgroundTurnState as ActiveBackgroundTurnState,
)
from orcia_api.routers.assistant_background_turns import (
    get_active_turn_for_workspace as get_active_turn_for_workspace,
)
from orcia_api.routers.assistant_background_turns import (
    record_prompt_telemetry_entry as record_prompt_telemetry_entry,
)
from orcia_api.routers.assistant_background_turns import (
    stop_active_turn_for_workspace as stop_active_turn_for_workspace,
)
from orcia_api.routers.assistant_llm_prompts import (
    build_assistant_system_instructions,
    build_multi_turn_messages,
    build_workspace_tools_schema,
    detect_adaptive_thinking_steps_for_question,
    resolve_5_layers_and_ontology_from_request,
    resolve_5_layers_and_ontology_from_request_async,
    resolve_assembled_system_instructions_for_turn_async,
    resolve_assembled_turn_context_and_instructions_async,
    resolve_request_locale,
)
from orcia_api.routers.assistant_llm_providers import (
    ResolvedLiveLlmEndpoint,
    build_legacy_local_chat_url,
    build_provider_headers,
    build_provider_request_body,
    extract_thinking_and_clean_content,
    is_anthropic_provider,
    is_safe_llm_endpoint_url,
    normalize_chat_completions_url,
    stream_provider_chat_sse_async,
)
from orcia_api.routers.assistant_llm_resolver import (
    ensure_active_chat_model_if_live as ensure_active_chat_model_if_live,
)
from orcia_api.routers.assistant_llm_resolver import (
    extract_tier_endpoint_from_dict as _extract_tier_endpoint_from_dict,
)
from orcia_api.routers.assistant_llm_resolver import (
    resolve_configured_llm_endpoint,
)
from orcia_api.routers.assistant_llm_resolver import (
    select_endpoint_from_tiers as _select_endpoint_from_tiers,
)
from orcia_core.orchestration.llm_tool_dialects import format_tool_result_message
from orcia_core.ports.llm_streaming_port import LlmStreamingPort, LlmStreamRequest


@dataclass(frozen=True, slots=True)
class LiveLlmTurnOutcome:
    """Outcome of a live async LLM turn."""

    response_text: str
    step_label: str
    latency_ms: float
    thinking_text: str | None = None
    invoked_tool_names: tuple[str, ...] = ()
    assembled_system_prompt: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"
    model_id: str = ""
    inference_tier: str | None = None
    effort: str | None = None
    citation_map: dict[str, Any] | None = None


def resolve_assembled_system_instructions_for_turn(
    request: Request,
    *,
    hat: str,
    speed_mode: str,
    workspace_id: str,
    user_id: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Build the complete 5-layer + ontology + preferences system prompt for a turn."""
    assembled_5_layers, ontology_summary = resolve_5_layers_and_ontology_from_request(
        request, workspace_id=workspace_id, user_id=user_id, hat=hat, locale=locale
    )
    return build_assistant_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
        assembled_5_layers_prompt=assembled_5_layers,
        ontology_concepts_summary=ontology_summary,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )


async def invoke_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    workspace_id: str = "scope-global",
    user_id: str = "u-anonymous",
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    conversation_history: list[dict[str, Any]] | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str | None = None,
    llm_port: LlmStreamingPort | None = None,
    user: Any | None = None,
    embedding_port: Any | None = None,
) -> LiveLlmTurnOutcome | None:
    """Invoke the configured LLM endpoint via `LlmStreamingPort` with 5-layer prompt & tools."""
    ep = await resolve_configured_llm_endpoint(
        request, requested_tier=requested_tier, workspace_id=workspace_id
    )
    if ep is None:
        return None

    active_port = llm_port or get_llm_streaming_port(request)
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
    system_msg, turn_ctx = await resolve_assembled_turn_context_and_instructions_async(
        request,
        hat=hat,
        speed_mode=speed_mode,
        workspace_id=workspace_id,
        user_id=user_id,
        user_prompt=user_prompt,
        user=user,
        embedding_port=embedding_port,
        requested_tier=requested_tier or ep.tier,
        thinking_effort=effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
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
    step_label = (
        f"💬 AI Model {ep.model_name} ({ep.provider} · {effort_label}) — reply generated"
        if resolved_locale == "en"
        else f"💬 Modèle IA {ep.model_name} ({ep.provider} · {effort_label}) — réponse générée"
    )
    messages = build_multi_turn_messages(
        system_msg=system_msg,
        user_prompt=user_prompt,
        conversation_history=conversation_history,
        max_tokens_budget=ep.max_tokens_budget,
    )
    tools = build_workspace_tools_schema(request, speed_mode) if ep.supports_tools else []

    outcome = await active_port.complete_chat(
        LlmStreamRequest(
            endpoint=ep,
            messages=tuple(messages),
            tools=tuple(tools),
            include_thoughts=True,
        )
    )
    if outcome is None:
        return None

    invoked_tools = tuple(tc.get("name", "") for tc in outcome.tool_calls if tc.get("name"))
    content = outcome.content
    total_in_tokens = outcome.input_tokens
    total_out_tokens = outcome.output_tokens
    usage_source = outcome.usage_source
    if not content and outcome.tool_calls:
        followup_msgs: list[dict[str, Any]] = [
            *messages,
            {"role": "assistant", "content": "", "tool_calls": list(outcome.tool_calls)},
            *[
                format_tool_result_message(
                    tool_call_id=str(tc.get("id") or f"call_{idx + 1}"),
                    name=str(tc.get("name") or "tool"),
                    content=(
                        f"Workspace context verified for '{user_prompt.strip()}' "
                        f"({tc.get('name') or 'tool'}). Synthesize answer."
                    ),
                )
                for idx, tc in enumerate(outcome.tool_calls)
            ],
        ]
        second = await active_port.complete_chat(
            LlmStreamRequest(endpoint=ep, messages=tuple(followup_msgs), include_thoughts=True)
        )
        if second is not None and second.content:
            content = second.content
            total_in_tokens += second.input_tokens
            total_out_tokens += second.output_tokens
            usage_source = "provider" if second.usage_source == "provider" else usage_source

    if not content:
        return None
    return LiveLlmTurnOutcome(
        response_text=content,
        step_label=step_label,
        latency_ms=outcome.latency_ms,
        thinking_text=outcome.thinking_text or default_thinking,
        invoked_tool_names=invoked_tools,
        assembled_system_prompt=system_msg,
        input_tokens=total_in_tokens,
        output_tokens=total_out_tokens,
        usage_source=usage_source,
        model_id=ep.model_name,
        inference_tier=requested_tier or ep.tier,
        effort=effort,
        citation_map=turn_ctx.citation_map_dict,
    )


__all__ = [
    "ActiveBackgroundTurnState",
    "LiveLlmTurnOutcome",
    "ResolvedLiveLlmEndpoint",
    "_extract_tier_endpoint_from_dict",
    "_get_or_create_async_http_client",
    "_select_endpoint_from_tiers",
    "build_assistant_system_instructions",
    "build_legacy_local_chat_url",
    "build_multi_turn_messages",
    "build_provider_headers",
    "build_provider_request_body",
    "build_workspace_tools_schema",
    "detect_adaptive_thinking_steps_for_question",
    "ensure_active_chat_model_if_live",
    "extract_thinking_and_clean_content",
    "get_active_turn_for_workspace",
    "invoke_configured_llm_for_assistant_turn",
    "is_anthropic_provider",
    "is_safe_llm_endpoint_url",
    "normalize_chat_completions_url",
    "record_prompt_telemetry_entry",
    "resolve_5_layers_and_ontology_from_request",
    "resolve_5_layers_and_ontology_from_request_async",
    "resolve_assembled_system_instructions_for_turn",
    "resolve_assembled_system_instructions_for_turn_async",
    "resolve_configured_llm_endpoint",
    "resolve_request_locale",
    "stop_active_turn_for_workspace",
    "stream_configured_llm_for_assistant_turn",
    "stream_provider_chat_sse_async",
]
