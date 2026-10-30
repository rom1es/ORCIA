"""HTTP/OpenAPI 3.1 schemas for Story 5.2 (Workspace Control Center, `RunAccessGuard` & `⌘K`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupervisedRunItemResponse(BaseModel):
    """Workflow Run item in Tab 1 (`RUNS_AND_ARTIFACTS`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workspace_id: str
    workspace_name: str
    workflow_key: str
    title: str
    status: Literal["RUNNING", "PAUSED_HUMAN_GATE", "PAUSED_ARBITRATION", "COMPLETED"]
    current_step_id: str
    current_step_key: str
    execution_mode: Literal["COACHING", "FAST_PATH"]
    access_mode: Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"]
    claimed_by_user_id: str | None = None
    claimed_by_display_name: str | None = None
    budget_consumed_usd: float
    blackboard_summary: str
    blackboard_payload_masked: bool = False


class SupervisedDatasourceItemResponse(BaseModel):
    """Attached datasource item in Tab 2 (`DATASOURCES`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    workspace_name: str
    alias: str
    scheme: str
    uri: str
    role: str
    execution_identity: str
    freshness_ttl_days: int
    tripartite_status: Literal["ALIGNED", "STALE_WARNING", "INDEXING"]


class GuidanceStepItemResponse(BaseModel):
    """Methodological guidance step in `<GuidanceDrawer />` (Tab 2)."""

    model_config = ConfigDict(extra="forbid")

    step_number: int
    title_fr: str
    description_fr: str
    action_command: str


class DeclarativeOverrideLayerResponse(BaseModel):
    """4-level override inspector item in Tab 3 (`WORKFLOWS_AND_OVERRIDES`)."""

    model_config = ConfigDict(extra="forbid")

    workflow_key: str
    title: str
    base_layer: str
    team_override: str
    workspace_override: str
    user_override: str
    spine_contract_ref: str


class WorkspaceGovernanceItemResponse(BaseModel):
    """Workspace product lifecycle & governance summary in Tab 4 (`TEAMS_AND_GOVERNANCE`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    slug: str
    name: str
    owner_org_unit_id: str
    visibility_mode: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED"]
    lifecycle_phase: Literal["RUN", "BUILD", "MIGRATION"]
    suggested_workflows: list[str]
    access_mode: Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"]
    finops_cost_usd: float | None = None
    blackboard_payload_masked: bool = False


class OrgUnitSummaryResponse(BaseModel):
    """Organization unit node in Tab 4 (`TEAMS_AND_GOVERNANCE`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    name: str
    unit_type: Literal["ENTERPRISE", "BU", "TRIBE", "TEAM", "SUB_TEAM"]
    parent_id: str | None = None


class ControlCenterOverviewResponse(BaseModel):
    """Consolidated 4-tab fractal payload (`GET /api/v1/control-center/overview`, `Story 5.2`)."""

    model_config = ConfigDict(extra="forbid")

    scope_type: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
    scope_id: str
    scope_label: str
    viewer_access_mode: Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"]
    observer_banner_fr: str | None = None
    consolidated_finops_usd: float
    contributor_runs: list[SupervisedRunItemResponse]
    observer_runs: list[SupervisedRunItemResponse]
    datasources: list[SupervisedDatasourceItemResponse]
    guidance_steps: list[GuidanceStepItemResponse]
    workflow_overrides: list[DeclarativeOverrideLayerResponse]
    org_units: list[OrgUnitSummaryResponse]
    workspaces_governance: list[WorkspaceGovernanceItemResponse]
    trace_id: str


class UpdateWorkspaceLifecycleRequest(BaseModel):
    """Request body for updating product lifecycle (`RUN | BUILD | MIGRATION`)."""

    model_config = ConfigDict(extra="forbid")

    lifecycle_phase: Literal["RUN", "BUILD", "MIGRATION"]


class RunMutationGuardCheckRequest(BaseModel):
    """Request body for checking `RunAccessGuard` before mutating a step/artifact/Gate."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="mutate_step", min_length=1, max_length=64)


class RunMutationGuardCheckResponse(BaseModel):
    """Response confirming `RunAccessGuard` allowed the mutation."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    step_execution_id: str
    allowed: bool = True
    access_mode: Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"]
    trace_id: str


class CommandPaletteEntryResponse(BaseModel):
    """Universal `⌘K` Command Palette item (`UX-DR13`, `< 1 s`)."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    category: Literal["RUN", "WORKSPACE", "NAVIGATION", "ONTOLOGY", "CATALOG"]
    label_fr: str
    subtitle_fr: str
    shortcut: str
    target_route: str
    access_mode: Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"] | None = None


class CommandPaletteSearchResponse(BaseModel):
    """Universal `⌘K` Command Palette search response."""

    model_config = ConfigDict(extra="forbid")

    query: str
    items: list[CommandPaletteEntryResponse]
    trace_id: str
