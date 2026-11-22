"""Tools Schema & Token-Budgeted Multi-Turn Message Builder (`Story 26.5`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.routers._assistant_prompt_sanitization import (
    ALLOWED_CLIENT_HISTORY_ROLES,
    sanitize_prompt_layer_markers,
)
from orcia_core.orchestration.assistant_context_budget import trim_messages_to_token_budget


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
    max_tokens_budget: int | None = None,
) -> list[dict[str, Any]]:
    """Build sanitized `[system, *history, user]` trimmed cleanly to `max_tokens_budget`."""
    sanitized_history: list[dict[str, Any]] = []
    for item in conversation_history or ():
        if isinstance(item, dict):
            role = str(item.get("role") or "user").strip().lower()
            content = sanitize_prompt_layer_markers(str(item.get("content") or ""))
            if role in ALLOWED_CLIENT_HISTORY_ROLES and content:
                msg: dict[str, Any] = {"role": role, "content": content}
                if item.get("name"):
                    msg["name"] = str(item["name"])
                sanitized_history.append(msg)
    budget = max(128, int(max_tokens_budget)) if max_tokens_budget is not None else 8192
    trimmed = trim_messages_to_token_budget(
        system_msg=system_msg,
        user_prompt=sanitize_prompt_layer_markers(user_prompt),
        conversation_history=sanitized_history,
        max_tokens_budget=budget,
    )
    return list(trimmed.messages)


__all__ = ["build_multi_turn_messages", "build_workspace_tools_schema"]
