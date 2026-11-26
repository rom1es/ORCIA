"""FastAPI Router for Agents (`🤖`) & Skills (`🛠️`) Creation, Attachment & Execution."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import get_agents_and_skills_service, get_llm_streaming_port
from orcia_api.routers import _agents_and_skills_helpers as _h
from orcia_api.routers._agents_and_skills_helpers import (
    sync_from_postgres18_if_enabled as _sync_from_postgres18_if_enabled,
)
from orcia_api.routers._agents_and_skills_skills_routes import skills_router
from orcia_api.routers._entity_delete_rbac import (
    build_catalog_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_api.routers._packs_scope_guards import (
    authorize_agents_skills_scope,
    filter_scoped_catalog_records,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas import agents_and_skills as _s
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


@router.get("", response_model=_s.AgentsAndSkillsListResponse, responses=PROBLEM_RESPONSES)
async def list_agents_and_skills(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
    workspace_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
) -> _s.AgentsAndSkillsListResponse:
    r_ws, unres, allow_ws, allow_orgs = await authorize_agents_skills_scope(
        request, workspace_id=workspace_id, persona_key=persona_key
    )
    await _h.sync_from_postgres18_if_enabled(
        request,
        svc,
        workspace_id=r_ws,
        unrestricted=unres,
        allowed_workspace_ids=allow_ws,
        allowed_org_ids=allow_orgs,
    )
    ag_list = filter_scoped_catalog_records(
        svc.agents, resolved_ws=r_ws, unrestricted=unres, allowed_ws=allow_ws
    )
    sk_list = filter_scoped_catalog_records(
        svc.skills, resolved_ws=r_ws, unrestricted=unres, allowed_ws=allow_ws
    )
    return _s.AgentsAndSkillsListResponse(
        agents=[_h.serialize_agent(a) for a in ag_list],  # type: ignore[arg-type]
        skills=[_h.serialize_skill(s) for s in sk_list],  # type: ignore[arg-type]
        trace_id=_h.trace_id_for(request),
    )


@router.get("/resolve", response_model=_s.ResolveAgentOrSkillResponse, responses=PROBLEM_RESPONSES)
async def resolve_agent_or_skill_endpoint(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    ref: Annotated[str, Query(min_length=1, max_length=256)],
    kind: Annotated[Literal["agent", "skill"], Query()] = "agent",
    workspace_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    strict_disambiguation: Annotated[bool, Query()] = False,
    persona_key: PersonaQuery = None,
) -> _s.ResolveAgentOrSkillResponse:
    """Resolve `@<pack>/<slug>`, `/<pack>/<slug>`, `<pack>:<slug>`, or bare handles flatly."""
    r_ws, unres, allow_ws, allow_orgs = await authorize_agents_skills_scope(
        request, workspace_id=workspace_id, persona_key=persona_key
    )
    priorities = await _h.sync_from_postgres18_if_enabled(
        request,
        svc,
        workspace_id=r_ws,
        unrestricted=unres,
        allowed_workspace_ids=allow_ws,
        allowed_org_ids=allow_orgs,
    )
    return _h.resolve_entity_for_api(
        svc,
        raw_ref=ref,
        kind=kind,
        active_pack_priorities=priorities or None,
        strict_disambiguation=strict_disambiguation,
        instance=str(request.url.path),
        trace_id=_h.trace_id_for(request),
    )


@router.post("/agents", response_model=_s.AgentItemResponse, responses=PROBLEM_RESPONSES)
async def upsert_agent_endpoint(
    payload: _s.UpsertAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    persona_key: PersonaQuery = None,
) -> _s.AgentItemResponse:
    _h.enforce_not_observer(request, persona_key)
    await _h.sync_from_postgres18_if_enabled(request, svc)
    agent = svc.upsert_agent(**payload.model_dump(), instance=str(request.url.path))
    await _h.run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, agent))
    return _h.serialize_agent(agent)


@router.post(
    "/agents/{agent_id}/duplicate", response_model=_s.AgentItemResponse, responses=PROBLEM_RESPONSES
)
async def duplicate_agent_endpoint(
    payload: _s.DuplicateAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> _s.AgentItemResponse:
    _h.enforce_not_observer(request, persona_key)
    await _h.sync_from_postgres18_if_enabled(request, svc)
    duplicated = svc.duplicate_agent(
        agent_id,
        new_name=payload.new_name,
        visibility_scope=payload.visibility_scope,
        instance=str(request.url.path),
    )
    await _h.run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, duplicated))
    return _h.serialize_agent(duplicated)


@router.patch(
    "/agents/{agent_id}/governance",
    response_model=_s.AgentItemResponse,
    responses=PROBLEM_RESPONSES,
)
async def update_agent_governance_endpoint(
    payload: _s.ToggleAgentGovernanceRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> _s.AgentItemResponse:
    _h.enforce_not_observer(request, persona_key)
    await _h.sync_from_postgres18_if_enabled(request, svc)
    updated = _h.apply_agent_governance_update(
        svc, agent_id, payload, instance=str(request.url.path)
    )
    await _h.run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, updated))
    return _h.serialize_agent(updated)


@router.patch(
    "/agents/{agent_id}/skills", response_model=_s.AgentItemResponse, responses=PROBLEM_RESPONSES
)
async def update_agent_skills_endpoint(
    payload: _s.UpdateAgentSkillsRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> _s.AgentItemResponse:
    _h.enforce_not_observer(request, persona_key)
    await _h.sync_from_postgres18_if_enabled(request, svc)
    agent = svc.set_agent_skills(
        agent_id, skill_ids=payload.skill_ids, instance=str(request.url.path)
    )
    await _h.run_pg_persistence(request, lambda eng: persist_agent_to_postgres18(eng, agent))
    return _h.serialize_agent(agent)


@router.delete(
    "/agents/{agent_id}", response_model=_s.DeleteSkillOrAgentResponse, responses=PROBLEM_RESPONSES
)
async def delete_agent_endpoint(
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    agent_id: IdPath,
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> _s.DeleteSkillOrAgentResponse:
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

    await _h.run_pg_persistence(request, _del_pg)
    removed = svc.delete_agent(existing.agent_id, instance=inst)
    return _s.DeleteSkillOrAgentResponse(
        deleted_id=removed.agent_id,
        detached_from_agent_ids=[],
        unlinked_draft_packs=unlinked,
        trace_id=trace_id,
    )


@router.post(
    "/agents/{agent_id}/execute",
    response_model=_s.ExecuteAgentResponse,
    responses=PROBLEM_RESPONSES,
)
async def execute_agent_endpoint(
    payload: _s.ExecuteAgentRequest,
    request: Request,
    svc: AgentsAndSkillsSvcDep,
    llm_port: Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)],
    agent_id: IdPath,
    persona_key: PersonaQuery = None,
) -> _s.ExecuteAgentResponse:
    _h.enforce_not_observer(request, persona_key)
    await _h.sync_from_postgres18_if_enabled(request, svc)
    agent = svc.get_agent(agent_id, instance=str(request.url.path))
    try:
        live_reply = await _h.complete_optional_live_turn(
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
            await _h.run_pg_persistence(
                request, lambda eng: persist_agent_to_postgres18(eng, failed_agent)
            )
        raise
    validated_agent = svc.get_agent(agent_id, instance=str(request.url.path))
    await _h.run_pg_persistence(
        request, lambda eng: persist_agent_to_postgres18(eng, validated_agent)
    )
    return _s.ExecuteAgentResponse(
        agent_id=outcome.agent_id,
        agent_name=outcome.agent_name,
        agent_handle=outcome.agent_handle,
        thinking_level=outcome.thinking_level,
        prompt=outcome.prompt,
        response_text=outcome.response_text,
        invoked_skills=[
            _s.InvokedSkillTraceResponseItem(**asdict(inv)) for inv in outcome.invoked_skills
        ],
        status=outcome.status,
        test_bench_status=outcome.test_bench_status,
        lifecycle_status=outcome.lifecycle_status,
        trace_id=_h.trace_id_for(request),
    )
