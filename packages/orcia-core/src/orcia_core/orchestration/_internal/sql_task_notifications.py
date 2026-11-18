"""PostgreSQL 18 repository for `task_notifications` (`0021_story_5_1`, `REM-10`)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._internal._sql_task_notifications_parents import (
    coerce_uuid,
    dt_or_none,
    ensure_notification_parents,
    resolve_nullable_user,
    row_to_notification_entity,
)
from orcia_core.orchestration.presence_and_sse import (
    NotificationStatus,
    TaskNotificationEntity,
)


class SqlTaskNotificationRepository:
    """Async SQLAlchemy repository for `task_notifications` in PostgreSQL 18."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `task_notifications` exists in PostgreSQL 18."""
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.task_notifications')"))
            ).scalar()
            return reg is not None

    async def insert_or_get_notification(
        self, entity: TaskNotificationEntity
    ) -> TaskNotificationEntity:
        """Persist a `TaskNotificationEntity` idempotently (deduplicated by `source_event_id`)."""
        notif_uuid = coerce_uuid(entity.id)
        src_uuid = coerce_uuid(entity.source_event_id) if entity.source_event_id else None
        async with self._engine.begin() as conn:
            if src_uuid is not None:
                existing = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT * FROM task_notifications "
                                "WHERE source_event_id = CAST(:src AS uuid) LIMIT 1"
                            ),
                            {"src": str(src_uuid)},
                        )
                    )
                    .mappings()
                    .first()
                )
                if existing is not None:
                    return row_to_notification_entity(existing)

            ws_uuid, run_uuid, step_uuid, team_uuid, user_uuid = await ensure_notification_parents(
                conn,
                workspace_id=entity.workspace_id,
                run_id=entity.run_id,
                step_execution_id=entity.step_execution_id,
                step_key=entity.step_key,
                target_team_id=entity.target_team_id,
                target_user_id=entity.target_user_id,
            )
            row = (
                (
                    await conn.execute(
                        sa.text(
                            """
                            INSERT INTO task_notifications (
                                id, workspace_id, target_team_id, target_user_id,
                                run_id, step_execution_id, step_key,
                                notification_type, scope_kind, title, summary,
                                status, source_event_id
                            ) VALUES (
                                CAST(:id AS uuid), CAST(:ws AS uuid),
                                CAST(:team AS uuid), CAST(:user AS uuid),
                                CAST(:run AS uuid), CAST(:step_exec AS uuid), :step_key,
                                :ntype, :scope_kind, :title, :summary,
                                :status, CAST(:src AS uuid)
                            )
                            ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                            RETURNING *
                            """
                        ),
                        {
                            "id": str(notif_uuid),
                            "ws": str(ws_uuid),
                            "team": str(team_uuid) if team_uuid is not None else None,
                            "user": str(user_uuid) if user_uuid is not None else None,
                            "run": str(run_uuid),
                            "step_exec": str(step_uuid),
                            "step_key": entity.step_key[:128],
                            "ntype": entity.notification_type,
                            "scope_kind": entity.scope_kind,
                            "title": entity.title[:255],
                            "summary": entity.summary,
                            "status": entity.status,
                            "src": str(src_uuid) if src_uuid is not None else None,
                        },
                    )
                )
                .mappings()
                .one()
            )
            return row_to_notification_entity(row)

    async def count_all(self) -> int:
        """Return total row count in `task_notifications`."""
        async with self._engine.connect() as conn:
            return int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM task_notifications"))).scalar()
                or 0
            )

    async def list_notifications(
        self,
        *,
        workspace_id: str | None = None,
        scope_filter: str = "ALL",
        notification_type: str | None = None,
        viewer_user_id: str | None = None,
    ) -> tuple[TaskNotificationEntity, ...]:
        """List persisted notifications from PG18."""
        clauses: list[str] = ["1 = 1"]
        params: dict[str, Any] = {}
        if workspace_id:
            clauses.append("workspace_id = CAST(:ws AS uuid)")
            params["ws"] = str(coerce_uuid(workspace_id))
        if scope_filter == "TEAM":
            clauses.append("scope_kind = 'TEAM'")
        elif scope_filter == "PERSONAL":
            if viewer_user_id:
                clauses.append(
                    "(scope_kind = 'PERSONAL' OR claimed_by_user_id = CAST(:viewer AS uuid))"
                )
                params["viewer"] = str(coerce_uuid(viewer_user_id))
            else:
                clauses.append("scope_kind = 'PERSONAL'")
        if notification_type:
            clauses.append("notification_type = :ntype")
            params["ntype"] = notification_type
        where_sql = " AND ".join(clauses)
        sql = f"SELECT * FROM task_notifications WHERE {where_sql} ORDER BY created_at ASC"
        async with self._engine.connect() as conn:
            rows = (await conn.execute(sa.text(sql), params)).mappings().all()
            return tuple(row_to_notification_entity(r) for r in rows)

    async def count_unclaimed_action_required(self, workspace_id: str | None = None) -> int:
        """Return count of `OPEN`/`CLAIMED` notifications in PG18."""
        sql = "SELECT COUNT(*) FROM task_notifications WHERE status IN ('OPEN', 'CLAIMED')"
        params: dict[str, Any] = {}
        if workspace_id:
            sql += " AND workspace_id = CAST(:ws AS uuid)"
            params["ws"] = str(coerce_uuid(workspace_id))
        async with self._engine.connect() as conn:
            return int((await conn.execute(sa.text(sql), params)).scalar() or 0)

    async def get_notification(self, task_id: str) -> TaskNotificationEntity | None:
        """Fetch a single notification by primary key `id`."""
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT * FROM task_notifications WHERE id = CAST(:id AS uuid) LIMIT 1"
                        ),
                        {"id": str(coerce_uuid(task_id))},
                    )
                )
                .mappings()
                .first()
            )
            return row_to_notification_entity(row) if row is not None else None

    async def get_by_step_execution(self, step_execution_id: str) -> TaskNotificationEntity | None:
        """Fetch a notification by `step_execution_id`."""
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT * FROM task_notifications "
                            "WHERE step_execution_id = CAST(:step AS uuid) "
                            "ORDER BY created_at DESC LIMIT 1"
                        ),
                        {"step": str(coerce_uuid(step_execution_id))},
                    )
                )
                .mappings()
                .first()
            )
            return row_to_notification_entity(row) if row is not None else None

    async def update_claim_state(
        self,
        *,
        task_id: str,
        status: NotificationStatus,
        claimed_by_user_id: str | None,
        claimed_by_display_name: str | None,
        claimed_at: str | None,
        lock_expires_at: str | None,
    ) -> TaskNotificationEntity | None:
        """Persist `OPEN`/`CLAIMED` transition in `task_notifications` and `step_executions`."""
        task_uuid = coerce_uuid(task_id)
        async with self._engine.begin() as conn:
            resolved_claimer = await resolve_nullable_user(conn, claimed_by_user_id)
            row = (
                (
                    await conn.execute(
                        sa.text(
                            """
                            UPDATE task_notifications
                               SET status = :status,
                                   claimed_by_user_id = CAST(:uid AS uuid),
                                   claimed_by_display_name = :dname,
                                   claimed_at = :claimed_at,
                                   lock_expires_at = :expires_at,
                                   updated_at = NOW()
                             WHERE id = CAST(:id AS uuid)
                            RETURNING *
                            """
                        ),
                        {
                            "id": str(task_uuid),
                            "status": status,
                            "uid": str(resolved_claimer) if resolved_claimer is not None else None,
                            "dname": claimed_by_display_name,
                            "claimed_at": dt_or_none(claimed_at),
                            "expires_at": dt_or_none(lock_expires_at),
                        },
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            await conn.execute(
                sa.text(
                    "UPDATE step_executions SET claimed_by_user_id = CAST(:uid AS uuid), "
                    "claimed_at = :claimed_at WHERE id = CAST(:step_id AS uuid)"
                ),
                {
                    "step_id": str(row["step_execution_id"]),
                    "uid": str(resolved_claimer) if resolved_claimer is not None else None,
                    "claimed_at": dt_or_none(claimed_at),
                },
            )
            return row_to_notification_entity(row)


__all__ = ["SqlTaskNotificationRepository", "coerce_uuid"]
