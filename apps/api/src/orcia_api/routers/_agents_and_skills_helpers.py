"""Serialization, Guard & PG18 Persistence Helpers for Agents & Skills (`Story 26.1`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers.assistant_llm_resolver import resolve_configured_llm_endpoint
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.agents_and_skills import AgentItemResponse, SkillItemResponse
from orcia_core.catalog.errors import ObserverModeReadOnlyError
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    ManagedAgentRecord,
    ManagedSkillRecord,
    load_agents_and_skills_from_postgres18,
)
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)

logger = get_logger("orcia.api.agents_skills")


def trace_id_for(request: Request) -> str:
    """Resolve active trace_id."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def enforce_not_observer(request: Request, persona_key: str | None) -> None:
    """Reject OBSERVER / BU_DIRECTOR / READ_ONLY_OBSERVER header mutations."""
    user = resolve_request_user(request, persona_key=persona_key)
    hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    if (
        hdr == "READ_ONLY_OBSERVER"
        or user.platform_role in ("OBSERVER", "BU_DIRECTOR")
        or persona_key in ("claire", "observer")
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))


def serialize_skill(s: ManagedSkillRecord) -> SkillItemResponse:
    """Serialize `ManagedSkillRecord`."""
    raw = {**asdict(s), "input_parameters": list(s.input_parameters)}
    filtered = {k: v for k, v in raw.items() if k in SkillItemResponse.model_fields}
    return SkillItemResponse(**filtered)


def serialize_agent(a: ManagedAgentRecord) -> AgentItemResponse:
    """Serialize `ManagedAgentRecord`."""
    raw = asdict(a)
    raw["skill_ids"] = list(a.skill_ids)
    raw["invocation_modes"] = list(a.invocation_modes)
    raw["allowed_rag_sources"] = list(a.allowed_rag_sources)
    raw["ontology_views"] = list(a.ontology_views)
    raw["mcp_tool_permissions"] = dict(a.mcp_tool_permissions)
    raw["guardrails"] = list(a.guardrails)
    filtered = {k: v for k, v in raw.items() if k in AgentItemResponse.model_fields}
    return AgentItemResponse(**filtered)


async def run_pg_persistence(
    request: Request, fn: Callable[[AsyncEngine], Awaitable[None]]
) -> None:
    """Execute PG18 persistence callback when DB engine is configured."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    if engine is None:
        return
    try:
        await fn(engine)
    except Exception as exc:
        logger.warning("agents_skills_pg_persistence_failed", error_type=type(exc).__name__)


async def sync_from_postgres18_if_enabled(
    request: Request, svc: AgentsAndSkillsManagementService
) -> None:
    """Hydrate agents & skills from PG18 when DB engine is configured."""

    async def _load(eng: AsyncEngine) -> None:
        skills, agents = await load_agents_and_skills_from_postgres18(eng)
        svc.sync_from_records(skills=skills, agents=agents)

    await run_pg_persistence(request, _load)


async def complete_optional_live_turn(
    request: Request,
    llm_port: LlmStreamingPort,
    *,
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """Optionally invoke injected `LlmStreamingPort` when a live chat endpoint is active."""
    ep = await resolve_configured_llm_endpoint(request)
    if ep is None:
        if getattr(request.app.state, "llm_streaming_port", None) is not None and not getattr(
            llm_port, "is_cassette_adapter", False
        ):
            ep = LlmEndpointConfig(
                provider="injected",
                model_name="injected",
                endpoint_uri="http://localhost",
                auth_mode="none",
            )
        else:
            return None
    outcome = await llm_port.complete_chat(
        LlmStreamRequest(
            endpoint=ep,
            messages=(
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ),
            include_thoughts=True,
        )
    )
    return outcome.content if outcome is not None and outcome.content else None
