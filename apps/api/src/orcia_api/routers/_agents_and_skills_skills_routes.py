"""Skills Sub-Router for Agents & Skills (`Story 26.1`)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import get_agents_and_skills_service
from orcia_api.routers._agents_and_skills_helpers import (
    enforce_not_observer,
    run_pg_persistence,
    serialize_skill,
    sync_from_postgres18_if_enabled,
    trace_id_for,
)
from orcia_api.routers.assistant_llm_bridge import invoke_configured_llm_for_assistant_turn
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas.agents_and_skills import (
    DeleteSkillOrAgentResponse,
    ExecuteSkillRequest,
    ExecuteSkillResponse,
    SkillItemResponse,
    UpsertSkillRequest,
)
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    delete_skill_from_postgres18,
    persist_skill_to_postgres18,
)

skills_router = APIRouter()
AgentsAndSkillsSvcDep = Annotated[
    AgentsAndSkillsManagementService, Depends(get_agents_and_skills_service)
]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]
IdPath = Annotated[str, Path(min_length=1, max_length=128)]


@skills_router.post("/skills", response_model=SkillItemResponse, responses=PROBLEM_RESPONSES)
async def upsert_skill_endpoint(
    payload: UpsertSkillRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
) -> SkillItemResponse:
    enforce_not_observer(request, persona_key)
    skill = svc.upsert_skill(**payload.model_dump(), instance=str(request.url.path))
    await run_pg_persistence(request, lambda eng: persist_skill_to_postgres18(eng, skill))
    return serialize_skill(skill)


@skills_router.delete(
    "/skills/{skill_id}", response_model=DeleteSkillOrAgentResponse, responses=PROBLEM_RESPONSES
)
async def delete_skill_endpoint(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    skill_id: IdPath,
    persona_key: PersonaQuery = None,
) -> DeleteSkillOrAgentResponse:
    enforce_not_observer(request, persona_key)
    removed, detached_ids = svc.delete_skill(skill_id, instance=str(request.url.path))
    updated_agents = tuple(svc.get_agent(aid) for aid in detached_ids)
    await run_pg_persistence(
        request, lambda eng: delete_skill_from_postgres18(eng, removed.skill_id, updated_agents)
    )
    return DeleteSkillOrAgentResponse(
        deleted_id=removed.skill_id,
        detached_from_agent_ids=list(detached_ids),
        trace_id=trace_id_for(request),
    )


@skills_router.post(
    "/skills/{skill_id}/execute", response_model=ExecuteSkillResponse, responses=PROBLEM_RESPONSES
)
async def execute_skill_endpoint(
    payload: ExecuteSkillRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    skill_id: IdPath,
    persona_key: PersonaQuery = None,
) -> ExecuteSkillResponse:
    enforce_not_observer(request, persona_key)
    await sync_from_postgres18_if_enabled(request, svc)
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
        allow_system_override=True,
    )
    outcome = svc.execute_skill(
        skill_id,
        input_text=payload.input_text,
        parameters=payload.parameters,
        instance=str(request.url.path),
        llm_response_override=live_llm.response_text if live_llm is not None else None,
    )
    return ExecuteSkillResponse(**asdict(outcome), trace_id=trace_id_for(request))
