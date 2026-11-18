"""Context & response helpers extracted from `assistant_workspace.py` (`<= 350 L`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.dependencies import get_assistant_folders_and_sharing_service
from orcia_api.routers._assistant_usage_telemetry import (
    persist_assistant_turn_ledger_entry,
    resolve_audit_ledger_sink,
    resolve_usage_with_fallback,
)
from orcia_api.routers.assistant_background_turns import (
    ActiveBackgroundTurnState,
    record_prompt_telemetry_entry,
)
from orcia_api.schemas.assistant import (
    ActiveBackgroundTurnStatusResponse,
    ThreeSpeedTurnRequest,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.models import UserIdentity

logger = get_logger("orcia.assistant.llm")


def resolve_turn_history(request: Request, payload: ThreeSpeedTurnRequest) -> list[dict[str, Any]]:
    """Build multi-turn conversation history, hydrating from thread summary if empty."""
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
            logger.warning(
                "assistant_thread_history_resolution_fallback",
                error_type=type(exc).__name__,
            )
    return history


def resolve_folder_notes(request: Request, payload: ThreeSpeedTurnRequest) -> str | None:
    """Resolve pinned folder notes from payload or persisted folder state."""
    if payload.folder_pinned_notes and payload.folder_pinned_notes.strip():
        return payload.folder_pinned_notes.strip()
    if payload.folder_id:
        try:
            folders_svc = get_assistant_folders_and_sharing_service(request)
            overview = folders_svc.get_workspace_overview(workspace_id=payload.workspace_id)
            for f in overview.folders:
                if f.folder_id == payload.folder_id and f.pinned_notes_markdown.strip():
                    return f.pinned_notes_markdown.strip()
        except Exception as exc:
            logger.warning(
                "assistant_folder_notes_resolution_fallback",
                error_type=type(exc).__name__,
            )
    return None


def to_active_turn_response(
    state: ActiveBackgroundTurnState,
) -> ActiveBackgroundTurnStatusResponse:
    """Serialize `ActiveBackgroundTurnState` to API response schema."""
    return ActiveBackgroundTurnStatusResponse(
        workspace_id=state.workspace_id,
        turn_id=state.turn_id,
        status=state.status,
        user_prompt=state.user_prompt,
        thinking_text=state.thinking_text,
        streamed_text=state.streamed_text,
        assembled_system_prompt=state.assembled_system_prompt,
        started_at_ms=state.started_at_ms,
        elapsed_ms=state.elapsed_ms,
        error_message=state.error_message,
    )


async def record_non_stream_turn_telemetry(
    request: Request,
    *,
    user: UserIdentity,
    payload: ThreeSpeedTurnRequest,
    turn: Any,
    live_outcome: Any | None,
    assembled_sys_prompt: str,
    history_count: int,
    resolved_notes: str | None,
) -> None:
    """Record prompt telemetry and `ASSISTANT_TURN_COMPLETED` audit ledger entry."""
    record_prompt_telemetry_entry(
        workspace_id=turn.workspace_id,
        turn_id=turn.turn_id,
        user_prompt=payload.user_prompt,
        assembled_system_prompt=assembled_sys_prompt,
        conversation_history_count=history_count,
        folder_pinned_notes=resolved_notes,
        thinking_text=(
            live_outcome.thinking_text if live_outcome and live_outcome.thinking_text else ""
        ),
        assistant_reply=turn.response_text,
        thinking_effort=payload.thinking_effort or "balanced",
    )
    in_tok, out_tok, u_src = (
        (live_outcome.input_tokens, live_outcome.output_tokens, live_outcome.usage_source)
        if live_outcome is not None
        and (live_outcome.input_tokens > 0 or live_outcome.output_tokens > 0)
        else resolve_usage_with_fallback(
            prompt_text=f"{assembled_sys_prompt}\n{payload.user_prompt}",
            reply_text=turn.response_text,
        )
    )
    await persist_assistant_turn_ledger_entry(
        audit_ledger_sink=resolve_audit_ledger_sink(request),
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        workspace_id=turn.workspace_id,
        turn_id=turn.turn_id,
        model_id=(
            live_outcome.model_id if live_outcome and live_outcome.model_id else "assistant-router"
        ),
        inference_tier=live_outcome.inference_tier if live_outcome else payload.requested_tier,
        effort=live_outcome.effort if live_outcome else payload.thinking_effort,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=live_outcome.latency_ms if live_outcome else turn.ttft_ms,
        usage_source=u_src,
        trace_id=getattr(getattr(request, "state", None), "trace_id", None),
        speed_mode=turn.speed_mode,
        invoked_targets=(
            live_outcome.invoked_tool_names if live_outcome else tuple(turn.invoked_targets)
        ),
    )
