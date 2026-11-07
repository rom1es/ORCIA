"""Pydantic v2 HTTP Transport Schemas for Assistant Citations & Folders (`Stories 10.3..10.4`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
