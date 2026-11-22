"""Pydantic v2 HTTP Transport Schemas for Assistant Folders & Threads (`Stories 10.3..10.4`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    run_id: str | None = None
    run_status: str | None = None
    dbos_workflow_id: str | None = None
    waiting_step_keys: list[str] = Field(default_factory=list)
    executed_step_keys: list[str] = Field(default_factory=list)
    snapshot_count: int = 0


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
