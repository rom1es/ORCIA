"""PostgreSQL 18 repository for `resource_leases` (`0021_story_5_1`, `DEC-CONC-01`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._internal.sql_task_notifications import coerce_uuid
from orcia_kernel.ports import ResourceLeaseRecord


def _iso_or_now(val: Any) -> str:
    if val is None:
        return datetime.now(UTC).isoformat()
    if isinstance(val, datetime):
        dt = val.astimezone(UTC) if val.tzinfo else val.replace(tzinfo=UTC)
        return dt.isoformat()
    return str(val)


def _dt_required(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class SqlResourceLeaseRepository:
    """Async SQLAlchemy repository for `resource_leases` (`0021_story_5_1`)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `resource_leases` exists in PostgreSQL 18."""
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.resource_leases')"))
            ).scalar()
            return reg is not None

    @staticmethod
    def _row_to_lease(row: RowMapping) -> ResourceLeaseRecord:
        return ResourceLeaseRecord(
            id=str(row["id"]),
            resource_uri=str(row["resource_uri"]),
            resource_class=str(row["resource_class"]),
            holder_run_id=str(row["holder_run_id"]),
            holder_root_run_id=str(row["holder_root_run_id"]),
            holder_parent_run_id=(
                str(row["holder_parent_run_id"])
                if row["holder_parent_run_id"] is not None
                else None
            ),
            holder_step_execution_id=str(row["holder_step_execution_id"]),
            fencing_token=int(row["fencing_token"]),
            acquired_at=_iso_or_now(row["acquired_at"]),
            expires_at=_iso_or_now(row["expires_at"]),
        )

    async def get_lease(self, resource_uri: str) -> ResourceLeaseRecord | None:
        """Fetch current lease row for `resource_uri` from PG18."""
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text("SELECT * FROM resource_leases WHERE resource_uri = :uri LIMIT 1"),
                        {"uri": resource_uri.strip()},
                    )
                )
                .mappings()
                .first()
            )
            return self._row_to_lease(row) if row is not None else None

    async def upsert_leases(self, records: tuple[ResourceLeaseRecord, ...]) -> None:
        """Atomically persist or refresh leased rows in `resource_leases`."""
        if not records:
            return
        async with self._engine.begin() as conn:
            for rec in records:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO resource_leases (
                            id, resource_uri, resource_class, holder_run_id,
                            holder_root_run_id, holder_parent_run_id,
                            holder_step_execution_id, fencing_token, acquired_at, expires_at
                        ) VALUES (
                            CAST(:id AS uuid), :uri, :rclass, CAST(:run_id AS uuid),
                            CAST(:root_id AS uuid), CAST(:parent_id AS uuid),
                            CAST(:step_id AS uuid), :token, :acq, :exp
                        )
                        ON CONFLICT (resource_uri) DO UPDATE SET
                            resource_class = EXCLUDED.resource_class,
                            holder_run_id = EXCLUDED.holder_run_id,
                            holder_root_run_id = EXCLUDED.holder_root_run_id,
                            holder_parent_run_id = EXCLUDED.holder_parent_run_id,
                            holder_step_execution_id = EXCLUDED.holder_step_execution_id,
                            fencing_token = EXCLUDED.fencing_token,
                            acquired_at = EXCLUDED.acquired_at,
                            expires_at = EXCLUDED.expires_at
                        """
                    ),
                    {
                        "id": str(coerce_uuid(rec.id)),
                        "uri": rec.resource_uri,
                        "rclass": rec.resource_class,
                        "run_id": str(coerce_uuid(rec.holder_run_id)),
                        "root_id": str(coerce_uuid(rec.holder_root_run_id)),
                        "parent_id": (
                            str(coerce_uuid(rec.holder_parent_run_id))
                            if rec.holder_parent_run_id
                            else None
                        ),
                        "step_id": str(coerce_uuid(rec.holder_step_execution_id)),
                        "token": rec.fencing_token,
                        "acq": _dt_required(rec.acquired_at),
                        "exp": _dt_required(rec.expires_at),
                    },
                )

    async def release_leases(self, *, holder_run_id: str, holder_step_execution_id: str) -> int:
        """Delete active leases held by `(holder_run_id, holder_step_execution_id)`."""
        async with self._engine.begin() as conn:
            res = await conn.execute(
                sa.text(
                    """
                    DELETE FROM resource_leases
                     WHERE holder_run_id = CAST(:run_id AS uuid)
                       AND holder_step_execution_id = CAST(:step_id AS uuid)
                    """
                ),
                {
                    "run_id": str(coerce_uuid(holder_run_id)),
                    "step_id": str(coerce_uuid(holder_step_execution_id)),
                },
            )
            return int(res.rowcount or 0)

    async def list_active_leases(self, *, now_utc: datetime) -> tuple[ResourceLeaseRecord, ...]:
        """List non-expired active leases ordered by `resource_uri`."""
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT * FROM resource_leases WHERE expires_at > :now "
                            "ORDER BY resource_uri ASC"
                        ),
                        {"now": now_utc},
                    )
                )
                .mappings()
                .all()
            )
            return tuple(self._row_to_lease(r) for r in rows)


__all__ = ["SqlResourceLeaseRepository"]
