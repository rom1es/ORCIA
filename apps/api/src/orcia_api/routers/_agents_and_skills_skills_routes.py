"""Skills Sub-Router for Agents & Skills (`Story 26.1`)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import get_agents_and_skills_service, get_llm_streaming_port
from orcia_api.routers._agents_and_skills_helpers import (
    complete_optional_live_turn,
    enforce_not_observer,
    run_pg_persistence,
    serialize_skill,
    sync_from_postgres18_if_enabled,
    trace_id_for,
)
from orcia_api.routers._entity_delete_rbac import (
    build_catalog_target_authorizer,
    prepare_entity_delete_guards,
)
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
from orcia_core.permissions.errors import ScopeAccessDeniedError
from orcia_core.ports.llm_streaming_port import LlmStreamingPort

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
    await sync_from_postgres18_if_enabled(request, svc)
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
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> DeleteSkillOrAgentResponse:
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    await sync_from_postgres18_if_enabled(request, svc)
    existing = svc.get_skill(skill_id, instance=inst)
    target_auth = build_catalog_target_authorizer(auth_svc, user, instance=inst)
    if existing.owner_workspace_id:
        target_auth(existing.owner_workspace_id, existing.visibility_scope)
    if existing.pack_slug:
        raise ScopeAccessDeniedError(
            detail_override="Pack-owned skills cannot be deleted individually.",
            instance=inst,
        )
    detached_preview = tuple(
        a
        for a in svc.agents
        if existing.skill_id in a.skill_ids and str(a.visibility_scope).upper() != "PACK"
    )
    updated_preview = tuple(
        a.__class__(
            **{**asdict(a), "skill_ids": tuple(s for s in a.skill_ids if s != existing.skill_id)}
        )
        for a in detached_preview
    )
    unlinked: list[dict[str, str]] = []

    async def _del_pg(eng: AsyncEngine) -> None:
        nonlocal unlinked
        unlinked = await delete_skill_from_postgres18(
            eng,
            existing.skill_id,
            updated_preview,
            unlink_from_draft_packs=unlink_from_draft_packs,
            authorize_target_cb=build_catalog_target_authorizer(auth_svc, user, instance=inst),
            authorize_draft_cb=authorize_draft,
            actor_id=user.id,
            actor_email=user.email,
            trace_id=trace_id,
            instance=inst,
        )

    await run_pg_persistence(request, _del_pg)
    removed, detached_ids = svc.delete_skill(existing.skill_id, instance=inst)
    return DeleteSkillOrAgentResponse(
        deleted_id=removed.skill_id,
        detached_from_agent_ids=list(detached_ids),
        unlinked_draft_packs=unlinked,
        trace_id=trace_id,
    )


@skills_router.post(
    "/skills/{skill_id}/execute", response_model=ExecuteSkillResponse, responses=PROBLEM_RESPONSES
)
async def execute_skill_endpoint(
    payload: ExecuteSkillRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    llm_port: Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)],
    skill_id: IdPath,
    persona_key: PersonaQuery = None,
) -> ExecuteSkillResponse:
    enforce_not_observer(request, persona_key)
    await sync_from_postgres18_if_enabled(request, svc)
    skill = svc.get_skill(skill_id, instance=str(request.url.path))
    live_reply = await complete_optional_live_turn(
        request,
        llm_port,
        system_prompt=(
            f"You are executing ORCIA skill « {skill.name} » ({skill.command_handle}). "
            f"Objective: {skill.objective}. Instructions: {skill.instructions}. "
            f"Expected output format: {skill.expected_output_format}. "
            "Respond in the exact same language as the user's message "
            "(unless the user explicitly asks for another language)."
        ),
        user_prompt=payload.input_text,
    )
    outcome = svc.execute_skill(
        skill_id,
        input_text=payload.input_text,
        parameters=payload.parameters,
        instance=str(request.url.path),
        llm_response_override=live_reply,
    )
    return ExecuteSkillResponse(**asdict(outcome), trace_id=trace_id_for(request))
