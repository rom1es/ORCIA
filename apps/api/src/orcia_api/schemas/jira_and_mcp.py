"""Pydantic v2 HTTP transport schemas for Story 4.4 Jira Staged Actions, Webhook & `/api/v1/mcp`."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JiraJqlSearchRequest(BaseModel):
    """Request payload for real-time JQL search across workspace Jira projects (`FR-24`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1, max_length=128)
    project_alias: str = Field(..., min_length=1, max_length=128)
    jql: str = Field(..., min_length=1, max_length=1024)


class JiraJqlSearchResponse(BaseModel):
    """Response payload returning matching Jira issues for the selected workspace project."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    project_alias: str
    project_key: str
    issues: list[dict[str, Any]]
    trace_id: str = Field(..., min_length=32, max_length=32)


class StageJiraActionRequest(BaseModel):
    """Request payload to stage a multi-project Jira operation (`AD-5`, `FR-24`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)
    project_alias: str = Field(..., min_length=1, max_length=128)
    action_type: Literal["create_issue", "update_issue", "add_comment", "transition_issue"]
    summary: str = Field(..., min_length=1, max_length=512)
    issue_key: str | None = Field(default=None, max_length=64)
    target_transition: str | None = Field(default=None, max_length=128)
    fields_payload: dict[str, Any] = Field(default_factory=dict)


class StagedJiraActionItemSchema(BaseModel):
    """Serialized staged or executed Jira action."""

    model_config = ConfigDict(extra="forbid")

    staged_action_id: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    project_alias: str
    project_key: str
    action_type: Literal["create_issue", "update_issue", "add_comment", "transition_issue"]
    issue_key: str | None
    summary: str
    target_transition: str | None
    fields_payload: dict[str, Any]
    status: Literal["STAGED", "EXECUTED"]
    idempotency_key: str
    provenance_run_lock_uri: str | None = None
    provenance_run_lock_sha256: str | None = None
    executed_issue_key: str | None = None
    replayed_from_cache: bool = False


class StageJiraActionResponse(BaseModel):
    """Response payload after staging a Jira action in `step_executions.draft_artifact_jsonb`."""

    model_config = ConfigDict(extra="forbid")

    staged_action: StagedJiraActionItemSchema
    draft_artifact_jsonb: dict[str, Any]
    trace_id: str = Field(..., min_length=32, max_length=32)


class StagedJiraActionListResponse(BaseModel):
    """Response payload listing staged or executed Jira actions (`Story 4.4`, `AD-5`)."""

    model_config = ConfigDict(extra="forbid")

    actions: list[StagedJiraActionItemSchema]
    trace_id: str = Field(..., min_length=32, max_length=32)


class CommitStagedJiraActionRequest(BaseModel):
    """Request payload to execute a staged Jira action on Gate pass (`AD-5`, `AD-11`)."""

    model_config = ConfigDict(extra="forbid")

    staged_action_id: str = Field(..., min_length=1, max_length=128)
    gate_status: Literal["PASS", "FAIL", "WAITING_HUMAN"]
    run_lock_sha256: str = Field(..., min_length=8, max_length=128)


class CommitStagedJiraActionResponse(BaseModel):
    """Response payload after executing a staged Jira action with `run-lock.json` provenance."""

    model_config = ConfigDict(extra="forbid")

    executed_action: StagedJiraActionItemSchema
    trace_id: str = Field(..., min_length=32, max_length=32)


class JiraIssueUpdatedWebhookRequest(BaseModel):
    """Incoming `jira:issue_updated` webhook payload (`FR-16`)."""

    model_config = ConfigDict(extra="forbid")

    webhook_event: str = Field(default="jira:issue_updated", min_length=1, max_length=128)
    issue_key: str = Field(..., min_length=3, max_length=64)
    new_status: str = Field(..., min_length=1, max_length=64)
    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)


class JiraIssueUpdatedWebhookResponse(BaseModel):
    """Response payload after handling `jira:issue_updated` (`< 500 ms`, `FR-16`)."""

    model_config = ConfigDict(extra="forbid")

    webhook_event: str
    issue_key: str
    project_key: str
    new_status: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    replay_triggered: bool
    outbox_event_id: str | None
    sse_channel: str
    processing_ms: float
    trace_id: str = Field(..., min_length=32, max_length=32)


class McpToolDescriptorSchema(BaseModel):
    """Serialized MCP tool descriptor (`AR-7`)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    mode: Literal["READ_ONLY", "GOVERNED_DRAFT_WRITE"]
    passthrough_required: bool
    blocks_human_authored_sections: bool


class McpToolsListResponse(BaseModel):
    """Response payload listing governed MCP tools (`/api/v1/mcp/tools`, `AR-7`)."""

    model_config = ConfigDict(extra="forbid")

    tools: list[McpToolDescriptorSchema]
    trace_id: str = Field(..., min_length=32, max_length=32)


class McpToolCallRequest(BaseModel):
    """Request payload for calling a governed MCP tool (`/api/v1/mcp/call`, `FR-24`, `AR-7`)."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., min_length=1, max_length=128)
    workspace_id: str = Field(..., min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)
    ide_client: str = Field(default="vscode", min_length=1, max_length=64)
    execution_identity: str = Field(default="passthrough", min_length=1, max_length=64)


class McpToolCallResponse(BaseModel):
    """Response payload for a governed MCP tool call."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    ide_client: str
    execution_identity: Literal["passthrough"]
    workspace_id: str
    status: Literal["OK"]
    data: dict[str, Any]
    trace_id: str = Field(..., min_length=32, max_length=32)
