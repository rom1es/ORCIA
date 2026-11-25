"""SQL candidate loaders for Two-Speed Federated Search (`AD-8`, `Story 23.5`, `Story 29.2`)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.rag._two_speed_search_models import FederatedSearchCandidate, SearchFamilyKey

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


def map_catalog_family(resource_type: str, item_type: str) -> tuple[SearchFamilyKey, str, str]:
    """Map catalog item metadata into federated search family, route, and deep-link."""
    upper_item = item_type.upper()
    lower_res = resource_type.lower()
    if upper_item == "HELP_ARTICLE":
        return "HELP_ACTIONS", "/help", "/help"
    if lower_res in ("agent", "skill"):
        return "AGENTS_SKILLS", "/agents", "/agents"
    if lower_res == "datasource":
        return "SOURCES_SNIPPETS", "/spaces", "/spaces"
    return "PROCESSES_EXECUTIONS", "/processes", "/processes"


def catalog_allowed_roles(visibility_scope: str) -> tuple[str, ...]:
    """Return roles allowed to inspect a catalog item according to its visibility scope."""
    vis = visibility_scope.upper()
    if vis == "PENDING_APPROVAL":
        return ("PLATFORM_ADMIN", "BU_DIRECTOR", "BU_LEAD")
    if vis == "DRAFT":
        return _EDIT_ROLES
    return _STANDARD_ROLES


def _non_private_ws(alias: str) -> str:
    """Return SQL predicate ensuring a workspace is neither `PRIVATE_USER` nor personal-owned."""
    return (
        f"(COALESCE({alias}.settings_jsonb->>'ui_visibility_mode', {alias}.visibility_mode) "
        f"IS DISTINCT FROM 'PRIVATE_USER' "
        f"AND NULLIF({alias}.settings_jsonb->>'personal_owner_user_id', '') IS NULL)"
    )


def _private_ws_guard(alias: str) -> str:
    """Return SQL predicate enforcing single-owner isolation for `PRIVATE_USER` workspaces."""
    return (
        f"({_non_private_ws(alias)} "
        f"OR (:uid != '' AND {alias}.settings_jsonb->>'personal_owner_user_id' = :uid))"
    )


def _ws_member_exists(ws_col: str) -> str:
    """Return SQL predicate checking explicit user or invited org-unit membership."""
    return (
        f"EXISTS (SELECT 1 FROM workspace_memberships wm "
        f"WHERE wm.workspace_id = {ws_col} AND (:uid != '' AND (wm.user_id::text = :uid "
        f"OR (:org_id != '' AND wm.invited_org_unit_id::text = :org_id))))"
    )


async def load_catalog_candidates_pg18(
    conn: AsyncConnection,
    *,
    clean_uid: str,
    clean_role: str,
    clean_org: str,
    normalized_locale: str,
    is_admin: bool,
    has_memberships: bool,
    has_workspaces: bool,
    limit_per_table: int,
) -> list[FederatedSearchCandidate]:
    """Load RBAC- and CONFIDENTIAL_RESTRICTED/PRIVATE_USER-isolated `catalog_items` rows."""
    membership_filter = (
        f"OR {_ws_member_exists('ci.owner_workspace_id')}" if has_memberships else ""
    )
    ws_join = (
        "LEFT JOIN workspaces ci_ws ON ci_ws.id = ci.owner_workspace_id" if has_workspaces else ""
    )
    ws_private_filter = (
        f"AND (ci.owner_workspace_id IS NULL OR {_private_ws_guard('ci_ws')})"
        if has_workspaces
        else ""
    )
    owner_ws_check = (
        "OR (:uid != '' AND ci_ws.settings_jsonb->>'personal_owner_user_id' = :uid)"
        if has_workspaces
        else ""
    )
    std_ws_check = "ci_ws.visibility_mode = 'STANDARD'" if has_workspaces else "TRUE"
    std_admin_check = (
        "(:is_admin AND ci_ws.visibility_mode = 'STANDARD')" if has_workspaces else "FALSE"
    )
    ws_std_or_member = (
        f"(ci.owner_workspace_id IS NULL OR {std_ws_check} {owner_ws_check} {membership_filter})"
    )
    ws_restricted_or_member = (
        f"(ci.owner_workspace_id IS NULL OR {std_admin_check} {owner_ws_check} {membership_filter})"
    )
    sql_params = {
        "limit": limit_per_table,
        "uid": clean_uid,
        "org_id": clean_org,
        "role": clean_role,
        "is_admin": is_admin,
        "locale": normalized_locale,
    }
    rows = await conn.execute(
        sa.text(
            f"""
            SELECT
                ci.resource_id, ci.uri, ci.title, ci.description, ci.resource_type,
                COALESCE(ci.item_type, 'CATALOG_RESOURCE') AS item_type,
                COALESCE(ci.owner_workspace_id::text, 'GLOBAL') AS ws_id,
                ci.visibility_scope
            FROM catalog_items ci
            {ws_join}
            WHERE (
                (
                    COALESCE(ci.item_type, 'CATALOG_RESOURCE') = 'HELP_ARTICLE'
                    AND LOWER(SPLIT_PART(COALESCE(
                        NULLIF(ci.metadata_jsonb->>'lang', ''),
                        CASE
                            WHEN ci.uri LIKE '%/en' OR ci.uri LIKE '%/en/%'
                              OR ci.resource_id LIKE '%-en' THEN 'en'
                            ELSE 'fr'
                        END
                    ), '-', 1)) = :locale
                    AND {ws_std_or_member}
                )
                OR (
                    COALESCE(ci.item_type, 'CATALOG_RESOURCE') != 'HELP_ARTICLE'
                    AND (
                        (ci.visibility_scope IN ('PUBLISHED_ORG', 'SHARED_TEAM', 'SHARED_BU')
                         AND {ws_std_or_member})
                        OR (ci.visibility_scope = 'PENDING_APPROVAL'
                            AND :role IN ('PLATFORM_ADMIN', 'BU_DIRECTOR', 'BU_LEAD')
                            AND {ws_std_or_member})
                        OR (ci.visibility_scope IN ('SHARED_WORKSPACE', 'DRAFT')
                            AND {ws_restricted_or_member})
                    )
                )
            )
            {ws_private_filter}
            ORDER BY ci.title ASC
            LIMIT :limit
            """
        ),
        sql_params,
    )
    out: list[FederatedSearchCandidate] = []
    for row in rows.fetchall():
        family, screen_route, deep_link = map_catalog_family(str(row[4]), str(row[5]))
        out.append(
            FederatedSearchCandidate(
                item_id=f"pg-catalog:{row[0]}",
                family=family,
                title=str(row[2]),
                snippet=str(row[3] or "").strip() or str(row[1]),
                workspace_id=str(row[6] or "GLOBAL"),
                screen_route=screen_route,
                deep_link_uri=deep_link,
                allowed_roles=catalog_allowed_roles(str(row[7] or "PUBLISHED_ORG")),
            )
        )
    return out


async def load_workspace_candidates_pg18(
    conn: AsyncConnection,
    *,
    clean_uid: str,
    clean_role: str,
    clean_org: str,
    has_memberships: bool,
    limit_per_table: int,
) -> list[FederatedSearchCandidate]:
    """Load `workspaces` candidates enforcing `STANDARD` & strict `PRIVATE_USER` isolation."""
    ws_member_clause = _ws_member_exists("w.id") if has_memberships else "FALSE"
    ws_rows = await conn.execute(
        sa.text(
            f"""
            SELECT
                w.id::text, w.name, w.slug,
                COALESCE(w.settings_jsonb->>'ui_visibility_mode', w.visibility_mode) AS eff_vis
            FROM workspaces w
            WHERE (
                ({_non_private_ws("w")} AND (w.visibility_mode = 'STANDARD' OR {ws_member_clause}))
                OR (:uid != '' AND w.settings_jsonb->>'personal_owner_user_id' = :uid)
            )
            ORDER BY w.name ASC
            LIMIT :limit
            """
        ),
        {"limit": limit_per_table, "uid": clean_uid, "org_id": clean_org},
    )
    out: list[FederatedSearchCandidate] = []
    for row in ws_rows.fetchall():
        ws_id = str(row[0])
        eff_vis = str(row[3] or "STANDARD").upper()
        allowed: tuple[str, ...] = (
            (clean_role,)
            if eff_vis in ("PRIVATE_USER", "CONFIDENTIAL_RESTRICTED")
            else _STANDARD_ROLES
        )
        out.append(
            FederatedSearchCandidate(
                item_id=f"pg-workspace:{ws_id}",
                family="FOLDERS_DISCUSSIONS",
                title=str(row[1]),
                snippet=str(row[2]),
                workspace_id=ws_id,
                screen_route="/spaces",
                deep_link_uri=f"/workspaces/{ws_id}",
                allowed_roles=allowed,
                visibility_mode=eff_vis,
            )
        )
    return out


async def load_folder_candidates_pg18(
    conn: AsyncConnection,
    *,
    clean_uid: str,
    clean_role: str,
    clean_org: str,
    is_admin: bool,
    has_memberships: bool,
    has_folder_shares: bool,
    has_workspaces: bool,
    limit_per_table: int,
) -> list[FederatedSearchCandidate]:
    """Load `assistant_folders` candidates with strict relational & `PRIVATE_USER` isolation."""
    share_clause = (
        "OR (f.visibility_mode = 'SHARED_SELECTED' AND EXISTS ("
        "SELECT 1 FROM assistant_folder_shares s "
        "WHERE s.folder_id = f.folder_id AND s.grantee_user_id::text = :uid))"
        if has_folder_shares
        else ""
    )
    ws_open_member = f"OR {_ws_member_exists('w.id')}" if has_memberships else ""
    ws_open_clause = (
        f"OR (f.visibility_mode = 'WORKSPACE_OPEN' AND EXISTS ("
        f"SELECT 1 FROM workspaces w WHERE w.id = f.workspace_id "
        f"AND {_non_private_ws('w')} "
        f"AND (w.visibility_mode = 'STANDARD' {ws_open_member})))"
        if has_workspaces
        else "OR (f.visibility_mode = 'WORKSPACE_OPEN' AND :is_admin)"
    )
    ws_private_guard = (
        f"AND EXISTS (SELECT 1 FROM workspaces w "
        f"WHERE w.id = f.workspace_id AND {_private_ws_guard('w')})"
        if has_workspaces
        else ""
    )
    folder_rows = await conn.execute(
        sa.text(
            f"""
            SELECT f.folder_id::text, f.workspace_id::text, f.title, f.consolidated_summary
            FROM assistant_folders f
            WHERE (f.owner_user_id::text = :uid {share_clause} {ws_open_clause})
            {ws_private_guard}
            ORDER BY f.updated_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit_per_table, "uid": clean_uid, "org_id": clean_org, "is_admin": is_admin},
    )
    return [
        FederatedSearchCandidate(
            item_id=f"pg-folder:{row[0]}",
            family="FOLDERS_DISCUSSIONS",
            title=str(row[2]),
            snippet=str(row[3] or "")[:180],
            workspace_id=str(row[1]),
            screen_route="/assistant",
            deep_link_uri=f"/assistant?folder={row[0]}",
            allowed_roles=(clean_role,),
        )
        for row in folder_rows.fetchall()
    ]
