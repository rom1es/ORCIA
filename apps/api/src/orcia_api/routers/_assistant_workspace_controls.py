"""3-Speed Turn Controls (`/active-turn`, `/stop`, `/feedback`, `/invalidate-cache`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from orcia_api.dependencies import get_assistant_three_speed_router_service
from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers._assistant_workspace_context import to_active_turn_response
from orcia_api.routers.assistant_llm_bridge import (
    get_active_turn_for_workspace,
    record_prompt_telemetry_entry,
    stop_active_turn_for_workspace,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    ActiveBackgroundTurnStatusResponse,
    InvalidatePromptCacheRequest,
    InvalidatePromptCacheResponse,
    RecordAssistantTurnFeedbackRequest,
    StopActiveBackgroundTurnRequest,
)
from orcia_core.orchestration.assistant_three_speed_router import AssistantThreeSpeedRouterService
from orcia_core.permissions.models import UserIdentity

controls_router = APIRouter()
CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
ThreeSpeedRouterDep = Annotated[
    AssistantThreeSpeedRouterService, Depends(get_assistant_three_speed_router_service)
]


@controls_router.get("/three-speed/active-turn", response_model=ActiveBackgroundTurnStatusResponse)
async def get_active_three_speed_turn_endpoint(
    workspace_id: str,
    request: Request,
    user: CurrentUserDep,
) -> ActiveBackgroundTurnStatusResponse:
    """Return the active or recently completed background turn for `(workspace_id, user_id)`."""
    await enforce_assistant_workspace_guard(request, user, workspace_id, require_write=False)
    state = await get_active_turn_for_workspace(workspace_id, request=request, user_id=user.id)
    if state is None:
        return ActiveBackgroundTurnStatusResponse(workspace_id=workspace_id, status="IDLE")
    return to_active_turn_response(state)


@controls_router.post("/three-speed/stop", response_model=ActiveBackgroundTurnStatusResponse)
async def stop_active_three_speed_turn_endpoint(
    payload: StopActiveBackgroundTurnRequest,
    request: Request,
    user: CurrentUserDep,
) -> ActiveBackgroundTurnStatusResponse:
    """Explicitly cancel the active background LLM task via Redis stop propagation."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    state = await stop_active_turn_for_workspace(
        payload.workspace_id, request=request, user_id=user.id, turn_id=payload.turn_id
    )
    if state is None:
        return ActiveBackgroundTurnStatusResponse(
            workspace_id=payload.workspace_id, status="STOPPED"
        )
    return to_active_turn_response(state)


@controls_router.post("/three-speed/feedback")
async def record_assistant_turn_feedback_endpoint(
    payload: RecordAssistantTurnFeedbackRequest,
    request: Request,
    user: CurrentUserDep,
) -> dict[str, object]:
    """Record user `LIKE` or `DISLIKE` feedback on a prompt telemetry entry."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    return record_prompt_telemetry_entry(
        workspace_id=payload.workspace_id,
        turn_id=payload.turn_id,
        user_prompt=payload.user_prompt,
        assembled_system_prompt=payload.assembled_system_prompt,
        assistant_reply=payload.assistant_reply,
        thinking_text=payload.thinking_text,
        user_feedback=payload.user_feedback,
    )


@controls_router.post("/three-speed/invalidate-cache", response_model=InvalidatePromptCacheResponse)
async def invalidate_prompt_cache_endpoint(
    payload: InvalidatePromptCacheRequest,
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> InvalidatePromptCacheResponse:
    """Invalidate 5-layer prompt cache (`SETTINGS_CHANGED` / `OVERRIDE_UPDATED`)."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    outcome = router_svc.invalidate_prompt_cache(
        workspace_id=payload.workspace_id, reason=payload.reason, user_id=payload.user_id
    )
    return InvalidatePromptCacheResponse(
        workspace_id=outcome.workspace_id,
        reason=outcome.reason,
        invalidated_keys_count=outcome.invalidated_keys_count,
        outbox_event_id=outcome.outbox_event_id,
    )
