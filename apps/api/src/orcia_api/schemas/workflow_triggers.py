"""OpenAPI 3.1 HTTP Transport Schemas for Workflow Triggers (`Story 7.2`, `AD-18`, `AD-21.3`)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.settings_and_studio import SecretInputPayload, SecretStatusResponse

WorkflowTriggerTypeLiteral = Literal[
    "WEBHOOK",
    "LOG_SINK_ALERT",
    "CRON",
    "OUTBOX_EVENT",
    "MANUAL_AUTONOMOUS",
]
WorkflowTriggerStatusLiteral = Literal["ACTIVE", "PAUSED", "CIRCUIT_OPEN"]
TriggerDispatchOutcomeLiteral = Literal[
    "DISPATCHED",
    "DUPLICATE_SUPPRESSED",
    "SELF_TRIGGER_BLOCKED",
    "CIRCUIT_OPEN",
    "PAUSED",
    "FAILED_FUNCTIONAL",
]


class WorkflowTriggerResponse(BaseModel):
    """Serialized governed workflow trigger (Write-Only secret metadata only)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    trigger_key: str
    workspace_id: str
    workflow_id: str
    trigger_type: WorkflowTriggerTypeLiteral
    contract_id: str | None = None
    cron_expr: str | None = None
    cooldown_window_seconds: int
    service_principal_id: str | None = None
    max_runs_per_hour: int
    max_daily_cost_usd: float
    max_consecutive_failures: int
    consecutive_failures: int = 0
    status: WorkflowTriggerStatusLiteral
    auto_help_on_publish: bool = False
    last_fired_at_iso: str | None = None
    log_sink_service: str | None = None
    log_sink_query_text: str | None = None
    outbox_event_filter: str | None = None
    webhook_secret_status: SecretStatusResponse


class WorkflowTriggerListResponse(BaseModel):
    """List of workflow triggers for a Studio V2 workflow."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    workflow_id: str
    items: list[WorkflowTriggerResponse] = Field(default_factory=list)
    trace_id: str


class CreateWorkflowTriggerRequest(BaseModel):
    """Create a governed workflow trigger attached to an active autonomy contract."""

    model_config = ConfigDict(extra="forbid")

    trigger_type: WorkflowTriggerTypeLiteral
    trigger_key: str | None = Field(default=None, max_length=128)
    cron_expr: str | None = Field(default=None, max_length=128)
    cooldown_window_seconds: int = Field(default=300, ge=0, le=86400)
    max_runs_per_hour: int = Field(default=10, ge=1, le=1000)
    max_daily_cost_usd: float = Field(default=25.0, ge=0.0)
    max_consecutive_failures: int = Field(default=3, ge=1, le=20)
    auto_help_on_publish: bool = False
    webhook_secret: SecretInputPayload | None = None
    log_sink_service: str | None = Field(default=None, max_length=128)
    log_sink_query_text: str | None = Field(default=None, max_length=255)
    outbox_event_filter: str | None = Field(default=None, max_length=128)
    status: Literal["ACTIVE", "PAUSED"] = "ACTIVE"


class UpdateWorkflowTriggerRequest(BaseModel):
    """Update a workflow trigger (status, CRON, opt-in help, or Write-Only secret)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ACTIVE", "PAUSED"] | None = None
    cron_expr: str | None = Field(default=None, max_length=128)
    cooldown_window_seconds: int | None = Field(default=None, ge=0, le=86400)
    max_runs_per_hour: int | None = Field(default=None, ge=1, le=1000)
    max_daily_cost_usd: float | None = Field(default=None, ge=0.0)
    max_consecutive_failures: int | None = Field(default=None, ge=1, le=20)
    auto_help_on_publish: bool | None = None
    webhook_secret: SecretInputPayload | None = None
    log_sink_service: str | None = Field(default=None, max_length=128)
    log_sink_query_text: str | None = Field(default=None, max_length=255)
    outbox_event_filter: str | None = Field(default=None, max_length=128)


class DeleteWorkflowTriggerResponse(BaseModel):
    """Confirmation of deleted workflow trigger."""

    model_config = ConfigDict(extra="forbid")

    deleted_id: str
    trace_id: str


class FireManualTriggerRequest(BaseModel):
    """Payload to fire a `MANUAL_AUTONOMOUS` (or test) trigger idempotently."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


class TriggerDispatchResponse(BaseModel):
    """Result of firing a trigger via manual action, webhook, or alert fallback."""

    model_config = ConfigDict(extra="forbid")

    dispatched: bool
    outcome: TriggerDispatchOutcomeLiteral
    trigger_id: str
    idempotency_key: str
    dbos_workflow_id: str
    run_id: str | None = None
    attempts: int = 0
    reason: str | None = None
    trace_id: str


class WorkflowTriggerWebhookRequest(BaseModel):
    """Inbound payload for `POST /api/v1/webhooks/triggers/{trigger_id}`."""

    model_config = ConfigDict(extra="allow")

    delivery_key: str | None = Field(default=None, max_length=255)
    event_name: str = Field(default="webhook.event", max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


class LogSinkAlertWebhookRequest(BaseModel):
    """Fallback platform log-sink alert webhook (`POST /api/v1/triggers/alerts`, `AD-23.5`)."""

    model_config = ConfigDict(extra="allow")

    trigger_id: str = Field(..., min_length=1)
    service: str = Field(default="api", max_length=128)
    exception_type: str = Field(default="RuntimeError", max_length=128)
    message: str = Field(default="Platform log alert", max_length=1000)
    traceback: str | None = None
    delivery_key: str | None = Field(default=None, max_length=255)
