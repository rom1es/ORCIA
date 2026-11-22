"""Prompt Assembly & Tool Schema Facade delegating to `AssistantPromptBuilder` (`AD-15`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.routers._assistant_prompt_sanitization import (
    ALLOWED_CLIENT_HISTORY_ROLES,
    sanitize_prompt_layer_markers,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    detect_adaptive_thinking_steps_for_question as detect_adaptive_thinking_steps_for_question,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    resolve_request_locale as resolve_request_locale,
)
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder

_PROMPT_BUILDER = AssistantPromptBuilder()


def _format_user_governance_and_folder_block(
    *,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Delegate Layer 4 Workspace, Layer 5 User prefs & Folder Notes formatting."""
    return _PROMPT_BUILDER.format_governance_and_folder_block(
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )


def build_assistant_system_instructions(
    *,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    assembled_5_layers_prompt: str | None = None,
    ontology_concepts_summary: str | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Delegate 5-layer + ontology + preferences prompt assembly to `AssistantPromptBuilder`."""
    return _PROMPT_BUILDER.build_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
        assembled_5_layers_prompt=assembled_5_layers_prompt,
        ontology_concepts_summary=ontology_concepts_summary,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )


def resolve_5_layers_and_ontology_from_request(
    request: Request,
    *,
    workspace_id: str,
    user_id: str,
    hat: str,
    locale: str = "fr",
) -> tuple[str | None, str | None]:
    """Read assembled 5-layer prompt and active L1-L4 Ontology concepts from domain services."""
    assembled_text: str | None = None
    ontology_summary: str | None = None
    try:
        from orcia_api.dependencies import get_assistant_three_speed_router_service

        router_svc = get_assistant_three_speed_router_service(request)
        cached = router_svc.get_or_assemble_cached_prompt(
            workspace_id=workspace_id, user_id=user_id, hat=hat, locale=locale
        )
        assembled_text = cached.assembled_prompt_text
    except Exception as exc:
        get_logger("orcia.assistant.llm").warning(
            "assistant_5_layer_prompt_resolution_fallback", error_type=type(exc).__name__
        )
    try:
        from orcia_api.dependencies import get_ontology_and_rag_services

        ont_svc, _, _ = get_ontology_and_rag_services(request)
        concepts = getattr(ont_svc, "concepts", ())
        lines = [
            f"- [{c.level}] {c.canonical_term}: {c.definition_text}"
            for c in list(concepts)[:8]
            if getattr(c, "snapshot_branch_status", "ACTIVE") == "ACTIVE"
        ]
        if lines:
            ontology_summary = "\n".join(lines)
    except Exception as exc:
        get_logger("orcia.assistant.llm").warning(
            "assistant_ontology_l1_l4_resolution_fallback", error_type=type(exc).__name__
        )
    return assembled_text, ontology_summary


async def resolve_5_layers_and_ontology_from_request_async(
    request: Request,
    *,
    workspace_id: str,
    user_id: str,
    hat: str,
    locale: str = "fr",
) -> tuple[str | None, str | None]:
    """Async version reading PG18 Mode A governance overrides and active L1-L4 Ontology concepts."""
    assembled_text: str | None = None
    ontology_summary: str | None = None
    try:
        from orcia_api.dependencies import get_assistant_three_speed_router_service

        router_svc = get_assistant_three_speed_router_service(request)
        cached = await router_svc.get_or_assemble_cached_prompt_async(
            workspace_id=workspace_id, user_id=user_id, hat=hat, locale=locale
        )
        assembled_text = cached.assembled_prompt_text
    except Exception as exc:
        get_logger("orcia.assistant.llm").warning(
            "assistant_5_layer_prompt_resolution_fallback", error_type=type(exc).__name__
        )
    try:
        from orcia_api.dependencies import get_ontology_and_rag_services

        ont_svc, _, _ = get_ontology_and_rag_services(request)
        concepts = getattr(ont_svc, "concepts", ())
        lines = [
            f"- [{c.level}] {c.canonical_term}: {c.definition_text}"
            for c in list(concepts)[:8]
            if getattr(c, "snapshot_branch_status", "ACTIVE") == "ACTIVE"
        ]
        if lines:
            ontology_summary = "\n".join(lines)
    except Exception as exc:
        get_logger("orcia.assistant.llm").warning(
            "assistant_ontology_l1_l4_resolution_fallback", error_type=type(exc).__name__
        )
    return assembled_text, ontology_summary


async def resolve_assembled_system_instructions_for_turn_async(
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
    """Async builder hydrating Mode A PG18 overrides into the 5-layer system prompt."""
    assembled_5_layers, ontology_summary = await resolve_5_layers_and_ontology_from_request_async(
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


def build_workspace_tools_schema(request: Request | None, speed_mode: str) -> list[dict[str, Any]]:
    """Build OpenAI/Anthropic JSON Schema `tools` list for `SPEED_2_AGENT_TOOLS` / `SPEED_3`."""
    if speed_mode not in ("SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"):
        return []
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "query_workspace_knowledge_and_glossary",
                "description": "Search workspace documents, L1-L4 ontology concepts, and sources.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
            },
        }
    ]
    if request is not None and hasattr(request, "app"):
        ag_svc = getattr(request.app.state, "agents_and_skills_service", None)
        if ag_svc is not None:
            for sk in list(getattr(ag_svc, "skills", ()))[:10]:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"skill_{sk.slug.replace('-', '_')}",
                            "description": f"{sk.name}: {sk.objective}",
                            "parameters": {
                                "type": "object",
                                "properties": {"input_text": {"type": "string"}},
                                "required": ["input_text"],
                            },
                        },
                    }
                )
    return tools


def build_multi_turn_messages(
    *,
    system_msg: str,
    user_prompt: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build sanitized `[system, *history, user]` restricting roles to `user|assistant`."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_msg}]
    for item in conversation_history or ():
        if isinstance(item, dict):
            role = str(item.get("role") or "user").strip().lower()
            content = sanitize_prompt_layer_markers(str(item.get("content") or ""))
            if role in ALLOWED_CLIENT_HISTORY_ROLES and content:
                msg: dict[str, Any] = {"role": role, "content": content}
                if item.get("name"):
                    msg["name"] = str(item["name"])
                messages.append(msg)
    messages.append({"role": "user", "content": sanitize_prompt_layer_markers(user_prompt)})
    return messages
