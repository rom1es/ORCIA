"""PostgreSQL 18 `AsyncSession` adapter for `reflexive_execution_sessions` (`Story 16.2`).

Persists `ReflexiveSessionSnapshot` rows in `reflexive_execution_sessions` with 24h TTL (`F5`
survival across page reloads and API restarts). Falls back to an in-memory dictionary ONLY when
`session_maker` is `None` (pure unit tests without a database) or unreachable in non-strict mode.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.ports.reflexive_runtime_ports import ReflexiveSessionStorePort

logger = get_logger("orcia.agents.sql_reflexive_sessions")


def _parse_iso_utc(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SqlReflexiveSessionStore(ReflexiveSessionStorePort):
    """PostgreSQL 18 session store (`AsyncSession`) implementing `ReflexiveSessionStorePort`."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        *,
        strict_sql: bool = False,
    ) -> None:
        self._session_maker = session_maker
        self._strict_sql = strict_sql
        self._memory_fallback: dict[str, dict[str, Any]] = {}

    async def save_session_record(
        self,
        execution_id: str,
        *,
        workspace_id: str | None,
        actor_slug: str,
        orchestration_mode: str,
        effort_level: str,
        status: str,
        snapshot_payload: dict[str, Any],
        expires_at_utc: str,
    ) -> None:
        """Upsert `reflexive_execution_sessions` in PostgreSQL 18 when `session_maker` is wired."""
        self._memory_fallback[execution_id] = dict(snapshot_payload)
        if self._session_maker is None:
            return

        expires_dt = _parse_iso_utc(expires_at_utc)
        payload_json = json.dumps(snapshot_payload, ensure_ascii=False)
        stmt = sa.text(
            """
            INSERT INTO reflexive_execution_sessions (
                id,
                execution_id,
                workspace_id,
                actor_slug,
                orchestration_mode,
                effort_level,
                status,
                snapshot_jsonb,
                created_at,
                updated_at,
                expires_at
            )
            VALUES (
                CAST(:id AS UUID),
                :execution_id,
                :workspace_id,
                :actor_slug,
                :orchestration_mode,
                :effort_level,
                :status,
                CAST(:snapshot_jsonb AS JSONB),
                NOW(),
                NOW(),
                :expires_at
            )
            ON CONFLICT (execution_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                actor_slug = EXCLUDED.actor_slug,
                orchestration_mode = EXCLUDED.orchestration_mode,
                effort_level = EXCLUDED.effort_level,
                status = EXCLUDED.status,
                snapshot_jsonb = EXCLUDED.snapshot_jsonb,
                updated_at = NOW(),
                expires_at = EXCLUDED.expires_at
            """
        )
        try:
            async with self._session_maker() as session:
                await session.execute(
                    stmt,
                    {
                        "id": new_uuid7_str(),
                        "execution_id": execution_id,
                        "workspace_id": workspace_id,
                        "actor_slug": actor_slug,
                        "orchestration_mode": orchestration_mode,
                        "effort_level": effort_level,
                        "status": status,
                        "snapshot_jsonb": payload_json,
                        "expires_at": expires_dt,
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "reflexive_session_sql_save_degraded",
                execution_id=execution_id,
                error_type=type(exc).__name__,
            )
            if self._strict_sql:
                raise

    async def load_session_record(self, execution_id: str) -> dict[str, Any] | None:
        """Load `snapshot_jsonb` from PostgreSQL 18 first (`F5` truth), then fallback if absent."""
        if self._session_maker is not None:
            stmt = sa.text(
                """
                SELECT snapshot_jsonb
                FROM reflexive_execution_sessions
                WHERE execution_id = :execution_id
                """
            )
            try:
                async with self._session_maker() as session:
                    row = (await session.execute(stmt, {"execution_id": execution_id})).first()
                if row is not None:
                    raw_snap = row[0]
                    if isinstance(raw_snap, str):
                        parsed: dict[str, Any] = json.loads(raw_snap)
                        return parsed
                    if isinstance(raw_snap, dict):
                        return dict(raw_snap)
                if self._strict_sql:
                    return None
            except Exception as exc:
                logger.warning(
                    "reflexive_session_sql_load_degraded",
                    execution_id=execution_id,
                    error_type=type(exc).__name__,
                )
                if self._strict_sql:
                    raise

        cached = self._memory_fallback.get(execution_id)
        return dict(cached) if cached is not None else None
