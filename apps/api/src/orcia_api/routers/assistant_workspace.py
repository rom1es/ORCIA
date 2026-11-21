"""Epic 10 Router — `Mon Assistant` All-in-One (`Stories 10.1..10.4`, `Story 26.1`)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import (
    get_assistant_three_speed_router_service,
    get_llm_streaming_port,
    get_optional_embedding_port,
)
from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers._assistant_workspace_context import (
    record_non_stream_turn_telemetry,
    resolve_effective_speed,
    resolve_folder_notes,
    resolve_turn_history,
)
from orcia_api.routers._assistant_workspace_controls import controls_router
from orcia_api.routers.assistant_llm_bridge import (
    ensure_active_chat_model_if_live,
    invoke_configured_llm_for_assistant_turn,
    resolve_assembled_system_instructions_for_turn,
    resolve_request_locale,
    stream_configured_llm_for_assistant_turn,
)
from orcia_api.routers.assistant_workspace_citations import router as citations_router
from orcia_api.routers.assistant_workspace_folders import router as folders_router
from orcia_api.routers.assistant_workspace_governance import router as governance_router
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.assistant import (
    ThreeSpeedStepProgressSchemaItem,
    ThreeSpeedTurnRequest,
    ThreeSpeedTurnResponse,
)
from orcia_core.orchestration.assistant_prompt_builder import resolve_default_hat
from orcia_core.orchestration.assistant_three_speed_router import AssistantThreeSpeedRouterService
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.ports.llm_streaming_port import LlmStreamingPort

router = APIRouter(
    prefix="/api/v1/assistant",
    tags=["assistant-workspace"],
    responses=PROBLEM_RESPONSES,
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
ThreeSpeedRouterDep = Annotated[
    AssistantThreeSpeedRouterService, Depends(get_assistant_three_speed_router_service)
]
LlmStreamingPortDep = Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)]


@router.post("/three-speed/turn", response_model=ThreeSpeedTurnResponse)
async def execute_three_speed_turn_endpoint(
    payload: ThreeSpeedTurnRequest,
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    llm_port: LlmStreamingPortDep,
) -> ThreeSpeedTurnResponse:
    """Execute a 3-Speed conversational turn (`Rapide`, `@Agent / /Skill`, `Approfondi`)."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    await ensure_active_chat_model_if_live(
        request, requested_tier=payload.requested_tier, workspace_id=payload.workspace_id
    )
    effective_deep_audit, effective_speed, resolved_speed = resolve_effective_speed(payload)
    resolved_notes = await resolve_folder_notes(request, payload, user=user)
    active_hat = resolve_default_hat(explicit_hat=payload.hat, user=user)
    history = await resolve_turn_history(request, payload, user=user)
    live_outcome = await invoke_configured_llm_for_assistant_turn(
        request,
        user_prompt=payload.user_prompt,
        hat=active_hat,
        speed_mode=resolved_speed,
        workspace_id=payload.workspace_id,
        user_id=user.id,
        requested_tier=payload.requested_tier,
        thinking_effort=payload.thinking_effort,
        conversation_history=history,
        response_tone=payload.response_tone,
        response_format=payload.response_format,
        personal_instructions=payload.personal_instructions,
        workspace_instructions=payload.workspace_instructions,
        folder_pinned_notes=resolved_notes,
        locale=payload.locale,
        llm_port=llm_port,
    )
    assembled_sys_prompt = (
        live_outcome.assembled_system_prompt
        if live_outcome is not None and live_outcome.assembled_system_prompt
        else resolve_assembled_system_instructions_for_turn(
            request,
            hat=active_hat,
            speed_mode=resolved_speed,
            workspace_id=payload.workspace_id,
            user_id=user.id,
            requested_tier=payload.requested_tier,
            thinking_effort=payload.thinking_effort,
            response_tone=payload.response_tone,
            response_format=payload.response_format,
            personal_instructions=payload.personal_instructions,
            workspace_instructions=payload.workspace_instructions,
            folder_pinned_notes=resolved_notes,
            locale=resolve_request_locale(request, payload.locale),
        )
    )
    turn = router_svc.execute_three_speed_turn(
        user,
        workspace_id=payload.workspace_id,
        user_prompt=payload.user_prompt,
        hat=payload.hat,
        requested_speed=effective_speed,
        deep_audit_pill_active=effective_deep_audit,
        llm_response_override=live_outcome.response_text if live_outcome is not None else None,
        llm_step_label_override=live_outcome.step_label if live_outcome is not None else None,
        llm_latency_ms_override=live_outcome.latency_ms if live_outcome is not None else None,
        llm_thinking_override=live_outcome.thinking_text if live_outcome is not None else None,
    )
    await record_non_stream_turn_telemetry(
        request,
        user=user,
        payload=payload,
        turn=turn,
        live_outcome=live_outcome,
        assembled_sys_prompt=assembled_sys_prompt,
        history_count=len(history),
        resolved_notes=resolved_notes,
    )
    return ThreeSpeedTurnResponse(
        turn_id=turn.turn_id,
        workspace_id=turn.workspace_id,
        user_id=turn.user_id,
        hat=turn.hat,
        speed_mode=turn.speed_mode,
        cache_key=turn.cache_key,
        cache_hit=turn.cache_hit,
        cache_lookup_ms=turn.cache_lookup_ms,
        nodes_1_to_4_deterministic_ms=turn.nodes_1_to_4_deterministic_ms,
        ttft_ms=turn.ttft_ms,
        intermediate_llm_calls=turn.intermediate_llm_calls,
        invoked_targets=list(turn.invoked_targets),
        step_progress=[
            ThreeSpeedStepProgressSchemaItem(
                step_code=st.step_code,
                label=st.label,
                duration_ms=st.duration_ms,
                status=st.status,
                connector_or_lens=st.connector_or_lens,
                intermediate_output=st.intermediate_output,
            )
            for st in turn.step_progress
        ],
        response_text=turn.response_text,
        assembled_prompt_sha256=turn.assembled_prompt_sha256,
        assembled_system_prompt=assembled_sys_prompt,
        deep_audit_lenses=list(turn.deep_audit_lenses),
    )


