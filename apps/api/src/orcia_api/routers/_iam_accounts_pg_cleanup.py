"""PostgreSQL 18 user cleanup helper for IAM account deletion (`Story 17.6`, `Story 27.7`)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.api.iam.pg_cleanup")


async def cleanup_or_disable_linked_user_on_postgres18(
    engine: AsyncEngine,
    *,
    principal_id: str | None = None,
    email: str | None = None,
) -> None:
    """Clean up or disable the linked `users` row upon IAM account deletion.

    Attempts hard delete first. If foreign keys (runs, audit ledger, etc.) prevent deletion,
    reassigns `primary_org_unit_id` to the ENTERPRISE root and marks `is_active = FALSE`.
    """
    targets = [x.strip().lower() for x in (principal_id, email) if x and x.strip()]
    if not targets:
        return

    where_clauses = ["LOWER(email) = :t0 OR id::text = :t0"]
    params: dict[str, str] = {"t0": targets[0]}
    if len(targets) > 1:
        where_clauses.append("LOWER(email) = :t1 OR id::text = :t1")
        params["t1"] = targets[1]

    async with engine.connect() as conn:
        res = await conn.execute(
            sa.text(
                f"""
                SELECT id, email, primary_org_unit_id
                FROM users
                WHERE {" OR ".join(where_clauses)}
                """
            ),
            params,
        )
        user_rows = res.fetchall()

    if not user_rows:
        return

    for u_row in user_rows:
        u_id = u_row[0]
        deleted = False
        try:
            async with engine.begin() as del_conn:
                await del_conn.execute(
                    sa.text("DELETE FROM user_transverse_groups WHERE user_id = :uid"),
                    {"uid": u_id},
                )
                await del_conn.execute(
                    sa.text("DELETE FROM users WHERE id = :uid"),
                    {"uid": u_id},
                )
                deleted = True
        except Exception as exc:
            logger.info(
                "iam_account_user_hard_delete_prevented_by_fk",
                user_id=str(u_id),
                error_type=type(exc).__name__,
            )
            deleted = False

        if not deleted:
            try:
                async with engine.begin() as upd_conn:
                    root_res = await upd_conn.execute(
                        sa.text(
                            """
                            SELECT id FROM org_units
                            WHERE unit_type = 'ENTERPRISE'
                            ORDER BY created_at ASC
                            LIMIT 1
                            """
                        )
                    )
                    root_id = root_res.scalar()
                    if root_id is not None:
                        await upd_conn.execute(
                            sa.text(
                                """
                                UPDATE users
                                SET primary_org_unit_id = :root_id,
                                    is_active = FALSE
                                WHERE id = :uid
                                """
                            ),
                            {"root_id": root_id, "uid": u_id},
                        )
                    else:
                        await upd_conn.execute(
                            sa.text("UPDATE users SET is_active = FALSE WHERE id = :uid"),
                            {"uid": u_id},
                        )
            except Exception as upd_exc:
                logger.warning(
                    "iam_account_user_deactivation_failed",
                    user_id=str(u_id),
                    error_type=type(upd_exc).__name__,
                )
