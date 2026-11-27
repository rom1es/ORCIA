"""Serialization, Guard & PG18 Persistence Helpers for Agents & Skills (`Story 26.1`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers.assistant_llm_resolver import resolve_configured_llm_endpoint
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.agents_and_skills import (
    AgentItemResponse,
    ResolveAgentOrSkillResponse,
    SkillItemResponse,
    ToggleAgentGovernanceRequest,
)
from orcia_core.catalog.errors import ObserverModeReadOnlyError
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    ManagedAgentRecord,
    ManagedSkillRecord,
    load_agents_and_skills_from_postgres18,
)
from orcia_core.orchestration.errors import AgentDraftLifecycleBlockedError
from orcia_core.packs import (
    WorkspaceEntityCandidate,
    format_agent_mention,
    format_skill_command,
    load_workspace_active_pack_priorities_pg,
    resolve_workspace_entity_candidates,
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
    raw = {
        **asdict(s),
        "input_parameters": list(s.input_parameters),
        "collision_pack_slugs": list(s.collision_pack_slugs),
        "qualified_ref": s.qualified_ref
        or format_skill_command(
            s.slug, pack_slug=s.pack_slug, workspace_scoped=(s.pack_slug is None)
        ),
    }
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
    raw["collision_pack_slugs"] = list(a.collision_pack_slugs)
    raw["qualified_ref"] = a.qualified_ref or format_agent_mention(
        a.slug, pack_slug=a.pack_slug, workspace_scoped=(a.pack_slug is None)
    )
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
        logger.error("agents_skills_pg_persistence_failed", error_type=type(exc).__name__)
        raise


async def sync_from_postgres18_if_enabled(
    request: Request,
    svc: AgentsAndSkillsManagementService,
    *,
    workspace_id: str | None = None,
    unrestricted: bool = True,
    allowed_workspace_ids: frozenset[str] | None = None,
    allowed_org_ids: frozenset[str] | None = None,
) -> dict[str, int]:
    """Hydrate agents & skills from PG18 when DB engine is configured."""
    priorities: dict[str, int] = {}

    async def _load(eng: AsyncEngine) -> None:
        nonlocal priorities
        skills, agents = await load_agents_and_skills_from_postgres18(
            eng,
            workspace_id=workspace_id,
            unrestricted=unrestricted,
            allowed_workspace_ids=allowed_workspace_ids,
            allowed_org_ids=allowed_org_ids,
        )
        if workspace_id:
            priorities, _ = await load_workspace_active_pack_priorities_pg(eng, workspace_id)
        svc.sync_from_records(
            skills=skills, agents=agents, active_pack_priorities=priorities or None
        )

    await run_pg_persistence(request, _load)
    return priorities


def resolve_entity_for_api(
    svc: AgentsAndSkillsManagementService,
    *,
    raw_ref: str,
    kind: str,
    active_pack_priorities: dict[str, int] | None,
    strict_disambiguation: bool,
    instance: str,
    trace_id: str,
) -> ResolveAgentOrSkillResponse:
    """Resolve an agent or skill ref with optional strict 409 disambiguation."""
    records = svc.skills if kind == "skill" else svc.agents
    default_kind = "skills" if kind == "skill" else "agents"
    cands = [
        WorkspaceEntityCandidate(
            entity_id=r.skill_id if isinstance(r, ManagedSkillRecord) else r.agent_id,
            entity_slug=r.slug,
            pack_slug=r.pack_slug,
            resolution_tier=r.resolution_tier,
            priority_order=(
                active_pack_priorities.get(r.pack_slug)
                if active_pack_priorities and r.pack_slug
                else None
            ),
            is_active_in_workspace=getattr(r, "enabled_in_workspace", True),
            payload=r,
        )
        for r in records
    ]
    resolved = resolve_workspace_entity_candidates(
        raw_ref,
        cands,
        default_kind=default_kind,
        active_pack_priorities=active_pack_priorities,
        strict_disambiguation=strict_disambiguation,
        instance=instance,
    )
    formatted_cands = [
        (
            format_skill_command(
                c.entity_slug,
                pack_slug=c.pack_slug,
                workspace_scoped=(c.resolution_tier == "WORKSPACE_OVERRIDE"),
            )
            if kind == "skill"
            else format_agent_mention(
                c.entity_slug,
                pack_slug=c.pack_slug,
                workspace_scoped=(c.resolution_tier == "WORKSPACE_OVERRIDE"),
            )
        )
        for c in resolved.candidates
    ]
    return ResolveAgentOrSkillResponse(
        kind="skill" if kind == "skill" else "agent",
        raw_ref=raw_ref,
        entity_id=resolved.winner.entity_id,
        slug=resolved.winner.entity_slug,
        pack_slug=resolved.pack_slug,
        qualified_ref=resolved.qualified_ref,
        is_colliding=resolved.is_colliding,
        collision_pack_slugs=list(resolved.collision_pack_slugs),
        resolution_tier=resolved.resolution_tier,
        candidates=formatted_cands,
        trace_id=trace_id,
    )


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


def apply_agent_governance_update(
    svc: AgentsAndSkillsManagementService,
    agent_id: str,
    payload: ToggleAgentGovernanceRequest,
    *,
    instance: str,
) -> ManagedAgentRecord:
    """Apply lifecycle, MCP exposure, visibility, and thinking governance rules."""
    cur = svc.get_agent(agent_id, instance=instance)
    target_lifecycle = payload.lifecycle_status or cur.lifecycle_status
    if payload.lifecycle_status == "DRAFT" and payload.mcp_exposed is True:
        raise AgentDraftLifecycleBlockedError(
            detail_code="ERR_DRAFT_AGENT_CANNOT_EXPOSE_MCP",
            detail_params={"agent_name": cur.name},
            instance=instance,
        )
    if payload.lifecycle_status is not None and payload.lifecycle_status != cur.lifecycle_status:
        cur = svc.set_agent_lifecycle_status(
            agent_id,
            lifecycle_status=payload.lifecycle_status,
            instance=instance,
        )
    next_mcp = payload.mcp_exposed if payload.mcp_exposed is not None else cur.mcp_exposed
    return svc.upsert_agent(
        agent_id=cur.agent_id,
        name=cur.name,
        role_mission=cur.role_mission,
        instructions=cur.instructions,
        thinking_level=payload.thinking_level or cur.thinking_level,
        skill_ids=cur.skill_ids,
        version=cur.version,
        visibility_scope=payload.visibility_scope or cur.visibility_scope,
        source_pack_key=cur.source_pack_key,
        enabled_in_workspace=(
            payload.enabled_in_workspace
            if payload.enabled_in_workspace is not None
            else cur.enabled_in_workspace
        ),
        mcp_exposed=next_mcp,
        agent_kind=cur.agent_kind,
        remote_endpoint_url=cur.remote_endpoint_url,
        test_bench_validated=cur.test_bench_validated,
        lifecycle_status=target_lifecycle,
        test_bench_status=cur.test_bench_status,
        instance=instance,
    )
