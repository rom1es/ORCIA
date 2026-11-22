"""Models & dataclasses for `AssistantFoldersAndSharingService` (`Story 10.4`, `AD-15`, `AD-21`).

Extracted from `assistant_folders_and_sharing.py` to keep both modules under `< 380` lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FolderVisibilityMode = Literal["PRIVATE", "SHARED_SELECTED", "WORKSPACE_OPEN"]
FolderAccessRole = Literal["READ_ONLY", "CO_CONTRIBUTOR"]
AssistantMainTab = Literal["ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"]

PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI = "orcia://pack-sdlc/workflows/ticket-to-tech-spec"
THREAD_TURN_LOCK_TTL_SECONDS = 60


@dataclass(frozen=True)
class FolderShareGrant:
    """Per-colleague share grant inside the same Workspace (`READ_ONLY` or `CO_CONTRIBUTOR`)."""

    grantee_user_id: str
    access_role: FolderAccessRole


@dataclass(frozen=True)
class AssistantThreadSummary:
    """Discussion thread belonging to a thematic `📁 Dossier` (or standalone)."""

    thread_id: str
    workspace_id: str
    folder_id: str | None
    creator_user_id: str
    title: str
    thread_summary: str
    turn_count: int
    last_author_user_id: str | None
    last_author_passthrough_identity: str | None


@dataclass(frozen=True)
class AssistantFolderRecord:
    """Thematic `📁 Dossier` in `Mon Assistant` with Layer 5 continuity & sharing."""

    folder_id: str
    workspace_id: str
    owner_user_id: str
    title: str
    pinned_notes_markdown: str
    working_attachments_uris: tuple[str, ...]
    consolidated_summary: str
    evidence_tags: tuple[str, ...]
    has_restricted_sources: bool
    visibility_mode: FolderVisibilityMode
    shares: tuple[FolderShareGrant, ...] = ()


@dataclass(frozen=True)
class Layer5FolderMemoryInjection:
    """Layer 5 (`5_UTILISATEUR`) memory continuity payload internal to `AssistantHarness`."""

    folder_id: str
    folder_title: str
    layer_number: int
    layer_code: str
    pinned_notes_markdown: str
    working_attachments_uris: tuple[str, ...]
    previous_threads_summaries: tuple[str, ...]
    assembled_layer5_prompt_block: str


@dataclass(frozen=True)
class FolderWorkflowLaunchPreparation:
    """1-click `☍ Lancer un Processus à partir de ce dossier →` pre-filled contract."""

    folder_id: str
    workspace_id: str
    workflow_uri: str
    initiated_by_user_id: str
    passthrough_identity: str
    prefilled_contract_inputs: dict[str, object]


@dataclass(frozen=True)
class FolderSharingUpdateResult:
    """Outcome of updating a folder's visibility and colleague grants (`🔒 | 👥 | 📦`)."""

    folder_id: str
    workspace_id: str
    visibility_mode: FolderVisibilityMode
    shares: tuple[FolderShareGrant, ...]
    has_restricted_sources: bool
    restricted_sources_warning: str | None


@dataclass(frozen=True)
class CollaborativeThreadTurnResult:
    """Outcome of sending a message in a shared thread under Redis turn lock & `Passthrough`."""

    thread_id: str
    folder_id: str | None
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


@dataclass(frozen=True)
class AssistantHistorySearchHit:
    """Search hit in the 3rd tab `🕘 Historique & Recherche`."""

    item_id: str
    item_kind: Literal["THREAD", "FOLDER", "ARTIFACT_CARD"]
    title: str
    snippet: str
    folder_id: str | None


@dataclass(frozen=True)
class AssistantWorkspaceOverview:
    """3-tab overview for `Mon Assistant` (`💬`, `📁 Dossiers (N)`, `🕘 Historique`)."""

    workspace_id: str
    tabs: tuple[AssistantMainTab, AssistantMainTab, AssistantMainTab]
    active_folder_pill_label: str | None
    folders_count: int
    folders: tuple[AssistantFolderRecord, ...]
    threads: tuple[AssistantThreadSummary, ...]
    history_hits: tuple[AssistantHistorySearchHit, ...]


__all__ = [
    "AssistantFolderRecord",
    "AssistantHistorySearchHit",
    "AssistantMainTab",
    "AssistantThreadSummary",
    "AssistantWorkspaceOverview",
    "CollaborativeThreadTurnResult",
    "FolderAccessRole",
    "FolderShareGrant",
    "FolderSharingUpdateResult",
    "FolderVisibilityMode",
    "FolderWorkflowLaunchPreparation",
    "Layer5FolderMemoryInjection",
    "PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI",
    "THREAD_TURN_LOCK_TTL_SECONDS",
]
