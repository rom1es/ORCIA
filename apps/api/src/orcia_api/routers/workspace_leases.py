"""Resource Leases & Monotonic Fencing Router (`DEC-CONC-01`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_notification_service, get_resource_lease_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.inbox_and_leases import (
    AcquireResourceLeasesRequest,
    AcquireResourceLeasesResponse,
    ResourceLeaseItemResponse,
    ValidateFencedWriteRequest,
    ValidateFencedWriteResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(tags=["inbox"])

_ERR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}


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
    records = await lease_svc.acquire_leases_async(
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
    outcome = await lease_svc.execute_fenced_resource_write_async(
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
