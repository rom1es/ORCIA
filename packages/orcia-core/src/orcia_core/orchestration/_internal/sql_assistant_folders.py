"""PG18 repository for `assistant_folders`, `assistant_threads` & `assistant_folder_shares`."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._assistant_folders_models import (
    AssistantFolderRecord,
    AssistantThreadSummary,
    FolderShareGrant,
    FolderVisibilityMode,
)
from orcia_core.orchestration._internal._sql_assistant_folders_mutations import (
    configure_sharing_sql,
    create_thread_sql,
    get_thread_sql,
    update_thread_turn_sql,
)
from orcia_core.orchestration._internal._sql_assistant_folders_queries import (
    SQL_UPSERT_FOLDER,
    coerce_folder_uuid,
    fetch_workspace_folders_and_threads,
    load_shares_for_folder,
    resolve_user_uuid,
    resolve_workspace_uuid,
    row_to_folder,
)
from orcia_core.permissions.models import UserIdentity


class SqlAssistantFoldersRepository:
    """Async SQLAlchemy repository for `assistant_folders`, `assistant_threads`, and shares."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `assistant_folders` exists in PG18."""
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.assistant_folders')"))
            ).scalar()
            return reg is not None

    async def upsert_folder(
        self, *, folder: AssistantFolderRecord, user: UserIdentity
    ) -> AssistantFolderRecord:
        """Create or update a folder in `assistant_folders` including attachment/tag metadata."""
        folder_uuid = coerce_folder_uuid(folder.folder_id)
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, folder.workspace_id, required=True)
            assert ws_uuid is not None
            owner_uuid = await resolve_user_uuid(
                conn, user_id=folder.owner_user_id, email=user.email, user=user
            )
            row = (
                (
                    await conn.execute(
                        SQL_UPSERT_FOLDER,
                        {
                            "folder_id": str(folder_uuid),
                            "workspace_id": str(ws_uuid),
                            "owner_user_id": str(owner_uuid),
                            "title": folder.title,
                            "pinned_notes_markdown": folder.pinned_notes_markdown,
                            "visibility_mode": folder.visibility_mode,
                            "consolidated_summary": folder.consolidated_summary,
                            "has_restricted_sources": folder.has_restricted_sources,
                            "working_attachments_uris": json.dumps(
                                list(folder.working_attachments_uris), ensure_ascii=False
                            ),
                            "evidence_tags": list(folder.evidence_tags),
                        },
                    )
                )
                .mappings()
                .one()
            )
            shares = await load_shares_for_folder(conn, folder_uuid)
            return row_to_folder(row, shares)

    async def get_folder(
        self, *, workspace_id: str, folder_id: str
    ) -> AssistantFolderRecord | None:
        """Fetch a single folder by `(workspace_id, folder_id)` from PG18."""
        folder_uuid = coerce_folder_uuid(folder_id)
        async with self._engine.connect() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=False)
            if ws_uuid is None:
                return None
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT folder_id, workspace_id, owner_user_id, title, "
                            "pinned_notes_markdown, visibility_mode, consolidated_summary, "
                            "has_restricted_sources, working_attachments_uris, evidence_tags "
                            "FROM assistant_folders "
                            "WHERE folder_id = CAST(:folder_id AS uuid) "
                            "AND workspace_id = CAST(:workspace_id AS uuid) LIMIT 1"
                        ),
                        {"folder_id": str(folder_uuid), "workspace_id": str(ws_uuid)},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            return row_to_folder(row, await load_shares_for_folder(conn, folder_uuid))

    async def create_thread(
        self, *, thread: AssistantThreadSummary, user: UserIdentity
    ) -> AssistantThreadSummary:
        """Insert or update a thread in `assistant_threads`."""
        return await create_thread_sql(self._engine, thread=thread, user=user)

    async def get_thread(
        self, *, workspace_id: str, thread_id: str
    ) -> AssistantThreadSummary | None:
        """Fetch a single thread by `(workspace_id, thread_id)` from PG18."""
        return await get_thread_sql(self._engine, workspace_id=workspace_id, thread_id=thread_id)

    async def update_thread_turn(
        self,
        *,
        thread_id: str,
        workspace_id: str,
        thread_summary: str,
        turn_count: int,
        author: UserIdentity,
        passthrough_identity: str,
    ) -> AssistantThreadSummary:
        """Persist updated summary, turn_count, and last author on `assistant_threads`."""
        return await update_thread_turn_sql(
            self._engine,
            thread_id=thread_id,
            workspace_id=workspace_id,
            thread_summary=thread_summary,
            turn_count=turn_count,
            author=author,
            passthrough_identity=passthrough_identity,
        )

    async def configure_sharing(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        visibility_mode: FolderVisibilityMode,
        shares: tuple[FolderShareGrant, ...],
    ) -> AssistantFolderRecord:
        """Update `visibility_mode` and replace `assistant_folder_shares` in PG18."""
        return await configure_sharing_sql(
            self._engine,
            workspace_id=workspace_id,
            folder_id=folder_id,
            visibility_mode=visibility_mode,
            shares=shares,
        )

    async def list_workspace_folders_and_threads(
        self, *, workspace_id: str
    ) -> tuple[tuple[AssistantFolderRecord, ...], tuple[AssistantThreadSummary, ...]]:
        """List all folders (with shares) and threads for `workspace_id` from PG18."""
        async with self._engine.connect() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=False)
            if ws_uuid is None:
                return (), ()
            return await fetch_workspace_folders_and_threads(conn, ws_uuid)


__all__ = ["SqlAssistantFoldersRepository"]
