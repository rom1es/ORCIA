"""HTTP/OpenAPI 3.1 schemas for Story 5.1 (Notification Inbox, SSE Claim & Resource Leases)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskNotificationItemResponse(BaseModel):
    """Unified notification item (`task_notifications`, `FR-2`, `UX-DR9`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    target_team_id: str | None = None
    target_user_id: str | None = None
    run_id: str
    step_execution_id: str
    step_key: str
    notification_type: Literal[
        "HUMAN_GATE",
        "HUMAN_ARBITRATION",
        "HUMAN_ANCHOR",
        "UPSTREAM_CHALLENGE",
        "PERMISSION_ALERT",
        "STALE_WARNING",
        "AUTONOMOUS_ESCALATION",
        "POST_HOC_AUDIT_SAMPLE",
    ]
    scope_kind: Literal["PERSONAL", "TEAM"]
    title: str
    summary: str
    status: Literal["OPEN", "CLAIMED", "RESOLVED"]
    claimed_by_user_id: str | None = None
    claimed_by_display_name: str | None = None
    claimed_at: str | None = None
    lock_expires_at: str | None = None
    presence_state: Literal["UNCLAIMED", "CLAIMED_BY_ME", "CLAIMED_BY_PEER"]
    peer_opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    can_force_unclaim: bool = False
    created_at: str


class InboxNotificationListResponse(BaseModel):
    """Unified Inbox notification list with amber sidebar counter (`UX-DR2`, `UX-DR9`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    viewer_user_id: str
    amber_badge_count: int = Field(ge=0)
    items: list[TaskNotificationItemResponse]
    trace_id: str


class ClaimTaskRequest(BaseModel):
    """Request body for claiming a task notification or step execution (`AD-4`)."""

    model_config = ConfigDict(extra="forbid")

    ttl_seconds: int = Field(default=900, ge=1, le=86400)
    force: bool = False
    workspace_id: str = Field(
        default="0195f000-0000-7000-8000-000000000301", min_length=1, max_length=64
    )
    step_key: str = Field(default="architecture-arbitration", min_length=1, max_length=128)


class ReleaseTaskClaimRequest(BaseModel):
    """Request body for releasing or force-unclaiming a task notification (`UX-DR9`)."""

    model_config = ConfigDict(extra="forbid")

    force: bool = False


class SseEventEnvelopeResponse(BaseModel):
    """SSE event envelope published to `channel:workspace:{ws_id}` (`AD-4`, `< 500 ms`)."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_name: str
    channel: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    published_at_iso: str
    dispatch_latency_ms: float = Field(ge=0.0)


class ClaimTaskResponse(BaseModel):
    """Response returned after atomic `SET lock:step:{step_execution_id} NX EX 900` (`AD-4`)."""

    model_config = ConfigDict(extra="forbid")

    notification: TaskNotificationItemResponse
    lock_key: str | None = None
    viewer_presence_state: Literal["UNCLAIMED", "CLAIMED_BY_ME", "CLAIMED_BY_PEER"]
    peer_presence_state: Literal["UNCLAIMED", "CLAIMED_BY_ME", "CLAIMED_BY_PEER"]
    sse_event: SseEventEnvelopeResponse
    trace_id: str


class AcquireResourceLeasesRequest(BaseModel):
    """Request body for acquiring shared resource leases in canonical order (`DEC-CONC-01`)."""

    model_config = ConfigDict(extra="forbid")

    resource_uris: list[str] = Field(min_length=1)
    holder_run_id: str = Field(min_length=1, max_length=128)
    holder_root_run_id: str = Field(min_length=1, max_length=128)
    holder_step_execution_id: str = Field(min_length=1, max_length=128)
    holder_parent_run_id: str | None = None
    ancestor_run_ids: list[str] = Field(default_factory=list)
    ttl_seconds: int = Field(default=120, ge=1, le=3600)


class ResourceLeaseItemResponse(BaseModel):
    """Active resource lease with monotonic `fencing_token` (`DEC-CONC-01`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    resource_uri: str
    resource_class: str
    holder_run_id: str
    holder_root_run_id: str
    holder_parent_run_id: str | None = None
    holder_step_execution_id: str
    fencing_token: int = Field(ge=1)
    acquired_at: str
    expires_at: str


class AcquireResourceLeasesResponse(BaseModel):
    """Response returned after canonical acquisition of shared resource leases (`DEC-CONC-01`)."""

    model_config = ConfigDict(extra="forbid")

    leases: list[ResourceLeaseItemResponse]
    canonical_order: list[str]
    trace_id: str


class ValidateFencedWriteRequest(BaseModel):
    """Request body for validating a monotonic fencing token before write (`DEC-CONC-01`)."""

    model_config = ConfigDict(extra="forbid")

    resource_uri: str = Field(min_length=1, max_length=512)
    fencing_token: int
    payload: dict[str, Any] = Field(default_factory=dict)


class ValidateFencedWriteResponse(BaseModel):
    """Response returned when a fenced connector write is accepted (`DEC-CONC-01`)."""

    model_config = ConfigDict(extra="forbid")

    resource_uri: str
    fencing_token: int
    resource_class: str
    status: Literal["COMMITTED_FENCED"]
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str
