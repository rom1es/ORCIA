"""FastAPI Router for Agents (`🤖`) & Skills (`🛠️`) Creation, 1-Click Attachment & Execution."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import get_agents_and_skills_service, get_or_create_shared_db_engine
from orcia_api.routers.assistant_llm_bridge import invoke_configured_llm_for_assistant_turn
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.agents_and_skills import (
    AgentItemResponse,
    AgentsAndSkillsListResponse,
    DeleteSkillOrAgentResponse,
    DuplicateAgentRequest,
    ExecuteAgentRequest,
    ExecuteAgentResponse,
    ExecuteSkillRequest,
    ExecuteSkillResponse,
    InvokedSkillTraceResponseItem,
    SkillItemResponse,
    ToggleAgentGovernanceRequest,
    UpdateAgentSkillsRequest,
    UpsertAgentRequest,
    UpsertSkillRequest,
)
from orcia_core.catalog.errors import ObserverModeReadOnlyError
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    ManagedAgentRecord,
    ManagedSkillRecord,
    delete_agent_from_postgres18,
    delete_skill_from_postgres18,
    load_agents_and_skills_from_postgres18,
    persist_agent_to_postgres18,
    persist_skill_to_postgres18,
)

logger = get_logger("orcia.api.agents_skills")
router = APIRouter(prefix="/api/v1/agents-and-skills", tags=["agents-and-skills"])

AgentsAndSkillsSvcDep = Annotated[
    AgentsAndSkillsManagementService, Depends(get_agents_and_skills_service)
]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]
IdPath = Annotated[str, Path(min_length=1, max_length=128)]


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _enforce_not_observer(request: Request, persona_key: str | None) -> None:
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR") or persona_key in ("claire", "observer"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))


def _serialize_skill(s: ManagedSkillRecord) -> SkillItemResponse:
    return SkillItemResponse(**{**asdict(s), "input_parameters": list(s.input_parameters)})


def _serialize_agent(a: ManagedAgentRecord) -> AgentItemResponse:
    return AgentItemResponse(**{**asdict(a), "skill_ids": list(a.skill_ids)})


async def _run_pg_persistence(
    request: Request, fn: Callable[[AsyncEngine], Awaitable[None]]
) -> None:
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") == "1":
        return
    try:
        engine = get_or_create_shared_db_engine(request)
        await fn(engine)
    except Exception as exc:
        logger.warning("agents_skills_pg_persistence_failed", error_type=type(exc).__name__)


async def _sync_from_postgres18_if_enabled(
    request: Request, svc: AgentsAndSkillsManagementService
) -> None:
    async def _load(eng: AsyncEngine) -> None:
        skills, agents = await load_agents_and_skills_from_postgres18(eng)
        svc.sync_from_records(skills=skills, agents=agents)

    await _run_pg_persistence(request, _load)


@router.get("", response_model=AgentsAndSkillsListResponse, responses=PROBLEM_RESPONSES)
async def list_agents_and_skills(
    request: Request, svc: AgentsAndSkillsSvcDep, persona_key: PersonaQuery = None
) -> AgentsAndSkillsListResponse:
    resolve_request_user(request, persona_key=persona_key)
    await _sync_from_postgres18_if_enabled(request, svc)
    return AgentsAndSkillsListResponse(
        agents=[_serialize_agent(a) for a in svc.agents],
        skills=[_serialize_skill(s) for s in svc.skills],
        trace_id=_trace(request),
    )


@router.post("/skills", response_model=SkillItemResponse, responses=PROBLEM_RESPONSES)
async def upsert_skill_endpoint(
    payload: UpsertSkillRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
) -> SkillItemResponse:
    _enforce_not_observer(request, persona_key)
    skill = svc.upsert_skill(**payload.model_dump(), instance=str(request.url.path))
    await _run_pg_persistence(request, lambda eng: persist_skill_to_postgres18(eng, skill))
    return _serialize_skill(skill)


@router.delete(
    "/skills/{skill_id}", response_model=DeleteSkillOrAgentResponse, responses=PROBLEM_RESPONSES
)
async def delete_skill_endpoint(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    skill_id: IdPath,
    persona_key: PersonaQuery = None,
) -> DeleteSkillOrAgentResponse:
    _enforce_not_observer(request, persona_key)
    removed, detached_ids = svc.delete_skill(skill_id, instance=str(request.url.path))
    updated_agents = tuple(svc.get_agent(aid) for aid in detached_ids)
    await _run_pg_persistence(
        request, lambda eng: delete_skill_from_postgres18(eng, removed.skill_id, updated_agents)
    )
    return DeleteSkillOrAgentResponse(
        deleted_id=removed.skill_id,
        detached_from_agent_ids=list(detached_ids),
        trace_id=_trace(request),
    )


@router.post(
    "/skills/{skill_id}/execute", response_model=ExecuteSkillResponse, responses=PROBLEM_RESPONSES
)
async def execute_skill_endpoint(
    payload: ExecuteSkillRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    skill_id: IdPath,
    persona_key: PersonaQuery = None,
) -> ExecuteSkillResponse:
    _enforce_not_observer(request, persona_key)
    await _sync_from_postgres18_if_enabled(request, svc)
    skill = svc.get_skill(skill_id, instance=str(request.url.path))
    live_llm = await invoke_configured_llm_for_assistant_turn(
        request,
        user_prompt=payload.input_text,
        hat="PLATFORM_ADMIN",
        speed_mode="SPEED_1_FAST",
        system_instructions_override=(
            f"Tu exécutes la compétence ORCIA « {skill.name} » ({skill.command_handle}). "
            f"Objectif : {skill.objective}. Instructions : {skill.instructions}. "
            f"Format attendu : {skill.expected_output_format}. "
            "Respond in the exact same language as the user's message "
            "(unless the user explicitly asks for another language)."
        ),
    )
    outcome = svc.execute_skill(
        skill_id,
        input_text=payload.input_text,
        parameters=payload.parameters,
        instance=str(request.url.path),
        llm_response_override=live_llm.response_text if live_llm is not None else None,
    )
    return ExecuteSkillResponse(**asdict(outcome), trace_id=_trace(request))


@router.post("/agents", response_model=AgentItemResponse, responses=PROBLEM_RESPONSES)
async def upsert_agent_endpoint(
    payload: UpsertAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
) -> AgentItemResponse:
    _enforce_not_observer(request, persona_key)
    agent = svc.upsert_agent(**payload.model_dump(), instance=str(request.url.path))
    await _run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, agent))
    return _serialize_agent(agent)


@router.post(
    "/agents/{agent_id}/duplicate", response_model=AgentItemResponse, responses=PROBLEM_RESPONSES
)
async def duplicate_agent_endpoint(
    payload: DuplicateAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> AgentItemResponse:
    _enforce_not_observer(request, persona_key)
    duplicated = svc.duplicate_agent(
        agent_id,
        new_name=payload.new_name,
        visibility_scope=payload.visibility_scope,
        instance=str(request.url.path),
    )
    await _run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, duplicated))
    return _serialize_agent(duplicated)


@router.patch(
    "/agents/{agent_id}/governance", response_model=AgentItemResponse, responses=PROBLEM_RESPONSES
)
async def update_agent_governance_endpoint(
    payload: ToggleAgentGovernanceRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> AgentItemResponse:
    _enforce_not_observer(request, persona_key)
    cur = svc.get_agent(agent_id, instance=str(request.url.path))
    updated = svc.upsert_agent(
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
        mcp_exposed=payload.mcp_exposed if payload.mcp_exposed is not None else cur.mcp_exposed,
        agent_kind=cur.agent_kind,
        remote_endpoint_url=cur.remote_endpoint_url,
        instance=str(request.url.path),
    )
    await _run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, updated))
    return _serialize_agent(updated)


@router.patch(
    "/agents/{agent_id}/skills", response_model=AgentItemResponse, responses=PROBLEM_RESPONSES
)
async def update_agent_skills_endpoint(
    payload: UpdateAgentSkillsRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> AgentItemResponse:
    _enforce_not_observer(request, persona_key)
    agent = svc.set_agent_skills(
        agent_id, skill_ids=payload.skill_ids, instance=str(request.url.path)
    )
    await _run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, agent))
    return _serialize_agent(agent)


@router.delete(
    "/agents/{agent_id}", response_model=DeleteSkillOrAgentResponse, responses=PROBLEM_RESPONSES
)
async def delete_agent_endpoint(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> DeleteSkillOrAgentResponse:
    _enforce_not_observer(request, persona_key)
    removed = svc.delete_agent(agent_id, instance=str(request.url.path))
    await _run_pg_persistence(
        request, lambda eng: delete_agent_from_postgres18(eng, removed.agent_id)
    )
    return DeleteSkillOrAgentResponse(
        deleted_id=removed.agent_id, detached_from_agent_ids=[], trace_id=_trace(request)
    )


@router.post(
    "/agents/{agent_id}/execute", response_model=ExecuteAgentResponse, responses=PROBLEM_RESPONSES
)
async def execute_agent_endpoint(
    payload: ExecuteAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> ExecuteAgentResponse:
    _enforce_not_observer(request, persona_key)
    await _sync_from_postgres18_if_enabled(request, svc)
    agent = svc.get_agent(agent_id, instance=str(request.url.path))
    live_llm = await invoke_configured_llm_for_assistant_turn(
        request,
        user_prompt=payload.prompt,
        hat="PLATFORM_ADMIN",
        speed_mode="SPEED_1_FAST",
        system_instructions_override=(
            f"Tu es l'agent ORCIA « {agent.name} » ({agent.handle}). "
            f"Rôle et mission : {agent.role_mission}. "
            f"Instructions : {agent.instructions}. "
            "Respond in the exact same language as the user's message "
            "(unless the user explicitly asks for another language)."
        ),
    )
    outcome = svc.execute_agent(
        agent_id,
        prompt=payload.prompt,
        instance=str(request.url.path),
        llm_response_override=live_llm.response_text if live_llm is not None else None,
    )
    return ExecuteAgentResponse(
        agent_id=outcome.agent_id,
        agent_name=outcome.agent_name,
        agent_handle=outcome.agent_handle,
        thinking_level=outcome.thinking_level,
        prompt=outcome.prompt,
        response_text=outcome.response_text,
        invoked_skills=[InvokedSkillTraceResponseItem(**asdict(s)) for s in outcome.invoked_skills],
        status=outcome.status,
        trace_id=_trace(request),
    )
