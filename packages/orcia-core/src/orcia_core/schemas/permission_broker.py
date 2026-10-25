"""Pydantic v2 contracts for Story 1.4 Permission Broker & Passthrough / Service Principal API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.permissions.broker import (
    BrokerConnectorScheme,
    BrokerStepState,
    BrokerTicketAction,
    BrokerTicketStatus,
)
from orcia_core.permissions.models import ExecutionIdentityMode


class PermissionBrokerPolicyItem(BaseModel):
    """Serialized Permission Broker KB policy (`permission_broker_policies`, FR-22)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=128)
    policy_key: str = Field(..., min_length=1, max_length=128)
    uri_pattern: str = Field(..., min_length=1, max_length=512)
    connector_scheme: BrokerConnectorScheme
    required_role: str = Field(..., min_length=1, max_length=128)
    approver_team: str = Field(..., min_length=1, max_length=128)
    request_url_template: str = Field(..., min_length=8, max_length=2048)
    sla_hours: int = Field(..., ge=1, le=720)
    procedure_markdown: str = Field(default="", max_length=16384)
    service_principal_allowed: bool = False
    approved_by_admin_id: str | None = Field(default=None, max_length=128)
    human_anchor_author_id: str | None = Field(default=None, max_length=128)
    human_anchor_signature: str | None = Field(default=None, max_length=512)
    freshness_ttl_days: int = Field(default=90, ge=1, le=3650)


class PermissionBrokerTicketItem(BaseModel):
    """Serialized blocked step ticket (`permission_broker_tickets`, UX-DR11, FR-22)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=128)
    ticket_key: str = Field(..., min_length=1, max_length=128)
    workspace_id: str | None = Field(default=None, max_length=128)
    requester_user_id: str = Field(..., min_length=1, max_length=128)
    policy_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    step_number: int = Field(..., ge=1, le=999)
    step_state: BrokerStepState
    status: BrokerTicketStatus
    target_uri: str = Field(..., min_length=4, max_length=1024)
    connector_scheme: BrokerConnectorScheme
    execution_identity: ExecutionIdentityMode
    upstream_http_status: Literal[401, 403]
    required_role: str = Field(..., min_length=1, max_length=128)
    approver_team: str = Field(..., min_length=1, max_length=128)
    sla_hours: int = Field(..., ge=1, le=720)
    jira_request_url: str = Field(..., min_length=8, max_length=4096)
    permission_broker_hint: str = Field(..., min_length=8, max_length=2048)
    procedure_markdown: str = Field(default="", max_length=16384)


class PermissionBrokerStateResponse(BaseModel):
    """Consolidated Permission Broker state (KB policies + blocked step tickets)."""

    model_config = ConfigDict(extra="forbid")

    policies: list[PermissionBrokerPolicyItem]
    tickets: list[PermissionBrokerTicketItem]
    trace_id: str = Field(..., min_length=32, max_length=32)


class PermissionPolicyImportMarkdownRequest(BaseModel):
    """Request payload for importing a Markdown + YAML frontmatter KB policy (`FR-22`)."""

    model_config = ConfigDict(extra="forbid")

    markdown_text: str = Field(..., min_length=16, max_length=16384)
    policy_key: str | None = Field(default=None, min_length=1, max_length=128)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class PermissionPolicyImportMarkdownResponse(BaseModel):
    """Response payload after importing a Markdown + YAML frontmatter KB policy."""

    model_config = ConfigDict(extra="forbid")

    policy: PermissionBrokerPolicyItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class PermissionCheckRequest(BaseModel):
    """Request payload for checking or intercepting external connector access (`AD-6`, `FR-22`)."""

    model_config = ConfigDict(extra="forbid")

    target_uri: str = Field(..., min_length=6, max_length=512)
    execution_identity: ExecutionIdentityMode = "passthrough"
    step_key: str = Field(default="step-02-execution", min_length=1, max_length=128)
    step_number: int = Field(default=2, ge=1, le=999)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)
    resource_id: str | None = Field(default=None, min_length=1, max_length=128)
    simulated_upstream_status: Literal[200, 401, 403] | None = None
    granted_external_roles: list[str] = Field(default_factory=list, max_length=32)
    raise_on_denied: bool = True


class PermissionCheckResponse(BaseModel):
    """Response payload when `check-access` completes without raising HTTP 403."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    status: Literal["GRANTED", "WAITING_FOR_PERMISSION"]
    execution_identity: ExecutionIdentityMode
    target_uri: str = Field(..., min_length=6, max_length=512)
    connector_scheme: BrokerConnectorScheme
    policy: PermissionBrokerPolicyItem
    ticket: PermissionBrokerTicketItem | None = None
    permission_broker_hint: str | None = None
    trace_id: str = Field(..., min_length=32, max_length=32)


class PermissionTicketActionRequest(BaseModel):
    """Request payload for pausing or replaying a blocked step ticket (`UX-DR11`, `FR-22`)."""

    model_config = ConfigDict(extra="forbid")

    action: BrokerTicketAction
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class PermissionTicketActionResponse(BaseModel):
    """Response payload after transitioning a Permission Broker ticket (`PAUSED` / `REPLAYED`)."""

    model_config = ConfigDict(extra="forbid")

    ticket: PermissionBrokerTicketItem
    trace_id: str = Field(..., min_length=32, max_length=32)
