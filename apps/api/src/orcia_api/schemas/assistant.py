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


class UserLayerPreferencesSchemaItem(BaseModel):
    """Tab 1 (`👤 Mes préférences — Couche 5 USER`) schema (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    workspace_id: str
    response_tone: Literal["SYNTHETIC", "BALANCED", "DETAILED_CODE"]
    favorite_format: Literal["BULLETS_SUMMARY", "STRUCTURED_SECTIONS", "STEP_BY_STEP"]
    default_hat: str
    personal_instructions: str
    sha256: str


class UpdateUserLayerPreferencesRequest(BaseModel):
    """Request payload for `PUT /api/v1/assistant/governance/mode-a/user` (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    response_tone: Literal["SYNTHETIC", "BALANCED", "DETAILED_CODE"] = "BALANCED"
    favorite_format: Literal["BULLETS_SUMMARY", "STRUCTURED_SECTIONS", "STEP_BY_STEP"] = (
        "STRUCTURED_SECTIONS"
    )
    default_hat: str = Field(default="PM", min_length=2)
    personal_instructions: str = Field(..., min_length=3)


class WorkspaceLayerSettingsSchemaItem(BaseModel):
    """Tab 2 (`📦 Réglages de l'Espace — Couche 4 WORKSPACE`) schema (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    workspace_instructions: str
    default_checked_sources: list[str]
    recommended_agents: list[str]
    arbitration_policy: Literal["PAUSE_AND_ESCALATE", "AUTO_RESOLVE_WITH_TRACE"]
    welcome_suggestions: list[str]
    mcp_expose_assistant: bool
    mcp_frozen_by_upper_layer: bool
    mcp_frozen_origin: Literal["PLATFORM", "TEAM"] | None = None
    mcp_endpoint_url: str
    mcp_tool_name: str
    mcp_ide_config_json: str
    sha256: str


class UpdateWorkspaceLayerSettingsRequest(BaseModel):
    """Request payload for `PUT /api/v1/assistant/governance/mode-a/workspace` (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    workspace_instructions: str = Field(..., min_length=3)
    default_checked_sources: list[str] = Field(default_factory=list)
    recommended_agents: list[str] = Field(default_factory=list)
    arbitration_policy: Literal["PAUSE_AND_ESCALATE", "AUTO_RESOLVE_WITH_TRACE"] = (
        "PAUSE_AND_ESCALATE"
    )
    welcome_suggestions: list[str] | None = None
    mcp_expose_assistant: bool = True


class AssembledLayerPreviewSchemaItem(BaseModel):
    """Tab 3 (`👁️ Assemblage complet`) layer item (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    layer_number: int
    layer_code: Literal[
        "1_CONSTITUTION",
        "2_PACK_METIER",
        "3_EQUIPE",
        "4_ESPACE",
        "5_UTILISATEUR",
    ]
    label: str
    immutable: bool
    origin_badge: Literal["SOCLE", "PACK", "EQUIPE", "ESPACE", "UTILISATEUR"]
    content: str
    sha256: str


class AssistantStudioNodeSchemaItem(BaseModel):
    """Mode B Studio node schema (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    title: str
    node_order: int
    is_harness_boundary: bool
    locked_by: Literal["HARNESS", "PLATFORM", "TEAM"] | None = None
    enabled: bool = True
    sub_layers_count: int = 3
    enabled_sub_layers: list[str] = Field(default_factory=list)
    sub_agent_uri: str | None = None


class AssistantStudioGraphStateSchemaItem(BaseModel):
    """Mode B Studio graph state (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    workflow_uri: str
    scope_level: Literal["DEFAULT", "TEAM", "WORKSPACE"]
    scope_id: str
    ai_pre_prompt: str
    nodes: list[AssistantStudioNodeSchemaItem]
    override_key: str | None = None
    sha256: str


class SaveAssistantStudioGraphRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/governance/mode-b/save` (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    scope_level: Literal["TEAM", "WORKSPACE"] = "WORKSPACE"
    scope_id: str = Field(..., min_length=1)
    ai_pre_prompt: str = Field(..., min_length=3)
    nodes: list[AssistantStudioNodeSchemaItem]


class ResetAssistantStudioGraphRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/governance/mode-b/reset` (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    scope_level: Literal["TEAM", "WORKSPACE"] = "WORKSPACE"
    scope_id: str = Field(..., min_length=1)


class AssistantGovernanceViewResponse(BaseModel):
    """Response envelope for `GET /api/v1/assistant/governance` (`Story 10.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    can_edit_workspace_layer: bool
    can_open_studio_mode_b: bool
    user_preferences: UserLayerPreferencesSchemaItem
    workspace_settings: WorkspaceLayerSettingsSchemaItem
    assembled_layers: list[AssembledLayerPreviewSchemaItem]
    studio_graph: AssistantStudioGraphStateSchemaItem


class ThreeSpeedStepProgressSchemaItem(BaseModel):
    """Real-time step progress item in 3-Speed routing (`Story 10.2`)."""

    model_config = ConfigDict(extra="forbid")

    step_code: str
    label: str
    duration_ms: float
    status: Literal["COMPLETED", "RUNNING"] = "COMPLETED"
    connector_or_lens: str | None = None


class ThreeSpeedTurnRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/three-speed/turn` (`Story 10.2`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    hat: str | None = None
    requested_speed: Literal["SPEED_1_FAST", "SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"] | None = (
        None
    )
    deep_audit_pill_active: bool = False


class ThreeSpeedTurnResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/three-speed/turn` (`Story 10.2`)."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str
    workspace_id: str
    user_id: str
    hat: str
    speed_mode: Literal["SPEED_1_FAST", "SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"]
    cache_key: str
    cache_hit: bool
    cache_lookup_ms: float
    nodes_1_to_4_deterministic_ms: float
    ttft_ms: float
    intermediate_llm_calls: int
    invoked_targets: list[str]
    step_progress: list[ThreeSpeedStepProgressSchemaItem]
    response_text: str
    assembled_prompt_sha256: str
    deep_audit_lenses: list[str] = Field(default_factory=list)


class InvalidatePromptCacheRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/three-speed/invalidate-cache` (`Story 10.2`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    reason: Literal["SETTINGS_CHANGED", "OVERRIDE_UPDATED", "GLOSSARY_PROMOTED"] = (
        "SETTINGS_CHANGED"
    )
    user_id: str | None = None


class InvalidatePromptCacheResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/three-speed/invalidate-cache` (`Story 10.2`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    reason: Literal["SETTINGS_CHANGED", "OVERRIDE_UPDATED", "GLOSSARY_PROMOTED"]
    invalidated_keys_count: int
    outbox_event_id: str


class RawSourceCandidateSchemaItem(BaseModel):
    """Input source candidate (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    uri: str
    title: str
    authority_tier: Literal["REFERENCE", "ACTIVE"] = "ACTIVE"
    freshness: Literal["FRESH", "STALE_WARNING"] = "FRESH"
    snippet: str
    line_start: int = 1
    line_end: int = 25
    relevance_score: float = 0.9


class RawGlossaryCandidateSchemaItem(BaseModel):
    """Input glossary / axiom candidate (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    term_or_axiom_id: str
    label: str
    ontology_level: Literal["N1_DIRECTIVE", "N2_NORME", "N3_MECANISME", "L4_GLOSSARY"] = (
        "L4_GLOSSARY"
    )
    definition: str


class RawToolOutputCandidateSchemaItem(BaseModel):
    """Input MCP tool / connector output candidate (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    connector_uri: str
    summary: str


class EvidenceSourceCitationSchemaItem(BaseModel):
    """Numbered `[S1..Sn]` source entry (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    index: int
    uri: str
    title: str
    authority_tier: Literal["REFERENCE", "ACTIVE"]
    freshness: Literal["FRESH", "STALE_WARNING"]
    snippet: str | None = None
    line_start: int
    line_end: int
    restricted_access: bool = False
    display_pill: str
    request_access_uri: str | None = None


class EvidenceGlossaryCitationSchemaItem(BaseModel):
    """Numbered `[G1..Gn]` glossary / axiom entry (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    index: int
    term_or_axiom_id: str
    label: str
    ontology_level: Literal["N1_DIRECTIVE", "N2_NORME", "N3_MECANISME", "L4_GLOSSARY"]
    definition: str


class EvidenceToolCitationSchemaItem(BaseModel):
    """Numbered `[O1..On]` tool entry (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    index: int
    tool_name: str
    connector_uri: str
    summary: str


class VerifyAndFilterCitationsRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/citations/verify-turn` (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    response_text: str = Field(..., min_length=1)
    sources: list[RawSourceCandidateSchemaItem] = Field(default_factory=list)
    glossary_items: list[RawGlossaryCandidateSchemaItem] = Field(default_factory=list)
    tool_outputs: list[RawToolOutputCandidateSchemaItem] = Field(default_factory=list)
    reader_allowed_source_uris: list[str] | None = None


class VerifyAndFilterCitationsResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/citations/verify-turn` (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    sanitized_text: str
    valid_tags: list[str]
    stripped_phantom_tags: list[str]
    verification_duration_ms: float
    audit_id: str | None = None
    sources: list[EvidenceSourceCitationSchemaItem]
    glossary_items: list[EvidenceGlossaryCitationSchemaItem]
    tool_outputs: list[EvidenceToolCitationSchemaItem]
    footer_summary_line: str
    citation_map_emitted_at_ms: float = 80.0


class ArtifactCardActionRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/artifacts/action` (`Story 10.3` V5 Guard)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    action_type: Literal[
        "COPY",
        "EXPORT_MD",
        "EXPORT_JSON",
        "SAVE_DRAFT",
        "CONTINUE_IN_PROCESS",
        "DIRECT_SI_WRITE",
        "PUBLISH_V1_VAULT",
    ]
    artifact_title: str = Field(..., min_length=1)
    artifact_content: str = Field(..., min_length=1)
    cited_tags: list[str] = Field(default_factory=list)
    target_uri: str | None = None


class ArtifactCardActionResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/artifacts/action` (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    workspace_id: str
    action_type: str
    artifact_title: str
    artifact_version_tag: str
    draft_uri: str | None = None
    process_launch_prefill: dict[str, object] = Field(default_factory=dict)


class FolderShareGrantSchemaItem(BaseModel):
    """Colleague share grant (`READ_ONLY` or `CO_CONTRIBUTOR`) (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    grantee_user_id: str = Field(..., min_length=1)
    access_role: Literal["READ_ONLY", "CO_CONTRIBUTOR"] = "READ_ONLY"


class CreateOrUpdateAssistantFolderRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/folders` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    folder_id: str | None = None
    title: str = Field(..., min_length=1)
    pinned_notes_markdown: str = ""
    working_attachments_uris: list[str] = Field(default_factory=list)
    consolidated_summary: str = ""
    evidence_tags: list[str] = Field(default_factory=lambda: ["S1"])
    has_restricted_sources: bool = False


class AssistantFolderSchemaItem(BaseModel):
    """Thematic `📁 Dossier` representation (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    folder_id: str
    workspace_id: str
    owner_user_id: str
    title: str
    pinned_notes_markdown: str
    working_attachments_uris: list[str]
    consolidated_summary: str
    evidence_tags: list[str]
    has_restricted_sources: bool
    visibility_mode: Literal["PRIVATE", "SHARED_SELECTED", "WORKSPACE_OPEN"]
    shares: list[FolderShareGrantSchemaItem] = Field(default_factory=list)
    assembled_layer5_prompt_block: str = ""


class CreateAssistantThreadRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/threads` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    folder_id: str | None = None
    title: str = Field(..., min_length=1)
    initial_summary: str = ""


class AssistantThreadSchemaItem(BaseModel):
    """Thread representation inside a `📁 Dossier` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    workspace_id: str
    folder_id: str | None = None
    creator_user_id: str
    title: str
    thread_summary: str
    turn_count: int
    last_author_user_id: str | None = None
    last_author_passthrough_identity: str | None = None


class ConfigureFolderSharingRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/folders/{folder_id}/share` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    visibility_mode: Literal["PRIVATE", "SHARED_SELECTED", "WORKSPACE_OPEN"]
    shares: list[FolderShareGrantSchemaItem] = Field(default_factory=list)
    outside_workspace_user_ids: list[str] = Field(default_factory=list)


class ConfigureFolderSharingResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/folders/{folder_id}/share` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    folder_id: str
    workspace_id: str
    visibility_mode: Literal["PRIVATE", "SHARED_SELECTED", "WORKSPACE_OPEN"]
    shares: list[FolderShareGrantSchemaItem]
    has_restricted_sources: bool
    restricted_sources_warning: str | None = None


class LaunchProcessFromFolderRequest(BaseModel):
    """Request for `POST /api/v1/assistant/folders/{folder_id}/launch-process` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    target_workflow_uri: str = "orcia://pack-sdlc/workflows/ticket-to-tech-spec"


class LaunchProcessFromFolderResponse(BaseModel):
    """Response for `POST /api/v1/assistant/folders/{folder_id}/launch-process` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    folder_id: str
    workspace_id: str
    workflow_uri: str
    initiated_by_user_id: str
    passthrough_identity: str
    prefilled_contract_inputs: dict[str, object]


class SendCollaborativeThreadTurnRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/threads/{thread_id}/turns` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    message_text: str = Field(..., min_length=1)
    release_lock_after_turn: bool = False


class SendCollaborativeThreadTurnResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/threads/{thread_id}/turns` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    folder_id: str | None = None
    workspace_id: str
    redis_lock_key: str
    lock_holder_user_id: str
    lock_ttl_seconds: int
    sse_presence_banner: str
    author_user_id: str
    author_passthrough_identity: str
    folder_creator_user_id: str
    layer5_memory_injected: bool
    assembled_layer5_preview: str
    assistant_reply_markdown: str


class AssistantHistorySearchHitSchemaItem(BaseModel):
    """Search hit in `🕘 Historique & Recherche` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    item_kind: Literal["THREAD", "FOLDER", "ARTIFACT_CARD"]
    title: str
    snippet: str
    folder_id: str | None = None


class AssistantWorkspaceOverviewResponse(BaseModel):
    """Response for `GET /api/v1/assistant/workspaces/{workspace_id}/overview` (`Story 10.4`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    tabs: list[Literal["ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"]]
    active_folder_pill_label: str | None = None
    folders_count: int
    folders: list[AssistantFolderSchemaItem]
    threads: list[AssistantThreadSchemaItem]
    history_hits: list[AssistantHistorySearchHitSchemaItem]
