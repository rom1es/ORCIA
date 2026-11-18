"""PostgreSQL 18 user-confined queries for Personal Profile Summary (`Story 20.4`).

Strictly scoped to the authenticated user (`actor_id` / `actor_email` / `initiated_by_user_id`):
zero cross-user leakage, zero N+1 queries.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import is_missing_table_error
from orcia_core.audit_finops._internal._sql_user_profile_orgs import (
    load_user_identity_and_orgs,
)
from orcia_core.audit_finops.user_profile_service import (
    PopularItemType,
    PopularUsageItem,
    UserProfileSummary,
    compute_activity_streaks,
    derive_user_handle,
    empty_user_profile_summary,
    rank_popular_usage_items,
)
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.audit_finops.user_profile")


def _coerce_utc_date(val: Any) -> date | None:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return date.fromisoformat(val.strip()[:10])
        except ValueError:
            return None
    return None


async def _load_user_token_stats_and_dates(
    conn: AsyncConnection, *, user_id: str, user_email: str
) -> tuple[int, int, list[date]]:
    total_tokens, peak_daily_tokens, active_dates = 0, 0, []
    params = {"user_id": user_id, "user_email": user_email}
    try:
        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT DATE(l.created_at AT TIME ZONE 'UTC') AS day_utc,
                           COALESCE(SUM(COALESCE(l.input_tokens, 0)
                                        + COALESCE(l.output_tokens, 0)), 0) AS day_tokens
                    FROM audit_ledger l
                    WHERE l.actor_id = :user_id
                       OR (:user_email <> ''
                           AND LOWER(COALESCE(l.actor_email, '')) = LOWER(:user_email))
                       OR (l.run_id IS NOT NULL AND EXISTS (
                           SELECT 1 FROM workflow_runs wr
                           WHERE wr.id = l.run_id AND wr.initiated_by_user_id::text = :user_id
                       ))
                    GROUP BY DATE(l.created_at AT TIME ZONE 'UTC')
                    ORDER BY day_utc ASC
                    """
                ),
                params,
            )
        ).fetchall()
        for row in rows:
            day_tokens = int(row[1] or 0)
            total_tokens += day_tokens
            peak_daily_tokens = max(peak_daily_tokens, day_tokens)
            if (d := _coerce_utc_date(row[0])) is not None:
                active_dates.append(d)
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_ledger_stats_failed", error_type=type(exc).__name__)
    try:
        wf_rows = (
            await conn.execute(
                sa.text(
                    "SELECT DISTINCT DATE(wr.created_at AT TIME ZONE 'UTC') "
                    "FROM workflow_runs wr WHERE wr.initiated_by_user_id::text = :user_id"
                ),
                {"user_id": user_id},
            )
        ).fetchall()
        for row in wf_rows:
            if (d := _coerce_utc_date(row[0])) is not None:
                active_dates.append(d)
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_workflow_dates_failed", error_type=type(exc).__name__)
    return total_tokens, peak_daily_tokens, active_dates


