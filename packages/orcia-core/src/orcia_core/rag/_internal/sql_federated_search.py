"""PostgreSQL 18 RBAC & multi-tenant candidate loader for Two-Speed Federated Search (`⌘K`)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.rag._internal._sql_federated_search_queries import (
    _EDIT_ROLES,
    _STANDARD_ROLES,
    load_catalog_candidates_pg18,
    load_folder_candidates_pg18,
    load_workspace_candidates_pg18,
    map_catalog_family,
)
from orcia_core.rag.two_speed_search import FederatedSearchCandidate

_map_catalog_family = map_catalog_family


def normalize_search_locale(locale: str | None) -> str:
    """Normalize a locale tag such as `fr-FR` or `en-US` into `fr` / `en`."""
    clean = (locale or "fr").strip().lower().replace("_", "-")
    base = clean.split("-", 1)[0].strip()
    return "en" if base == "en" else "fr"


async def load_federated_search_candidates_pg18(
    conn: AsyncConnection,
    *,
    user_id: str = "",
    user_role: str = "CONTRIBUTOR",
    primary_org_unit_id: str | None = None,
    locale: str = "fr",
    limit_per_table: int = 50,
) -> tuple[FederatedSearchCandidate, ...]:
    """Load RBAC- and tenant-isolated entities from PG18 in bounded non-N+1 queries."""
    tables_res = await conn.execute(
        sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    existing_tables = {str(r[0]) for r in tables_res.fetchall()}
    clean_uid = user_id.strip()
    clean_role = user_role.strip() or "CONTRIBUTOR"
    clean_org = (primary_org_unit_id or "").strip()
    normalized_locale = normalize_search_locale(locale)
    is_admin = clean_role == "PLATFORM_ADMIN"
    has_memberships = "workspace_memberships" in existing_tables
    has_folder_shares = "assistant_folder_shares" in existing_tables
    has_workspaces = "workspaces" in existing_tables
    candidates: list[FederatedSearchCandidate] = []

    if "catalog_items" in existing_tables:
        candidates.extend(
            await load_catalog_candidates_pg18(
                conn,
                clean_uid=clean_uid,
                clean_role=clean_role,
                clean_org=clean_org,
                normalized_locale=normalized_locale,
                is_admin=is_admin,
                has_memberships=has_memberships,
                has_workspaces=has_workspaces,
                limit_per_table=limit_per_table,
            )
        )

    if "workflow_definitions_v2" in existing_tables:
        wf_rows = await conn.execute(
            sa.text(
                """
                SELECT DISTINCT ON (workflow_id)
                    workflow_id,
                    slug,
                    pack_id,
                    COALESCE(spec_jsonb->>'title', slug) AS title,
                    COALESCE(spec_jsonb->>'summary', spec_jsonb->>'objective', '') AS summary,
                    status
                FROM workflow_definitions_v2
                ORDER BY workflow_id, updated_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit_per_table},
        )
        for row in wf_rows.fetchall():
            wf_id = str(row[0])
            wf_status = str(row[5] or "published").lower()
            candidates.append(
                FederatedSearchCandidate(
                    item_id=f"pg-workflow:{wf_id}",
                    family="PROCESSES_EXECUTIONS",
                    title=str(row[3]),
                    snippet=str(row[4] or f"{row[2]} · {row[1]}"),
                    workspace_id="GLOBAL",
                    screen_route="/processes",
                    deep_link_uri=f"/processes/studio/{wf_id}",
                    allowed_roles=_EDIT_ROLES if wf_status == "draft" else _STANDARD_ROLES,
                )
            )

    if "declarative_pack_bundles" in existing_tables:
        pack_rows = await conn.execute(
            sa.text(
                """
                SELECT pack_id, slug, name, version
                FROM declarative_pack_bundles
                ORDER BY name ASC
                LIMIT :limit
                """
            ),
            {"limit": limit_per_table},
        )
        for row in pack_rows.fetchall():
            pack_id = str(row[0])
            candidates.append(
                FederatedSearchCandidate(
                    item_id=f"pg-pack:{pack_id}",
                    family="PROCESSES_EXECUTIONS",
                    title=str(row[2]),
                    snippet=f"{row[1]} v{row[3]}",
                    workspace_id="GLOBAL",
                    screen_route="/settings/packs",
                    deep_link_uri="/settings/packs",
                    allowed_roles=_STANDARD_ROLES,
                )
            )

    if has_workspaces:
        candidates.extend(
            await load_workspace_candidates_pg18(
                conn,
                clean_uid=clean_uid,
                clean_role=clean_role,
                clean_org=clean_org,
                has_memberships=has_memberships,
                limit_per_table=limit_per_table,
            )
        )

    if "assistant_folders" in existing_tables and clean_uid:
        candidates.extend(
            await load_folder_candidates_pg18(
                conn,
                clean_uid=clean_uid,
                clean_role=clean_role,
                clean_org=clean_org,
                is_admin=is_admin,
                has_memberships=has_memberships,
                has_folder_shares=has_folder_shares,
                has_workspaces=has_workspaces,
                limit_per_table=limit_per_table,
            )
        )

    return tuple(candidates)
