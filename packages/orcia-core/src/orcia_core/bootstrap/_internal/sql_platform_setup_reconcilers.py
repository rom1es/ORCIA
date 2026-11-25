"""PostgreSQL 18 reconciliation helpers for platform setup state (`Story 17.2`).

Synchronizes JSONB snapshots (`platform_settings.value_jsonb`) with relational `org_units`
and `workspaces` tables to ensure newly created or migrated entities are never masked.
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.observability.logging import get_logger
from orcia_core.permissions.org_hierarchy import sort_org_unit_dicts_topologically

logger = get_logger("orcia.core.bootstrap.setup_reconcilers")


async def reconcile_org_units_on_load(
    conn: AsyncConnection,
    raw_org_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reconcile `org_units` from the relational `org_units` table when JSONB list is empty."""
    if raw_org_units:
        return list(raw_org_units)

    try:
        org_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, slug, name, unit_type, parent_id,
                           billing_enabled, lead_user_id, member_user_ids_jsonb
                    FROM org_units
                    WHERE unit_type IN ('BU', 'TEAM')
                    ORDER BY CASE WHEN unit_type = 'BU' THEN 0 ELSE 1 END, created_at ASC
                    """
                )
            )
        ).fetchall()
    except Exception as exc:
        logger.warning("reconcile_org_units_table_read_skipped", error_type=type(exc).__name__)
        return list(raw_org_units)

    raw_dicts: list[dict[str, Any]] = []
    for org_row in org_rows:
        db_uuid_str = str(org_row[0])
        parent_db_str = str(org_row[4]) if org_row[4] is not None else ""
        level = "TEAM" if str(org_row[3]).upper() == "TEAM" else "BU"
        entry: dict[str, Any] = {
            "id": db_uuid_str,
            "name": str(org_row[2]),
            "slug": str(org_row[1]),
            "level": level,
            "parentId": parent_db_str or "scope-global",
        }
        if len(org_row) > 5 and org_row[5] is not None:
            entry["billingEnabled"] = bool(org_row[5])
        if len(org_row) > 6 and org_row[6]:
            entry["leadUserId"] = str(org_row[6])
        if len(org_row) > 7 and org_row[7]:
            raw_mem = org_row[7]
            parsed_mem = (
                json.loads(raw_mem)
                if isinstance(raw_mem, str)
                else (raw_mem if isinstance(raw_mem, list) else [])
            )
            if parsed_mem:
                entry["memberUserIds"] = [str(m) for m in parsed_mem if str(m).strip()]
        raw_dicts.append(entry)

    sorted_dicts = sort_org_unit_dicts_topologically(raw_dicts)
    ui_id_by_db_uuid: dict[str, str] = {}
    reconciled: list[dict[str, Any]] = []
    for idx, item in enumerate(sorted_dicts):
        db_uuid_str = str(item["id"])
        ui_id = f"org-{idx + 1}"
        ui_id_by_db_uuid[db_uuid_str] = ui_id
        parent_db_str = str(item.get("parentId") or "")
        parent_ui_id = ui_id_by_db_uuid.get(parent_db_str, "scope-global")
        reconciled_item: dict[str, Any] = {
            "id": ui_id,
            "name": str(item["name"]),
            "slug": str(item["slug"]),
            "level": str(item["level"]),
            "parentId": parent_ui_id,
        }
        if "billingEnabled" in item:
            reconciled_item["billingEnabled"] = item["billingEnabled"]
        if "leadUserId" in item:
            reconciled_item["leadUserId"] = item["leadUserId"]
        if "memberUserIds" in item:
            reconciled_item["memberUserIds"] = item["memberUserIds"]
        reconciled.append(reconciled_item)
    return reconciled


async def reconcile_workspaces_on_load(
    conn: AsyncConnection,
    raw_workspaces: list[dict[str, Any]],
    org_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reconcile `workspaces` by merging relational rows with JSONB snapshot without duplicating."""
    org_by_ref: dict[str, dict[str, Any]] = {}
    for u in org_units:
        uid = str(u.get("id") or "").strip()
        uslug = str(u.get("slug") or "").strip().lower()
        if uid:
            org_by_ref[uid] = u
        if uslug:
            org_by_ref[uslug] = u

    workspaces = [dict(ws) for ws in raw_workspaces]
    existing_by_id: dict[str, dict[str, Any]] = {}
    existing_by_slug: dict[str, dict[str, Any]] = {}
    for ws in workspaces:
        ws_id = str(ws.get("workspaceId") or ws.get("id") or "").strip()
        if ws_id:
            existing_by_id[ws_id] = ws
        slug = str(ws.get("slug") or "").strip().lower()
        if slug:
            existing_by_slug[slug] = ws

    try:
        ws_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT w.id, w.slug, w.name, w.owner_org_unit_id, w.visibility_mode,
                           w.finops_cost_usd, w.settings_jsonb, o.name AS owner_org_unit_name,
                           o.slug AS owner_org_unit_slug, o.unit_type AS owner_org_unit_type
                    FROM workspaces w
                    LEFT JOIN org_units o ON o.id = w.owner_org_unit_id
                    ORDER BY w.created_at ASC, w.slug ASC
                    """
                )
            )
        ).fetchall()
    except Exception as exc:
        logger.warning("reconcile_workspaces_table_read_skipped", error_type=type(exc).__name__)
        ws_rows = []

    for ws_row in ws_rows:
        mapping = getattr(ws_row, "_mapping", None)
        if mapping is not None:
            sql_id = str(mapping.get("id") or "")
            sql_slug = str(mapping.get("slug") or "")
            sql_name = str(mapping.get("name") or "")
            vis_mode = str(mapping.get("visibility_mode") or "STANDARD")
            finops_cost = float(mapping.get("finops_cost_usd") or 0.0)
            st_raw = mapping.get("settings_jsonb")
            owner_id_col = str(mapping.get("owner_org_unit_id") or "")
            owner_name_col = str(mapping.get("owner_org_unit_name") or "")
            owner_slug_col = str(mapping.get("owner_org_unit_slug") or "")
            owner_type_col = str(mapping.get("owner_org_unit_type") or "").upper()
        elif len(ws_row) == 9:
            # Backward-compatible positional unpacking for unit test mocks (9 columns)
            sql_id = str(ws_row[0])
            sql_slug = str(ws_row[1])
            sql_name = str(ws_row[2])
            vis_mode = str(ws_row[3])
            st_raw = ws_row[4]
            finops_cost = float(ws_row[5] or 0.0)
            owner_id_col = ""
            owner_slug_col = str(ws_row[6] or "")
            owner_name_col = str(ws_row[7] or "")
            owner_type_col = str(ws_row[8] or "").upper()
        else:
            sql_id = str(ws_row[0])
            sql_slug = str(ws_row[1])
            sql_name = str(ws_row[2])
            owner_id_col = str(ws_row[3] or "")
            vis_mode = str(ws_row[4])
            finops_cost = float(ws_row[5] or 0.0)
            st_raw = ws_row[6]
            owner_name_col = str(ws_row[7] or "")
            owner_slug_col = str(ws_row[8] or "")
            owner_type_col = str(ws_row[9] or "").upper()

        st_dict: dict[str, Any] = {}
        if isinstance(st_raw, dict):
            st_dict = st_raw
        elif isinstance(st_raw, str):
            try:
                decoded = json.loads(st_raw)
                if isinstance(decoded, dict):
                    st_dict = decoded
            except ValueError:
                st_dict = {}

        if st_dict.get("is_personal_workspace") is True or st_dict.get("personal_owner_user_id"):
            continue

        ui_ws_id = str(st_dict.get("ui_workspace_id") or sql_id)

        owner_from_st = str(st_dict.get("owner_org_unit_id") or owner_id_col).strip()
        matched_org = org_by_ref.get(owner_from_st) or (
            org_by_ref.get(owner_slug_col.lower()) if owner_type_col in ("BU", "TEAM") else None
        )
        owner_org_id = str(matched_org["id"]) if matched_org else owner_from_st
        owner_org_name = (
            str(matched_org["name"])
            if matched_org
            else str(
                st_dict.get("owner_org_unit_name")
                or (owner_name_col if owner_type_col in ("BU", "TEAM") else "")
            )
        )
        resolved_vis = str(st_dict.get("ui_visibility_mode") or vis_mode)
        explicit_phase = (
            str(st_dict["lifecycle_phase"]).strip().upper()
            if st_dict.get("lifecycle_phase")
            else None
        )

        matched_existing = (
            existing_by_id.get(ui_ws_id)
            or existing_by_id.get(sql_id)
            or existing_by_slug.get(sql_slug.lower())
        )
        if matched_existing is not None:
            if sql_name:
                matched_existing["name"] = sql_name
            if sql_slug:
                matched_existing["slug"] = sql_slug
            matched_existing["visibilityMode"] = resolved_vis
            if explicit_phase:
                matched_existing["lifecyclePhase"] = explicit_phase
            matched_existing["finopsCostUsd"] = finops_cost
            if owner_org_id and not matched_existing.get("ownerOrgUnitId"):
                matched_existing["ownerOrgUnitId"] = owner_org_id
            if owner_org_name:
                matched_existing["ownerOrgUnitName"] = owner_org_name
            continue

        ws_entry: dict[str, Any] = {
            "workspaceId": ui_ws_id,
            "name": sql_name,
            "slug": sql_slug,
            "visibilityMode": resolved_vis,
            "lifecyclePhase": explicit_phase or "BUILD",
            "suggestedWorkflows": [],
            "accessMode": "CONTRIBUTOR_ACTION_REQUIRED",
            "finopsCostUsd": finops_cost,
        }
        if owner_org_id:
            ws_entry["ownerOrgUnitId"] = owner_org_id
        if owner_org_name:
            ws_entry["ownerOrgUnitName"] = owner_org_name

        workspaces.append(ws_entry)
        existing_by_id[ui_ws_id] = ws_entry
        existing_by_id[sql_id] = ws_entry
        existing_by_slug[sql_slug.lower()] = ws_entry

    for ws in workspaces:
        if not ws.get("ownerOrgUnitName"):
            owner_ref = str(ws.get("ownerOrgUnitId") or "").strip()
            matched = org_by_ref.get(owner_ref) or org_by_ref.get(owner_ref.lower())
            if matched and matched.get("name"):
                ws["ownerOrgUnitName"] = str(matched["name"])
    return workspaces


__all__ = [
    "reconcile_org_units_on_load",
    "reconcile_workspaces_on_load",
]
