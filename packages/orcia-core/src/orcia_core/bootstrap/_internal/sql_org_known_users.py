"""PostgreSQL 18 query & search helpers for known active platform users (`Story 17.2`).

Union of active human accounts from `iam_accounts` and `users` (deduplicated by lowercase
principal_id), with ILIKE search, deterministic sorting, and single-query `LIMIT + 1` pagination.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.bootstrap._internal.sql_iam_account_helpers import ensure_iam_accounts_schema
from orcia_core.permissions.org_user_validation import KnownOrgUser


def _escape_like_pattern(raw: str) -> str:
    """Escape `\\`, `%`, and `_` for SQL ILIKE with ESCAPE '\\\\'."""
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def load_known_org_users_from_postgres18(conn: AsyncConnection) -> list[KnownOrgUser]:
    """Load active known human accounts from `iam_accounts` and `users` (single query, zero N+1)."""
    await ensure_iam_accounts_schema(conn)
    query = sa.text(
        """
        SELECT principal_id, display_name, email FROM iam_accounts
        WHERE account_kind = 'HUMAN' AND status <> 'DISABLED'
        UNION ALL
        SELECT email AS principal_id, display_name, email FROM users WHERE is_active = TRUE
        """
    )
    rows = (await conn.execute(query)).fetchall()
    by_key: dict[str, KnownOrgUser] = {}
    for r in rows:
        p_id = str(r[0] or "").strip()
        if not p_id:
            continue
        d_name, mail = str(r[1] or "").strip() or p_id, str(r[2] or "").strip() if r[2] else None
        canon, alt = p_id.lower(), mail.lower() if mail else None
        prev = by_key.get(canon) or (by_key.get(alt) if alt else None)
        if prev is not None:
            m_display = prev.display_name if prev.display_name != prev.principal_id else d_name
            merged = KnownOrgUser(prev.principal_id, m_display, prev.email or mail)
            by_key[prev.principal_id.lower()] = merged
            if merged.email:
                by_key[merged.email.lower()] = merged
        else:
            created = KnownOrgUser(p_id, d_name, mail)
            by_key[canon] = created
            if alt:
                by_key[alt] = created
    unique = {id(u): u for u in by_key.values()}.values()
    return sorted(unique, key=lambda u: (u.display_name.lower(), u.principal_id.lower()))


async def search_known_org_users_from_postgres18(
    conn: AsyncConnection,
    *,
    q: str | None = None,
    limit: int = 10,
) -> tuple[list[KnownOrgUser], bool]:
    """Search known human accounts with ILIKE pattern and single-query `LIMIT + 1` pagination."""
    await ensure_iam_accounts_schema(conn)
    clean_q = (q or "").replace("\x00", "").strip()
    safe_limit = max(1, min(limit, 100))
    limit_plus_one = safe_limit + 1
    pattern: str | None = f"%{_escape_like_pattern(clean_q)}%" if clean_q else None
    filter_sql = (
        """
        AND (
            principal_id ILIKE :q_pattern ESCAPE '\\'
            OR display_name ILIKE :q_pattern ESCAPE '\\'
            OR (email IS NOT NULL AND email ILIKE :q_pattern ESCAPE '\\')
        )
        """
        if pattern is not None
        else ""
    )
    query = sa.text(
        f"""
        WITH raw_users AS (
            SELECT principal_id, display_name, email, 1 AS src_rank
            FROM iam_accounts WHERE account_kind = 'HUMAN' AND status <> 'DISABLED'
            UNION ALL
            SELECT email AS principal_id, display_name, email, 2 AS src_rank
            FROM users WHERE is_active = TRUE
        ),
        distinct_users AS (
            SELECT DISTINCT ON (LOWER(principal_id))
                principal_id,
                COALESCE(NULLIF(TRIM(display_name), ''), principal_id) AS display_name,
                NULLIF(TRIM(email), '') AS email
            FROM raw_users
            WHERE principal_id IS NOT NULL AND TRIM(principal_id) <> ''
            ORDER BY LOWER(principal_id), src_rank ASC
        )
        SELECT principal_id, display_name, email FROM distinct_users
        WHERE 1 = 1 {filter_sql}
        ORDER BY LOWER(display_name) ASC, LOWER(principal_id) ASC
        LIMIT :limit_plus_one
        """
    )
    params: dict[str, object] = {"limit_plus_one": limit_plus_one}
    if pattern is not None:
        params["q_pattern"] = pattern
    rows = (await conn.execute(query, params)).fetchall()
    has_more = len(rows) > safe_limit
    items = [
        KnownOrgUser(str(r[0]), str(r[1]), str(r[2]) if r[2] is not None else None)
        for r in rows[:safe_limit]
    ]
    return items, has_more


__all__ = [
    "load_known_org_users_from_postgres18",
    "search_known_org_users_from_postgres18",
]
