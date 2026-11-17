"""HTTP OpenAPI 3.1 transport schemas for Epic 16 Reflexive Execution & Surgical Exploration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.agents.reflexive_schemas import (
    ProcessOrchestrationType,
    ReflexiveEffortMode,
    ReflexiveExecutionStatus,
    TraceEventKind,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalFileBadgeCode,
    SurgicalPrimitiveName,
)
from orcia_core.workflows.schemas_v2 import EffortLevel


class SurgicalLineEntryItem(BaseModel):
    """HTTP transport item representing a single 1-indexed line slice entry."""

    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(ge=1)
    content: str


class SurgicalOutlineNodeItem(BaseModel):
    """HTTP transport item representing a structural heading, key, or symbol."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    line_number: int = Field(ge=1)
    level: int = Field(default=1, ge=1, le=6)


class SurgicalSnippetMatchItem(BaseModel):
    """HTTP transport item representing a bounded `#Lstart-end` workspace match."""

    model_config = ConfigDict(extra="forbid")

    resource_uri: str
    display_filename: str
    file_badge_code: SurgicalFileBadgeCode = "DOC"
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    line_anchor: str = ""
    excerpt: str


class SurgicalInspectLinesResponse(BaseModel):
    """HTTP response envelope for `GET /api/v1/sources/inspect-lines`."""

    model_config = ConfigDict(extra="forbid")

    kind: SurgicalPrimitiveName = SurgicalPrimitiveName.INSPECT_RESOURCE_LINES
    resource_uri: str
    display_filename: str
    file_badge_code: SurgicalFileBadgeCode = "DOC"
    formatted_badge: str = ""
    exists: bool = True
    start_line: int | None = None
    end_line: int | None = None
    total_lines: int = 0
    lines: list[SurgicalLineEntryItem] = Field(default_factory=list)
    outline: list[SurgicalOutlineNodeItem] = Field(default_factory=list)
    snippets: list[SurgicalSnippetMatchItem] = Field(default_factory=list)
    check_label: str | None = None
    summary: str = ""
    sha256: str | None = None
    redacted: bool = False
    redacted_reason: str | None = None
    permission_request_hint: str | None = None
    trace_id: str


class SurgicalExploreRequest(BaseModel):
    """HTTP request payload for `POST /api/v1/sources/surgical-explore`."""

    model_config = ConfigDict(extra="forbid")

    primitive: SurgicalPrimitiveName
    resource_uri: str = Field(default="", max_length=1024)
    query: str = Field(default="", max_length=256)
    start_line: int = Field(default=1, ge=1, le=1_000_000)
    end_line: int = Field(default=200, ge=1, le=1_000_000)
    max_results: int = Field(default=20, ge=1, le=50)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class SurgicalExploreResponse(SurgicalInspectLinesResponse):
    """HTTP response envelope for `POST /api/v1/sources/surgical-explore`."""


class RequestedWritePreviewInput(BaseModel):
    """HTTP transport input specifying an external write preview to gate (`Story 16.2`)."""

    model_config = ConfigDict(extra="forbid")

    connector_type: str = Field(default="mcp:default", min_length=1, max_length=64)
    action: str = Field(default="write_resource", min_length=1, max_length=128)
    target_resource_uri: str = Field(min_length=1, max_length=1024)
    action_summary: str = Field(min_length=1, max_length=512)
    payload: dict[str, Any] = Field(default_factory=dict)


class StartReflexiveExecutionRequest(BaseModel):
    """HTTP request payload for `POST /api/v1/executions/reflexive` (`Story 16.2`)."""

    model_config = ConfigDict(extra="forbid")

    actor_slug: str = Field(default="assistant-agent", min_length=1, max_length=128)
    objective: str = Field(min_length=1, max_length=8000)
    effort_level: EffortLevel = EffortLevel.MEDIUM
    effort_mode: ReflexiveEffortMode | None = None
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)
    allow_sub_agent_delegation: bool = False
    available_delegate_agents: list[str] = Field(default_factory=list)
    initial_resources: list[str] = Field(default_factory=list)
    requested_write_preview: RequestedWritePreviewInput | None = None
    run_in_background: bool = False
    step_delay_ms: int = Field(default=0, ge=0, le=5_000)


