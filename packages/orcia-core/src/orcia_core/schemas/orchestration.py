"""Pydantic v2 schemas for Story 3.1: Workflow-as-Code, Multi-Audience Templates & Run Lock."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.catalog.models import AdaptiveGatePolicy, ScalarValue
from orcia_core.orchestration.models import (
    TieBreakPolicy,
    WorkflowCriticality,
    WorkflowEngineeringMode,
    WorkflowExecutionRegime,
    WorkflowRunStatus,
    WorkflowStepType,
)
from orcia_core.permissions.models import ExecutionIdentityMode
from orcia_core.schemas.catalog import RunLockSourceTripletItem


class WorkflowValidationFindingSchemaItem(BaseModel):
    """Line-accurate validation finding for a Workflow-as-Code YAML/JSON manifest."""

    model_config = ConfigDict(extra="forbid")

    line: int = Field(..., ge=1)
    rule_code: str
    field_path: str
    message: str


class WorkflowStepSpecSchemaItem(BaseModel):
    """Serialized step node in a validated Workflow-as-Code DAG."""

    model_config = ConfigDict(extra="forbid")

    step_key: str
    title: str
    step_type: WorkflowStepType
    instructions: str
    depends_on: list[str]
    feedback_target_step_key: str | None = None
    max_agent_retries: int = Field(..., ge=1, le=10)
    agent_uri: str | None = None
    skill_uri: str | None = None
    sub_workflow_uri: str | None = None
    input_mapping: dict[str, str]
    output_mapping: dict[str, str]
    template_key: str | None = None
    kb_uris: list[str]
    human_authored_required: bool
    requires_human_gate: bool
    declares_intention: bool
    writes_code: bool
    reverse_doc_from_code: bool
    verification_window_seconds: int | None = None
    line_number: int = Field(..., ge=1)


class WorkflowAsCodeDefinitionSchemaItem(BaseModel):
    """Serialized Workflow-as-Code DAG supporting `SUB_WORKFLOW <= 3` and criticality."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str | None = None
    uri: str
    title: str
    description: str
    version: str
    criticality: WorkflowCriticality
    execution_regime: WorkflowExecutionRegime
    tie_break_policy: TieBreakPolicy
    mode: WorkflowEngineeringMode
    adaptive_gate_policy: AdaptiveGatePolicy
    max_cost_usd: float = Field(..., ge=0.0)
    scalars: dict[str, ScalarValue]
    datasources: list[str]
    rules: list[str]
    facts: list[str]
    steps: list[WorkflowStepSpecSchemaItem]
    sha256: str = Field(..., min_length=64, max_length=64)
    max_nesting_depth: int = Field(..., ge=0, le=3)


class WorkflowManifestValidateRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/workflows/validate`."""

    model_config = ConfigDict(extra="forbid")

    raw_manifest: str = Field(..., min_length=1, max_length=65536)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class WorkflowManifestValidateResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/workflows/validate`."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    workflow: WorkflowAsCodeDefinitionSchemaItem | None = None
    findings: list[WorkflowValidationFindingSchemaItem]
    resolved_max_nesting_depth: int = Field(..., ge=0)
    topological_order: list[str]
    trace_id: str = Field(..., min_length=32, max_length=32)


class WorkflowManifestRegisterRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/workflows/register`."""

    model_config = ConfigDict(extra="forbid")

    raw_manifest: str = Field(..., min_length=1, max_length=65536)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class WorkflowManifestRegisterResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/workflows/register`."""

    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowAsCodeDefinitionSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class CompiledMarkdownChunkSchemaItem(BaseModel):
    """Cognitive chunk (`<= 800 words`) produced for human Canvas review (`FR-6`)."""

    model_config = ConfigDict(extra="forbid")

    chunk_index: int = Field(..., ge=0)
    section_key: str
    section_title: str
    markdown_content: str
    word_count: int = Field(..., ge=0)
    human_authored_required: bool


class CompiledArtifactTemplateSchemaItem(BaseModel):
    """Dual-compiled Multi-Audience Artifact Template (`FR-12`)."""

    model_config = ConfigDict(extra="forbid")

    template_key: str
    uri: str
    version: str
    human_markdown_view: str
    cognitive_chunks: list[CompiledMarkdownChunkSchemaItem]
    agent_json_schema: dict[str, Any]
    bound_ontology_terms: list[str]
    sha256: str = Field(..., min_length=64, max_length=64)


class ArtifactTemplateCompileRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/templates/compile`."""

    model_config = ConfigDict(extra="forbid")

    template_key: str = Field(..., min_length=1, max_length=128)
    variables: dict[str, str] = Field(default_factory=dict)
    workspace_id: str = Field(default="ws-solution-paiement", min_length=1, max_length=128)


class ArtifactTemplateCompileResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/templates/compile`."""

    model_config = ConfigDict(extra="forbid")

    compiled_template: CompiledArtifactTemplateSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class SubWorkflowLockSchemaItem(BaseModel):
    """Recursive sub-workflow lock entry in `run-lock.json` (`FR-30`, `AD-18`)."""

    model_config = ConfigDict(extra="forbid")

    step_key: str
    workflow_uri: str
    workflow_version: str
    workflow_sha256: str = Field(..., min_length=64, max_length=64)
    effective_workflow_sha256: str = Field(..., min_length=64, max_length=64)
    nesting_depth: int = Field(..., ge=1, le=3)
    applied_override_keys: list[str]
    sources: list[RunLockSourceTripletItem]
    sub_workflow_locks: list[SubWorkflowLockSchemaItem] = Field(default_factory=list)


class RecursiveRunLockManifestSchemaItem(BaseModel):
    """Extended `run-lock.json` pinning sources, overrides, KB hash, and sub-workflows."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workspace_id: str
    workflow_uri: str
    workflow_version: str
    workflow_sha256: str = Field(..., min_length=64, max_length=64)
    effective_workflow_sha256: str = Field(..., min_length=64, max_length=64)
    overrides_sha256: str = Field(..., min_length=64, max_length=64)
    kb_snapshot_hash: str
    applied_override_keys: list[str]
    sources: list[RunLockSourceTripletItem]
    sub_workflow_locks: list[SubWorkflowLockSchemaItem]
    manifest_sha256: str = Field(..., min_length=64, max_length=64)


class WorkflowRunSchemaItem(BaseModel):
    """Instantiated Workflow Run or nested Sub-Workflow Run (`nesting_depth <= 3`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    run_key: str
    workspace_id: str
    workflow_def_id: str
    workflow_uri: str
    parent_run_id: str | None = None
    parent_step_execution_id: str | None = None
    root_run_id: str
    nesting_depth: int = Field(..., ge=0, le=3)
    execution_regime: WorkflowExecutionRegime
    criticality: WorkflowCriticality
    trigger_id: str | None = None
    trigger_idempotency_key: str | None = None
    status: WorkflowRunStatus
    initiated_by_user_id: str | None = None
    execution_identity_mode: ExecutionIdentityMode
    budget_max_usd: float = Field(..., ge=0.0)
    run_lock: RecursiveRunLockManifestSchemaItem


class WorkflowRunInstantiateRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/runs/instantiate`."""

    model_config = ConfigDict(extra="forbid")

    workflow_uri: str = Field(..., min_length=8, max_length=512)
    workspace_id: str = Field(..., min_length=1, max_length=128)
    parent_run_id: str | None = Field(default=None, min_length=1, max_length=128)
    parent_step_execution_id: str | None = Field(default=None, min_length=1, max_length=128)
    trigger_id: str | None = Field(default=None, min_length=1, max_length=128)
    trigger_idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)
    execution_identity_mode: ExecutionIdentityMode = "passthrough"


class WorkflowRunInstantiateResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/runs/instantiate`."""

    model_config = ConfigDict(extra="forbid")

    run: WorkflowRunSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class OrchestrationSetupStateResponse(BaseModel):
    """Response payload for `GET /api/v1/orchestration/state`."""

    model_config = ConfigDict(extra="forbid")

    workflows: list[WorkflowAsCodeDefinitionSchemaItem]
    runs: list[WorkflowRunSchemaItem]
    compiled_default_template: CompiledArtifactTemplateSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)
