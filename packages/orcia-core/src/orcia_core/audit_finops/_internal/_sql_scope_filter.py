"""Shared SQL scope filtering and error classification helpers for FinOps (`BLOCKING-01`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops.finops_models import ScopeType


def safe_uuid(val: str | None) -> UUID | None:
    """Parse optional string UUID safely, returning `None` on invalid input."""
    if not val:
        return None
    try:
        return UUID(val)
    except (ValueError, TypeError, AttributeError):
        return None


def is_missing_table_error(exc: Exception) -> bool:
    """Return `True` ONLY when a table relation does not exist (never mask missing columns)."""
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
    if pgcode == "42703":  # undefined_column -> MUST surface immediately
        return False
    if pgcode == "42P01":  # undefined_table
        return True
    msg = str(exc).lower()
    if "column " in msg and " does not exist" in msg:
        return False
    return ("relation " in msg and " does not exist" in msg) or ("no such table" in msg)


def build_scoped_workspaces_cte(
    scope_type: ScopeType,
    uuid_val: UUID | None,
) -> tuple[str, dict[str, Any]]:
    """Build recursive `org_tree` and `scoped_workspaces` CTEs for `GLOBAL|BU|TEAM|WORKSPACE`."""
    params: dict[str, Any] = {
        "scope_type": scope_type,
        "scope_id": uuid_val,
    }
    cte = """
    WITH RECURSIVE org_tree AS (
        SELECT ou.id
        FROM org_units ou
        WHERE CAST(:scope_id AS uuid) IS NOT NULL
          AND ou.id = CAST(:scope_id AS uuid)
        UNION ALL
        SELECT child.id
        FROM org_units child
        JOIN org_tree parent ON child.parent_id = parent.id
    ),
    scoped_workspaces AS (
        SELECT w.id
        FROM workspaces w
        WHERE (:scope_type = 'GLOBAL' OR CAST(:scope_id AS uuid) IS NULL)
           OR (:scope_type = 'WORKSPACE' AND w.id = CAST(:scope_id AS uuid))
           OR (:scope_type IN ('BU', 'TEAM') AND w.owner_org_unit_id IN (
               SELECT id FROM org_tree
           ))
    )
    """
    return cte, params


def build_scoped_cte_with_acl(
    scope_type: ScopeType,
    scope_id: str | None,
    allowed_workspace_ids: tuple[str, ...] | None,
) -> tuple[UUID | None, str, dict[str, Any]]:
    """Build `scoped_workspaces` CTE combined with optional RBAC workspace UUID allowlist."""
    uuid_val = safe_uuid(scope_id)
    cte_sql, params = build_scoped_workspaces_cte(scope_type, uuid_val)
    if allowed_workspace_ids is not None:
        uuids = [u for raw in allowed_workspace_ids if (u := safe_uuid(raw)) is not None]
        if uuids:
            params["allowed_ws_ids"] = uuids
            ws_acl_clause = "AND w.id = ANY(:allowed_ws_ids)"
        else:
            ws_acl_clause = "AND FALSE"
        cte_sql = cte_sql.replace(
            "FROM workspaces w\n        WHERE",
            f"FROM workspaces w\n        WHERE TRUE {ws_acl_clause} AND (",
        ).rstrip()
        last_paren = cte_sql.rfind(")")
        cte_sql = cte_sql[:last_paren] + ")\n    )"
    return uuid_val, cte_sql, params


def build_time_interval_clause(time_window: str, col_name: str) -> str:
    """Build SQL time-window filter predicate for `7D | 30D | 90D`."""
    if time_window == "7D":
        return f"AND {col_name} >= NOW() - INTERVAL '7 days'"
    if time_window == "30D":
        return f"AND {col_name} >= NOW() - INTERVAL '30 days'"
    if time_window == "90D":
        return f"AND {col_name} >= NOW() - INTERVAL '90 days'"
    return ""


def build_cognitive_scope_clause(
    scope_type: ScopeType,
    uuid_val: UUID | None,
    ws_col: str,
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build hierarchical recursive org-unit + ACL workspace filter on `ws_col`."""
    clauses: list[str] = []
    params: dict[str, Any] = {}

    if uuid_val is not None and scope_type != "GLOBAL":
        params["scope_id"] = uuid_val
        if scope_type == "WORKSPACE":
            clauses.append(f"AND {ws_col} = :scope_id")
        else:
            clauses.append(
                f"""AND {ws_col} IN (
                    WITH RECURSIVE org_tree AS (
                        SELECT id FROM org_units WHERE id = :scope_id
                        UNION ALL
                        SELECT ou.id FROM org_units ou
                        JOIN org_tree ot ON ou.parent_id = ot.id
                    )
                    SELECT w.id FROM workspaces w
                    WHERE w.owner_org_unit_id IN (SELECT id FROM org_tree)
                )"""
            )

    if allowed_workspace_ids is not None:
        uuids = [u for raw in allowed_workspace_ids if (u := safe_uuid(raw)) is not None]
        if not uuids:
            clauses.append("AND FALSE")
        else:
            clauses.append(f"AND {ws_col} = ANY(:allowed_ws_ids)")
            params["allowed_ws_ids"] = uuids

    return " ".join(clauses), params