class SignedApprovalTokenInput(BaseModel):
    """HTTP transport representation of an HMAC-SHA256 `SignedApprovalToken`."""

    model_config = ConfigDict(extra="forbid")

    preview_id: str = Field(min_length=1, max_length=128)
    approver_user_id: str = Field(min_length=1, max_length=128)
    approved_at_utc: str = Field(min_length=1, max_length=64)
    payload_sha256: str = Field(min_length=64, max_length=64)
    broker_signature: str = Field(min_length=16, max_length=128)


class ApproveReflexiveWriteRequest(BaseModel):
    """HTTP request payload for `POST /api/v1/executions/{execution_id}/approve-write`."""

    model_config = ConfigDict(extra="forbid")

    approved: bool = True
    preview_id: str = Field(min_length=1, max_length=128)
    rejection_reason: str = Field(default="", max_length=1024)
    approval_token: SignedApprovalTokenInput | None = None


class AgentTraceEventItem(BaseModel):
    """HTTP transport item for a typed SSE / timeline `AgentTraceEvent`."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    execution_id: str
    sequence_index: int = Field(ge=0)
    turn_index: int = Field(ge=0)
    kind: TraceEventKind
    timestamp_utc: str
    status_label: str | None = None
    group_title: str | None = None
    delta_text: str | None = None
    thought_duration_ms: int | None = None
    resource_uri: str | None = None
    display_filename: str | None = None
    file_badge_code: SurgicalFileBadgeCode | None = None
    formatted_badge: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    check_label: str | None = None
    delegate_agent_slug: str | None = None
    write_preview_id: str | None = None
    redacted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingWritePreviewItem(BaseModel):
    """HTTP transport envelope for a pending `WritePreviewCard` (`WAITING_WRITE_PREVIEW`)."""

    model_config = ConfigDict(extra="forbid")

    preview_id: str
    connector_type: str
    action: str
    target_resource_uri: str
    action_summary: str
    diff_or_payload_preview: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_sha256: str
    created_at_utc: str


class ClaimCheckPointerItem(BaseModel):
    """HTTP transport envelope for a SHA-256 `ClaimCheckPointer` artifact."""

    model_config = ConfigDict(extra="forbid")

    s3_uri: str
    sha256: str
    byte_size: int = Field(ge=0)
    mime_type: str = "text/markdown"
    inline_preview: str | None = None


class ReflexiveScratchpadItem(BaseModel):
    """HTTP transport item for a `ReflexiveScratchpadEntry`."""

    model_config = ConfigDict(extra="forbid")

    turn_index: int = Field(ge=0)
    action_kind: str
    resource_uri: str = ""
    line_anchor: str = ""
    formatted_badge: str = ""
    summary: str = ""
    excerpt: str = ""
    redacted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReflexiveExecutionSnapshotResponse(BaseModel):
    """HTTP response envelope for `ReflexiveSessionSnapshot` (`Story 16.2`, `F5` survival)."""

    model_config = ConfigDict(extra="forbid")

    execution_id: str
    workspace_id: str | None = None
    actor_slug: str
    actor_user_id: str | None = None
    objective: str
    orchestration_type: ProcessOrchestrationType
    effort_level: EffortLevel
    effort_mode: ReflexiveEffortMode
    status: ReflexiveExecutionStatus
    force_final: bool = False
    allow_sub_agent_delegation: bool = False
    delegation_depth: int = Field(ge=0, le=1)
    available_delegate_agents: list[str] = Field(default_factory=list)
    turns_used: int = Field(ge=0)
    max_turns: int = Field(ge=1)
    tokens_used: int = Field(ge=0)
    max_budget_tokens: int = Field(ge=256)
    scratchpad: list[ReflexiveScratchpadItem] = Field(default_factory=list)
    trace_events: list[AgentTraceEventItem] = Field(default_factory=list)
    pending_write_preview: PendingWritePreviewItem | None = None
    final_markdown: str = ""
    artifact_pointer: ClaimCheckPointerItem | None = None
    created_at_utc: str
    updated_at_utc: str
    expires_at_utc: str
    trace_id: str
