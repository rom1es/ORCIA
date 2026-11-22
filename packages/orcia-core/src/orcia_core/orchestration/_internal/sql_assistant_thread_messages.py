"""PG18 SQLAlchemy repository for `assistant_thread_messages` (`AD-25`, `D4`, `Story 26.5`)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._internal._sql_assistant_folders_queries import (
    coerce_folder_uuid,
    resolve_workspace_uuid,
)
from orcia_kernel.ids import new_uuid7_str

MessageRole = Literal["user", "assistant"]

_SQL_UPSERT_MESSAGE = sa.text(
    """
    INSERT INTO assistant_thread_messages (
        id, thread_id, workspace_id, turn_id, parent_turn_id,
        role, content, citation_map, token_count
    ) VALUES (
        CAST(:id AS uuid), CAST(:thread_id AS uuid), CAST(:workspace_id AS uuid),
        CAST(:turn_id AS uuid), CAST(:parent_turn_id AS uuid),
        :role, :content, CAST(:citation_map AS jsonb), :token_count
    )
    ON CONFLICT (turn_id, role) DO UPDATE SET
        content = EXCLUDED.content,
        citation_map = EXCLUDED.citation_map,
        token_count = EXCLUDED.token_count
    RETURNING id, thread_id, workspace_id, turn_id, parent_turn_id,
              role, content, citation_map, token_count, created_at;
    """
)

_SQL_LIST_MESSAGES = sa.text(
    """
    SELECT m.id, m.thread_id, m.workspace_id, m.turn_id, m.parent_turn_id,
           m.role, m.content, m.citation_map, m.token_count, m.created_at
    FROM assistant_thread_messages m
    JOIN workspaces w ON w.id = m.workspace_id
    WHERE m.thread_id = CAST(:thread_id AS uuid)
      AND (w.id::text = :ws OR w.slug = :ws)
    ORDER BY m.created_at ASC, m.id ASC
    LIMIT :limit;
    """
)


@dataclass(frozen=True, slots=True)
class AssistantThreadMessageRecord:
    """Persisted row representation for `assistant_thread_messages` (`D4`)."""

    message_id: str
    thread_id: str
    workspace_id: str
    turn_id: str
    role: MessageRole
    content: str
    parent_turn_id: str | None = None
    citation_map: dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    created_at: str = ""


def _decode_citation_map(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        decoded = json.loads(raw)
        if isinstance(decoded, dict):
            return decoded
    return {}


class SqlAssistantThreadMessagesRepository:
    """Async PostgreSQL 18 repository for `assistant_thread_messages` (`D4`, `H-18`)."""

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self._engine = engine
        self._tables_ready_verified = False

    def set_engine(self, engine: AsyncEngine | None) -> None:
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
        self._engine = engine
        self._tables_ready_verified = False

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `assistant_thread_messages` exists in PostgreSQL 18."""
        if self._engine is None:
            return False
        if self._tables_ready_verified:
            return True
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.assistant_thread_messages')")
                )
            ).scalar()
            ready = reg is not None
            if ready:
                self._tables_ready_verified = True
            return ready

    async def append_message(
        self,
        *,
        thread_id: str,
        workspace_id: str,
        turn_id: str,
        role: MessageRole,
        content: str,
        parent_turn_id: str | None = None,
        citation_map: dict[str, Any] | None = None,
        token_count: int | None = None,
    ) -> AssistantThreadMessageRecord:
        """Idempotently persist a `user` or `assistant` message in `assistant_thread_messages`."""
        thread_uuid = coerce_folder_uuid(thread_id)
        turn_uuid = coerce_folder_uuid(turn_id)
        parent_uuid = str(coerce_folder_uuid(parent_turn_id)) if parent_turn_id else None
        computed_tokens = (
            max(0, int(token_count))
            if token_count is not None
            else (max(1, len(content) // 4) if content else 0)
        )
        c_map = dict(citation_map or {})
        if not await self.pg_tables_ready():
            return AssistantThreadMessageRecord(
                message_id=new_uuid7_str(),
                thread_id=str(thread_uuid),
                workspace_id=workspace_id,
                turn_id=str(turn_uuid),
                parent_turn_id=parent_uuid,
                role=role,
                content=content,
                citation_map=c_map,
                token_count=computed_tokens,
            )
        assert self._engine is not None
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=True)
            assert ws_uuid is not None
            row = (
                (
                    await conn.execute(
                        _SQL_UPSERT_MESSAGE,
                        {
                            "id": new_uuid7_str(),
                            "thread_id": str(thread_uuid),
                            "workspace_id": str(ws_uuid),
                            "turn_id": str(turn_uuid),
                            "parent_turn_id": parent_uuid,
                            "role": role,
                            "content": content,
                            "citation_map": json.dumps(c_map),
                            "token_count": computed_tokens,
                        },
                    )
                )
                .mappings()
                .one()
            )
        return self._row_to_record(row)

    async def list_messages_for_thread(
        self,
        *,
        workspace_id: str,
        thread_id: str,
        limit: int = 200,
    ) -> tuple[AssistantThreadMessageRecord, ...]:
        """Return ordered `(user, assistant)` messages for `(workspace_id, thread_id)`."""
        if not await self.pg_tables_ready():
            return ()
        assert self._engine is not None
        thread_uuid = coerce_folder_uuid(thread_id)
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        _SQL_LIST_MESSAGES,
                        {
                            "thread_id": str(thread_uuid),
                            "ws": workspace_id.strip(),
                            "limit": max(1, min(int(limit), 500)),
                        },
                    )
                )
                .mappings()
                .all()
            )
        return tuple(self._row_to_record(r) for r in rows)

    @staticmethod
    def _row_to_record(row: sa.RowMapping) -> AssistantThreadMessageRecord:
        created = row["created_at"]
        return AssistantThreadMessageRecord(
            message_id=str(row["id"]),
            thread_id=str(row["thread_id"]),
            workspace_id=str(row["workspace_id"]),
            turn_id=str(row["turn_id"]),
            parent_turn_id=str(row["parent_turn_id"]) if row["parent_turn_id"] else None,
            role=cast(MessageRole, str(row["role"])),
            content=str(row["content"]),
            citation_map=_decode_citation_map(row["citation_map"]),
            token_count=int(row["token_count"] or 0),
            created_at=created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
        )


__all__ = [
    "AssistantThreadMessageRecord",
    "MessageRole",
    "SqlAssistantThreadMessagesRepository",
]
