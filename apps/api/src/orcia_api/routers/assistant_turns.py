"""Canonical Unified Assistant Turn Router (`/api/v1/assistant/turns*`, `AD-25`, `Story 26.7`)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse

import orcia_api.routers._assistant_context_assembly as _ctx_asm
import orcia_api.routers._assistant_turn_consumer as _turn_consumer
from orcia_api.dependencies import (
    get_assistant_thread_messages_repository,
    get_assistant_turn_engine,
    get_llm_streaming_port,
    get_optional_embedding_port,
)
from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers._agents_lifecycle_guards import enforce_active_agents_for_assistant_prompt
from orcia_api.routers._assistant_background_registry import (
    get_rate_limiter_from_request,
    get_thread_turn_lock_from_request,
    get_tracked_turn_tasks_from_request,
    get_turn_registry_from_request,
    turn_record_to_background_state,
)
from orcia_api.routers._assistant_thread_messages_routes import thread_messages_router
from orcia_api.routers._assistant_turn_controls_routes import (
    controls_router,
    require_owned_assistant_turn,
)
from orcia_api.routers._assistant_usage_telemetry import (
    resolve_assistant_outbox_emitter,
    resolve_audit_ledger_sink,
)
from orcia_api.routers._assistant_workspace_context import (
    resolve_effective_speed,
    resolve_folder_notes,
    resolve_turn_history,
    to_active_turn_response,
)
from orcia_api.routers.assistant_background_turns import start_background_assistant_turn
from orcia_api.routers.assistant_llm_bridge import (
    ensure_active_chat_model_if_live,
    resolve_configured_llm_endpoint,
    resolve_request_locale,
)
from orcia_api.routers.assistant_llm_prompts import (
    build_multi_turn_messages,
    detect_adaptive_thinking_steps_for_question,
    resolve_turn_tools_and_router_async,
)
from orcia_api.routers.assistant_workspace_folders import router as folders_router
from orcia_api.routers.assistant_workspace_governance import router as governance_router
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.assistant import (
    AssistantActiveTurnsListResponse,
    AssistantTurnAcceptedResponse,
    AssistantTurnCreateRequest,
)
from orcia_core.orchestration.assistant_prompt_builder import resolve_default_hat
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.ports.llm_streaming_port import LlmStreamingPort

router = APIRouter(
    prefix="/api/v1/assistant",
    tags=["assistant-turns"],
    responses=PROBLEM_RESPONSES,
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
TurnEngineDep = Annotated[AssistantTurnEngine, Depends(get_assistant_turn_engine)]
LlmStreamingPortDep = Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)]


@router.post("/turns", status_code=202, response_model=AssistantTurnAcceptedResponse)
async def create_assistant_turn_endpoint(
    payload: AssistantTurnCreateRequest,
    request: Request,
    user: CurrentUserDep,
    turn_engine: TurnEngineDep,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    llm_port: LlmStreamingPortDep,
) -> AssistantTurnAcceptedResponse:
    """Converged N1-N6 turn entry point (`Speed 1` & `Speed 2/3`) returning `202` + `turn_id`."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    await enforce_active_agents_for_assistant_prompt(request, payload.user_prompt)
    effective_deep, effective_speed, resolved_speed = resolve_effective_speed(payload)
    await ensure_active_chat_model_if_live(
        request,
        requested_tier=payload.requested_tier,
        workspace_id=payload.workspace_id,
        speed_mode=resolved_speed,
    )
    thread_lock = get_thread_turn_lock_from_request(request) if payload.thread_id else None
    thread_lock_token: str | None = None
    if thread_lock is not None and payload.thread_id:
        _, thread_lock_token = await thread_lock.acquire_async(
            thread_id=payload.thread_id, user_id=user.id, ttl_seconds=300
        )
    try:
        active_hat = resolve_default_hat(explicit_hat=payload.hat, user=user)
        resolved_locale = resolve_request_locale(request, payload.locale)
        history, resolved_notes, ep, turn_ctx = await asyncio.gather(
            resolve_turn_history(request, payload, user=user),
            resolve_folder_notes(request, payload, user=user),
            resolve_configured_llm_endpoint(
                request, requested_tier=payload.requested_tier, workspace_id=payload.workspace_id
            ),
            _ctx_asm.assemble_real_workspace_context_for_turn_async(
                request,
                workspace_id=payload.workspace_id,
                user_id=user.id,
                hat=active_hat,
                user_prompt=payload.user_prompt,
                user=user,
                embedding_port=_embedding_port,
                locale=resolved_locale,
            ),
        )
        tier_eff = payload.requested_tier or (ep.tier if ep is not None else "medium")
        plan = await turn_engine.n2_plan_and_assemble_async(
            user,
            workspace_id=payload.workspace_id,
            user_prompt=payload.user_prompt,
            hat=active_hat,
            requested_speed=effective_speed or resolved_speed,
            deep_audit_pill_active=effective_deep,
            thinking_effort=payload.thinking_effort,
            requested_tier=tier_eff,
            endpoint=ep,
            ontology_concepts_summary=turn_ctx.ontology_summary,
            federated_evidence_summary=turn_ctx.federated_evidence_summary,
            response_tone=(
                payload.response_tone
                if payload.response_tone is not None
                else turn_ctx.response_tone
            ),
            response_format=(
                payload.response_format
                if payload.response_format is not None
                else turn_ctx.response_format
            ),
            personal_instructions=(
                payload.personal_instructions
                if payload.personal_instructions is not None
                else turn_ctx.personal_instructions
            ),
            workspace_instructions=(
                payload.workspace_instructions
                if payload.workspace_instructions is not None
                else turn_ctx.workspace_instructions
            ),
            folder_pinned_notes=resolved_notes,
            assembled_5_layers_prompt=turn_ctx.assembled_5_layers_prompt,
            base_assembly_latency_ms=turn_ctx.assembly_latency_ms,
            locale=resolved_locale,
            instance=str(request.url.path),
            has_evidence=turn_ctx.has_evidence,
            pack_key=turn_ctx.pack_key,
        )
        default_thinking = " · ".join(
            f"{t}: {s}"
            for t, s in detect_adaptive_thinking_steps_for_question(
                payload.user_prompt, locale=resolved_locale
            )
        )
        trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or "")
        max_budget = ep.max_tokens_budget if ep is not None else 8192
        tools_schema, tool_catalog, tool_router = await resolve_turn_tools_and_router_async(
            request,
            speed_mode=plan.speed_mode,
            tools_enabled=plan.supports_tools,
            user=user,
            workspace_id=payload.workspace_id,
            active_hat=plan.active_hat,
            embedding_port=_embedding_port,
        )
        turn_id = await start_background_assistant_turn(
            registry=get_turn_registry_from_request(request),
            rate_limiter=get_rate_limiter_from_request(request),
            task_set=get_tracked_turn_tasks_from_request(request),
            workspace_id=payload.workspace_id,
            user_id=user.id,
            user_prompt=payload.user_prompt,
            system_msg=plan.system_instructions,
            default_thinking=default_thinking,
            fallback_response_text=None,
            ep=ep,
            llm_port=llm_port,
            http_client_getter=lambda: request.app.state.http_client,
            messages_builder=lambda: build_multi_turn_messages(
                system_msg=plan.system_instructions,
                user_prompt=payload.user_prompt,
                conversation_history=history,
                max_tokens_budget=max_budget,
            ),
            tools_builder=lambda: list(tools_schema),
            conversation_history_count=len(history),
            folder_pinned_notes=resolved_notes,
            thinking_effort=payload.thinking_effort,
            user_email=user.email,
            user_display_name=user.display_name,
            model_tier=tier_eff,
            audit_ledger_sink=resolve_audit_ledger_sink(request),
            outbox_emitter=resolve_assistant_outbox_emitter(request),
            trace_id=trace_id,
            speed_mode=plan.speed_mode,
            locale=resolved_locale,
            instance=str(request.url.path),
            thread_id=payload.thread_id,
            parent_turn_id=payload.parent_turn_id,
            citation_map=turn_ctx.citation_map_dict,
            prompt_assembly_latency_ms=plan.assembly_latency_ms,
            thread_messages_repo=get_assistant_thread_messages_repository(request),
            tool_router=tool_router,
            tool_catalog=tool_catalog,
            user_identity=user,
            active_hat=plan.active_hat,
            turn_engine=turn_engine,
            base_evidence_table=turn_ctx.evidence_table,
            supports_tools=plan.supports_tools,
            thread_lock=thread_lock,
            thread_lock_token=thread_lock_token,
        )
    except Exception:
        if thread_lock is not None and payload.thread_id and thread_lock_token:
            await thread_lock.release_async(
                thread_id=payload.thread_id, user_id=user.id, token=thread_lock_token
            )
        raise
    return AssistantTurnAcceptedResponse(
        turn_id=turn_id,
        workspace_id=payload.workspace_id,
        thread_id=payload.thread_id,
        parent_turn_id=payload.parent_turn_id,
        speed_mode=plan.speed_mode,
        status="RUNNING",
        stream_url=f"/api/v1/assistant/turns/{turn_id}/stream",
        trace_id=trace_id,
    )


