"""Reflexive Execution, Live SSE Trace & Stateless Write-Preview Router (`Story 16.2`, `CAP-160`).

Exposes:
- `POST /api/v1/executions/reflexive`: Start or run a pure `asyncio` reflexive session.
- `GET /api/v1/executions/{execution_id}`: Rehydrate `ReflexiveSessionSnapshot` (`F5` survival).
- `GET /api/v1/executions/{execution_id}/trace-stream`: Real `AsyncIterator` SSE (`\n` kept).
- `POST /api/v1/executions/{execution_id}/synthesize-now`: Trigger `force_final=True`.
- `POST /api/v1/executions/{execution_id}/cancel`: Immediate cancel (`■ Arrêter`, `0` LLM turns).
- `POST /api/v1/executions/{execution_id}/approve-write`: Approve/reject `WritePreviewCard`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import (
    get_auth_service,
    get_reflexive_event_stream_broker,
    get_reflexive_runtime_service,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.reflexive_execution import (
    ApproveReflexiveWriteRequest,
    ReflexiveExecutionSnapshotResponse,
    StartReflexiveExecutionRequest,
)
from orcia_connectors import issue_broker_write_approval
from orcia_core.agents import (
    NonDeterministicReflexiveRuntime,
    ReflexiveEventStreamBroker,
    ReflexiveRuntimeConfig,
    ReflexiveSessionSnapshot,
    ReflexiveWriteApprovalInput,
)
from orcia_core.agents.errors import (
    ObserverModeReadOnlyError,
    PolicyDeniedError,
    ReflexiveInvalidStateError,
    ResourceNotFoundError,
)
from orcia_core.kernel.errors import resolve_locale
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions import UserIdentity

router = APIRouter(
    prefix="/api/v1/executions",
    tags=["executions-reflexive"],
    responses={
        **PROBLEM_RESPONSES,
        409: PROBLEM_RESPONSES[422],
    },
)

ReflexiveRuntimeDep = Annotated[
    NonDeterministicReflexiveRuntime, Depends(get_reflexive_runtime_service)
]
EventStreamBrokerDep = Annotated[
    ReflexiveEventStreamBroker, Depends(get_reflexive_event_stream_broker)
]
ExecutionIdPath = Annotated[str, Path(min_length=1, max_length=128)]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]

_DENIED_HEADER_VALUES: frozenset[str] = frozenset({"0", "false", "denied", "restricted", "no"})
_OBSERVER_PERSONAS: frozenset[str] = frozenset({"claire", "observer"})


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _resolve_has_read_source(request: Request) -> bool:
    raw = (request.headers.get("x-orcia-read-source") or "").strip().lower()
    return raw not in _DENIED_HEADER_VALUES


def _enforce_not_observer(
    request: Request,
    *,
    persona_key: str | None,
    workspace_id: str | None = None,
) -> UserIdentity:
    """Reject `READ_ONLY_OBSERVER` actors on all mutation routes with `HTTP 403`."""
    user = resolve_request_user(request, persona_key=persona_key)
    access_hdr = (request.headers.get("x-orcia-access-mode") or "").strip().upper()
    if (
        user.platform_role in ("OBSERVER", "BU_DIRECTOR")
        or (persona_key or "").strip().lower() in _OBSERVER_PERSONAS
        or access_hdr == "READ_ONLY_OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    if workspace_id:
        ws_access = get_auth_service(request).evaluator.resolve_workspace_access(user, workspace_id)
        if ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return user


def _serialize_snapshot(
    snap: ReflexiveSessionSnapshot,
    trace_id: str,
) -> ReflexiveExecutionSnapshotResponse:
    data = snap.model_dump(
        mode="json",
        exclude={"has_read_source", "locale", "initial_resources", "requested_write_preview"},
    )
    return ReflexiveExecutionSnapshotResponse.model_validate({**data, "trace_id": trace_id})


@router.post(
    "/reflexive",
    response_model=ReflexiveExecutionSnapshotResponse,
    summary="Start a pure `asyncio` reflexive execution (`Standard` or `Approfondi`)",
)
async def start_reflexive_execution_endpoint(
    payload: StartReflexiveExecutionRequest,
    request: Request,
    runtime: ReflexiveRuntimeDep,
    persona_key: PersonaQuery = None,
) -> ReflexiveExecutionSnapshotResponse:
    """Launch a reflexive execution loop (`run_in_background=True` or synchronous await)."""
    user = _enforce_not_observer(
        request, persona_key=persona_key, workspace_id=payload.workspace_id
    )
    locale = resolve_locale(request.headers.get("accept-language"))
    cfg_kwargs: dict[str, object] = {
        "effort_level": payload.effort_level,
        "allow_sub_agent_delegation": payload.allow_sub_agent_delegation,
        "available_delegate_agents": payload.available_delegate_agents,
        "workspace_id": payload.workspace_id,
        "actor_user_id": user.id,
        "has_read_source": _resolve_has_read_source(request),
        "locale": locale,
        "initial_resources": payload.initial_resources,
        "requested_write_preview": (
            payload.requested_write_preview.model_dump(mode="json")
            if payload.requested_write_preview is not None
            else None
        ),
        "step_delay_ms": payload.step_delay_ms,
    }
    if payload.effort_mode is not None:
        cfg_kwargs["effort_mode"] = payload.effort_mode
    config = ReflexiveRuntimeConfig.model_validate(cfg_kwargs)

    if payload.run_in_background:
        exec_id, _task = runtime.start_background_execution(
            actor_slug=payload.actor_slug,
            objective=payload.objective,
            config=config,
        )
        for _ in range(20):
            await asyncio.sleep(0.005)
            snap = await runtime.get_session_snapshot(exec_id)
            if snap is not None:
                return _serialize_snapshot(snap, _trace(request))
        raise ResourceNotFoundError(
            detail_override=f"Execution '{exec_id}' non initialisée.",
            instance=str(request.url.path),
        )

    snapshot = await runtime.run_execution(
        actor_slug=payload.actor_slug,
        objective=payload.objective,
        config=config,
    )
    return _serialize_snapshot(snapshot, _trace(request))


@router.get(
    "/{execution_id}",
    response_model=ReflexiveExecutionSnapshotResponse,
    summary="Rehydrate `ReflexiveSessionSnapshot` by `execution_id` (`F5` page reload survival)",
)
async def get_reflexive_execution_endpoint(
    execution_id: ExecutionIdPath,
    request: Request,
    runtime: ReflexiveRuntimeDep,
    persona_key: PersonaQuery = None,
) -> ReflexiveExecutionSnapshotResponse:
    """Return active or PostgreSQL 18 persisted `ReflexiveSessionSnapshot`."""
    resolve_request_user(request, persona_key=persona_key)
    snapshot = await runtime.get_session_snapshot(execution_id)
    if snapshot is None:
        raise ResourceNotFoundError(
            detail_override=f"Execution '{execution_id}' introuvable.",
            instance=str(request.url.path),
        )
    return _serialize_snapshot(snapshot, _trace(request))


@router.get(
    "/{execution_id}/trace-stream",
    summary="Stream real-time `AgentTraceEvent` SSE events (`text/event-stream`, `\\n` preserved)",
)
async def stream_reflexive_execution_trace_endpoint(
    execution_id: ExecutionIdPath,
    request: Request,
    runtime: ReflexiveRuntimeDep,
    broker: EventStreamBrokerDep,
    persona_key: PersonaQuery = None,
) -> StreamingResponse:
    """Consume real `AsyncIterator` trace events without space splitting."""
    resolve_request_user(request, persona_key=persona_key)
    snapshot = await runtime.get_session_snapshot(execution_id)
    if snapshot is None:
        raise ResourceNotFoundError(
            detail_override=f"Execution '{execution_id}' introuvable.",
            instance=str(request.url.path),
        )
    broker.sync_history_from_snapshot(
        execution_id,
        [ev.model_dump(mode="json") for ev in snapshot.trace_events],
    )

    async def _sse_event_generator() -> AsyncIterator[str]:
        async for ev in broker.subscribe_events(execution_id):
            kind = str(ev.get("kind", "trace_event"))
            serialized = json.dumps(ev, ensure_ascii=False)
            yield f"event: {kind}\ndata: {serialized}\n\n"

    return StreamingResponse(
        _sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{execution_id}/synthesize-now",
    response_model=ReflexiveExecutionSnapshotResponse,
    summary="Raise `force_final=True` (`Synthétiser maintenant`) for immediate synthesis",
)
async def synthesize_reflexive_execution_now_endpoint(
    execution_id: ExecutionIdPath,
    request: Request,
    runtime: ReflexiveRuntimeDep,
    persona_key: PersonaQuery = None,
) -> ReflexiveExecutionSnapshotResponse:
    """Request immediate synthesis on the active or paused reflexive session."""
    _enforce_not_observer(request, persona_key=persona_key)
    snapshot = await runtime.request_synthesize_now(execution_id, resume_if_idle=True)
    return _serialize_snapshot(snapshot, _trace(request))


@router.post(
    "/{execution_id}/cancel",
    response_model=ReflexiveExecutionSnapshotResponse,
    summary="Immediately cancel `execution_id` (`■ Arrêter` — `0` extra LLM calls)",
)
async def cancel_reflexive_execution_endpoint(
    execution_id: ExecutionIdPath,
    request: Request,
    runtime: ReflexiveRuntimeDep,
    persona_key: PersonaQuery = None,
) -> ReflexiveExecutionSnapshotResponse:
    """Cancel an in-flight or waiting reflexive execution without triggering synthesis."""
    _enforce_not_observer(request, persona_key=persona_key)
    snapshot = await runtime.cancel_execution(execution_id)
    return _serialize_snapshot(snapshot, _trace(request))


@router.post(
    "/{execution_id}/approve-write",
    response_model=ReflexiveExecutionSnapshotResponse,
    summary="Approve (`SignedApprovalToken` verified) or reject `WritePreviewCard` and resume loop",
)
async def approve_reflexive_write_endpoint(
    execution_id: ExecutionIdPath,
    payload: ApproveReflexiveWriteRequest,
    request: Request,
    runtime: ReflexiveRuntimeDep,
    persona_key: PersonaQuery = None,
) -> ReflexiveExecutionSnapshotResponse:
    """Statelessly reload `WAITING_WRITE_PREVIEW` session, enforce write gate, and resume."""
    user = _enforce_not_observer(request, persona_key=persona_key)
    snapshot = await runtime.get_session_snapshot(execution_id)
    if snapshot is None:
        raise ResourceNotFoundError(
            detail_override=f"Execution '{execution_id}' introuvable.",
            instance=str(request.url.path),
        )
    if snapshot.status != "WAITING_WRITE_PREVIEW" or snapshot.pending_write_preview is None:
        raise ReflexiveInvalidStateError(
            detail_override=(
                f"ERR_REFLEXIVE_STATE_INVALID: Execution '{execution_id}' is in status "
                f"'{snapshot.status}', expected 'WAITING_WRITE_PREVIEW'."
            ),
            instance=str(request.url.path),
        )
    pending = snapshot.pending_write_preview
    if payload.preview_id != pending.preview_id:
        raise PolicyDeniedError(
            detail_override=(
                f"ERR_WRITE_PREVIEW_MISMATCH: preview_id '{payload.preview_id}' "
                f"ne correspond pas à '{pending.preview_id}'."
            ),
            instance=str(request.url.path),
        )

    approval_input: ReflexiveWriteApprovalInput | None = None
    if payload.approved:
        if payload.approval_token is not None:
            approval_input = ReflexiveWriteApprovalInput(
                **payload.approval_token.model_dump(mode="json")
            )
        else:
            approval_input = issue_broker_write_approval(
                preview=pending,
                approver_user_id=user.id,
            )

    resumed = await runtime.resume_after_write_decision(
        execution_id,
        approved=payload.approved,
        approval=approval_input,
        rejection_reason=payload.rejection_reason,
    )
    return _serialize_snapshot(resumed, _trace(request))
