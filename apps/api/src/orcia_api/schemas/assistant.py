"""Pydantic v2 HTTP Transport Schemas for Assistant Agent (`Story 3.3`, `AD-15`, `UX-DR12/15`)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AssistantChatRequest(BaseModel):
    """Request payload for a conversational turn with `orcia://system/workflows/assistant-agent`."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    human_profile_archetype: str | None = Field(default=None)
    allowed_datasource_aliases: list[str] = Field(default_factory=list)


class AssistantNodeTraceSchemaItem(BaseModel):
    """Telemetry item for one of the 5 nodes in the Assistant Agent DAG."""

    model_config = ConfigDict(extra="forbid")

    node_id: Literal[
        "1_INTENT_ROUTER",
        "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
        "3_PARALLEL_FAN_OUT",
        "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
        "5_PROFILE_ADAPTIVE_SYNTHESIZER",
    ]
    node_order: int
    status: Literal["COMPLETED"]
    duration_ms: float
    summary: str
    output_metadata: dict[str, Any] = Field(default_factory=dict)


class PromptLayerBlockSchemaItem(BaseModel):
    """Metadata for one of the 5 prompt layers assembled by `AssistantHarness`."""

    model_config = ConfigDict(extra="forbid")

    layer_id: Literal[
        "1_CONSTITUTIONAL_IMMUTABLE",
        "2_ONTOLOGY_AND_AXIOMS_L1_L4",
        "3_HUMAN_PROFILE_ADAPTATION",
        "4_FEDERATED_CONTEXT_FANOUT",
        "5_CONVERSATIONAL_INTENT_AND_COMPOSER",
    ]
    layer_order: int
    immutable: bool
    content_sha256: str


class XyFlowNodeSchemaItem(BaseModel):
    """`@xyflow/react` v12 node schema item for Cockpit Canvas (`UX-DR15`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    position_x: float
    position_y: float
    label: str
    step_type: str
    human_authored_required: bool


class XyFlowEdgeSchemaItem(BaseModel):
    """`@xyflow/react` v12 edge schema item for Cockpit Canvas (`UX-DR15`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    animated: bool = True


class AssistantWorkflowProposalSchemaItem(BaseModel):
    """Workflow proposal with `@xyflow/react` graph and YAML manifest (`UX-DR15`, `FR-11`)."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    workflow_uri: str
    title: str
    description: str
    execution_regime: str
    manifest_yaml: str
    nodes: list[XyFlowNodeSchemaItem]
    edges: list[XyFlowEdgeSchemaItem]


class AssistantChatResponse(BaseModel):
    """Response envelope for `POST /api/v1/assistant/chat` (`Story 3.3`)."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str
    workflow_uri: str
    workspace_id: str
    human_profile_archetype: str
    register_label: str
    vocabulary_tier: str
    highlighted_indicators: list[str]
    intent: str
    response_text: str
    first_token_latency_ms: float
    constitutional_sha256: str
    cited_uris: list[str]
    stale_warnings: list[str]
    node_traces: list[AssistantNodeTraceSchemaItem]
    prompt_layers: list[PromptLayerBlockSchemaItem]
    workflow_proposal: AssistantWorkflowProposalSchemaItem | None = None


class AssistantSaveAndLaunchRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/workflows/save-and-launch` (`FR-11`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    manifest_yaml: str = Field(..., min_length=10)


class AssistantSaveAndLaunchResponse(BaseModel):
    """Response envelope for `POST /api/v1/assistant/workflows/save-and-launch` (`FR-11`)."""

    model_config = ConfigDict(extra="forbid")

    workflow_uri: str
    version: str
    run_id: str
    execution_regime: str
    run_status: str
    executed_step_keys: list[str]
    snapshot_count: int