def build_ledger_scope_clause(
    scope_type: ScopeType,
    uuid_val: UUID | None,
    alias: str = "l",
) -> str:
    """Filter `audit_ledger` rows against `scoped_workspaces` or `org_tree`."""
    if scope_type == "GLOBAL" or uuid_val is None:
        return "TRUE"
    if scope_type == "WORKSPACE":
        return f"{alias}.workspace_id = CAST(:scope_id AS uuid)"
    return (
        f"({alias}.workspace_id IN (SELECT id FROM scoped_workspaces) "
        f"OR ({alias}.workspace_id IS NULL AND {alias}.org_unit_id IN (SELECT id FROM org_tree)))"
    )


def build_connector_scope_clause(
    scope_type: ScopeType,
    uuid_val: UUID | None,
) -> str:
    """Filter `finops_connector_quotas` rows against `GLOBAL` and hierarchical targets."""
    if scope_type == "GLOBAL" or uuid_val is None:
        return "TRUE"
    if scope_type == "WORKSPACE":
        return "(scope_type = 'GLOBAL' OR scope_id = CAST(:scope_id AS uuid))"
    return (
        "(scope_type = 'GLOBAL' "
        "OR scope_id IN (SELECT id FROM org_tree) "
        "OR scope_id IN (SELECT id FROM scoped_workspaces))"
    )


async def fetch_monthly_scope_spend_sql(
    engine: AsyncEngine,
    workspace_id: str | None,
) -> dict[str, Any] | None:
    """Fetch current-month aggregated expenditure across `GLOBAL -> BU -> TEAM -> WORKSPACE`."""
    if not isinstance(engine, AsyncEngine):
        return None
    ws_uuid = safe_uuid(workspace_id)
    stmt_global = sa.text(
        """
        SELECT COALESCE(SUM(cost_usd), 0.000000) AS monthly_usd
        FROM audit_ledger
        WHERE created_at >= date_trunc('month', NOW());
        """
    )
    stmt_ws = sa.text(
        """
        SELECT COALESCE(SUM(cost_usd), 0.000000) AS monthly_usd
        FROM audit_ledger
        WHERE workspace_id = :ws_id
          AND created_at >= date_trunc('month', NOW());
        """
    )
    stmt_ancestors = sa.text(
        """
        WITH RECURSIVE anc AS (
            SELECT ou.id, ou.parent_id
            FROM workspaces w
            JOIN org_units ou ON ou.id = w.owner_org_unit_id
            WHERE w.id = :ws_id
            UNION ALL
            SELECT p.id, p.parent_id
            FROM org_units p
            JOIN anc a ON p.id = a.parent_id
        )
        SELECT id FROM anc;
        """
    )
    stmt_ou_spend = sa.text(
        """
        WITH RECURSIVE desc_ous AS (
            SELECT id FROM org_units WHERE id = :ou_id
            UNION ALL
            SELECT c.id FROM org_units c
            JOIN desc_ous d ON c.parent_id = d.id
        )
        SELECT COALESCE(SUM(l.cost_usd), 0.000000) AS monthly_usd
        FROM audit_ledger l
        LEFT JOIN workspaces w ON w.id = l.workspace_id
        WHERE l.created_at >= date_trunc('month', NOW())
          AND (
              w.owner_org_unit_id IN (SELECT id FROM desc_ous)
              OR (l.workspace_id IS NULL AND l.org_unit_id IN (SELECT id FROM desc_ous))
          );
        """
    )
    async with engine.connect() as conn:
        global_usd = Decimal(str((await conn.execute(stmt_global)).scalar() or 0))
        ws_usd = (
            Decimal(str((await conn.execute(stmt_ws, {"ws_id": ws_uuid})).scalar() or 0))
            if ws_uuid is not None
            else Decimal("0.000000")
        )
        ancestors: list[str] = []
        ou_spend: dict[str, Decimal] = {}
        if ws_uuid is not None:
            anc_rows = (await conn.execute(stmt_ancestors, {"ws_id": ws_uuid})).all()
            for r in anc_rows:
                ou_uuid = r[0]
                ou_str = str(ou_uuid)
                ancestors.append(ou_str)
                val = Decimal(
                    str((await conn.execute(stmt_ou_spend, {"ou_id": ou_uuid})).scalar() or 0)
                )
                ou_spend[ou_str] = val
    return {
        "global_monthly_usd": global_usd,
        "workspace_monthly_usd": ws_usd,
        "ancestor_org_unit_ids": set(ancestors),
        "org_unit_monthly_usd": ou_spend,
    }


__all__ = [
    "build_cognitive_scope_clause",
    "build_connector_scope_clause",
    "build_ledger_scope_clause",
    "build_scoped_cte_with_acl",
    "build_scoped_workspaces_cte",
    "build_time_interval_clause",
    "fetch_monthly_scope_spend_sql",
    "is_missing_table_error",
    "safe_uuid",
]
