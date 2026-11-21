"""Async read, launch-prep, and sharing mixin for `AssistantFoldersAndSharingService`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.orchestration._assistant_folders_helpers import (
    assemble_layer5_injection,
    assemble_overview,
    build_sharing_result,
    ensure_not_observer,
    make_launch_prep,
    validate_sharing_request,
)
from orcia_core.orchestration._assistant_folders_models import (
    PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    AssistantFolderRecord,
    AssistantWorkspaceOverview,
    FolderShareGrant,
    FolderSharingUpdateResult,
    FolderVisibilityMode,
    FolderWorkflowLaunchPreparation,
    Layer5FolderMemoryInjection,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration._internal.sql_assistant_folders import (
        SqlAssistantFoldersRepository,
    )


class _AssistantFoldersAsyncOpsMixin:
    """Async PostgreSQL 18 folder memory, launch preparation, sharing, and overview helpers."""

    _sql_repo: SqlAssistantFoldersRepository | None
    _folders: dict[str, AssistantFolderRecord]
    _folder_meta: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]
    _workspace_members: dict[str, set[str]]

    if TYPE_CHECKING:

        async def _pg_ready(self) -> bool: ...
        def build_layer5_folder_memory_injection(
            self, **kwargs: Any
        ) -> Layer5FolderMemoryInjection: ...
        def prepare_workflow_launch_from_folder(
            self, **kwargs: Any
        ) -> FolderWorkflowLaunchPreparation: ...
        def configure_folder_sharing(self, **kwargs: Any) -> FolderSharingUpdateResult: ...
        def get_workspace_overview(self, **kwargs: Any) -> AssistantWorkspaceOverview: ...

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
