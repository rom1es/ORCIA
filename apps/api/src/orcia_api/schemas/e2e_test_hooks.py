"""OpenAPI transport schemas for isolated E2E test hooks (`Story 22.8`)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvictMemoryCachesResponse(BaseModel):
    """Result of evicting all in-memory service caches on the E2E server."""

    evicted: bool = Field(..., description="True when all RAM caches/mirrors were evicted.")
    cleared_caches: list[str] = Field(
        default_factory=list,
        description="Names of `app.state` service caches cleared for cold PG18 reload.",
    )
    trace_id: str = Field(..., min_length=1, description="W3C OpenTelemetry trace_id.")
