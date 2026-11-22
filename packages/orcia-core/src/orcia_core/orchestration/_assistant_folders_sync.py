"""Synchronous & Redis-lock operations mixin for `AssistantFoldersAndSharingService`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.orchestration._assistant_folders_helpers import (
    assemble_layer5_injection,
    assemble_overview,
    build_sharing_result,
    build_turn_result,
    enforce_folder_turn_access,
    ensure_not_observer,
    make_launch_prep,
    validate_sharing_request,
)
from orcia_core.orchestration._assistant_folders_models import (
    PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    THREAD_TURN_LOCK_TTL_SECONDS,
    AssistantFolderRecord,
    AssistantThreadSummary,
    AssistantWorkspaceOverview,
    CollaborativeThreadTurnResult,
    FolderShareGrant,
    FolderSharingUpdateResult,
    FolderVisibilityMode,
    FolderWorkflowLaunchPreparation,
    Layer5FolderMemoryInjection,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.orchestration.redis_thread_lock import RedisThreadTurnLock
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration._internal.sql_assistant_folders import (
        SqlAssistantFoldersRepository,
    )


class _AssistantFoldersSyncMixin:
    """In-memory test fallback & Redis turn lock primitives."""

    _sql_repo: SqlAssistantFoldersRepository | None
    _folders: dict[str, AssistantFolderRecord]
    _threads: dict[str, AssistantThreadSummary]
    _folder_meta: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]
    _workspace_members: dict[str, set[str]]
    _thread_lock: Any

    @staticmethod
    def build_thread_lock_key(thread_id: str) -> str:
        """Return canonical Redis turn lock key `lock:thread:<thread_id>` (`AD-4`)."""
        return f"lock:thread:{thread_id}"

    def register_workspace_members(self, workspace_id: str, member_user_ids: list[str]) -> None:
        """Register explicit member user IDs for `workspace_id` confinement checks (`AD-21`)."""
        self._workspace_members.setdefault(workspace_id, set()).update(member_user_ids)

    def _build_folder_record(
        self,
        *,
        workspace_id: str,
        user: UserIdentity,
        title: str,
        pinned_notes_markdown: str,
        working_attachments_uris: list[str] | None,
        consolidated_summary: str,
        evidence_tags: list[str] | None,
        has_restricted_sources: bool,
        folder_id: str | None,
        existing: AssistantFolderRecord | None,
    ) -> AssistantFolderRecord:
        raise NotImplementedError

    def create_or_update_folder(
        self,
        *,
        workspace_id: str,
        user: UserIdentity,
        title: str,
        pinned_notes_markdown: str = "",
        working_attachments_uris: list[str] | None = None,
        consolidated_summary: str = "",
        evidence_tags: list[str] | None = None,
        has_restricted_sources: bool = False,
        folder_id: str | None = None,
    ) -> AssistantFolderRecord:
        """Create or update a thematic `📁 Dossier` in memory (unit tests)."""
        existing = self._folders.get(folder_id) if folder_id else None
        record = self._build_folder_record(
            workspace_id=workspace_id,
            user=user,
            title=title,
            pinned_notes_markdown=pinned_notes_markdown,
            working_attachments_uris=working_attachments_uris,
            consolidated_summary=consolidated_summary,
            evidence_tags=evidence_tags,
            has_restricted_sources=has_restricted_sources,
            folder_id=folder_id,
            existing=existing,
        )
        self._folders[record.folder_id] = record
        return record

    def create_thread_in_folder(
        self,
        *,
        workspace_id: str,
        user: UserIdentity,
        title: str,
        folder_id: str | None = None,
        initial_summary: str = "",
        thread_id: str | None = None,
    ) -> AssistantThreadSummary:
        """Create a discussion thread inside a `📁 Dossier` (or standalone)."""
        ensure_not_observer(user)
        if folder_id is not None and folder_id not in self._folders:
            raise ResourceNotFoundError(detail_override=f"Dossier introuvable : {folder_id}")
        self.register_workspace_members(workspace_id, [user.id])
        resolved_thread_id = thread_id or new_uuid7_str()
        thread = AssistantThreadSummary(
            thread_id=resolved_thread_id,
            workspace_id=workspace_id,
            folder_id=folder_id,
            creator_user_id=user.id,
            title=title.strip() or "Nouvelle discussion",
            thread_summary=initial_summary.strip(),
            turn_count=1 if initial_summary.strip() else 0,
            last_author_user_id=user.id,
            last_author_passthrough_identity=f"passthrough:oidc:{user.id}:{user.email}",
        )
        self._threads[resolved_thread_id] = thread
        return thread

    def build_layer5_folder_memory_injection(
        self, *, workspace_id: str, folder_id: str
    ) -> Layer5FolderMemoryInjection:
        """Assemble internal Layer 5 (`AD-15`) memory block for `AssistantHarness`."""
        folder = self._folders.get(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise ResourceNotFoundError(
                detail_override=f"Dossier introuvable dans l'Espace {workspace_id} : {folder_id}"
            )
        threads = [
            t.thread_summary
            for t in self._threads.values()
            if t.workspace_id == workspace_id and t.folder_id == folder_id and t.thread_summary
        ]
        return assemble_layer5_injection(folder, threads)

    def prepare_workflow_launch_from_folder(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        user: UserIdentity,
        target_workflow_uri: str = PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    ) -> FolderWorkflowLaunchPreparation:
        """Pre-fill a Process contract in 1 click from a thematic folder."""
        ensure_not_observer(user)
        memory = self.build_layer5_folder_memory_injection(
            workspace_id=workspace_id, folder_id=folder_id
        )
        return make_launch_prep(self._folders[folder_id], memory, user, target_workflow_uri)

    def configure_folder_sharing(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        owner_user: UserIdentity,
        visibility_mode: FolderVisibilityMode,
        shares: list[FolderShareGrant] | None = None,
        outside_workspace_user_ids: list[str] | None = None,
    ) -> FolderSharingUpdateResult:
        """Configure folder visibility (`🔒 | 👥 | 📦`) confined to Workspace."""
        ensure_not_observer(owner_user)
        folder = self._folders.get(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise ResourceNotFoundError(detail_override=f"Dossier introuvable : {folder_id}")
        resolved_shares = tuple(shares or ())
        validate_sharing_request(
            workspace_id=workspace_id,
            folder=folder,
            owner_user=owner_user,
            shares=resolved_shares,
            outside_workspace_user_ids=outside_workspace_user_ids,
            known_members=self._workspace_members.get(workspace_id, set()),
        )
        updated = AssistantFolderRecord(
            folder_id=folder.folder_id,
            workspace_id=folder.workspace_id,
            owner_user_id=folder.owner_user_id,
            title=folder.title,
            pinned_notes_markdown=folder.pinned_notes_markdown,
            working_attachments_uris=folder.working_attachments_uris,
            consolidated_summary=folder.consolidated_summary,
            evidence_tags=folder.evidence_tags,
            has_restricted_sources=folder.has_restricted_sources,
            visibility_mode=visibility_mode,
            shares=resolved_shares if visibility_mode == "SHARED_SELECTED" else (),
        )
        self._folders[folder_id] = updated
        return build_sharing_result(updated)

    def acquire_thread_turn_lock(
        self, *, thread_id: str, user_id: str, ttl_seconds: int = THREAD_TURN_LOCK_TTL_SECONDS
    ) -> str:
        """Acquire atomic turn lock `SET lock:thread:<thread_id> <user_id> NX EX 60` (`AD-4`)."""
        lock_impl = getattr(self, "_thread_lock", None) or RedisThreadTurnLock()
        lock_key, _ = lock_impl.acquire_sync(
            thread_id=thread_id, user_id=user_id, ttl_seconds=ttl_seconds
        )
        return str(lock_key)

    def release_thread_turn_lock(self, *, thread_id: str, user_id: str) -> None:
        """Release the turn lock if held by `user_id`."""
        lock_impl = getattr(self, "_thread_lock", None) or RedisThreadTurnLock()
        lock_impl.release_sync(thread_id=thread_id, user_id=user_id)

    def send_collaborative_thread_turn(
        self,
        *,
        workspace_id: str,
        thread_id: str,
        sender_user: UserIdentity,
        message_text: str,
        release_lock_after_turn: bool = False,
    ) -> CollaborativeThreadTurnResult:
        """Execute a turn in a shared thread with Redis turn lock (`NX EX 60`)."""
        ensure_not_observer(sender_user)
        thread = self._threads.get(thread_id)
        if thread is None or thread.workspace_id != workspace_id:
            raise ResourceNotFoundError(detail_override=f"Discussion introuvable : {thread_id}")
        folder = self._folders.get(thread.folder_id) if thread.folder_id else None
        enforce_folder_turn_access(folder, sender_user)
        lock_key = self.acquire_thread_turn_lock(
            thread_id=thread_id, user_id=sender_user.id, ttl_seconds=THREAD_TURN_LOCK_TTL_SECONDS
        )
        personal_passthrough = f"passthrough:oidc:{sender_user.id}:{sender_user.email}"
        updated = AssistantThreadSummary(
            thread_id=thread.thread_id,
            workspace_id=thread.workspace_id,
            folder_id=thread.folder_id,
            creator_user_id=thread.creator_user_id,
            title=thread.title,
            thread_summary=f"{thread.thread_summary} | {message_text.strip()}".strip(" |"),
            turn_count=thread.turn_count + 1,
            last_author_user_id=sender_user.id,
            last_author_passthrough_identity=personal_passthrough,
        )
        self._threads[thread_id] = updated
        if release_lock_after_turn:
            self.release_thread_turn_lock(thread_id=thread_id, user_id=sender_user.id)
        return build_turn_result(
            thread=updated,
            folder=folder,
            workspace_id=workspace_id,
            sender_user=sender_user,
            lock_key=lock_key,
            personal_passthrough=personal_passthrough,
        )

    def get_workspace_overview(
        self, *, workspace_id: str, active_folder_id: str | None = None, search_query: str = ""
    ) -> AssistantWorkspaceOverview:
        """Return the 3-tab structure (`💬`, `📁 Dossiers (N)`, `🕘 Historique`)."""
        return assemble_overview(
            workspace_id=workspace_id,
            ws_folders=tuple(f for f in self._folders.values() if f.workspace_id == workspace_id),
            ws_threads=tuple(t for t in self._threads.values() if t.workspace_id == workspace_id),
            active_folder_id=active_folder_id,
            search_query=search_query,
        )
