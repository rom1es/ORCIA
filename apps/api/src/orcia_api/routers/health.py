"""Health and readiness probe routers (`/api/v1/health`, `/ready`, `/api/v1/ready`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.shell import HealthResponse, ReadinessResponse
from orcia_core import __version__
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(prefix="/api/v1", tags=["system"])
probe_router = APIRouter(tags=["system"])

_PROBE_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    500: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    503: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}


def _resolve_trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _build_readiness_response(request: Request) -> ReadinessResponse | JSONResponse:
    """Perform a non-blocking `< 100 ms` readiness check without SQL queries."""
    trace_id = _resolve_trace_id(request)
    initialized = getattr(request.app.state, "orchestration_service", None) is not None
    if not initialized:
        problem = ProblemDetails(
            type="https://orcia.io/problems/service-not-ready",
            title="Service Not Ready",
            status=503,
            detail="ORCIA API Composition Root services are not initialized.",
            instance=str(request.url.path),
            error_code="ERR_API_NOT_READY",
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=503,
            media_type="application/problem+json",
            content=problem.model_dump(),
        )
    return ReadinessResponse(
        status="ready",
        version=__version__,
        trace_id=trace_id,
        initialized=True,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check ORCIA API liveness and propagate W3C trace_id",
    responses={
        422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
        500: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    },
)
async def get_health(request: Request) -> HealthResponse:
    """Return platform liveness status and active 32-hex W3C `trace_id`."""
    return HealthResponse(
        status="ok",
        version=__version__,
        trace_id=_resolve_trace_id(request),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Check ORCIA API readiness without heavy SQL queries",
    responses=_PROBE_ERROR_RESPONSES,
)
async def get_api_v1_ready(request: Request) -> ReadinessResponse | JSONResponse:
    """Return lightweight readiness status (`< 100 ms`) under `/api/v1/ready`."""
    return _build_readiness_response(request)


@probe_router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Root OpenShift readinessProbe endpoint",
    responses=_PROBE_ERROR_RESPONSES,
)
async def get_root_ready(request: Request) -> ReadinessResponse | JSONResponse:
    """Return lightweight readiness status (`< 100 ms`) under `/ready`."""
    return _build_readiness_response(request)
