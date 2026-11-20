"""PostgreSQL 18 SQLAlchemy Async repository for `mcp_governed_proposals` (`Story 24.1`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str

_SELECT_COLS = (
    "id::text, workspace_id, run_id, section_key, content_markdown, "
    "ide_client, execution_identity, status, proposed_by, created_at, updated_at"
)


def _row_to_proposal(row: RowMapping) -> dict[str, Any]:
    created = row["created_at"]
    updated = row["updated_at"]
    return {
        "proposal_id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "run_id": str(row["run_id"]),
        "section_key": str(row["section_key"]),
        "content_markdown": str(row["content_markdown"]),
        "ide_client": str(row["ide_client"]),
        "execution_identity": str(row["execution_identity"]),
        "status": str(row["status"]),
        "proposed_by": str(row["proposed_by"]) if row["proposed_by"] is not None else None,
        "created_at": created.isoformat() if isinstance(created, datetime) else str(created),
        "updated_at": updated.isoformat() if isinstance(updated, datetime) else str(updated),
    }


class SqlMcpProposalsRepository:
    """Async SQLAlchemy repository for `mcp_governed_proposals` in PostgreSQL 18."""

    def __init__(
        self,
        *,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        if session_maker is not None:
            self._session_maker: async_sessionmaker[AsyncSession] | None = session_maker
        elif engine is not None:
            self._session_maker = async_sessionmaker(engine, expire_on_commit=False)
        else:
            self._session_maker = None

    async def record_proposal(
        self,
        *,
        workspace_id: str,
        run_id: str,
        section_key: str,
        content_markdown: str,
        ide_client: str,
        execution_identity: str = "passthrough",
        proposed_by: str | None = None,
    ) -> dict[str, Any]:
        """Insert a governed MCP draft proposal into `mcp_governed_proposals`."""
        if self._session_maker is None:
            raise RuntimeError("SqlMcpProposalsRepository requires session_maker or engine.")
        proposal_id = new_uuid7_str()
        stmt = sa.text(
            f"""
            INSERT INTO mcp_governed_proposals (
                id, workspace_id, run_id, section_key, content_markdown,
                ide_client, execution_identity, status, proposed_by, created_at, updated_at
            ) VALUES (
                CAST(:id AS uuid), :workspace_id, :run_id, :section_key, :content_markdown,
                :ide_client, :execution_identity, 'PROPOSED', :proposed_by, NOW(), NOW()
            )
            RETURNING {_SELECT_COLS};
            """
        )
        async with self._session_maker() as session:
            row = (
                (
                    await session.execute(
                        stmt,
                        {
                            "id": proposal_id,
                            "workspace_id": workspace_id,
                            "run_id": run_id,
                            "section_key": section_key,
                            "content_markdown": content_markdown,
                            "ide_client": ide_client,
                            "execution_identity": execution_identity,
                            "proposed_by": proposed_by,
                        },
                    )
                )
                .mappings()
                .one()
            )
            await session.commit()
            return _row_to_proposal(row)

    async def list_proposals(
        self,
        *,
        workspace_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List persisted MCP draft proposals for a workspace (and optional run) from PG18."""
        if self._session_maker is None:
            return []
        clean_run = run_id.strip() if run_id else ""
        if clean_run:
            stmt = sa.text(
                f"SELECT {_SELECT_COLS} FROM mcp_governed_proposals "
                "WHERE workspace_id = :workspace_id AND run_id = :run_id "
                "ORDER BY created_at DESC, id DESC;"
            )
            params: dict[str, Any] = {"workspace_id": workspace_id, "run_id": clean_run}
        else:
            stmt = sa.text(
                f"SELECT {_SELECT_COLS} FROM mcp_governed_proposals "
                "WHERE workspace_id = :workspace_id "
                "ORDER BY created_at DESC, id DESC;"
            )
            params = {"workspace_id": workspace_id}

        async with self._session_maker() as session:
            rows = (await session.execute(stmt, params)).mappings().all()
            return [_row_to_proposal(r) for r in rows]
