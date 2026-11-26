"""FastAPI Router for Agents (`🤖`) & Skills (`🛠️`) Creation, Attachment & Execution."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import get_agents_and_skills_service, get_llm_streaming_port
from orcia_api.routers._agents_and_skills_helpers import (
    apply_agent_governance_update as _apply_agent_governance_update,
)
from orcia_api.routers._agents_and_skills_helpers import (
    complete_optional_live_turn as _complete_optional_live_turn,
)
from orcia_api.routers._agents_and_skills_helpers import (
    enforce_not_observer as _enforce_not_observer,
)
from orcia_api.routers._agents_and_skills_helpers import (
    resolve_entity_for_api as _resolve_entity_for_api,
)
from orcia_api.routers._agents_and_skills_helpers import (
    run_pg_persistence as _run_pg_persistence,
)
from orcia_api.routers._agents_and_skills_helpers import (
    serialize_agent as _serialize_agent,
)
from orcia_api.routers._agents_and_skills_helpers import (
    serialize_skill as _serialize_skill,
)
from orcia_api.routers._agents_and_skills_helpers import (
    sync_from_postgres18_if_enabled as _sync_from_postgres18_if_enabled,
)
from orcia_api.routers._agents_and_skills_helpers import (
    trace_id_for as _trace,
)
from orcia_api.routers._agents_and_skills_skills_routes import skills_router
from orcia_api.routers._entity_delete_rbac import (
    build_catalog_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.agents_and_skills import (
    AgentItemResponse,
    AgentsAndSkillsListResponse,
    DeleteSkillOrAgentResponse,
    DuplicateAgentRequest,
    ExecuteAgentRequest,
    ExecuteAgentResponse,
    InvokedSkillTraceResponseItem,
    ResolveAgentOrSkillResponse,
    ToggleAgentGovernanceRequest,
    UpdateAgentSkillsRequest,
    UpsertAgentRequest,
)
from orcia_core.catalog.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    delete_agent_from_postgres18,
    persist_agent_to_postgres18,
)
from orcia_core.permissions.errors import ScopeAccessDeniedError
from orcia_core.ports.llm_streaming_port import LlmStreamingPort

router = APIRouter(prefix="/api/v1/agents-and-skills", tags=["agents-and-skills"])
router.include_router(skills_router)

AgentsAndSkillsSvcDep = Annotated[
    AgentsAndSkillsManagementService, Depends(get_agents_and_skills_service)
]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]
IdPath = Annotated[str, Path(min_length=1, max_length=128)]


@router.get("", response_model=AgentsAndSkillsListResponse, responses=PROBLEM_RESPONSES)
async def list_agents_and_skills(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
    workspace_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
) -> AgentsAndSkillsListResponse:
    resolve_request_user(request, persona_key=persona_key)
    await _sync_from_postgres18_if_enabled(request, svc, workspace_id=workspace_id)
    return AgentsAndSkillsListResponse(
        agents=[_serialize_agent(a) for a in svc.agents],
        skills=[_serialize_skill(s) for s in svc.skills],
        trace_id=_trace(request),
    )


@router.get("/resolve", response_model=ResolveAgentOrSkillResponse, responses=PROBLEM_RESPONSES)
async def resolve_agent_or_skill_endpoint(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    ref: Annotated[str, Query(min_length=1, max_length=256)],
    kind: Annotated[Literal["agent", "skill"], Query()] = "agent",
    workspace_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    strict_disambiguation: Annotated[bool, Query()] = False,
    persona_key: PersonaQuery = None,
) -> ResolveAgentOrSkillResponse:
    """Resolve `@<pack>/<slug>`, `/<pack>/<slug>`, `<pack>:<slug>`, or bare handles flatly."""
    resolve_request_user(request, persona_key=persona_key)
    priorities = await _sync_from_postgres18_if_enabled(request, svc, workspace_id=workspace_id)
    return _resolve_entity_for_api(
        svc,
        raw_ref=ref,
        kind=kind,
        active_pack_priorities=priorities or None,
        strict_disambiguation=strict_disambiguation,
        instance=str(request.url.path),
        trace_id=_trace(request),
    )


@router.post("/agents", response_model=AgentItemResponse, responses=PROBLEM_RESPONSES)
async def upsert_agent_endpoint(
    payload: UpsertAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
) -> AgentItemResponse:
    _enforce_not_observer(request, persona_key)
    await _sync_from_postgres18_if_enabled(request, svc)
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
    await _sync_from_postgres18_if_enabled(request, svc)
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
    await _sync_from_postgres18_if_enabled(request, svc)
    updated = _apply_agent_governance_update(svc, agent_id, payload, instance=str(request.url.path))
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
    await _sync_from_postgres18_if_enabled(request, svc)
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
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> DeleteSkillOrAgentResponse:
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    await _sync_from_postgres18_if_enabled(request, svc)
    existing = svc.get_agent(agent_id, instance=inst)
    target_auth = build_catalog_target_authorizer(auth_svc, user, instance=inst)
    if existing.owner_workspace_id:
        target_auth(existing.owner_workspace_id, existing.visibility_scope)
    if existing.pack_slug:
        raise ScopeAccessDeniedError(
            detail_override="Pack-owned agents cannot be deleted individually.",
            instance=inst,
        )
    unlinked: list[dict[str, str]] = []

    async def _del_pg(eng: AsyncEngine) -> None:
        nonlocal unlinked
        unlinked = await delete_agent_from_postgres18(
            eng,
            existing.agent_id,
            unlink_from_draft_packs=unlink_from_draft_packs,
            authorize_target_cb=build_catalog_target_authorizer(auth_svc, user, instance=inst),
            authorize_draft_cb=authorize_draft,
            actor_id=user.id,
            actor_email=user.email,
            trace_id=trace_id,
            instance=inst,
        )

    await _run_pg_persistence(request, _del_pg)
    removed = svc.delete_agent(existing.agent_id, instance=inst)
    return DeleteSkillOrAgentResponse(
        deleted_id=removed.agent_id,
        detached_from_agent_ids=[],
        unlinked_draft_packs=unlinked,
        trace_id=trace_id,
    )


@router.post(
    "/agents/{agent_id}/execute", response_model=ExecuteAgentResponse, responses=PROBLEM_RESPONSES
)
async def execute_agent_endpoint(
    payload: ExecuteAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    llm_port: Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)],
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> ExecuteAgentResponse:
    _enforce_not_observer(request, persona_key)
    await _sync_from_postgres18_if_enabled(request, svc)
    agent = svc.get_agent(agent_id, instance=str(request.url.path))
    try:
        live_reply = await _complete_optional_live_turn(
            request,
            llm_port,
            system_prompt=(
                f"You are ORCIA agent « {agent.name} » ({agent.handle}). "
                f"Posture: {agent.posture} | Partner: {agent.human_partner_role}. "
                f"Mission: {agent.role_mission}. Instructions: {agent.instructions}. "
                "Respond in the exact same language as the user's message "
                "(unless the user explicitly asks for another language)."
            ),
            user_prompt=payload.prompt,
        )
        outcome = svc.execute_agent(
            agent_id,
            prompt=payload.prompt,
            instance=str(request.url.path),
            llm_response_override=live_reply,
        )
    except (ValidationDomainError, ResourceNotFoundError):
        raise
    except Exception:
        failed_agent = svc.mark_agent_test_bench_failed(agent_id)
        if failed_agent is not None:
            await _run_pg_persistence(
                request, lambda eng: persist_agent_to_postgres18(eng, failed_agent)
            )
        raise
    validated_agent = svc.get_agent(agent_id, instance=str(request.url.path))
    await _run_pg_persistence(
        request, lambda eng: persist_agent_to_postgres18(eng, validated_agent)
    )
    return ExecuteAgentResponse(
        agent_id=outcome.agent_id,
        agent_name=outcome.agent_name,
        agent_handle=outcome.agent_handle,
        thinking_level=outcome.thinking_level,
        prompt=outcome.prompt,
        response_text=outcome.response_text,
        invoked_skills=[
            InvokedSkillTraceResponseItem(**asdict(inv)) for inv in outcome.invoked_skills
        ],
        status=outcome.status,
        test_bench_status=outcome.test_bench_status,
        lifecycle_status=outcome.lifecycle_status,
        trace_id=_trace(request),
    )
