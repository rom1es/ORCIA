"""Dynamic Governed Workspace Tools Schema & Multi-Turn Message Builder (`Story 26.5`, `26.6b`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.dependencies.assistant_tools import (
    build_assistant_tool_catalog_context_async,
    get_governed_assistant_tool_router,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    ALLOWED_CLIENT_HISTORY_ROLES,
    sanitize_prompt_layer_markers,
)
from orcia_core.agents import build_authorized_tool_catalog
from orcia_core.orchestration.assistant_context_budget import trim_messages_to_token_budget
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AssistantToolExecutorPort,
    AuthorizedToolDescriptor,
    SkillCatalogEntry,
)
from orcia_core.ports.embedding import EmbeddingPort


def build_workspace_tools_schema(
    request: Request | None,
    speed_mode: str,
    *,
    rag_active: bool = False,
    user: UserIdentity | None = None,
    workspace_id: str = "",
) -> list[dict[str, Any]]:
    """Build OpenAI/Anthropic JSON Schema `tools` list for authorized Speed 2/3 callers."""
    if speed_mode not in ("SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"):
        return []
    if user is None or not user.id or user.id == "u-anonymous":
        return []
    role = str(user.platform_role or "OBSERVER").upper()
    user_roles = frozenset({role, *user.roles, *user.transverse_groups})
    user_perms: frozenset[str] = (
        frozenset({"read"})
        if role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR")
        else frozenset({"read", "execute"})
    )
    target_ws = workspace_id.strip() or "scope-global"
    skills: list[SkillCatalogEntry] = []
    if request is not None and hasattr(request, "app"):
        from orcia_api.dependencies import get_auth_service

        evaluator = get_auth_service(request).evaluator
        if target_ws != "scope-global":
            ws = evaluator.get_workspace(target_ws)
            if ws is None:
                return []
            access = evaluator.resolve_workspace_access(user, ws.id)
            if access is None:
                return []
            if access.access_mode == "READ_ONLY_OBSERVER":
                role = "READ_ONLY_OBSERVER"
                user_perms = frozenset({"read"})
        ag_svc = getattr(request.app.state, "agents_and_skills_service", None)
        if ag_svc is not None:
            for sk in getattr(ag_svc, "skills", ()):
                skills.append(
                    SkillCatalogEntry(
                        skill_id=sk.skill_id,
                        slug=sk.slug,
                        name=sk.name,
                        objective=sk.objective,
                        input_parameters=tuple(sk.input_parameters),
                        instructions=sk.instructions,
                        expected_output_format=sk.expected_output_format,
                        enabled_in_workspace=bool(sk.enabled_in_workspace),
                        sandbox_tier="TIER_1_WASM",
                        is_si_write=bool(getattr(sk, "is_si_write", False)),
                        human_authored_required=bool(getattr(sk, "human_authored_required", False)),
                        uri=sk.uri,
                    )
                )
    ctx = AssistantToolCatalogContext(
        workspace_id=target_ws,
        user_id=user.id,
        user_role=role,
        active_hat=str(user.human_profile_archetype or "ARCHITECT"),
        user_roles=user_roles,
        user_permissions=user_perms,
        rag_active=rag_active,
        skills=tuple(skills),
    )
    if request is not None and hasattr(request, "app"):
        router = get_governed_assistant_tool_router(request)
        catalog = router.build_authorized_catalog(ctx)
    else:
        catalog = build_authorized_tool_catalog(ctx)
    return [desc.to_llm_tool_schema() for desc in catalog]


async def build_workspace_tools_and_catalog_async(
    request: Request,
    *,
    speed_mode: str,
    user: UserIdentity | None,
    workspace_id: str,
    active_hat: str = "ARCHITECT",
    embedding_port: EmbeddingPort | None = None,
) -> tuple[list[dict[str, Any]], tuple[AuthorizedToolDescriptor, ...]]:
    """Build authorized PG18/RBAC/MCP tool catalog and serialized schemas for Speed 2/3."""
    if speed_mode not in ("SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"):
        return [], ()
    router = get_governed_assistant_tool_router(request)
    ctx = await build_assistant_tool_catalog_context_async(
        request,
        user=user,
        workspace_id=workspace_id,
        active_hat=active_hat,
        embedding_port=embedding_port,
    )
    catalog = router.build_authorized_catalog(ctx)
    return [desc.to_llm_tool_schema() for desc in catalog], tuple(catalog)


async def resolve_turn_tools_and_router_async(
    request: Request,
    *,
    speed_mode: str,
    tools_enabled: bool,
    user: UserIdentity | None,
    workspace_id: str,
    active_hat: str = "ARCHITECT",
    embedding_port: EmbeddingPort | None = None,
) -> tuple[
    list[dict[str, Any]], tuple[AuthorizedToolDescriptor, ...], AssistantToolExecutorPort | None
]:
    """Resolve authorized tools schema, descriptors, and `GovernedAssistantToolRouter`."""
    if not tools_enabled:
        return [], (), None
    tools_schema, catalog = await build_workspace_tools_and_catalog_async(
        request,
        speed_mode=speed_mode,
        user=user,
        workspace_id=workspace_id,
        active_hat=active_hat,
        embedding_port=embedding_port,
    )
    return tools_schema, catalog, get_governed_assistant_tool_router(request)


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


__all__ = [
    "build_multi_turn_messages",
    "build_workspace_tools_and_catalog_async",
    "build_workspace_tools_schema",
    "resolve_turn_tools_and_router_async",
]
