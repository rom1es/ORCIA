"""Canonical v2 Redis-Backed Assistant Turn Endpoints (`POST /turns`, `/stream`, `/stop`)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import get_llm_streaming_port, get_optional_embedding_port
from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers._assistant_background_registry import (
    get_rate_limiter_from_request,
    get_tracked_turn_tasks_from_request,
    get_turn_registry_from_request,
    turn_record_to_background_state,
)
from orcia_api.routers._assistant_turn_consumer import stream_assistant_turn_events
from orcia_api.routers._assistant_usage_telemetry import resolve_audit_ledger_sink
from orcia_api.routers._assistant_workspace_context import (
    resolve_effective_speed,
    resolve_folder_notes,
    resolve_turn_history,
    to_active_turn_response,
)
from orcia_api.routers.assistant_background_turns import (
    start_background_assistant_turn,
    stop_assistant_turn_by_id,
)
from orcia_api.routers.assistant_llm_bridge import (
    ensure_active_chat_model_if_live,
    resolve_assembled_system_instructions_for_turn,
    resolve_configured_llm_endpoint,
    resolve_request_locale,
)
from orcia_api.routers.assistant_llm_prompts import (
    build_multi_turn_messages,
    build_workspace_tools_schema,
    detect_adaptive_thinking_steps_for_question,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    ActiveBackgroundTurnStatusResponse,
    AssistantActiveTurnsListResponse,
    AssistantTurnAcceptedResponse,
    ThreeSpeedTurnRequest,
)
from orcia_core.orchestration.assistant_prompt_builder import resolve_default_hat
from orcia_core.orchestration.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.ports.llm_streaming_port import LlmStreamingPort

turns_v2_router = APIRouter()
CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
LlmStreamingPortDep = Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)]


@turns_v2_router.post("/turns", status_code=202, response_model=AssistantTurnAcceptedResponse)
async def create_assistant_turn_v2_endpoint(
    payload: ThreeSpeedTurnRequest,
    request: Request,
    user: CurrentUserDep,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    llm_port: LlmStreamingPortDep,
) -> AssistantTurnAcceptedResponse:
    """Validate guards & rate limits, launch tracked background turn, return `202` + `turn_id`."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    await ensure_active_chat_model_if_live(
        request, requested_tier=payload.requested_tier, workspace_id=payload.workspace_id
    )
    _, _, resolved_speed = resolve_effective_speed(payload)
    active_hat = resolve_default_hat(explicit_hat=payload.hat, user=user)
    history = await resolve_turn_history(request, payload, user=user)
    resolved_notes = await resolve_folder_notes(request, payload, user=user)
    resolved_locale = resolve_request_locale(request, payload.locale)
    ep = await resolve_configured_llm_endpoint(
        request, requested_tier=payload.requested_tier, workspace_id=payload.workspace_id
    )
    system_msg = resolve_assembled_system_instructions_for_turn(
        request,
        hat=active_hat,
        speed_mode=resolved_speed,
        workspace_id=payload.workspace_id,
        user_id=user.id,
        requested_tier=payload.requested_tier or (ep.tier if ep is not None else "medium"),
        thinking_effort=payload.thinking_effort,
        response_tone=payload.response_tone,
        response_format=payload.response_format,
        personal_instructions=payload.personal_instructions,
        workspace_instructions=payload.workspace_instructions,
        folder_pinned_notes=resolved_notes,
        locale=resolved_locale,
    )
    default_thinking = " · ".join(
        f"{t}: {s}"
        for t, s in detect_adaptive_thinking_steps_for_question(
            payload.user_prompt, locale=resolved_locale
        )
    )
    trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or "")
    turn_id = await start_background_assistant_turn(
        registry=get_turn_registry_from_request(request),
        rate_limiter=get_rate_limiter_from_request(request),
        task_set=get_tracked_turn_tasks_from_request(request),
        workspace_id=payload.workspace_id,
        user_id=user.id,
        user_prompt=payload.user_prompt,
        system_msg=system_msg,
        default_thinking=default_thinking,
        fallback_response_text=None,
        ep=ep,
        llm_port=llm_port,
        http_client_getter=lambda: request.app.state.http_client,
        messages_builder=lambda: build_multi_turn_messages(
            system_msg=system_msg, user_prompt=payload.user_prompt, conversation_history=history
        ),
        tools_builder=lambda: build_workspace_tools_schema(request, resolved_speed),
        conversation_history_count=len(history),
        folder_pinned_notes=resolved_notes,
        thinking_effort=payload.thinking_effort,
        user_email=user.email,
        user_display_name=user.display_name,
        model_tier=payload.requested_tier or (ep.tier if ep is not None else "medium"),
        audit_ledger_sink=resolve_audit_ledger_sink(request),
        trace_id=trace_id,
        speed_mode=resolved_speed,
        locale=resolved_locale,
        instance=str(request.url.path),
    )
    return AssistantTurnAcceptedResponse(
        turn_id=turn_id,
        workspace_id=payload.workspace_id,
        thread_id=payload.thread_id,
        speed_mode=resolved_speed,
        status="RUNNING",
        stream_url=f"/api/v1/assistant/turns/{turn_id}/stream",
        trace_id=trace_id,
    )


