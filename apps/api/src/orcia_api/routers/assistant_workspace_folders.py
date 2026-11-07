"""Epic 10 Sub-Router — Thematic Folders, Layer 5 Memory & Shared Threads (`Story 10.4`).

Exposes:
- `POST /api/v1/assistant/folders`
- `POST /api/v1/assistant/threads`
- `POST /api/v1/assistant/folders/{folder_id}/share`
- `POST /api/v1/assistant/folders/{folder_id}/launch-process`
- `POST /api/v1/assistant/threads/{thread_id}/turns`
- `GET /api/v1/assistant/workspaces/{workspace_id}/overview`
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from orcia_api.dependencies import get_assistant_folders_and_sharing_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant_citations_and_folders import (
    AssistantFolderSchemaItem,
    AssistantHistorySearchHitSchemaItem,
    AssistantThreadSchemaItem,
    AssistantWorkspaceOverviewResponse,
    ConfigureFolderSharingRequest,
    ConfigureFolderSharingResponse,
    CreateAssistantThreadRequest,
    CreateOrUpdateAssistantFolderRequest,
    FolderShareGrantSchemaItem,
    LaunchProcessFromFolderRequest,
    LaunchProcessFromFolderResponse,
    SendCollaborativeThreadTurnRequest,
    SendCollaborativeThreadTurnResponse,
)
from orcia_core.orchestration.assistant_folders_and_sharing import (
    AssistantFoldersAndSharingService,
    FolderShareGrant,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter()

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
FoldersSharingDep = Annotated[
    AssistantFoldersAndSharingService, Depends(get_assistant_folders_and_sharing_service)
]


@router.post("/folders", response_model=AssistantFolderSchemaItem)
def create_or_update_assistant_folder_endpoint(
    payload: CreateOrUpdateAssistantFolderRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> AssistantFolderSchemaItem:
    """Create or update a thematic `📁 Dossier` (`📌 Notes du dossier`, Layer 5 continuity)."""
    record = folders_svc.create_or_update_folder(
        workspace_id=payload.workspace_id,
        user=user,
        title=payload.title,
        pinned_notes_markdown=payload.pinned_notes_markdown,
        working_attachments_uris=payload.working_attachments_uris,
        consolidated_summary=payload.consolidated_summary,
        evidence_tags=payload.evidence_tags,
        has_restricted_sources=payload.has_restricted_sources,
        folder_id=payload.folder_id,
    )
    layer5 = folders_svc.build_layer5_folder_memory_injection(
        workspace_id=payload.workspace_id,
        folder_id=record.folder_id,
    )
    return AssistantFolderSchemaItem(
        folder_id=record.folder_id,
        workspace_id=record.workspace_id,
        owner_user_id=record.owner_user_id,
        title=record.title,
        pinned_notes_markdown=record.pinned_notes_markdown,
        working_attachments_uris=list(record.working_attachments_uris),
        consolidated_summary=record.consolidated_summary,
        evidence_tags=list(record.evidence_tags),
        has_restricted_sources=record.has_restricted_sources,
        visibility_mode=record.visibility_mode,
        shares=[
            FolderShareGrantSchemaItem(
                grantee_user_id=g.grantee_user_id,
                access_role=g.access_role,
            )
            for g in record.shares
        ],
        assembled_layer5_prompt_block=layer5.assembled_layer5_prompt_block,
    )


@router.post("/threads", response_model=AssistantThreadSchemaItem)
def create_assistant_thread_endpoint(
    payload: CreateAssistantThreadRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> AssistantThreadSchemaItem:
    """Create a discussion thread inside a `📁 Dossier` (`Story 10.4`)."""
    thread = folders_svc.create_thread_in_folder(
        workspace_id=payload.workspace_id,
        user=user,
        title=payload.title,
        folder_id=payload.folder_id,
        initial_summary=payload.initial_summary,
    )
    return AssistantThreadSchemaItem(
        thread_id=thread.thread_id,
        workspace_id=thread.workspace_id,
        folder_id=thread.folder_id,
        creator_user_id=thread.creator_user_id,
        title=thread.title,
        thread_summary=thread.thread_summary,
        turn_count=thread.turn_count,
        last_author_user_id=thread.last_author_user_id,
        last_author_passthrough_identity=thread.last_author_passthrough_identity,
    )


@router.post("/folders/{folder_id}/share", response_model=ConfigureFolderSharingResponse)
def configure_folder_sharing_endpoint(
    folder_id: str,
    payload: ConfigureFolderSharingRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> ConfigureFolderSharingResponse:
    """Configure folder visibility (`🔒 Privé | 👥 Partagé | 📦 Espace`) confined to Workspace."""
    outcome = folders_svc.configure_folder_sharing(
        workspace_id=payload.workspace_id,
        folder_id=folder_id,
        owner_user=user,
        visibility_mode=payload.visibility_mode,
        shares=[
            FolderShareGrant(
                grantee_user_id=s.grantee_user_id,
                access_role=s.access_role,
            )
            for s in payload.shares
        ],
        outside_workspace_user_ids=payload.outside_workspace_user_ids,
    )
    return ConfigureFolderSharingResponse(
        folder_id=outcome.folder_id,
        workspace_id=outcome.workspace_id,
        visibility_mode=outcome.visibility_mode,
        shares=[
            FolderShareGrantSchemaItem(
                grantee_user_id=s.grantee_user_id,
                access_role=s.access_role,
            )
            for s in outcome.shares
        ],
        has_restricted_sources=outcome.has_restricted_sources,
        restricted_sources_warning=outcome.restricted_sources_warning,
    )


@router.post("/folders/{folder_id}/launch-process", response_model=LaunchProcessFromFolderResponse)
def launch_process_from_folder_endpoint(
    folder_id: str,
    payload: LaunchProcessFromFolderRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> LaunchProcessFromFolderResponse:
    """Pre-fill a Process contract in 1 click (`☍ Lancer un Processus à partir de ce dossier →`)."""
    prep = folders_svc.prepare_workflow_launch_from_folder(
        workspace_id=payload.workspace_id,
        folder_id=folder_id,
        user=user,
        target_workflow_uri=payload.target_workflow_uri,
    )
    return LaunchProcessFromFolderResponse(
        folder_id=prep.folder_id,
        workspace_id=prep.workspace_id,
        workflow_uri=prep.workflow_uri,
        initiated_by_user_id=prep.initiated_by_user_id,
        passthrough_identity=prep.passthrough_identity,
        prefilled_contract_inputs=prep.prefilled_contract_inputs,
    )


@router.post("/threads/{thread_id}/turns", response_model=SendCollaborativeThreadTurnResponse)
def send_collaborative_thread_turn_endpoint(
    thread_id: str,
    payload: SendCollaborativeThreadTurnRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> SendCollaborativeThreadTurnResponse:
    """Execute a turn in a shared thread under Redis turn lock (`NX EX 60`)."""
    outcome = folders_svc.send_collaborative_thread_turn(
        workspace_id=payload.workspace_id,
        thread_id=thread_id,
        sender_user=user,
        message_text=payload.message_text,
        release_lock_after_turn=payload.release_lock_after_turn,
    )
    return SendCollaborativeThreadTurnResponse(
        thread_id=outcome.thread_id,
        folder_id=outcome.folder_id,
        workspace_id=outcome.workspace_id,
        redis_lock_key=outcome.redis_lock_key,
        lock_holder_user_id=outcome.lock_holder_user_id,
        lock_ttl_seconds=outcome.lock_ttl_seconds,
        sse_presence_banner=outcome.sse_presence_banner,
        author_user_id=outcome.author_user_id,
        author_passthrough_identity=outcome.author_passthrough_identity,
        folder_creator_user_id=outcome.folder_creator_user_id,
        layer5_memory_injected=outcome.layer5_memory_injected,
        assembled_layer5_preview=outcome.assembled_layer5_preview,
        assistant_reply_markdown=outcome.assistant_reply_markdown,
    )


@router.get(
    "/workspaces/{workspace_id}/overview", response_model=AssistantWorkspaceOverviewResponse
)
def get_assistant_workspace_overview_endpoint(
    workspace_id: str,
    folders_svc: FoldersSharingDep,
    active_folder_id: str | None = Query(default=None),
    search_query: str = Query(default=""),
) -> AssistantWorkspaceOverviewResponse:
    """Return the 3-tab `Mon Assistant` workspace overview (`💬`, `📁`, `🕘`) (`Story 10.4`)."""
    overview = folders_svc.get_workspace_overview(
        workspace_id=workspace_id,
        active_folder_id=active_folder_id,
        search_query=search_query,
    )
    return AssistantWorkspaceOverviewResponse(
        workspace_id=overview.workspace_id,
        tabs=list(overview.tabs),
        active_folder_pill_label=overview.active_folder_pill_label,
        folders_count=overview.folders_count,
        folders=[
            AssistantFolderSchemaItem(
                folder_id=f.folder_id,
                workspace_id=f.workspace_id,
                owner_user_id=f.owner_user_id,
                title=f.title,
                pinned_notes_markdown=f.pinned_notes_markdown,
                working_attachments_uris=list(f.working_attachments_uris),
                consolidated_summary=f.consolidated_summary,
                evidence_tags=list(f.evidence_tags),
                has_restricted_sources=f.has_restricted_sources,
                visibility_mode=f.visibility_mode,
                shares=[
                    FolderShareGrantSchemaItem(
                        grantee_user_id=g.grantee_user_id,
                        access_role=g.access_role,
                    )
                    for g in f.shares
                ],
                assembled_layer5_prompt_block=folders_svc.build_layer5_folder_memory_injection(
                    workspace_id=workspace_id,
                    folder_id=f.folder_id,
                ).assembled_layer5_prompt_block,
            )
            for f in overview.folders
        ],
        threads=[
            AssistantThreadSchemaItem(
                thread_id=t.thread_id,
                workspace_id=t.workspace_id,
                folder_id=t.folder_id,
                creator_user_id=t.creator_user_id,
                title=t.title,
                thread_summary=t.thread_summary,
                turn_count=t.turn_count,
                last_author_user_id=t.last_author_user_id,
                last_author_passthrough_identity=t.last_author_passthrough_identity,
            )
            for t in overview.threads
        ],
        history_hits=[
            AssistantHistorySearchHitSchemaItem(
                item_id=h.item_id,
                item_kind=h.item_kind,
                title=h.title,
                snippet=h.snippet,
                folder_id=h.folder_id,
            )
            for h in overview.history_hits
        ],
    )
