"""Governance & 3-Speed Assistant HTTP Schemas (`Stories 10.1..10.2`, `Story 26.1`)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
    layer_code: Literal["1_CONSTITUTION", "2_PACK_METIER", "3_EQUIPE", "4_ESPACE", "5_UTILISATEUR"]
    label: str
    immutable: bool
    origin_badge: Literal["SOCLE", "PACK", "EQUIPE", "ESPACE", "UTILISATEUR"]
    content: str
    sha256: str


class AssistantGovernanceViewResponse(BaseModel):
    """Response envelope for `GET /api/v1/assistant/governance` (`Mode A`, `Story 26.4b`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    can_edit_workspace_layer: bool
    user_preferences: UserLayerPreferencesSchemaItem
    workspace_settings: WorkspaceLayerSettingsSchemaItem
    assembled_layers: list[AssembledLayerPreviewSchemaItem]


class ConversationTurnMessageItem(BaseModel):
    """Single message item in multi-turn `conversation_history` (`Story 10.2`, `Story 26.1`)."""

    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)
    name: str | None = None
    tool_call_id: str | None = None


class AssistantTurnCreateRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/turns` (`AD-25`, `Story 26.7`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    hat: str | None = None
    requested_speed: Literal["SPEED_1_FAST", "SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"] | None = (
        None
    )
    deep_audit_pill_active: bool = False
    requested_tier: Literal["simple", "medium", "complex", "auto"] | None = None
    thinking_effort: Literal["fast", "balanced", "deep"] | None = None
    conversation_history: list[ConversationTurnMessageItem] = Field(default_factory=list)
    thread_id: str | None = None
    parent_turn_id: str | None = None
    folder_id: str | None = None
    folder_pinned_notes: str | None = None
    response_tone: Literal["SYNTHETIC", "BALANCED", "DETAILED_CODE"] | None = None
    response_format: Literal["BULLETS_SUMMARY", "STRUCTURED_SECTIONS", "STEP_BY_STEP"] | None = None
    personal_instructions: str | None = None
    workspace_instructions: str | None = None
    locale: str | None = None


class ActiveBackgroundTurnStatusResponse(BaseModel):
    """Status snapshot for `GET /api/v1/assistant/turns/active` (`Story 26.3`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    turn_id: str | None = None
    status: Literal["IDLE", "RUNNING", "COMPLETED", "STOPPED", "ERROR"] = "IDLE"
    user_prompt: str = ""
    thinking_text: str = ""
    streamed_text: str = ""
    assembled_system_prompt: str = ""
    started_at_ms: float = 0.0
    elapsed_ms: float = 0.0
    error_message: str | None = None


class AssistantTurnSynthesizeNowResponse(BaseModel):
    """202 Accepted response for `POST /api/v1/assistant/turns/{turn_id}/synthesize-now`."""

    model_config = ConfigDict(extra="forbid")
    turn_id: str
    workspace_id: str
    status: Literal["SYNTHESIZING", "RUNNING", "COMPLETED", "STOPPED"]
    message: str


class AssistantTurnApproveRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/turns/{turn_id}/approve` (`AD-25`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(..., min_length=1)
    proposal_id: str = Field(..., min_length=1)
    approved: bool = True
    human_authored_required: bool = True
    human_anchor_markdown: str | None = None
    rationale: str | None = None


class AssistantTurnApproveResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/turns/{turn_id}/approve` (`AD-25`)."""

    model_config = ConfigDict(extra="forbid")
    turn_id: str
    proposal_id: str
    workspace_id: str
    approved: bool
    status: Literal["APPROVED", "REJECTED"]
    human_anchor_sha256: str | None = None
    audit_id: str | None = None


class AssistantTurnAcceptedResponse(BaseModel):
    """202 Accepted payload for `POST /api/v1/assistant/turns` (`AD-25`, `Story 26.3`)."""

    model_config = ConfigDict(extra="forbid")
    turn_id: str
    workspace_id: str
    thread_id: str | None = None
    parent_turn_id: str | None = None
    speed_mode: Literal["SPEED_1_FAST", "SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"]
    status: Literal["RUNNING", "COMPLETED", "STOPPED", "ERROR"] = "RUNNING"
    stream_url: str
    trace_id: str


class AssistantActiveTurnsListResponse(BaseModel):
    """Active/recent turns for `(workspace_id, user_id)` from Redis (`Story 26.3`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    turns: list[ActiveBackgroundTurnStatusResponse] = Field(default_factory=list)


class AssistantTurnFeedbackRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/turns/{turn_id}/feedback` (`AD-25`, `R5`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(..., min_length=1)
    rating: Literal["up", "down"]
    reason_code: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)


class AssistantTurnFeedbackResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/turns/{turn_id}/feedback` (`AD-25`, `R5`)."""

    model_config = ConfigDict(extra="forbid")
    feedback_id: str
    turn_id: str
    workspace_id: str
    user_id: str
    rating: Literal["up", "down"]
    reason_code: str | None = None
    comment: str | None = None


class AssistantThreadMessageSchemaItem(BaseModel):
    """Persisted conversational turn message (`D4`, `Story 26.5`)."""

    model_config = ConfigDict(extra="forbid")
    message_id: str
    thread_id: str
    workspace_id: str
    turn_id: str
    parent_turn_id: str | None = None
    role: Literal["user", "assistant"]
    content: str
    citation_map: dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0
    created_at: str = ""


class AssistantThreadMessagesListResponse(BaseModel):
    """Response payload for `GET /api/v1/assistant/threads/{thread_id}/messages` (`Story 26.5`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    thread_id: str
    messages: list[AssistantThreadMessageSchemaItem] = Field(default_factory=list)