@turns_v2_router.get("/turns/active", response_model=AssistantActiveTurnsListResponse)
async def list_active_assistant_turns_v2_endpoint(
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


@turns_v2_router.get(
    "/turns/{turn_id}/stream",
    responses={
        200: {
            "description": "Cursor-reattachable Redis Streams SSE stream (`text/event-stream`).",
            "content": {"text/event-stream": {"schema": {"type": "object"}}},
        }
    },
)
async def stream_assistant_turn_v2_endpoint(
    turn_id: str,
    request: Request,
    user: CurrentUserDep,
    after: str | None = Query(default=None),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Replay and live-tail Redis Streams entries strictly after `after` cursor."""
    reg = get_turn_registry_from_request(request)
    rec = await reg.get_turn_by_id(turn_id)
    if rec is None:
        raise ResourceNotFoundError(
            detail_override=f"Turn '{turn_id}' not found.", instance=str(request.url.path)
        )
    await enforce_assistant_workspace_guard(request, user, rec.workspace_id, require_write=False)
    if rec.user_id != user.id:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    cursor = (after or last_event_id or "0-0").strip() or "0-0"
    trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or rec.trace_id)
    locale = resolve_request_locale(request, None)

    async def _sse() -> AsyncIterator[str]:
        async for evt in stream_assistant_turn_events(
            reg,
            turn_id=turn_id,
            after_cursor=cursor,
            trace_id=trace_id,
            instance=str(request.url.path),
            locale=locale,
        ):
            c_id = evt.get("cursor") or ""
            ev_name = evt["event"]
            data_json = json.dumps(evt["data"], ensure_ascii=False)
            yield f"id: {c_id}\nevent: {ev_name}\ndata: {data_json}\n\n"

    return StreamingResponse(_sse(), media_type="text/event-stream")


@turns_v2_router.post("/turns/{turn_id}/stop", response_model=ActiveBackgroundTurnStatusResponse)
async def stop_assistant_turn_v2_endpoint(
    turn_id: str,
    request: Request,
    user: CurrentUserDep,
) -> ActiveBackgroundTurnStatusResponse:
    """Propagate cross-worker `stop` via Redis and flush partial FinOps in `finally`."""
    reg = get_turn_registry_from_request(request)
    rec = await reg.get_turn_by_id(turn_id)
    if rec is None:
        raise ResourceNotFoundError(
            detail_override=f"Turn '{turn_id}' not found.", instance=str(request.url.path)
        )
    await enforce_assistant_workspace_guard(request, user, rec.workspace_id, require_write=True)
    if rec.user_id != user.id:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    state = await stop_assistant_turn_by_id(turn_id, request=request, stopped_by_user_id=user.id)
    assert state is not None
    return to_active_turn_response(state)
