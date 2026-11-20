"""PostgreSQL 18 RBAC & multi-tenant candidate loader for Two-Speed Federated Search (`⌘K`)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.rag.two_speed_search import FederatedSearchCandidate, SearchFamilyKey

_STANDARD_ROLES: tuple[str, ...] = (
    "PLATFORM_ADMIN",
    "BU_DIRECTOR",
    "BU_LEAD",
    "TEAM_LEAD",
    "CONTRIBUTOR",
    "GATE_REVIEWER",
    "ONTOLOGY_STEWARD_L3",
    "OBSERVER",
)
_EDIT_ROLES: tuple[str, ...] = (
    "PLATFORM_ADMIN",
    "BU_DIRECTOR",
    "BU_LEAD",
    "TEAM_LEAD",
    "CONTRIBUTOR",
)
_ADMIN_ONLY_ROLES: tuple[str, ...] = ("PLATFORM_ADMIN",)


def _map_catalog_family(resource_type: str, item_type: str) -> tuple[SearchFamilyKey, str, str]:
    upper_item = item_type.upper()
    lower_res = resource_type.lower()
    if upper_item == "HELP_ARTICLE":
        return "HELP_ACTIONS", "/help", "/help"
    if lower_res in ("agent", "skill"):
        return "AGENTS_SKILLS", "/agents", "/agents"
    if lower_res == "datasource":
        return "SOURCES_SNIPPETS", "/spaces", "/spaces"
    return "PROCESSES_EXECUTIONS", "/processes", "/processes"


def _catalog_allowed_roles(visibility_scope: str) -> tuple[str, ...]:
    vis = visibility_scope.upper()
    if vis == "PENDING_APPROVAL":
        return ("PLATFORM_ADMIN", "BU_DIRECTOR", "BU_LEAD")
    if vis == "DRAFT":
        return _EDIT_ROLES
    return _STANDARD_ROLES


async def load_federated_search_candidates_pg18(
    conn: AsyncConnection,
    *,
    user_id: str = "",
    user_role: str = "CONTRIBUTOR",
    primary_org_unit_id: str | None = None,
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
    is_admin = clean_role == "PLATFORM_ADMIN"
    has_memberships = "workspace_memberships" in existing_tables
    has_folder_shares = "assistant_folder_shares" in existing_tables
    candidates: list[FederatedSearchCandidate] = []

    if "catalog_items" in existing_tables:
        membership_filter = (
            "OR EXISTS (SELECT 1 FROM workspace_memberships wm "
            "WHERE wm.workspace_id = ci.owner_workspace_id "
            "AND (:uid != '' AND (wm.user_id::text = :uid "
            "OR (:org_id != '' AND wm.invited_org_unit_id::text = :org_id))))"
            if has_memberships
            else ""
        )
        cat_rows = await conn.execute(
            sa.text(
                f"""
                SELECT
                    ci.resource_id,
                    ci.uri,
                    ci.title,
                    ci.description,
                    ci.resource_type,
                    COALESCE(ci.item_type, 'CATALOG_RESOURCE') AS item_type,
                    COALESCE(ci.owner_workspace_id::text, 'GLOBAL') AS ws_id,
                    ci.visibility_scope
                FROM catalog_items ci
                WHERE (
                    COALESCE(ci.item_type, 'CATALOG_RESOURCE') = 'HELP_ARTICLE'
                    OR ci.visibility_scope IN ('PUBLISHED_ORG', 'SHARED_TEAM', 'SHARED_BU')
                    OR (
                        ci.visibility_scope = 'PENDING_APPROVAL'
                        AND :role IN ('PLATFORM_ADMIN', 'BU_DIRECTOR', 'BU_LEAD')
                    )
                    OR (
                        ci.visibility_scope IN ('SHARED_WORKSPACE', 'DRAFT')
                        AND (
                            :is_admin
                            OR ci.owner_workspace_id IS NULL
                            {membership_filter}
                        )
                    )
                )
                ORDER BY ci.title ASC
                LIMIT :limit
                """
            ),
            {
                "limit": limit_per_table,
                "uid": clean_uid,
                "org_id": clean_org,
                "role": clean_role,
                "is_admin": is_admin,
            },
        )
        for row in cat_rows.fetchall():
            resource_id = str(row[0])
            uri = str(row[1])
            title = str(row[2])
            description = str(row[3] or "").strip()
            vis_scope = str(row[7] or "PUBLISHED_ORG")
            family, screen_route, deep_link = _map_catalog_family(str(row[4]), str(row[5]))
            candidates.append(
                FederatedSearchCandidate(
                    item_id=f"pg-catalog:{resource_id}",
                    family=family,
                    title=title,
                    snippet=description or uri,
                    workspace_id=str(row[6] or "GLOBAL"),
                    screen_route=screen_route,
                    deep_link_uri=deep_link,
                    allowed_roles=_catalog_allowed_roles(vis_scope),
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

    if "workspaces" in existing_tables:
        ws_member_clause = (
            "(:uid != '' AND EXISTS (SELECT 1 FROM workspace_memberships wm "
            "WHERE wm.workspace_id = w.id AND (wm.user_id::text = :uid "
            "OR (:org_id != '' AND wm.invited_org_unit_id::text = :org_id))))"
            if has_memberships
            else "FALSE"
        )
        ws_rows = await conn.execute(
            sa.text(
                f"""
                SELECT
                    w.id::text,
                    w.name,
                    w.slug,
                    COALESCE(
                        w.settings_jsonb->>'ui_visibility_mode', w.visibility_mode
                    ) AS eff_vis
                FROM workspaces w
                WHERE (
                    COALESCE(
                        w.settings_jsonb->>'ui_visibility_mode', w.visibility_mode
                    ) = 'STANDARD'
                    OR {ws_member_clause}
                    OR (
                        :is_admin
                        AND COALESCE(
                            w.settings_jsonb->>'ui_visibility_mode', w.visibility_mode
                        ) != 'PRIVATE_USER'
                    )
                )
                ORDER BY w.name ASC
                LIMIT :limit
                """
            ),
            {
                "limit": limit_per_table,
                "uid": clean_uid,
                "org_id": clean_org,
                "is_admin": is_admin,
            },
        )
        for row in ws_rows.fetchall():
            ws_id = str(row[0])
            eff_vis = str(row[3] or "STANDARD").upper()
            if eff_vis == "PRIVATE_USER":
                allowed: tuple[str, ...] = (clean_role,)
            elif eff_vis == "CONFIDENTIAL_RESTRICTED":
                allowed = (clean_role, *_ADMIN_ONLY_ROLES)
            else:
                allowed = _STANDARD_ROLES
            candidates.append(
                FederatedSearchCandidate(
                    item_id=f"pg-workspace:{ws_id}",
                    family="FOLDERS_DISCUSSIONS",
                    title=str(row[1]),
                    snippet=str(row[2]),
                    workspace_id=ws_id,
                    screen_route="/spaces",
                    deep_link_uri=f"/workspaces/{ws_id}",
                    allowed_roles=allowed,
                )
            )

    if "assistant_folders" in existing_tables and clean_uid:
        share_clause = (
            "OR (f.visibility_mode = 'SHARED_SELECTED' AND EXISTS ("
            "SELECT 1 FROM assistant_folder_shares s "
            "WHERE s.folder_id = f.folder_id AND s.grantee_user_id::text = :uid))"
            if has_folder_shares
            else ""
        )
        ws_open_member = (
            "OR EXISTS (SELECT 1 FROM workspace_memberships wm "
            "WHERE wm.workspace_id = w.id AND (wm.user_id::text = :uid "
            "OR (:org_id != '' AND wm.invited_org_unit_id::text = :org_id)))"
            if has_memberships
            else ""
        )
        ws_open_clause = (
            f"OR (f.visibility_mode = 'WORKSPACE_OPEN' AND EXISTS ("
            f"SELECT 1 FROM workspaces w WHERE w.id = f.workspace_id "
            f"AND COALESCE(w.settings_jsonb->>'ui_visibility_mode', "
            f"w.visibility_mode) != 'PRIVATE_USER' "
            f"AND (COALESCE(w.settings_jsonb->>'ui_visibility_mode', "
            f"w.visibility_mode) = 'STANDARD' "
            f"OR :is_admin {ws_open_member})))"
            if "workspaces" in existing_tables
            else "OR (f.visibility_mode = 'WORKSPACE_OPEN' AND :is_admin)"
        )
        folder_rows = await conn.execute(
            sa.text(
                f"""
                SELECT f.folder_id::text, f.workspace_id::text, f.title, f.consolidated_summary
                FROM assistant_folders f
                WHERE (
                    f.owner_user_id::text = :uid
                    {share_clause}
                    {ws_open_clause}
                )
                ORDER BY f.updated_at DESC
                LIMIT :limit
                """
            ),
            {
                "limit": limit_per_table,
                "uid": clean_uid,
                "org_id": clean_org,
                "is_admin": is_admin,
            },
        )
        for row in folder_rows.fetchall():
            folder_id = str(row[0])
            candidates.append(
                FederatedSearchCandidate(
                    item_id=f"pg-folder:{folder_id}",
                    family="FOLDERS_DISCUSSIONS",
                    title=str(row[2]),
                    snippet=str(row[3] or "")[:180],
                    workspace_id=str(row[1]),
                    screen_route="/assistant",
                    deep_link_uri=f"/assistant?folder={folder_id}",
                    allowed_roles=(clean_role,),
                )
            )

    return tuple(candidates)
