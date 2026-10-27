"""Health check router (`/api/v1/health`) with OpenTelemetry `trace_id` propagation."""

from __future__ import annotations

from fastapi import APIRouter, Request

from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.shell import HealthResponse
from orcia_core import __version__
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check ORCIA API health and propagate W3C trace_id",
    responses={
        422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
        500: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    },
)
async def get_health(request: Request) -> HealthResponse:
    """Return platform health status and active 32-hex W3C `trace_id`."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    return HealthResponse(
        status="ok",
        version=__version__,
        trace_id=trace_id,
    )
