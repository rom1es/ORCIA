"""SQL statements & row mappers for `SqlAssistantFoldersRepository` (`0025_story_10_4`)."""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.orchestration._assistant_folders_models import (
    AssistantFolderRecord,
    AssistantThreadSummary,
    FolderAccessRole,
    FolderShareGrant,
    FolderVisibilityMode,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_kernel.ids import new_uuid7_str

_ORCIA_FOLDER_NS = UUID("0195f000-0000-7000-8000-00000000f000")

SQL_UPSERT_FOLDER = sa.text(
    """
    INSERT INTO assistant_folders (
        folder_id, workspace_id, owner_user_id, title,
        pinned_notes_markdown, visibility_mode,
        consolidated_summary, has_restricted_sources
    ) VALUES (
        CAST(:folder_id AS uuid), CAST(:workspace_id AS uuid),
        CAST(:owner_user_id AS uuid), :title,
        :pinned_notes_markdown, :visibility_mode,
        :consolidated_summary, :has_restricted_sources
    )
    ON CONFLICT (folder_id) DO UPDATE SET
        title = EXCLUDED.title,
        pinned_notes_markdown = EXCLUDED.pinned_notes_markdown,
        consolidated_summary = EXCLUDED.consolidated_summary,
        has_restricted_sources = EXCLUDED.has_restricted_sources,
        updated_at = NOW()
    RETURNING folder_id, workspace_id, owner_user_id, title,
              pinned_notes_markdown, visibility_mode,
              consolidated_summary, has_restricted_sources
    """
)

SQL_UPSERT_THREAD = sa.text(
    """
    INSERT INTO assistant_threads (
        thread_id, workspace_id, folder_id, creator_user_id,
        title, thread_summary, turn_count,
        last_author_user_id, last_author_passthrough_identity
    ) VALUES (
        CAST(:thread_id AS uuid), CAST(:workspace_id AS uuid),
        CAST(:folder_id AS uuid), CAST(:creator_user_id AS uuid),
        :title, :thread_summary, :turn_count,
        CAST(:last_author_user_id AS uuid), :last_author_passthrough_identity
    )
    ON CONFLICT (thread_id) DO UPDATE SET
        title = EXCLUDED.title,
        thread_summary = EXCLUDED.thread_summary,
        turn_count = EXCLUDED.turn_count,
        last_author_user_id = EXCLUDED.last_author_user_id,
        last_author_passthrough_identity = EXCLUDED.last_author_passthrough_identity,
        updated_at = NOW()
    RETURNING thread_id, workspace_id, folder_id, creator_user_id,
              title, thread_summary, turn_count,
              last_author_user_id, last_author_passthrough_identity
    """
)

SQL_UPDATE_THREAD_TURN = sa.text(
    """
    UPDATE assistant_threads
       SET thread_summary = :thread_summary,
           turn_count = :turn_count,
           last_author_user_id = CAST(:author_id AS uuid),
           last_author_passthrough_identity = :passthrough_id,
           updated_at = NOW()
     WHERE thread_id = CAST(:thread_id AS uuid)
       AND workspace_id = CAST(:workspace_id AS uuid)
    RETURNING thread_id, workspace_id, folder_id, creator_user_id,
              title, thread_summary, turn_count,
              last_author_user_id, last_author_passthrough_identity
    """
)

SQL_UPSERT_SHARE = sa.text(
    """
    INSERT INTO assistant_folder_shares (
        share_id, folder_id, workspace_id, grantee_user_id, access_role
    ) VALUES (
        CAST(:share_id AS uuid), CAST(:folder_id AS uuid),
        CAST(:workspace_id AS uuid), CAST(:grantee_user_id AS uuid), :access_role
    )
    ON CONFLICT (folder_id, grantee_user_id) DO UPDATE SET
        access_role = EXCLUDED.access_role
    """
)


def coerce_folder_uuid(raw_id: str | None) -> UUID:
    """Convert any ID into a valid UUID (deterministic UUIDv5 for non-UUID keys)."""
    if raw_id is None or not raw_id.strip():
        return UUID(new_uuid7_str())
    cleaned = raw_id.strip()
    try:
        return UUID(cleaned)
    except ValueError:
        return uuid5(_ORCIA_FOLDER_NS, cleaned)


async def resolve_workspace_uuid(
    conn: AsyncConnection, workspace_id: str, *, required: bool = True
) -> UUID | None:
    """Resolve `workspaces.id` by UUID string or slug."""
    row = (
        await conn.execute(
            sa.text("SELECT id FROM workspaces WHERE id::text = :ws OR slug = :ws LIMIT 1"),
            {"ws": workspace_id.strip()},
        )
    ).first()
    if row is not None:
        return UUID(str(row[0]))
    if required:
        raise ResourceNotFoundError(
            detail_override=f"Espace de travail '{workspace_id}' introuvable en base."
        )
    return None


async def resolve_user_uuid(
    conn: AsyncConnection, *, user_id: str, email: str | None = None
) -> UUID:
    """Resolve `users.id` by UUID or email, falling back to first registered user."""
    row = (
        await conn.execute(
            sa.text(
                "SELECT id FROM users "
                "WHERE id::text = :uid OR (:email <> '' AND lower(email) = lower(:email)) "
                "LIMIT 1"
            ),
            {"uid": user_id.strip(), "email": (email or "").strip()},
        )
    ).first()
    if row is not None:
        return UUID(str(row[0]))
    fallback = (
        await conn.execute(sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1"))
    ).first()
    if fallback is not None:
        return UUID(str(fallback[0]))
    raise ResourceNotFoundError(
        detail_override="Aucun compte utilisateur enregistré en base pour cette opération."
    )


def row_to_folder(
    row: RowMapping,
    shares: tuple[FolderShareGrant, ...],
    attachments: tuple[str, ...] = (),
    evidence_tags: tuple[str, ...] = ("S1",),
) -> AssistantFolderRecord:
    """Map an `assistant_folders` row into `AssistantFolderRecord`."""
    return AssistantFolderRecord(
        folder_id=str(row["folder_id"]),
        workspace_id=str(row["workspace_id"]),
        owner_user_id=str(row["owner_user_id"]),
        title=str(row["title"]),
        pinned_notes_markdown=str(row["pinned_notes_markdown"] or ""),
        working_attachments_uris=attachments,
        consolidated_summary=str(row["consolidated_summary"] or ""),
        evidence_tags=evidence_tags,
        has_restricted_sources=bool(row["has_restricted_sources"]),
        visibility_mode=cast(FolderVisibilityMode, str(row["visibility_mode"])),
        shares=shares,
    )


def row_to_thread(row: RowMapping) -> AssistantThreadSummary:
    """Map an `assistant_threads` row into `AssistantThreadSummary`."""
    return AssistantThreadSummary(
        thread_id=str(row["thread_id"]),
        workspace_id=str(row["workspace_id"]),
        folder_id=str(row["folder_id"]) if row["folder_id"] is not None else None,
        creator_user_id=str(row["creator_user_id"]),
        title=str(row["title"]),
        thread_summary=str(row["thread_summary"] or ""),
        turn_count=int(row["turn_count"] or 0),
        last_author_user_id=(
            str(row["last_author_user_id"]) if row["last_author_user_id"] is not None else None
        ),
        last_author_passthrough_identity=(
            str(row["last_author_passthrough_identity"])
            if row["last_author_passthrough_identity"] is not None
            else None
        ),
    )


async def load_shares_for_folder(
    conn: AsyncConnection, folder_uuid: UUID
) -> tuple[FolderShareGrant, ...]:
    """Load `assistant_folder_shares` for `folder_uuid`."""
    rows = (
        (
            await conn.execute(
                sa.text(
                    "SELECT grantee_user_id, access_role FROM assistant_folder_shares "
                    "WHERE folder_id = CAST(:folder_id AS uuid) ORDER BY created_at ASC"
                ),
                {"folder_id": str(folder_uuid)},
            )
        )
        .mappings()
        .all()
    )
    return tuple(
        FolderShareGrant(
            grantee_user_id=str(r["grantee_user_id"]),
            access_role=cast(FolderAccessRole, str(r["access_role"])),
        )
        for r in rows
    )


async def fetch_workspace_folders_and_threads(
    conn: AsyncConnection, ws_uuid: UUID
) -> tuple[tuple[AssistantFolderRecord, ...], tuple[AssistantThreadSummary, ...]]:
    """Query folders, share grants, and threads for `ws_uuid`."""
    folder_rows = (
        (
            await conn.execute(
                sa.text(
                    "SELECT folder_id, workspace_id, owner_user_id, title, "
                    "pinned_notes_markdown, visibility_mode, consolidated_summary, "
                    "has_restricted_sources FROM assistant_folders "
                    "WHERE workspace_id = CAST(:workspace_id AS uuid) ORDER BY created_at ASC"
                ),
                {"workspace_id": str(ws_uuid)},
            )
        )
        .mappings()
        .all()
    )
    share_rows = (
        (
            await conn.execute(
                sa.text(
                    "SELECT folder_id, grantee_user_id, access_role FROM assistant_folder_shares "
                    "WHERE workspace_id = CAST(:workspace_id AS uuid) ORDER BY created_at ASC"
                ),
                {"workspace_id": str(ws_uuid)},
            )
        )
        .mappings()
        .all()
    )
    shares_by_folder: dict[str, list[FolderShareGrant]] = {}
    for sr in share_rows:
        shares_by_folder.setdefault(str(sr["folder_id"]), []).append(
            FolderShareGrant(
                grantee_user_id=str(sr["grantee_user_id"]),
                access_role=cast(FolderAccessRole, str(sr["access_role"])),
            )
        )
    folders = tuple(
        row_to_folder(fr, tuple(shares_by_folder.get(str(fr["folder_id"]), ())))
        for fr in folder_rows
    )
    thread_rows = (
        (
            await conn.execute(
                sa.text(
                    "SELECT thread_id, workspace_id, folder_id, creator_user_id, title, "
                    "thread_summary, turn_count, last_author_user_id, "
                    "last_author_passthrough_identity FROM assistant_threads "
                    "WHERE workspace_id = CAST(:workspace_id AS uuid) ORDER BY created_at ASC"
                ),
                {"workspace_id": str(ws_uuid)},
            )
        )
        .mappings()
        .all()
    )
    return folders, tuple(row_to_thread(tr) for tr in thread_rows)