@router.post(
    "/three-speed/stream",
    responses={
        200: {
            "description": "Server-Sent Events stream (`text/event-stream`).",
            "content": {"text/event-stream": {"schema": {"type": "object"}}},
        }
    },
)
async def stream_three_speed_turn_endpoint(
    payload: ThreeSpeedTurnRequest,
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    llm_port: LlmStreamingPortDep,
) -> StreamingResponse:
    """Stream SSE events (`cache_status`, `step_progress`, `thinking_delta`, `token_delta`)."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    await ensure_active_chat_model_if_live(
        request, requested_tier=payload.requested_tier, workspace_id=payload.workspace_id
    )
    effective_deep_audit, effective_speed, resolved_speed = resolve_effective_speed(payload)
    active_hat = resolve_default_hat(explicit_hat=payload.hat, user=user)
    history = await resolve_turn_history(request, payload, user=user)
    resolved_notes = await resolve_folder_notes(request, payload, user=user)

    async def _event_generator() -> AsyncIterator[str]:
        for evt in router_svc.stream_three_speed_turn_sse(
            user,
            workspace_id=payload.workspace_id,
            user_prompt=payload.user_prompt,
            hat=payload.hat,
            requested_speed=effective_speed,
            deep_audit_pill_active=effective_deep_audit,
        ):
            event_name = evt["event"]
            yield f"event: {event_name}\ndata: {json.dumps(evt['data'], ensure_ascii=False)}\n\n"
            if event_name == "token":
                token_data = evt["data"]
                full_txt = str(token_data.get("text") or "") if isinstance(token_data, dict) else ""
                async for stream_evt in stream_configured_llm_for_assistant_turn(
                    request,
                    user_prompt=payload.user_prompt,
                    hat=active_hat,
                    speed_mode=resolved_speed,
                    workspace_id=payload.workspace_id,
                    user_id=user.id,
                    requested_tier=payload.requested_tier,
                    thinking_effort=payload.thinking_effort,
                    conversation_history=history,
                    response_tone=payload.response_tone,
                    response_format=payload.response_format,
                    personal_instructions=payload.personal_instructions,
                    workspace_instructions=payload.workspace_instructions,
                    folder_pinned_notes=resolved_notes,
                    locale=payload.locale,
                    fallback_response_text=full_txt,
                    user_email=user.email,
                    user_display_name=user.display_name,
                    llm_port=llm_port,
                ):
                    if stream_evt["event"] in (
                        "thinking_delta",
                        "token_delta",
                        "turn_completed",
                        "stream_error",
                    ):
                        s_name = stream_evt["event"]
                        s_json = json.dumps(stream_evt["data"], ensure_ascii=False)
                        yield f"event: {s_name}\ndata: {s_json}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


router.include_router(controls_router)
router.include_router(governance_router)
router.include_router(citations_router)
router.include_router(folders_router)
