"""SQL statements & row mappers for `SqlAssistantFoldersRepository` (`0025_story_10_4`, `26.4b`)."""

from __future__ import annotations

import json
from typing import Any, cast
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
from orcia_core.orchestration._internal._sql_assistant_folders_sql import (
    SQL_UPDATE_THREAD_TURN as SQL_UPDATE_THREAD_TURN,
)
from orcia_core.orchestration._internal._sql_assistant_folders_sql import (
    SQL_UPSERT_FOLDER as SQL_UPSERT_FOLDER,
)
from orcia_core.orchestration._internal._sql_assistant_folders_sql import (
    SQL_UPSERT_SHARE as SQL_UPSERT_SHARE,
)
from orcia_core.orchestration._internal._sql_assistant_folders_sql import (
    SQL_UPSERT_THREAD as SQL_UPSERT_THREAD,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_kernel.ids import new_uuid7_str

_ORCIA_FOLDER_NS = UUID("0195f000-0000-7000-8000-00000000f000")


def _decode_str_list(raw: Any, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if raw is None:
        return default
    if isinstance(raw, str):
        parsed = json.loads(raw) if raw.strip() else []
        return tuple(str(x) for x in parsed) if isinstance(parsed, list) else default
    if isinstance(raw, (list, tuple)):
        return tuple(str(x) for x in raw)
    return default


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
            detail_override=f"Workspace '{workspace_id}' not found in PostgreSQL 18."
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
        detail_override="No registered user account found in PostgreSQL 18 for this operation."
    )


def row_to_folder(
    row: RowMapping,
    shares: tuple[FolderShareGrant, ...],
) -> AssistantFolderRecord:
    """Map an `assistant_folders` row into `AssistantFolderRecord`."""
    attachments = _decode_str_list(row.get("working_attachments_uris"), default=())
    tags = _decode_str_list(row.get("evidence_tags"), default=())
    return AssistantFolderRecord(
        folder_id=str(row["folder_id"]),
        workspace_id=str(row["workspace_id"]),
        owner_user_id=str(row["owner_user_id"]),
        title=str(row["title"]),
        pinned_notes_markdown=str(row["pinned_notes_markdown"] or ""),
        working_attachments_uris=attachments,
        consolidated_summary=str(row["consolidated_summary"] or ""),
        evidence_tags=tags if tags else ("S1",),
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
                    "has_restricted_sources, working_attachments_uris, evidence_tags "
                    "FROM assistant_folders "
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