async def _load_user_popular_items(
    conn: AsyncConnection, *, user_id: str, user_email: str
) -> tuple[PopularUsageItem, ...]:
    items: list[PopularUsageItem] = []
    try:
        proc_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT wd.id::text AS item_key,
                           COALESCE(NULLIF(wd.steps_schema_jsonb->>'title', ''),
                                    NULLIF(split_part(wd.uri, '/', -1), ''), wd.uri) AS title,
                           COUNT(DISTINCT wr.id) AS usage_count
                    FROM workflow_runs wr
                    JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
                    WHERE wr.initiated_by_user_id::text = :user_id
                    GROUP BY wd.id, wd.steps_schema_jsonb, wd.uri
                    ORDER BY usage_count DESC, title ASC LIMIT 10
                    """
                ),
                {"user_id": user_id},
            )
        ).fetchall()
        for r in proc_rows:
            k = str(r[0])
            items.append(
                PopularUsageItem(
                    "PROCESS", k, str(r[1] or k), int(r[2] or 0), f"/processes/studio/{k}"
                )
            )
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_popular_processes_failed", error_type=type(exc).__name__)
    try:
        step_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT se.step_type, se.step_key, COUNT(*) AS usage_count
                    FROM step_executions se
                    JOIN workflow_runs wr ON wr.id = se.run_id
                    WHERE wr.initiated_by_user_id::text = :user_id
                      AND se.step_type IN ('AGENT', 'SKILL')
                    GROUP BY se.step_type, se.step_key
                    ORDER BY usage_count DESC, se.step_key ASC LIMIT 10
                    """
                ),
                {"user_id": user_id},
            )
        ).fetchall()
        for r in step_rows:
            rt = str(r[0] or "AGENT").upper()
            it: PopularItemType = cast(PopularItemType, rt) if rt in ("AGENT", "SKILL") else "AGENT"
            k = str(r[1] or "")
            items.append(
                PopularUsageItem(
                    it,
                    k,
                    k.replace("-", " ").replace("_", " ").strip() or k,
                    int(r[2] or 0),
                    "/agents",
                )
            )
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_popular_steps_failed", error_type=type(exc).__name__)
    try:
        tool_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT l.metadata_jsonb->>'tool_name' AS tool_name, COUNT(*) AS usage_count
                    FROM audit_ledger l
                    WHERE (l.actor_id = :user_id
                           OR (:user_email <> ''
                               AND LOWER(COALESCE(l.actor_email, '')) = LOWER(:user_email)))
                      AND NULLIF(l.metadata_jsonb->>'tool_name', '') IS NOT NULL
                    GROUP BY l.metadata_jsonb->>'tool_name'
                    ORDER BY usage_count DESC, tool_name ASC LIMIT 10
                    """
                ),
                {"user_id": user_id, "user_email": user_email},
            )
        ).fetchall()
        for r in tool_rows:
            if tn := str(r[0] or "").strip():
                items.append(PopularUsageItem("TOOL", tn, tn, int(r[1] or 0), "/agents"))
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_popular_tools_failed", error_type=type(exc).__name__)
    return rank_popular_usage_items(items, limit=5)


async def fetch_user_profile_summary_sql(
    engine: AsyncEngine | None,
    *,
    user_id: str,
    user_email: str,
    display_name: str,
    roles: Sequence[str],
    today: date | None = None,
) -> UserProfileSummary:
    """Load personal profile KPIs, org attachments & top-5 popular items from PG18."""
    roles_tuple = tuple(r for r in roles if r) or ("CONTRIBUTOR",)
    if engine is None:
        return empty_user_profile_summary(
            user_id=user_id, user_email=user_email, display_name=display_name, roles=roles_tuple
        )
    async with engine.connect() as conn:
        org_info = await load_user_identity_and_orgs(
            conn,
            user_id=user_id,
            user_email=user_email,
            display_name=display_name,
            roles=roles_tuple,
        )
        eff_name, eff_email, eff_roles, led_bus, onto_bus, led_teams, member_teams = org_info
        total_tokens, peak_daily_tokens, active_dates = await _load_user_token_stats_and_dates(
            conn, user_id=user_id, user_email=eff_email
        )
        popular_items = await _load_user_popular_items(conn, user_id=user_id, user_email=eff_email)
    longest_streak, current_streak = compute_activity_streaks(active_dates, today=today)
    return UserProfileSummary(
        user_id=user_id,
        display_name=eff_name,
        handle=derive_user_handle(eff_email, eff_name),
        email=eff_email,
        primary_role=eff_roles[0],
        roles=eff_roles,
        led_business_units=led_bus,
        ontology_business_units=onto_bus,
        led_teams=led_teams,
        member_teams=member_teams,
        total_tokens=total_tokens,
        peak_daily_tokens=peak_daily_tokens,
        longest_streak_days=longest_streak,
        current_streak_days=current_streak,
        popular_items=popular_items,
    )


__all__ = ["fetch_user_profile_summary_sql"]
