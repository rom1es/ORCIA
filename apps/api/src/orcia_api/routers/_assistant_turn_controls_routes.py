"""Canonical Assistant Turn Control Sub-Routes (`/stop`, `/synthesize-now`, `/approve`)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from orcia_api.dependencies import (
    get_assistant_feedback_repository,
    get_assistant_turn_engine,
)
from orcia_api.dependencies._assistant_guards import (
    enforce_assistant_workspace_guard,
    require_not_observer_write,
)
from orcia_api.routers._assistant_background_registry import (
    get_turn_registry_from_request,
    stop_assistant_turn_by_id,
)
from orcia_api.routers._assistant_process_wiring import launch_assistant_process_from_api
from orcia_api.routers._assistant_turn_finalizer import record_turn_approval_audit
from orcia_api.routers._assistant_usage_telemetry import resolve_audit_ledger_sink
from orcia_api.routers._assistant_workspace_context import to_active_turn_response
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    ActiveBackgroundTurnStatusResponse,
    AssistantTurnApproveRequest,
    AssistantTurnApproveResponse,
    AssistantTurnFeedbackRequest,
    AssistantTurnFeedbackResponse,
    AssistantTurnSynthesizeNowResponse,
)
from orcia_core.orchestration.assistant_feedback import SqlAssistantFeedbackRepository
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import UserIdentity

controls_router = APIRouter()
CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
TurnEngineDep = Annotated[AssistantTurnEngine, Depends(get_assistant_turn_engine)]
FeedbackRepoDep = Annotated[
    SqlAssistantFeedbackRepository, Depends(get_assistant_feedback_repository)
]


async def require_owned_assistant_turn(
    turn_id: str, request: Request, user: UserIdentity, *, require_write: bool
) -> tuple[Any, Any]:
    """Load Redis turn record, enforce workspace guard, and assert ownership."""
    if require_write:
        require_not_observer_write(request, user)
    reg = get_turn_registry_from_request(request)
    rec = await reg.get_turn_by_id(turn_id)
    if rec is None:
        raise ResourceNotFoundError(
            detail_override=f"Turn '{turn_id}' not found.", instance=str(request.url.path)
        )
    await enforce_assistant_workspace_guard(
        request, user, rec.workspace_id, require_write=require_write
    )
    if rec.user_id != user.id:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    return reg, rec


@controls_router.post("/turns/{turn_id}/stop", response_model=ActiveBackgroundTurnStatusResponse)
async def stop_assistant_turn_endpoint(
    turn_id: str,
    request: Request,
    user: CurrentUserDep,
) -> ActiveBackgroundTurnStatusResponse:
    """Propagate cross-worker `stop` via Redis and flush partial FinOps in `finally`."""
    _, rec = await require_owned_assistant_turn(turn_id, request, user, require_write=True)
    state = await stop_assistant_turn_by_id(turn_id, request=request, stopped_by_user_id=user.id)
    if state is None:
        return ActiveBackgroundTurnStatusResponse(
            workspace_id=rec.workspace_id, turn_id=turn_id, status="STOPPED"
        )
    return to_active_turn_response(state)


@controls_router.post(
    "/turns/{turn_id}/synthesize-now",
    status_code=202,
    response_model=AssistantTurnSynthesizeNowResponse,
)
async def synthesize_now_assistant_turn_endpoint(
    turn_id: str,
    request: Request,
    user: CurrentUserDep,
    turn_engine: TurnEngineDep,
) -> AssistantTurnSynthesizeNowResponse:
    """Signal early transition from `N3` tool loop to `N4 -> N5 -> CitationGuard` (`202`)."""
    reg, rec = await require_owned_assistant_turn(turn_id, request, user, require_write=True)
    await reg.request_synthesize_now(turn_id)
    if turn_engine.reflexive_runtime is not None:
        await turn_engine.reflexive_runtime.request_synthesize_now(turn_id, resume_if_idle=False)
    return AssistantTurnSynthesizeNowResponse(
        turn_id=turn_id,
        workspace_id=rec.workspace_id,
        status="SYNTHESIZING",
        message="Early synthesis requested; completing active tool round before final synthesis.",
    )


@controls_router.post("/turns/{turn_id}/approve", response_model=AssistantTurnApproveResponse)
async def approve_assistant_turn_proposal_endpoint(
    turn_id: str,
    payload: AssistantTurnApproveRequest,
    request: Request,
    user: CurrentUserDep,
) -> AssistantTurnApproveResponse:
    """Enforce Lock V5 human-authored anchor before approving a process/write proposal."""
    _, rec = await require_owned_assistant_turn(turn_id, request, user, require_write=True)
    if rec.workspace_id != payload.workspace_id:
        await enforce_assistant_workspace_guard(
            request, user, payload.workspace_id, require_write=True
        )
    if (
        payload.approved
        and payload.human_authored_required
        and (not payload.human_anchor_markdown or len(payload.human_anchor_markdown.strip()) < 10)
    ):
        raise HumanAnchorRequiredError(instance=str(request.url.path))
    trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or rec.trace_id)
    anchor_sha, audit_id = await record_turn_approval_audit(
        sink=resolve_audit_ledger_sink(request),
        turn_id=turn_id,
        proposal_id=payload.proposal_id,
        workspace_id=payload.workspace_id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        approved=payload.approved,
        human_anchor_markdown=payload.human_anchor_markdown,
        rationale=payload.rationale,
        trace_id=trace_id,
    )
    run_outcome = None
    should_launch = payload.approved and (
        payload.continue_in_process or payload.target_workflow_uri is not None
    )
    if should_launch:
        run_outcome = await launch_assistant_process_from_api(
            request,
            user=user,
            workspace_id=payload.workspace_id,
            workflow_uri=payload.target_workflow_uri,
            idempotency_token=f"turn:{turn_id}:{payload.proposal_id}",
            seed_inputs={
                "turn_id": turn_id,
                "proposal_id": payload.proposal_id,
                "user_prompt": rec.user_prompt,
                "human_anchor_markdown": payload.human_anchor_markdown or "",
            },
            trace_id=trace_id,
        )
    return AssistantTurnApproveResponse(
        turn_id=turn_id,
        proposal_id=payload.proposal_id,
        workspace_id=payload.workspace_id,
        approved=payload.approved,
        status="APPROVED" if payload.approved else "REJECTED",
        human_anchor_sha256=anchor_sha,
        audit_id=audit_id,
        run_id=run_outcome.run.id if run_outcome is not None else None,
        workflow_uri=run_outcome.workflow_uri if run_outcome is not None else None,
        run_status=run_outcome.run_status if run_outcome is not None else None,
        dbos_workflow_id=run_outcome.dbos_workflow_id if run_outcome is not None else None,
        waiting_step_keys=list(run_outcome.waiting_step_keys) if run_outcome is not None else [],
        executed_step_keys=list(run_outcome.executed_step_keys) if run_outcome is not None else [],
        snapshot_count=run_outcome.snapshot_count if run_outcome is not None else 0,
    )


@controls_router.post("/turns/{turn_id}/feedback", response_model=AssistantTurnFeedbackResponse)
async def upsert_assistant_turn_feedback_endpoint(
    turn_id: str,
    payload: AssistantTurnFeedbackRequest,
    request: Request,
    user: CurrentUserDep,
    feedback_repo: FeedbackRepoDep,
) -> AssistantTurnFeedbackResponse:
    """Idempotently upsert user feedback for `(turn_id, user_id)` in `assistant_turn_feedback`."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    rec = await feedback_repo.upsert_feedback(
        turn_id=turn_id,
        workspace_id=payload.workspace_id,
        user=user,
        rating=payload.rating,
        reason_code=payload.reason_code,
        comment=payload.comment,
    )
    return AssistantTurnFeedbackResponse(
        feedback_id=rec.feedback_id,
        turn_id=rec.turn_id,
        workspace_id=rec.workspace_id,
        user_id=rec.user_id,
        rating=rec.rating,
        reason_code=rec.reason_code,
        comment=rec.comment,
    )
