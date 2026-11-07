"""Epic 10 Router — `Mon Assistant` All-in-One (`Stories 10.1..10.4`)."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import (
    get_assistant_folders_and_sharing_service,
    get_assistant_three_speed_router_service,
)
from orcia_api.routers.assistant_llm_bridge import (
    invoke_configured_llm_for_assistant_turn,
    stream_configured_llm_for_assistant_turn,
)
from orcia_api.routers.assistant_workspace_citations import router as citations_router
from orcia_api.routers.assistant_workspace_folders import router as folders_router
from orcia_api.routers.assistant_workspace_governance import router as governance_router
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    InvalidatePromptCacheRequest,
    InvalidatePromptCacheResponse,
    ThreeSpeedStepProgressSchemaItem,
    ThreeSpeedTurnRequest,
    ThreeSpeedTurnResponse,
)
from orcia_core.orchestration.assistant_three_speed_router import (
    AssistantSpeedMode,
    AssistantThreeSpeedRouterService,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant-workspace"])

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
ThreeSpeedRouterDep = Annotated[
    AssistantThreeSpeedRouterService, Depends(get_assistant_three_speed_router_service)
]
_SPEED2_MENTION_OR_SLASH_RE = re.compile(r"(?:^|\s)(?:@[a-zA-Z0-9_-]{2,}|/[a-zA-Z0-9_-]{2,})")


def _resolve_turn_history(request: Request, payload: ThreeSpeedTurnRequest) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = [
        {"role": m.role, "content": m.content, "name": m.name, "tool_call_id": m.tool_call_id}
        for m in payload.conversation_history
    ]
    if payload.thread_id and not history:
        try:
            folders_svc = get_assistant_folders_and_sharing_service(request)
            overview = folders_svc.get_workspace_overview(workspace_id=payload.workspace_id)
            for t in overview.threads:
                if t.thread_id == payload.thread_id and t.thread_summary:
                    for part in t.thread_summary.split(" | "):
                        if part.strip():
                            history.append({"role": "user", "content": part.strip()})
        except Exception as exc:
            from orcia_core.observability.logging import get_logger

            get_logger("orcia.assistant.llm").warning(
                "assistant_thread_history_resolution_fallback", error_type=type(exc).__name__
            )
    return history


def _resolve_effective_speed(
    payload: ThreeSpeedTurnRequest,
) -> tuple[bool, AssistantSpeedMode | None, AssistantSpeedMode]:
    effective_deep_audit = payload.deep_audit_pill_active or payload.thinking_effort == "deep"
    effective_speed: AssistantSpeedMode | None = payload.requested_speed or (
        "SPEED_3_DEEP_AUDIT"
        if effective_deep_audit
        else "SPEED_2_AGENT_TOOLS"
        if payload.thinking_effort == "balanced"
        else None
    )
    resolved_for_llm: AssistantSpeedMode = effective_speed or (
        "SPEED_2_AGENT_TOOLS"
        if _SPEED2_MENTION_OR_SLASH_RE.search(payload.user_prompt or "")
        else "SPEED_1_FAST"
    )
    return effective_deep_audit, effective_speed, resolved_for_llm


@router.post("/three-speed/turn", response_model=ThreeSpeedTurnResponse)
async def execute_three_speed_turn_endpoint(
    payload: ThreeSpeedTurnRequest,
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> ThreeSpeedTurnResponse:
    """Execute a 3-Speed conversational turn (`⚡ Rapide`, `@Agent / /Skill`, `🧠 Approfondi`)."""
    effective_deep_audit, effective_speed, resolved_speed = _resolve_effective_speed(payload)
    live_outcome = await invoke_configured_llm_for_assistant_turn(
        request,
        user_prompt=payload.user_prompt,
        hat=payload.hat or user.human_profile_archetype or "PLATFORM_ADMIN",
        speed_mode=resolved_speed,
        workspace_id=payload.workspace_id,
        user_id=user.id,
        requested_tier=payload.requested_tier,
        thinking_effort=payload.thinking_effort,
        conversation_history=_resolve_turn_history(request, payload),
        locale=payload.locale,
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
        deep_audit_lenses=list(turn.deep_audit_lenses),
    )


@router.post("/three-speed/stream")
async def stream_three_speed_turn_endpoint(
    payload: ThreeSpeedTurnRequest,
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> StreamingResponse:
    """Stream SSE events (`cache_status`, `step_progress`, `thinking_delta`, `token_delta`)."""
    effective_deep_audit, effective_speed, resolved_speed = _resolve_effective_speed(payload)
    active_hat = payload.hat or user.human_profile_archetype or "PLATFORM_ADMIN"
    history = _resolve_turn_history(request, payload)

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
            if event_name == "step_progress":
                step_data = evt["data"]
                if isinstance(step_data, dict) and step_data.get("intermediate_output"):
                    think_json = json.dumps(
                        {
                            "step_code": step_data.get("step_code"),
                            "thinking_text": step_data.get("intermediate_output"),
                        },
                        ensure_ascii=False,
                    )
                    yield f"event: thinking_delta\ndata: {think_json}\n\n"
            elif event_name == "token":
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
                    locale=payload.locale,
                    fallback_response_text=full_txt,
                ):
                    if stream_evt["event"] in ("thinking_delta", "token_delta", "turn_completed"):
                        s_name = stream_evt["event"]
                        s_json = json.dumps(stream_evt["data"], ensure_ascii=False)
                        yield f"event: {s_name}\ndata: {s_json}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


@router.post("/three-speed/invalidate-cache", response_model=InvalidatePromptCacheResponse)
def invalidate_prompt_cache_endpoint(
    payload: InvalidatePromptCacheRequest,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> InvalidatePromptCacheResponse:
    """Invalidate Redis 5-layer prompt cache (`SETTINGS_CHANGED` / `OVERRIDE_UPDATED`)."""
    outcome = router_svc.invalidate_prompt_cache(
        workspace_id=payload.workspace_id, reason=payload.reason, user_id=payload.user_id
    )
    return InvalidatePromptCacheResponse(
        workspace_id=outcome.workspace_id,
        reason=outcome.reason,
        invalidated_keys_count=outcome.invalidated_keys_count,
        outbox_event_id=outcome.outbox_event_id,
    )


router.include_router(governance_router)
router.include_router(citations_router)
router.include_router(folders_router)