@router.get("/turns/active", response_model=AssistantActiveTurnsListResponse)
async def list_active_assistant_turns_endpoint(
    workspace_id: str,
    request: Request,
    user: CurrentUserDep,
) -> AssistantActiveTurnsListResponse:
    """List active or recent turns for `(workspace_id, user_id)` from Redis."""
    await enforce_assistant_workspace_guard(request, user, workspace_id, require_write=False)
    reg = get_turn_registry_from_request(request)
    records = await reg.list_active_turns(workspace_id, user.id)
    return AssistantActiveTurnsListResponse(
        workspace_id=workspace_id,
        turns=[to_active_turn_response(turn_record_to_background_state(r)) for r in records],
    )


@router.get("/turns/{turn_id}/stream", responses=_turn_consumer.SSE_STREAM_RESPONSES)
async def stream_assistant_turn_endpoint(
    turn_id: str,
    request: Request,
    user: CurrentUserDep,
    after: str | None = Query(default=None),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Replay and live-tail Redis Streams entries strictly after `after` cursor."""
    reg, rec = await require_owned_assistant_turn(turn_id, request, user, require_write=False)
    cursor = (after or last_event_id or "0-0").strip() or "0-0"
    trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or rec.trace_id)
    locale = resolve_request_locale(request, None)

    async def _sse() -> AsyncIterator[str]:
        async for evt in _turn_consumer.stream_assistant_turn_events(
            reg,
            turn_id=turn_id,
            after_cursor=cursor,
            trace_id=trace_id,
            instance=str(request.url.path),
            locale=locale,
        ):
            data_json = json.dumps(evt["data"], ensure_ascii=False)
            yield f"id: {evt.get('cursor') or ''}\nevent: {evt['event']}\ndata: {data_json}\n\n"

    return StreamingResponse(_sse(), media_type="text/event-stream")


router.include_router(controls_router)
router.include_router(thread_messages_router)
router.include_router(governance_router)
router.include_router(folders_router)
