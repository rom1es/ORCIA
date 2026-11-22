"""PG18 SQLAlchemy repository for `assistant_turn_feedback` (`AD-25`, `R5`, `Story 26.4b`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._internal._sql_assistant_folders_queries import (
    coerce_folder_uuid,
    resolve_user_uuid,
    resolve_workspace_uuid,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

FeedbackRating = Literal["up", "down"]

_SQL_UPSERT_TURN_FEEDBACK = sa.text(
    """
    INSERT INTO assistant_turn_feedback (
        id, turn_id, workspace_id, user_id, rating, reason_code, comment
    ) VALUES (
        CAST(:id AS uuid), CAST(:turn_id AS uuid), CAST(:workspace_id AS uuid),
        CAST(:user_id AS uuid), :rating, :reason_code, :comment
    )
    ON CONFLICT (turn_id, user_id) DO UPDATE SET
        rating = EXCLUDED.rating,
        reason_code = EXCLUDED.reason_code,
        comment = EXCLUDED.comment,
        updated_at = NOW()
    RETURNING id, turn_id, workspace_id, user_id, rating, reason_code, comment
    """
)


@dataclass(frozen=True, slots=True)
class TurnFeedbackRecord:
    """Persisted row representation for `assistant_turn_feedback`."""

    feedback_id: str
    turn_id: str
    workspace_id: str
    user_id: str
    rating: FeedbackRating
    reason_code: str | None = None
    comment: str | None = None


class SqlAssistantFeedbackRepository:
    """Async PostgreSQL 18 repository for idempotent `(turn_id, user_id)` feedback upserts."""

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self._engine = engine

    def set_engine(self, engine: AsyncEngine | None) -> None:
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
        self._engine = engine

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `assistant_turn_feedback` exists in PostgreSQL 18."""
        if self._engine is None:
            return False
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.assistant_turn_feedback')"))
            ).scalar()
            return reg is not None

    async def upsert_feedback(
        self,
        *,
        turn_id: str,
        workspace_id: str,
        user: UserIdentity,
        rating: FeedbackRating,
        reason_code: str | None = None,
        comment: str | None = None,
    ) -> TurnFeedbackRecord:
        """Idempotently upsert feedback for `(turn_id, user_id)` in `assistant_turn_feedback`."""
        turn_uuid = coerce_folder_uuid(turn_id)
        if not await self.pg_tables_ready():
            return TurnFeedbackRecord(
                feedback_id=new_uuid7_str(),
                turn_id=str(turn_uuid),
                workspace_id=workspace_id,
                user_id=user.id,
                rating=rating,
                reason_code=reason_code,
                comment=comment,
            )
        assert self._engine is not None
        async with self._engine.begin() as conn:
            ws_uuid = await resolve_workspace_uuid(conn, workspace_id, required=True)
            assert ws_uuid is not None
            user_uuid = await resolve_user_uuid(conn, user_id=user.id, email=user.email)
            row = (
                (
                    await conn.execute(
                        _SQL_UPSERT_TURN_FEEDBACK,
                        {
                            "id": new_uuid7_str(),
                            "turn_id": str(turn_uuid),
                            "workspace_id": str(ws_uuid),
                            "user_id": str(user_uuid),
                            "rating": rating,
                            "reason_code": reason_code.strip()[:64] if reason_code else None,
                            "comment": comment.strip() if comment else None,
                        },
                    )
                )
                .mappings()
                .one()
            )
            return TurnFeedbackRecord(
                feedback_id=str(row["id"]),
                turn_id=str(row["turn_id"]),
                workspace_id=str(row["workspace_id"]),
                user_id=str(row["user_id"]),
                rating=cast(FeedbackRating, str(row["rating"])),
                reason_code=str(row["reason_code"]) if row["reason_code"] is not None else None,
                comment=str(row["comment"]) if row["comment"] is not None else None,
            )


__all__ = ["FeedbackRating", "SqlAssistantFeedbackRepository", "TurnFeedbackRecord"]
