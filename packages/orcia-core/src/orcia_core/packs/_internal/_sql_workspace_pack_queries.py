"""SQL resolution & effective slot binding queries for workspace packs (`Story 31.4`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs.errors import PackActivationInvalidError, PackBundleNotFoundError
from orcia_core.packs.models import PackSlotSpec, PackSlotTargetKind
from orcia_core.packs.slot_guard import EffectiveSlotBindingView
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError


def decode_declared_slots(raw: object) -> list[PackSlotSpec]:
    """Decode `declarative_pack_bundles.declared_slots_jsonb` into `PackSlotSpec` models."""
    items: list[Any] = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = parsed
        except ValueError:
            items = []
    return [PackSlotSpec.model_validate(item) for item in items if isinstance(item, dict)]


async def resolve_workspace_identity_conn(
    conn: AsyncConnection,
    workspace_id: str,
    *,
    instance: str | None = None,
) -> tuple[str, str | None]:
    """Resolve `(workspace_uuid, owner_org_unit_id)` or raise `ResourceNotFoundError` (`404`)."""
    clean = (workspace_id or "").strip().removeprefix("scope-ws-").strip()
    if not clean:
        raise ResourceNotFoundError(detail_override="Workspace ID is required.", instance=instance)
    row = (
        await conn.execute(
            sa.text(
                "SELECT id::text, owner_org_unit_id::text FROM workspaces "
                "WHERE id::text = :ws OR LOWER(slug) = LOWER(:ws) LIMIT 1"
            ),
            {"ws": clean},
        )
    ).first()
    if row is None:
        raise ResourceNotFoundError(
            detail_override=f"Workspace {workspace_id!r} not found.", instance=instance
        )
    return str(row[0]), (str(row[1]) if row[1] is not None else None)


async def load_ancestor_org_unit_ids_conn(
    conn: AsyncConnection,
    descendant_id: str | None,
) -> frozenset[str]:
    """Load `descendant_id` and all ancestor `org_units.id` strings in one CTE (`<= 8` hops)."""
    if not descendant_id or not descendant_id.strip():
        return frozenset()
    rows = (
        await conn.execute(
            sa.text(
                """
                WITH RECURSIVE anc AS (
                    SELECT id, parent_id, 0 AS depth FROM org_units WHERE id::text = :desc_id
                    UNION ALL
                    SELECT ou.id, ou.parent_id, anc.depth + 1
                    FROM org_units ou JOIN anc ON ou.id = anc.parent_id
                    WHERE anc.depth < 8
                )
                SELECT id::text FROM anc
                """
            ),
            {"desc_id": descendant_id.strip()},
        )
    ).scalars()
    return frozenset(str(row) for row in rows)


def is_bundle_visible_with_ancestors(
    *,
    scope_type: str,
    scope_id: str,
    ws_uuid: str,
    ancestor_org_unit_ids: frozenset[str],
) -> bool:
    """Pure visibility check using preloaded workspace ancestor org units (`P2-4`)."""
    upper = scope_type.strip().upper()
    if upper == "GLOBAL":
        return True
    if upper == "WORKSPACE":
        return scope_id.strip() == ws_uuid
    if upper in ("BU", "TEAM"):
        return scope_id.strip() in ancestor_org_unit_ids
    return False


async def is_bundle_visible_to_workspace_conn(
    conn: AsyncConnection,
    *,
    scope_type: str,
    scope_id: str,
    ws_uuid: str,
    ws_org_unit_id: str | None,
) -> bool:
    """Enforce `GLOBAL | BU | TEAM | WORKSPACE` bundle visibility for `ws_uuid`."""
    ancestors = await load_ancestor_org_unit_ids_conn(conn, ws_org_unit_id)
    return is_bundle_visible_with_ancestors(
        scope_type=scope_type,
        scope_id=scope_id,
        ws_uuid=ws_uuid,
        ancestor_org_unit_ids=ancestors,
    )


def _row_to_slot_binding(r: Any) -> EffectiveSlotBindingView:
    tkind = PackSlotTargetKind(str(r["target_kind"]))
    live_ds_id = str(r["live_ds_id"]) if r["live_ds_id"] is not None else None
    live_ec_id = str(r["live_ec_id"]) if r["live_ec_id"] is not None else None
    ec_enabled = bool(r["live_ec_enabled"]) if r["live_ec_enabled"] is not None else False
    eff_bound, target_uri, target_name = False, None, None
    if tkind == PackSlotTargetKind.WORKSPACE_DATASOURCE:
        eff_bound = bool(r["bound_datasource_id"] and live_ds_id)
        target_uri = str(r["live_ds_uri"]) if live_ds_id and r["live_ds_uri"] else None
        target_name = str(r["live_ds_alias"]) if live_ds_id and r["live_ds_alias"] else None
    elif tkind == PackSlotTargetKind.ENTERPRISE_CONNECTOR:
        eff_bound = bool(r["bound_connector_id"] and live_ec_id and ec_enabled)
        target_uri = str(r["live_ec_url"]) if live_ec_id and r["live_ec_url"] else None
        target_name = str(r["live_ec_name"]) if live_ec_id and r["live_ec_name"] else None
    elif tkind == PackSlotTargetKind.INTERNAL:
        eff_bound = True
        target_uri = f"orcia://internal/{r['slot_key']}"
        target_name = "ORCIA Internal"

    bound_at = r["bound_at"]
    return EffectiveSlotBindingView(
        id=str(r["id"]),
        workspace_id=str(r["workspace_id"]),
        pack_bundle_id=str(r["pack_bundle_id"]),
        pack_slug=str(r["pack_slug"]).strip().lower(),
        slot_key=str(r["slot_key"]),
        target_kind=tkind,
        target_id=str(r["target_id"]) if r["target_id"] is not None else None,
        bound_datasource_id=(
            str(r["bound_datasource_id"]) if r["bound_datasource_id"] is not None else None
        ),
        bound_connector_id=(
            str(r["bound_connector_id"]) if r["bound_connector_id"] is not None else None
        ),
        connector_scheme=str(r["connector_scheme"]) if r["connector_scheme"] is not None else None,
        bound_by=str(r["bound_by"]),
        bound_at_iso=bound_at.isoformat() if hasattr(bound_at, "isoformat") else str(bound_at),
        is_effective_bound=eff_bound,
        target_uri=target_uri,
        target_display_name=target_name,
        target_enabled=ec_enabled if tkind == PackSlotTargetKind.ENTERPRISE_CONNECTOR else True,
    )


async def load_effective_slot_bindings_conn(
    conn: AsyncConnection,
    ws_uuid: str,
) -> dict[str, dict[str, EffectiveSlotBindingView]]:
    """Load `workspace_pack_slot_bindings` joined with live targets (`ON DELETE SET NULL` aware)."""
    rows = (
        await conn.execute(
            sa.text(
                """
                SELECT wpsb.id::text, wpsb.workspace_id::text, wpsb.pack_bundle_id::text,
                       wpsb.pack_slug, wpsb.slot_key, wpsb.target_kind, wpsb.target_id,
                       wpsb.bound_datasource_id::text, wpsb.bound_connector_id::text,
                       wpsb.connector_scheme, wpsb.bound_by, wpsb.bound_at,
                       wd.id::text AS live_ds_id, wd.uri AS live_ds_uri,
                       wd.alias AS live_ds_alias,
                       ec.id::text AS live_ec_id, ec.base_url AS live_ec_url,
                       ec.name AS live_ec_name, ec.enabled AS live_ec_enabled
                FROM workspace_pack_slot_bindings wpsb
                LEFT JOIN workspace_datasources wd
                    ON wd.id = wpsb.bound_datasource_id AND wd.workspace_id = wpsb.workspace_id
                LEFT JOIN enterprise_connectors ec ON ec.id = wpsb.bound_connector_id
                WHERE wpsb.workspace_id = CAST(:ws AS uuid)
                ORDER BY wpsb.pack_slug ASC, wpsb.slot_key ASC
                """
            ),
            {"ws": ws_uuid},
        )
    ).mappings()
    by_pack: dict[str, dict[str, EffectiveSlotBindingView]] = {}
    for r in rows:
        view = _row_to_slot_binding(r)
        by_pack.setdefault(view.pack_slug, {})[view.slot_key] = view
    return by_pack


async def resolve_bundle_for_workspace_conn(
    conn: AsyncConnection,
    *,
    ws_uuid: str,
    ws_org_unit_id: str | None,
    pack_slug: str,
    bundle_id: str | None = None,
    version: str | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Resolve a visible `PUBLISHED` pack bundle for `ws_uuid` or raise `404`/`403`/`422`."""
    cols = (
        "id::text, pack_id, slug, name, version, bundle_kind, scope_type, "
        "scope_id, status, archive_sha256, cas_object_key, declared_slots_jsonb, "
        "author, description"
    )
    scope_rank = (
        "(CASE WHEN scope_type = 'WORKSPACE' AND scope_id = :ws THEN 0 "
        "WHEN scope_type = 'TEAM' THEN 1 WHEN scope_type = 'BU' THEN 2 ELSE 3 END)"
    )
    order_sql = (
        f"(CASE WHEN status = 'PUBLISHED' THEN 0 ELSE 1 END), {scope_rank}, "
        "version DESC, updated_at DESC"
    )
    where_sql = (
        "id::text = :bid OR pack_id = :bid"
        if bundle_id and bundle_id.strip()
        else (
            "LOWER(slug) = LOWER(:slug) "
            + ("AND version = :ver" if version and version.strip() else "")
        )
    )
    params: dict[str, Any] = {"ws": ws_uuid}
    if bundle_id and bundle_id.strip():
        params["bid"] = bundle_id.strip()
    else:
        params["slug"] = pack_slug.strip()
        if version and version.strip():
            params["ver"] = version.strip()
    rows = (
        (
            await conn.execute(
                sa.text(
                    f"SELECT {cols} FROM declarative_pack_bundles "
                    f"WHERE {where_sql} ORDER BY {order_sql}"
                ),
                params,
            )
        )
        .mappings()
        .all()
    )

    if not rows:
        raise PackBundleNotFoundError(
            detail_override=f"Pack bundle {bundle_id or pack_slug!r} not found.",
            instance=instance,
        )
    visible: list[dict[str, Any]] = []
    for row in rows:
        if await is_bundle_visible_to_workspace_conn(
            conn,
            scope_type=str(row["scope_type"]),
            scope_id=str(row["scope_id"]),
            ws_uuid=ws_uuid,
            ws_org_unit_id=ws_org_unit_id,
        ):
            visible.append(dict(row))
    if not visible:
        raise ScopeAccessDeniedError(
            detail_override=(
                f"Pack {bundle_id or pack_slug!r} is outside workspace {ws_uuid!r} visibility."
            ),
            instance=instance,
        )
    chosen = next((r for r in visible if str(r["status"]) == "PUBLISHED"), visible[0])
    if str(chosen["status"]) != "PUBLISHED":
        raise PackActivationInvalidError(
            detail_override=(
                f"Pack {chosen['slug']!r} ({chosen['status']}) must be PUBLISHED before binding."
            ),
            instance=instance,
        )
    return chosen


__all__ = [
    "decode_declared_slots",
    "is_bundle_visible_to_workspace_conn",
    "is_bundle_visible_with_ancestors",
    "load_ancestor_org_unit_ids_conn",
    "load_effective_slot_bindings_conn",
    "resolve_bundle_for_workspace_conn",
    "resolve_workspace_identity_conn",
]
