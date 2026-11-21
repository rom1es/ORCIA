"""Serialization, Guard & PG18 Persistence Helpers for Agents & Skills (`Story 26.1`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

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
    return SkillItemResponse(**{**asdict(s), "input_parameters": list(s.input_parameters)})


def serialize_agent(a: ManagedAgentRecord) -> AgentItemResponse:
    """Serialize `ManagedAgentRecord`."""
    raw = asdict(a)
    raw["skill_ids"] = list(a.skill_ids)
    raw["invocation_modes"] = list(a.invocation_modes)
    raw["allowed_rag_sources"] = list(a.allowed_rag_sources)
    raw["ontology_views"] = list(a.ontology_views)
    raw["mcp_tool_permissions"] = dict(a.mcp_tool_permissions)
    raw["guardrails"] = list(a.guardrails)
    return AgentItemResponse(**raw)


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
