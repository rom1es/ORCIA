"""FastAPI Pydantic v2 schemas for Autonomous Run Supervision & Emergency Controls (`Story 7.4`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AutonomousRunSupervisionItemSchema(BaseModel):
    """Supervised autonomous workflow run item (`UX-DR17`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workspace_id: str
    workflow_id: str
    workflow_title: str
    trigger_id: str | None = None
    trigger_label: str
    trigger_type: str
    trigger_status: str
    run_status: str
    post_hoc_status: str
    contract_id: str
    cost_usd: float
    created_at_iso: str
    help_resource_id: str | None = None
    previous_version_available: bool = False


class AutonomousRunsListResponse(BaseModel):
    """List of autonomous contract runs in a workspace or across authorized workspaces."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str | None = None
    runs: list[AutonomousRunSupervisionItemSchema] = Field(default_factory=list)
    trace_id: str | None = None


class EmergencyStopRequest(BaseModel):
    """Request to activate an immediate emergency stop (`KILL_SWITCH_STOPPED`)."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="", max_length=1000)
    suspend_trigger: bool = True
    workspace_id: str | None = None


class EmergencyStopResponse(BaseModel):
    """Response confirming `KILL_SWITCH_STOPPED` and optional trigger suspension."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workspace_id: str
    status: str
    trigger_suspended: bool
    sse_dispatch_latency_ms: float
    trace_id: str | None = None


class InvalidateAndRestoreRequest(BaseModel):
    """Request to invalidate an autonomous artifact/help article and restore `@v(N-1)`."""

    model_config = ConfigDict(extra="forbid")

    comment: str = Field(default="", max_length=1000)
    help_resource_id: str | None = None
    workspace_id: str | None = None


class InvalidateAndRestoreResponse(BaseModel):
    """Response confirming `@v(N-1)` restoration and Redis cache invalidation."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workspace_id: str
    status: str
    restored_version: str
    help_resource_id: str | None = None
    redis_cache_invalidated_ms: float
    sse_dispatch_latency_ms: float
    trace_id: str | None = None


class PostHocReviewRequest(BaseModel):
    """Request to validate or invalidate a sampled autonomous run."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["VALIDATED", "INVALIDATED_ROLLED_BACK"]
    comment: str = Field(default="", max_length=1000)
    help_resource_id: str | None = None
    workspace_id: str | None = None


class PostHocReviewResponse(BaseModel):
    """Response after completing a post-hoc sample quality review."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    review_status: Literal["VALIDATED", "INVALIDATED_ROLLED_BACK"]
    run_status: str
    restored_version: str | None = None
    trace_id: str | None = None
