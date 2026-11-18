"""PG18 repository for `assistant_folders`, `assistant_threads` & `assistant_folder_shares`.

Aligned on Alembic migration `0025_story_10_4` (`REM-08`).
"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._assistant_folders_models import (
    AssistantFolderRecord,
    AssistantThreadSummary,
    FolderShareGrant,
    FolderVisibilityMode,
)
from orcia_core.orchestration._internal._sql_assistant_folders_queries import (
    SQL_UPDATE_THREAD_TURN,
    SQL_UPSERT_FOLDER,
    SQL_UPSERT_SHARE,
    SQL_UPSERT_THREAD,
    coerce_folder_uuid,
    fetch_workspace_folders_and_threads,
    load_shares_for_folder,
    resolve_user_uuid,
    resolve_workspace_uuid,
    row_to_folder,
    row_to_thread,
)
from orcia_core.orchestration.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str


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
        """Create or update a folder in `assistant_folders`."""
        folder_uuid = coerce_folder_uuid(folder.folder_id)
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, folder.workspace_id, required=True)
            assert ws_uuid is not None
            owner_uuid = await resolve_user_uuid(
                conn, user_id=folder.owner_user_id, email=user.email
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
                        },
                    )
                )
                .mappings()
                .one()
            )
            shares = await load_shares_for_folder(conn, folder_uuid)
            return row_to_folder(
                row,
                shares,
                attachments=folder.working_attachments_uris,
                evidence_tags=folder.evidence_tags,
            )

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
                            "has_restricted_sources FROM assistant_folders "
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
        thread_uuid = coerce_folder_uuid(thread.thread_id)
        folder_uuid = coerce_folder_uuid(thread.folder_id) if thread.folder_id else None
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, thread.workspace_id, required=True)
            assert ws_uuid is not None
            if folder_uuid is not None:
                exists_f = (
                    await conn.execute(
                        sa.text(
                            "SELECT folder_id FROM assistant_folders "
                            "WHERE folder_id = CAST(:fid AS uuid) "
                            "AND workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"fid": str(folder_uuid), "ws": str(ws_uuid)},
                    )
                ).first()
                if exists_f is None:
                    raise ResourceNotFoundError(
                        detail_override=f"Dossier introuvable : {thread.folder_id}"
                    )
            creator_uuid = await resolve_user_uuid(
                conn, user_id=thread.creator_user_id, email=user.email
            )
            row = (
                (
                    await conn.execute(
                        SQL_UPSERT_THREAD,
                        {
                            "thread_id": str(thread_uuid),
                            "workspace_id": str(ws_uuid),
                            "folder_id": str(folder_uuid) if folder_uuid is not None else None,
                            "creator_user_id": str(creator_uuid),
                            "title": thread.title,
                            "thread_summary": thread.thread_summary,
                            "turn_count": thread.turn_count,
                            "last_author_user_id": str(creator_uuid),
                            "last_author_passthrough_identity": (
                                thread.last_author_passthrough_identity
                            ),
                        },
                    )
                )
                .mappings()
                .one()
            )
            return row_to_thread(row)

    async def get_thread(
        self, *, workspace_id: str, thread_id: str
    ) -> AssistantThreadSummary | None:
        """Fetch a single thread by `(workspace_id, thread_id)` from PG18."""
        thread_uuid = coerce_folder_uuid(thread_id)
        async with self._engine.connect() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=False)
            if ws_uuid is None:
                return None
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT thread_id, workspace_id, folder_id, creator_user_id, title, "
                            "thread_summary, turn_count, last_author_user_id, "
                            "last_author_passthrough_identity FROM assistant_threads "
                            "WHERE thread_id = CAST(:thread_id AS uuid) "
                            "AND workspace_id = CAST(:workspace_id AS uuid) LIMIT 1"
                        ),
                        {"thread_id": str(thread_uuid), "workspace_id": str(ws_uuid)},
                    )
                )
                .mappings()
                .first()
            )
            return row_to_thread(row) if row is not None else None

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
        thread_uuid = coerce_folder_uuid(thread_id)
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=True)
            assert ws_uuid is not None
            author_uuid = await resolve_user_uuid(conn, user_id=author.id, email=author.email)
            row = (
                (
                    await conn.execute(
                        SQL_UPDATE_THREAD_TURN,
                        {
                            "thread_summary": thread_summary,
                            "turn_count": turn_count,
                            "author_id": str(author_uuid),
                            "passthrough_id": passthrough_identity,
                            "thread_id": str(thread_uuid),
                            "workspace_id": str(ws_uuid),
                        },
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ResourceNotFoundError(detail_override=f"Discussion introuvable : {thread_id}")
            return row_to_thread(row)

    async def configure_sharing(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        visibility_mode: FolderVisibilityMode,
        shares: tuple[FolderShareGrant, ...],
    ) -> AssistantFolderRecord:
        """Update `visibility_mode` and replace `assistant_folder_shares` in PG18."""
        folder_uuid = coerce_folder_uuid(folder_id)
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=True)
            assert ws_uuid is not None
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "UPDATE assistant_folders SET visibility_mode = :visibility_mode, "
                            "updated_at = NOW() WHERE folder_id = CAST(:folder_id AS uuid) "
                            "AND workspace_id = CAST(:workspace_id AS uuid) "
                            "RETURNING folder_id, workspace_id, owner_user_id, title, "
                            "pinned_notes_markdown, visibility_mode, consolidated_summary, "
                            "has_restricted_sources"
                        ),
                        {
                            "visibility_mode": visibility_mode,
                            "folder_id": str(folder_uuid),
                            "workspace_id": str(ws_uuid),
                        },
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ResourceNotFoundError(detail_override=f"Dossier introuvable : {folder_id}")
            await conn.execute(
                sa.text("DELETE FROM assistant_folder_shares WHERE folder_id = CAST(:fid AS uuid)"),
                {"fid": str(folder_uuid)},
            )
            persisted_shares: list[FolderShareGrant] = []
            if visibility_mode == "SHARED_SELECTED":
                for grant in shares:
                    grantee_row = (
                        await conn.execute(
                            sa.text(
                                "SELECT id FROM users WHERE id::text = :uid "
                                "OR lower(email) = lower(:uid) LIMIT 1"
                            ),
                            {"uid": grant.grantee_user_id.strip()},
                        )
                    ).first()
                    if grantee_row is None:
                        raise ScopeAccessDeniedError(
                            detail_override=(
                                f"Confinement à l'Espace ({workspace_id}) : utilisateur "
                                f"introuvable '{grant.grantee_user_id}' (AD-21)."
                            )
                        )
                    grantee_uuid = UUID(str(grantee_row[0]))
                    await conn.execute(
                        SQL_UPSERT_SHARE,
                        {
                            "share_id": new_uuid7_str(),
                            "folder_id": str(folder_uuid),
                            "workspace_id": str(ws_uuid),
                            "grantee_user_id": str(grantee_uuid),
                            "access_role": grant.access_role,
                        },
                    )
                    persisted_shares.append(
                        FolderShareGrant(
                            grantee_user_id=str(grantee_uuid),
                            access_role=grant.access_role,
                        )
                    )
            return row_to_folder(row, tuple(persisted_shares))

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
