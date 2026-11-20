"""Request-scoped helper ensuring a PG18 user's isolated Personal Workspace exists."""

from __future__ import annotations

import inspect
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap import (
    build_personal_workspace_name,
    ensure_personal_workspace_on_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.personal_workspace_sync")


async def ensure_user_personal_workspace_from_pg(
    engine: AsyncEngine | None,
    user: UserIdentity,
    *,
    evaluator: MatrixPermissionEvaluator | None = None,
    locale: str = "fr",
) -> str | None:
    """Idempotently ensure `user` has an isolated Personal Workspace in PostgreSQL 18."""
    if engine is None:
        return None
    try:
        uid = UUID(str(user.id).strip())
    except (ValueError, TypeError):
        return None

    try:
        begin_ctx = engine.begin()
        if inspect.iscoroutine(begin_ctx):
            begin_ctx.close()
            return None
        async with begin_ctx as conn:
            users_reg = (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar()
            ws_reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.workspaces')"))
            ).scalar()
            if users_reg is None or ws_reg is None:
                return None
            user_row = (
                await conn.execute(
                    sa.text(
                        "SELECT id, display_name, primary_org_unit_id "
                        "FROM users WHERE id = :uid AND is_active = TRUE LIMIT 1"
                    ),
                    {"uid": uid},
                )
            ).first()
            if user_row is None:
                return None
            resolved_name = str(user_row[1] or user.display_name or user.email)
            ws_id = await ensure_personal_workspace_on_postgres18(
                conn,
                user_id=str(uid),
                display_name=resolved_name,
                locale=locale,
            )
            if evaluator is not None:
                owner_ou = str(user_row[2] or user.primary_org_unit_id)
                evaluator.upsert_workspace(
                    WorkspaceEntity(
                        id=ws_id,
                        slug=f"personal-{uid}",
                        name=build_personal_workspace_name(resolved_name, locale=locale),
                        owner_org_unit_id=owner_ou,
                        visibility_mode="CONFIDENTIAL_RESTRICTED",
                        personal_owner_user_id=str(uid),
                        ui_visibility_mode="PRIVATE_USER",
                    )
                )
                evaluator.upsert_membership(
                    WorkspaceMembershipEntity(
                        id=new_uuid7_str(),
                        workspace_id=ws_id,
                        role=user.platform_role,
                        access_mode="CONTRIBUTOR_ACTION_REQUIRED",
                        user_id=str(uid),
                    )
                )
            return ws_id
    except Exception as exc:
        logger.warning(
            "ensure_user_personal_workspace_from_pg_skipped",
            user_id=str(user.id),
            error_type=type(exc).__name__,
        )
        return None


async def ensure_email_personal_workspace_from_pg(
    engine: AsyncEngine | None,
    *,
    email: str,
    display_name: str,
    locale: str = "fr",
) -> str | None:
    """Ensure personal workspace when a `users` row exists for `email` in PG18."""
    if engine is None or not email.strip():
        return None
    try:
        begin_ctx = engine.begin()
        if inspect.iscoroutine(begin_ctx):
            begin_ctx.close()
            return None
        async with begin_ctx as conn:
            users_reg = (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar()
            ws_reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.workspaces')"))
            ).scalar()
            if users_reg is None or ws_reg is None:
                return None
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT id, display_name FROM users "
                        "WHERE LOWER(email) = LOWER(:email) AND is_active = TRUE LIMIT 1"
                    ),
                    {"email": email.strip().lower()},
                )
            ).first()
            if row is None or row[0] is None:
                return None
            return await ensure_personal_workspace_on_postgres18(
                conn,
                user_id=str(row[0]),
                display_name=str(row[1] or display_name),
                locale=locale,
            )
    except Exception as exc:
        logger.warning(
            "ensure_email_personal_workspace_from_pg_skipped",
            error_type=type(exc).__name__,
        )
        return None


__all__ = [
    "ensure_email_personal_workspace_from_pg",
    "ensure_user_personal_workspace_from_pg",
]
