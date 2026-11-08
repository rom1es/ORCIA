"""Story 5.1 FastAPI router: Unified Notification Inbox, Atomic SSE Claim & Leases (`AD-4`)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import get_notification_service, get_resource_lease_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.inbox_and_leases import (
    AcquireResourceLeasesRequest,
    AcquireResourceLeasesResponse,
    ClaimTaskRequest,
    ClaimTaskResponse,
    InboxNotificationListResponse,
    ReleaseTaskClaimRequest,
    ResourceLeaseItemResponse,
    SseEventEnvelopeResponse,
    TaskNotificationItemResponse,
    ValidateFencedWriteRequest,
    ValidateFencedWriteResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration.notifications_and_claims import (
    ClaimActionOutcome,
    NotificationType,
    SseEventEnvelope,
    TaskNotificationEntity,
)

router = APIRouter(prefix="/api/v1", tags=["inbox"])

_ERR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}


def _to_notification_item_response(
    entity: TaskNotificationEntity, viewer_user_id: str
) -> TaskNotificationItemResponse:
    presence = entity.resolve_presence_state(viewer_user_id)
    return TaskNotificationItemResponse(
        id=entity.id,
        workspace_id=entity.workspace_id,
        target_team_id=entity.target_team_id,
        target_user_id=entity.target_user_id,
        run_id=entity.run_id,
        step_execution_id=entity.step_execution_id,
        step_key=entity.step_key,
        notification_type=entity.notification_type,
        scope_kind=entity.scope_kind,
        title=entity.title,
        summary=entity.summary,
        status=entity.status,
        claimed_by_user_id=entity.claimed_by_user_id,
        claimed_by_display_name=entity.claimed_by_display_name,
        claimed_at=entity.claimed_at,
        lock_expires_at=entity.lock_expires_at,
        presence_state=presence,
        peer_opacity=0.85 if presence == "CLAIMED_BY_PEER" else 1.0,
        can_force_unclaim=entity.can_force_unclaim(),
        created_at=entity.created_at,
    )


def _to_claim_response(
    outcome: ClaimActionOutcome, viewer_user_id: str, trace_id: str
) -> ClaimTaskResponse:
    return ClaimTaskResponse(
        notification=_to_notification_item_response(outcome.notification, viewer_user_id),
        lock_key=outcome.lock_record.lock_key if outcome.lock_record else None,
        viewer_presence_state=outcome.viewer_presence_state,
        peer_presence_state=outcome.peer_presence_state,
        sse_event=SseEventEnvelopeResponse(
            event_id=outcome.sse_event.event_id,
            event_name=outcome.sse_event.event_name,
            channel=outcome.sse_event.channel,
            workspace_id=outcome.sse_event.workspace_id,
            run_id=outcome.sse_event.run_id,
            step_execution_id=outcome.sse_event.step_execution_id,
            payload=dict(outcome.sse_event.payload),
            published_at_iso=outcome.sse_event.published_at_iso,
            dispatch_latency_ms=outcome.sse_event.dispatch_latency_ms,
        ),
        trace_id=trace_id,
    )


@router.get(
    "/inbox/notifications",
    response_model=InboxNotificationListResponse,
    summary="List unified personal & team notifications with presence lock state (`Story 5.1`)",
    responses=_ERR_RESPONSES,
)
async def list_inbox_notifications(
    request: Request,
    workspace_id: Annotated[
        str,
        Query(min_length=1, max_length=64),
    ] = "0195f000-0000-7000-8000-000000000301",
    scope_filter: Annotated[Literal["ALL", "PERSONAL", "TEAM"], Query()] = "ALL",
    notification_type: Annotated[NotificationType | None, Query()] = None,
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> InboxNotificationListResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_notification_service(request)
    items = svc.list_notifications(
        workspace_id=workspace_id,
        scope_filter=scope_filter,
        notification_type=notification_type,
        viewer_user_id=user.id,
    )
    return InboxNotificationListResponse(
        workspace_id=workspace_id,
        viewer_user_id=user.id,
        amber_badge_count=svc.count_unclaimed_action_required(workspace_id=workspace_id),
        items=[_to_notification_item_response(item, user.id) for item in items],
        trace_id=trace_id,
    )


@router.post(
    "/tasks/{task_id}/claim",
    response_model=ClaimTaskResponse,
    summary="Atomically claim a notification (`SET lock:step:{step_id} NX EX 900`, `AD-4`)",
    responses=_ERR_RESPONSES,
)
async def claim_task_notification(
    task_id: str,
    payload: ClaimTaskRequest,
    request: Request,
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> ClaimTaskResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_notification_service(request)
    outcome = svc.claim_by_task_id(
        user,
        task_id=task_id,
        ttl_seconds=payload.ttl_seconds,
        force=payload.force,
        instance=str(request.url.path),
    )
    return _to_claim_response(outcome, user.id, trace_id)


@router.post(
    "/tasks/{task_id}/release",
    response_model=ClaimTaskResponse,
    summary="Release or Force-Unclaim (after 15m inactivity) a task notification (`UX-DR9`)",
    responses=_ERR_RESPONSES,
)
async def release_task_notification_claim(
    task_id: str,
    payload: ReleaseTaskClaimRequest,
    request: Request,
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> ClaimTaskResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_notification_service(request)
    outcome = svc.release_claim(
        user,
        task_id=task_id,
        force=payload.force,
        instance=str(request.url.path),
    )
    return _to_claim_response(outcome, user.id, trace_id)


@router.post(
    "/runs/{run_id}/steps/{step_id}/claim",
    response_model=ClaimTaskResponse,
    summary="Atomically claim a step execution (`SET lock:step:{step_id} NX EX 900`, `AD-4`)",
    responses=_ERR_RESPONSES,
)
async def claim_step_execution(
    run_id: str,
    step_id: str,
    payload: ClaimTaskRequest,
    request: Request,
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> ClaimTaskResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_notification_service(request)
    outcome = svc.claim_by_step_execution(
        user,
        run_id=run_id,
        step_execution_id=step_id,
        workspace_id=payload.workspace_id,
        step_key=payload.step_key,
        ttl_seconds=payload.ttl_seconds,
        force=payload.force,
        instance=str(request.url.path),
    )
    return _to_claim_response(outcome, user.id, trace_id)


def _format_sse_envelope(evt: SseEventEnvelope) -> str:
    frame = {
        "event_id": evt.event_id,
        "event_name": evt.event_name,
        "channel": evt.channel,
        "workspace_id": evt.workspace_id,
        "run_id": evt.run_id,
        "step_execution_id": evt.step_execution_id,
        "payload": evt.payload,
        "published_at_iso": evt.published_at_iso,
        "dispatch_latency_ms": evt.dispatch_latency_ms,
    }
    data_str = json.dumps(frame, sort_keys=True)
    return f"id: {evt.event_id}\nevent: {evt.event_name}\ndata: {data_str}\n\n"


@router.get(
    "/events/stream",
    summary="Unified Server-Sent Events stream (`channel:workspace:{ws_id}`, `< 500 ms`, `AD-4`)",
    responses={
        **_ERR_RESPONSES,
        200: {"content": {"text/event-stream": {"schema": {"type": "object"}}}},
    },
)
async def stream_workspace_events(
    request: Request,
    workspace_id: Annotated[
        str,
        Query(min_length=1, max_length=64),
    ] = "0195f000-0000-7000-8000-000000000301",
    live: Annotated[
        bool | None,
        Query(description="Keep SSE connection open for real-time events (`AD-4`)."),
    ] = None,
) -> StreamingResponse:
    svc = get_notification_service(request)
    keep_alive = live if live is not None else (request.url.hostname != "testserver")

    async def _event_generator() -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        live_queue: asyncio.Queue[SseEventEnvelope] = asyncio.Queue()
        unsubscribe = (
            svc.sse_broker.subscribe(
                lambda evt: loop.call_soon_threadsafe(live_queue.put_nowait, evt),
                workspace_id=workspace_id,
            )
            if keep_alive
            else (lambda: None)
        )
        try:
            recent = svc.sse_broker.list_recent_events(workspace_id=workspace_id)
            conn_payload = json.dumps({"channel": f"channel:workspace:{workspace_id}"})
            yield f"event: connected\ndata: {conn_payload}\n\n"
            seen_ids: set[str] = set()
            for evt in recent:
                seen_ids.add(evt.event_id)
                yield _format_sse_envelope(evt)
            if not keep_alive:
                return
            while not await request.is_disconnected():
                try:
                    evt = await asyncio.wait_for(live_queue.get(), timeout=0.25)
                except TimeoutError:
                    continue
                if evt.event_id in seen_ids:
                    continue
                seen_ids.add(evt.event_id)
                yield _format_sse_envelope(evt)
        finally:
            unsubscribe()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/resource-leases/acquire",
    response_model=AcquireResourceLeasesResponse,
    summary="Acquire shared resource leases in canonical order with fencing (`DEC-CONC-01`)",
    responses=_ERR_RESPONSES,
)
async def acquire_resource_leases(
    payload: AcquireResourceLeasesRequest,
    request: Request,
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> AcquireResourceLeasesResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    notif_svc = get_notification_service(request)
    notif_svc._enforce_not_observer(user, instance=str(request.url.path))
    lease_svc = get_resource_lease_service(request)
    records = lease_svc.acquire_leases(
        resource_uris=tuple(payload.resource_uris),
        holder_run_id=payload.holder_run_id,
        holder_root_run_id=payload.holder_root_run_id,
        holder_step_execution_id=payload.holder_step_execution_id,
        holder_parent_run_id=payload.holder_parent_run_id,
        ancestor_run_ids=tuple(payload.ancestor_run_ids),
        ttl_seconds=payload.ttl_seconds,
    )
    return AcquireResourceLeasesResponse(
        leases=[
            ResourceLeaseItemResponse(
                id=r.id,
                resource_uri=r.resource_uri,
                resource_class=r.resource_class,
                holder_run_id=r.holder_run_id,
                holder_root_run_id=r.holder_root_run_id,
                holder_parent_run_id=r.holder_parent_run_id,
                holder_step_execution_id=r.holder_step_execution_id,
                fencing_token=r.fencing_token,
                acquired_at=r.acquired_at,
                expires_at=r.expires_at,
            )
            for r in records
        ],
        canonical_order=[r.resource_uri for r in records],
        trace_id=trace_id,
    )


@router.post(
    "/resource-leases/fenced-write",
    response_model=ValidateFencedWriteResponse,
    summary="Validate monotonic fencing token before shared resource write (`DEC-CONC-01`)",
    responses=_ERR_RESPONSES,
)
async def execute_fenced_resource_write(
    payload: ValidateFencedWriteRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> ValidateFencedWriteResponse:
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    user = resolve_request_user(request, persona_key=persona_key)
    notif_svc = get_notification_service(request)
    notif_svc._enforce_not_observer(user, instance=str(request.url.path))
    lease_svc = get_resource_lease_service(request)
    outcome = lease_svc.execute_fenced_write(
        resource_uri=payload.resource_uri,
        fencing_token=payload.fencing_token,
        payload=payload.payload,
    )
    return ValidateFencedWriteResponse(
        resource_uri=str(outcome["resource_uri"]),
        fencing_token=int(outcome["fencing_token"]),
        resource_class=str(outcome["resource_class"]),
        status="COMMITTED_FENCED",
        payload=dict(outcome["payload"]),
        trace_id=trace_id,
    )
