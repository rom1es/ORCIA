"""Pydantic v2 OpenAPI 3.1 schemas for Story 3.2: Step Executions & Append-Only Blackboard."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.blackboard.models import (
    MemlogMarkerType,
    SnapshotBranchStatus,
    StepExecutionStatus,
)
from orcia_core.orchestration.models import (
    WorkflowExecutionRegime,
    WorkflowStepType,
)


class StepMemlogSchemaItem(BaseModel):
    """Structured reasoning, assumption, or divergence entry in `step_memlog_jsonb`."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    step_key: str
    marker_type: MemlogMarkerType
    summary: str
    details: str
    source_uris: list[str] = Field(default_factory=list)


class BlackboardSnapshotSchemaItem(BaseModel):
    """Immutable append-only checkpoint row in `blackboard_snapshots` (`AD-2`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    snapshot_key: str
    run_id: str
    step_execution_id: str
    parent_snapshot_id: str | None = None
    step_key: str
    branch_status: SnapshotBranchStatus
    artifact_payload: dict[str, Any]
    artifact_cas_key: str
    artifact_sha256: str = Field(..., min_length=64, max_length=64)
    memlog_summary: list[StepMemlogSchemaItem] = Field(default_factory=list)
    superseded_snapshot_ids: list[str] = Field(default_factory=list)


class StepExecutionSchemaItem(BaseModel):
    """Mutable draft and execution state for a single workflow step (`AD-2`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    step_execution_key: str
    run_id: str
    step_key: str
    step_index: int = Field(..., ge=0)
    step_type: WorkflowStepType
    execution_mode: WorkflowExecutionRegime
    status: StepExecutionStatus
    attempt_count: int = Field(..., ge=0, le=10)
    max_agent_retries: int = Field(..., ge=1, le=10)
    draft_artifact: dict[str, Any]
    draft_cas_key: str | None = None
    step_memlog: list[StepMemlogSchemaItem] = Field(default_factory=list)
    hydrated_input_uris: list[str] = Field(default_factory=list)
    child_run_id: str | None = None
    committed_snapshot_id: str | None = None
    cost_usd: float = Field(..., ge=0.0)


class HydratedStepContextSchemaItem(BaseModel):
    """Filtered Just-In-Time context injected into Step $k$ (`JitStepHydrator`, `AD-13`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    step_key: str
    step_title: str
    step_type: WorkflowStepType
    execution_mode: WorkflowExecutionRegime
    step_directive: str
    declared_input_uris: list[str]
    resolved_inputs: dict[str, Any]
    future_step_instructions_leaked: int = Field(default=0, ge=0, le=0)
    undeclared_artifacts_leaked: int = Field(default=0, ge=0, le=0)


class StepHydrateRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/runs/steps/hydrate`."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)


class StepHydrateResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/runs/steps/hydrate`."""

    model_config = ConfigDict(extra="forbid")

    hydrated_context: HydratedStepContextSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class StepExecuteRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/runs/steps/execute`."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    commit_immediately: bool = Field(default=True)
    simulated_divergence: str | None = Field(default=None, max_length=512)
    cost_usd: float = Field(default=0.25, ge=0.0, le=500.0)


class StepExecuteResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/runs/steps/execute`."""

    model_config = ConfigDict(extra="forbid")

    step_execution: StepExecutionSchemaItem
    committed_snapshot: BlackboardSnapshotSchemaItem | None = None
    trace_id: str = Field(..., min_length=32, max_length=32)


class BackgroundAuditRunRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/runs/fast-path-audit` (`UJ-10`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=128)
    divergence_note: str = Field(
        default="Écart seuil TRA : Confluence v12 indique 500€ vs Codebase git:// indique 350€",
        min_length=1,
        max_length=512,
    )


class BackgroundAuditReportSchemaItem(BaseModel):
    """Consolidated report for `BACKGROUND_FAST_PATH` (`UJ-10`, `AD-13`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_uri: str
    total_steps_committed: int = Field(..., ge=0)
    assumptions: list[StepMemlogSchemaItem]
    suspected_code_bugs: list[StepMemlogSchemaItem]
    suspected_obsolete_docs: list[StepMemlogSchemaItem]
    sse_event_topic: str
    sse_latency_ms: float = Field(..., ge=0.0, lt=500.0)


class BackgroundAuditRunResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/runs/fast-path-audit`."""

    model_config = ConfigDict(extra="forbid")

    report: BackgroundAuditReportSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class RunBlackboardStateResponse(BaseModel):
    """Response payload for `GET /api/v1/orchestration/runs/{run_id}/blackboard`."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    root_run_id: str
    accumulated_root_cost_usd: float
    step_executions: list[StepExecutionSchemaItem]
    active_snapshots: list[BlackboardSnapshotSchemaItem]
    trace_id: str = Field(..., min_length=32, max_length=32)
