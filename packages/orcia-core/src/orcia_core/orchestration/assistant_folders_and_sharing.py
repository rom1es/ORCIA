"""Story 10.4 — Thematic Folders (`📁 Dossiers`), Layer 5 Memory Continuity (`AD-15`),
Collaborative Sharing (`🔒 | 👥 | 📦`, `AD-21`) & Redis Turn Lock (`AD-4`, `AD-6`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from orcia_core.orchestration._assistant_folders_helpers import (
    assemble_layer5_injection,
    assemble_overview,
    build_sharing_result,
    build_turn_result,
    enforce_folder_turn_access,
    ensure_not_observer,
    make_launch_prep,
    sanitize_user_pinned_notes,
    validate_sharing_request,
)
from orcia_core.orchestration._assistant_folders_models import (
    PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    THREAD_TURN_LOCK_TTL_SECONDS,
    AssistantFolderRecord,
    AssistantHistorySearchHit,
    AssistantMainTab,
    AssistantThreadSummary,
    AssistantWorkspaceOverview,
    CollaborativeThreadTurnResult,
    FolderAccessRole,
    FolderShareGrant,
    FolderSharingUpdateResult,
    FolderVisibilityMode,
    FolderWorkflowLaunchPreparation,
    Layer5FolderMemoryInjection,
    _ActiveTurnLockEntry,
)
from orcia_core.orchestration._assistant_folders_sync import _AssistantFoldersSyncMixin
from orcia_core.orchestration._internal.sql_assistant_folders import SqlAssistantFoldersRepository
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


class AssistantFoldersAndSharingService(_AssistantFoldersSyncMixin):
    """Domain service for Story 10.4 (`📁 Dossiers`, Layer 5 Memory, Sharing & Redis Turn Lock)."""

    def __init__(self, *, engine: AsyncEngine | None = None) -> None:
        self._engine: AsyncEngine | None = engine
        self._sql_repo: SqlAssistantFoldersRepository | None = (
            SqlAssistantFoldersRepository(engine) if engine is not None else None
        )
        self._folders: dict[str, AssistantFolderRecord] = {}
        self._threads: dict[str, AssistantThreadSummary] = {}
        self._folder_meta: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        self._workspace_members: dict[str, set[str]] = {}
        self._turn_locks: dict[str, _ActiveTurnLockEntry] = {}

    def set_engine(self, engine: AsyncEngine | None) -> None:
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
        self._engine = engine
        self._sql_repo = SqlAssistantFoldersRepository(engine) if engine is not None else None

    async def _pg_ready(self) -> bool:
        return self._sql_repo is not None and await self._sql_repo.pg_tables_ready()

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
        ensure_not_observer(user)
        clean_title = title.strip()
        if not clean_title:
            raise ValidationDomainError(
                detail_override="Le titre du dossier thématique ne peut pas être vide."
            )
        self.register_workspace_members(workspace_id, [user.id])
        resolved_folder_id = folder_id or new_uuid7_str()
        attachments = tuple(working_attachments_uris or ())
        tags = tuple(evidence_tags or ("S1",))
        self._folder_meta[resolved_folder_id] = (attachments, tags)
        return AssistantFolderRecord(
            folder_id=resolved_folder_id,
            workspace_id=workspace_id,
            owner_user_id=existing.owner_user_id if existing is not None else user.id,
            title=clean_title,
            pinned_notes_markdown=sanitize_user_pinned_notes(pinned_notes_markdown),
            working_attachments_uris=attachments,
            consolidated_summary=consolidated_summary.strip(),
            evidence_tags=tags,
            has_restricted_sources=has_restricted_sources,
            visibility_mode=existing.visibility_mode if existing is not None else "PRIVATE",
            shares=existing.shares if existing is not None else (),
        )

    async def create_or_update_folder_async(
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
        """Create or update a thematic `📁 Dossier` persisted in PostgreSQL 18."""
        existing = (
            await self._sql_repo.get_folder(workspace_id=workspace_id, folder_id=folder_id)
            if (folder_id and await self._pg_ready() and self._sql_repo is not None)
            else (self._folders.get(folder_id) if folder_id else None)
        )
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
        if not await self._pg_ready():
            self._folders[record.folder_id] = record
            return record
        assert self._sql_repo is not None
        persisted = await self._sql_repo.upsert_folder(folder=record, user=user)
        self._folders[persisted.folder_id] = persisted
        return persisted

    async def create_thread_in_folder_async(
        self,
        *,
        workspace_id: str,
        user: UserIdentity,
        title: str,
        folder_id: str | None = None,
        initial_summary: str = "",
        thread_id: str | None = None,
    ) -> AssistantThreadSummary:
        """Create and persist a discussion thread in PostgreSQL 18 `assistant_threads`."""
        if not await self._pg_ready():
            return self.create_thread_in_folder(
                workspace_id=workspace_id,
                user=user,
                title=title,
                folder_id=folder_id,
                initial_summary=initial_summary,
                thread_id=thread_id,
            )
        assert self._sql_repo is not None
        ensure_not_observer(user)
        self.register_workspace_members(workspace_id, [user.id])
        draft = AssistantThreadSummary(
            thread_id=thread_id or new_uuid7_str(),
            workspace_id=workspace_id,
            folder_id=folder_id,
            creator_user_id=user.id,
            title=title.strip() or "Nouvelle discussion",
            thread_summary=initial_summary.strip(),
            turn_count=1 if initial_summary.strip() else 0,
            last_author_user_id=user.id,
            last_author_passthrough_identity=f"passthrough:oidc:{user.id}:{user.email}",
        )
        persisted = await self._sql_repo.create_thread(thread=draft, user=user)
        self._threads[persisted.thread_id] = persisted
        return persisted

    async def build_layer5_folder_memory_injection_async(
        self, *, workspace_id: str, folder_id: str
    ) -> Layer5FolderMemoryInjection:
        """Assemble internal Layer 5 memory block from PG18 folder & threads."""
        if not await self._pg_ready():
            return self.build_layer5_folder_memory_injection(
                workspace_id=workspace_id, folder_id=folder_id
            )
        assert self._sql_repo is not None
        folders, threads = await self._sql_repo.list_workspace_folders_and_threads(
            workspace_id=workspace_id
        )
        folder = next((f for f in folders if f.folder_id == folder_id), None)
        if folder is None:
            raise ResourceNotFoundError(
                detail_override=f"Dossier introuvable dans l'Espace {workspace_id} : {folder_id}"
            )
        att, tags = self._folder_meta.get(
            folder_id, (folder.working_attachments_uris, folder.evidence_tags)
        )
        enriched = AssistantFolderRecord(
            **{**folder.__dict__, "working_attachments_uris": att, "evidence_tags": tags}
        )
        summaries = [
            t.thread_summary for t in threads if t.folder_id == folder_id and t.thread_summary
        ]
        return assemble_layer5_injection(enriched, summaries)

    async def prepare_workflow_launch_from_folder_async(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        user: UserIdentity,
        target_workflow_uri: str = PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    ) -> FolderWorkflowLaunchPreparation:
        """Pre-fill a Process contract in 1 click from a PG18 thematic folder."""
        if not await self._pg_ready():
            return self.prepare_workflow_launch_from_folder(
                workspace_id=workspace_id,
                folder_id=folder_id,
                user=user,
                target_workflow_uri=target_workflow_uri,
            )
        assert self._sql_repo is not None
        ensure_not_observer(user)
        memory = await self.build_layer5_folder_memory_injection_async(
            workspace_id=workspace_id, folder_id=folder_id
        )
        folder = await self._sql_repo.get_folder(workspace_id=workspace_id, folder_id=folder_id)
        if folder is None:
            raise ResourceNotFoundError(detail_override=f"Dossier introuvable : {folder_id}")
        return make_launch_prep(folder, memory, user, target_workflow_uri)

    async def configure_folder_sharing_async(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        owner_user: UserIdentity,
        visibility_mode: FolderVisibilityMode,
        shares: list[FolderShareGrant] | None = None,
        outside_workspace_user_ids: list[str] | None = None,
    ) -> FolderSharingUpdateResult:
        """Configure folder visibility (`🔒 | 👥 | 📦`) and persist to PG18."""
        if not await self._pg_ready():
            return self.configure_folder_sharing(
                workspace_id=workspace_id,
                folder_id=folder_id,
                owner_user=owner_user,
                visibility_mode=visibility_mode,
                shares=shares,
                outside_workspace_user_ids=outside_workspace_user_ids,
            )
        assert self._sql_repo is not None
        ensure_not_observer(owner_user)
        folder = await self._sql_repo.get_folder(workspace_id=workspace_id, folder_id=folder_id)
        if folder is None:
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
        updated = await self._sql_repo.configure_sharing(
            workspace_id=workspace_id,
            folder_id=folder_id,
            visibility_mode=visibility_mode,
            shares=resolved_shares,
        )
        self._folders[updated.folder_id] = updated
        return build_sharing_result(updated)

    async def send_collaborative_thread_turn_async(
        self,
        *,
        workspace_id: str,
        thread_id: str,
        sender_user: UserIdentity,
        message_text: str,
        release_lock_after_turn: bool = False,
    ) -> CollaborativeThreadTurnResult:
        """Execute and persist a collaborative thread turn in PG18."""
        if not await self._pg_ready():
            return self.send_collaborative_thread_turn(
                workspace_id=workspace_id,
                thread_id=thread_id,
                sender_user=sender_user,
                message_text=message_text,
                release_lock_after_turn=release_lock_after_turn,
            )
        assert self._sql_repo is not None
        ensure_not_observer(sender_user)
        thread = await self._sql_repo.get_thread(workspace_id=workspace_id, thread_id=thread_id)
        if thread is None:
            raise ResourceNotFoundError(detail_override=f"Discussion introuvable : {thread_id}")
        folder = (
            await self._sql_repo.get_folder(workspace_id=workspace_id, folder_id=thread.folder_id)
            if thread.folder_id
            else None
        )
        enforce_folder_turn_access(folder, sender_user)
        lock_key = self.acquire_thread_turn_lock(
            thread_id=thread_id, user_id=sender_user.id, ttl_seconds=THREAD_TURN_LOCK_TTL_SECONDS
        )
        personal_passthrough = f"passthrough:oidc:{sender_user.id}:{sender_user.email}"
        next_summary = f"{thread.thread_summary} | {message_text.strip()}".strip(" |")
        updated = await self._sql_repo.update_thread_turn(
            thread_id=thread_id,
            workspace_id=workspace_id,
            thread_summary=next_summary,
            turn_count=thread.turn_count + 1,
            author=sender_user,
            passthrough_identity=personal_passthrough,
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

    async def get_workspace_overview_async(
        self, *, workspace_id: str, active_folder_id: str | None = None, search_query: str = ""
    ) -> AssistantWorkspaceOverview:
        """Return the 3-tab structure hydrated from PostgreSQL 18."""
        if not await self._pg_ready():
            return self.get_workspace_overview(
                workspace_id=workspace_id,
                active_folder_id=active_folder_id,
                search_query=search_query,
            )
        assert self._sql_repo is not None
        ws_folders, ws_threads = await self._sql_repo.list_workspace_folders_and_threads(
            workspace_id=workspace_id
        )
        return assemble_overview(
            workspace_id=workspace_id,
            ws_folders=ws_folders,
            ws_threads=ws_threads,
            active_folder_id=active_folder_id,
            search_query=search_query,
        )


__all__ = [
    "AssistantFolderRecord",
    "AssistantFoldersAndSharingService",
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
    "sanitize_user_pinned_notes",
]
