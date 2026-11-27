"""SQL views and active run-readiness loader for workspace packs (`Story 31.4`)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.packs._internal._sql_workspace_pack_queries import (
    decode_declared_slots,
    is_bundle_visible_with_ancestors,
    load_ancestor_org_unit_ids_conn,
    load_effective_slot_bindings_conn,
    resolve_workspace_identity_conn,
)
from orcia_core.packs.errors import PackActivationInvalidError
from orcia_core.packs.slot_guard import (
    PinnedPackManifestEntry,
    WorkspacePackView,
    evaluate_pack_slot_readiness,
)


async def list_workspace_packs_sql(
    engine: AsyncEngine,
    workspace_id: str,
    *,
    instance: str | None = None,
) -> list[WorkspacePackView]:
    """List workspace-visible packs with activation order, slot bindings & missing slots."""
    async with engine.connect() as conn:
        ws_uuid, ws_ou_id = await resolve_workspace_identity_conn(
            conn, workspace_id, instance=instance
        )
        bundle_rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, pack_id, slug, name, version, bundle_kind, scope_type, "
                        "scope_id, status, archive_sha256, cas_object_key, declared_slots_jsonb, "
                        "author, description FROM declarative_pack_bundles "
                        "WHERE status = 'PUBLISHED' ORDER BY slug ASC, version DESC"
                    )
                )
            )
            .mappings()
            .all()
        )
        act_rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT pack_bundle_id::text, pack_slug, priority_order, is_active, "
                        "activated_by, activated_at FROM workspace_pack_activations "
                        "WHERE workspace_id = CAST(:ws AS uuid)"
                    ),
                    {"ws": ws_uuid},
                )
            )
            .mappings()
            .all()
        )
        bindings_by_pack = await load_effective_slot_bindings_conn(conn, ws_uuid)
        ancestor_ou_ids = await load_ancestor_org_unit_ids_conn(conn, ws_ou_id)

        act_by_bundle = {str(a["pack_bundle_id"]): dict(a) for a in act_rows}
        views: list[WorkspacePackView] = []
        for r in bundle_rows:
            if not is_bundle_visible_with_ancestors(
                scope_type=str(r["scope_type"]),
                scope_id=str(r["scope_id"]),
                ws_uuid=ws_uuid,
                ancestor_org_unit_ids=ancestor_ou_ids,
            ):
                continue
            bid = str(r["id"])
            pslug = str(r["slug"]).strip().lower()
            declared = decode_declared_slots(r["declared_slots_jsonb"])
            pack_bindings = bindings_by_pack.get(pslug, {})
            _, missing = evaluate_pack_slot_readiness(
                declared, pack_bindings, pack_slug=pslug, raise_on_missing=False
            )
            act = act_by_bundle.get(bid)
            is_act = bool(act and act["is_active"])
            act_at = act["activated_at"] if act else None
            views.append(
                WorkspacePackView(
                    bundle_id=bid,
                    pack_id=str(r["pack_id"]),
                    slug=pslug,
                    name=str(r["name"]),
                    version=str(r["version"]),
                    bundle_kind=str(r["bundle_kind"]),
                    scope_type=str(r["scope_type"]),
                    scope_id=str(r["scope_id"]),
                    status=str(r["status"]),
                    archive_sha256=str(r["archive_sha256"]).strip(),
                    cas_object_key=str(r["cas_object_key"]) if r["cas_object_key"] else None,
                    description=str(r["description"] or ""),
                    author=str(r["author"]) if r["author"] else None,
                    is_active=is_act,
                    priority_order=(int(act["priority_order"]) if is_act and act else None),
                    activated_at_iso=(
                        act_at.isoformat()
                        if act_at is not None and hasattr(act_at, "isoformat")
                        else (str(act_at) if act_at else None)
                    ),
                    activated_by=str(act["activated_by"]) if act else None,
                    declared_slots=declared,
                    slot_bindings=list(pack_bindings.values()),
                    missing_slots=missing,
                    readiness_ok=(len(missing) == 0),
                )
            )
    views.sort(
        key=lambda v: (
            0 if v.is_active else 1,
            v.priority_order if v.priority_order is not None else 999999,
            v.slug,
            v.version,
        )
    )
    return views


async def _resolve_target_pack_bundle_conn(
    conn: AsyncConnection,
    workflow_pack_id: str | None,
) -> dict[str, object] | None:
    clean_pid = (workflow_pack_id or "").strip()
    if not clean_pid:
        return None
    row = (
        (
            await conn.execute(
                sa.text(
                    "SELECT id::text, pack_id, slug, declared_slots_jsonb "
                    "FROM declarative_pack_bundles "
                    "WHERE status = 'PUBLISHED' AND (pack_id = :pid OR LOWER(slug) = LOWER(:pid)) "
                    "ORDER BY version DESC, updated_at DESC LIMIT 1"
                ),
                {"pid": clean_pid},
            )
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


async def load_active_workspace_packs_for_run_conn(
    conn: AsyncConnection,
    *,
    workspace_id: str | None,
    workflow_pack_id: str | None = None,
    instance: str | None = None,
) -> list[PinnedPackManifestEntry]:
    """Validate required slots across active workspace packs & build pinned manifest entries."""
    target_bundle = await _resolve_target_pack_bundle_conn(conn, workflow_pack_id)
    clean = (workspace_id or "").strip().removeprefix("scope-ws-").strip()
    if not clean:
        if target_bundle is not None:
            tslug = str(target_bundle["slug"]).strip().lower()
            tdeclared = decode_declared_slots(target_bundle["declared_slots_jsonb"])
            evaluate_pack_slot_readiness(
                tdeclared, {}, pack_slug=tslug, raise_on_missing=True, instance=instance
            )
            raise PackActivationInvalidError(
                detail_override=(
                    f"Workspace context is required to run workflow for pack {tslug!r}."
                ),
                instance=instance,
            )
        return []
    ws_row = (
        await conn.execute(
            sa.text(
                "SELECT id::text FROM workspaces "
                "WHERE id::text = :ws OR LOWER(slug) = LOWER(:ws) LIMIT 1"
            ),
            {"ws": clean},
        )
    ).first()
    if ws_row is None:
        if target_bundle is not None:
            raise PackActivationInvalidError(
                detail_override=f"Workspace {workspace_id!r} not found for pack workflow.",
                instance=instance,
            )
        return []
    ws_uuid = str(ws_row[0])
    rows = (
        (
            await conn.execute(
                sa.text(
                    """
                SELECT wpa.pack_bundle_id::text, dpb.pack_id, dpb.slug, dpb.version,
                       dpb.archive_sha256, dpb.declared_slots_jsonb, wpa.priority_order
                FROM workspace_pack_activations wpa
                JOIN declarative_pack_bundles dpb ON dpb.id = wpa.pack_bundle_id
                WHERE wpa.workspace_id = CAST(:ws AS uuid) AND wpa.is_active = TRUE
                ORDER BY wpa.priority_order ASC, wpa.pack_slug ASC
                """
                ),
                {"ws": ws_uuid},
            )
        )
        .mappings()
        .all()
    )
    bindings_by_pack = await load_effective_slot_bindings_conn(conn, ws_uuid)
    if target_bundle is not None:
        t_pid = str(target_bundle["pack_id"]).lower()
        t_slug = str(target_bundle["slug"]).strip().lower()
        is_active_target = any(
            str(r["pack_id"]).lower() == t_pid or str(r["slug"]).strip().lower() == t_slug
            for r in rows
        )
        if not is_active_target:
            tdeclared = decode_declared_slots(target_bundle["declared_slots_jsonb"])
            evaluate_pack_slot_readiness(
                tdeclared,
                bindings_by_pack.get(t_slug, {}),
                pack_slug=t_slug,
                raise_on_missing=True,
                instance=instance,
            )
            raise PackActivationInvalidError(
                detail_override=(
                    f"Pack {t_slug!r} must be activated in workspace {ws_uuid!r} before execution."
                ),
                instance=instance,
            )
    if not rows:
        return []
    norm_target = (workflow_pack_id or "").strip().lower()
    ordered_rows = sorted(
        rows,
        key=lambda r: (
            0
            if norm_target and norm_target in (str(r["pack_id"]).lower(), str(r["slug"]).lower())
            else 1,
            int(r["priority_order"] or 9999),
        ),
    )
    pinned: list[PinnedPackManifestEntry] = []
    for r in ordered_rows:
        pslug = str(r["slug"]).strip().lower()
        declared = decode_declared_slots(r["declared_slots_jsonb"])
        resolved_slots, _ = evaluate_pack_slot_readiness(
            declared,
            bindings_by_pack.get(pslug, {}),
            pack_slug=pslug,
            raise_on_missing=True,
            instance=instance,
        )
        pinned.append(
            PinnedPackManifestEntry(
                pack_bundle_id=str(r["pack_bundle_id"]),
                pack_slug=pslug,
                version=str(r["version"]),
                archive_sha256=str(r["archive_sha256"]).strip(),
                priority_order=int(r["priority_order"]),
                resolved_pack_slots=resolved_slots,
            )
        )
    pinned.sort(key=lambda entry: (entry.priority_order, entry.pack_slug))
    return pinned


__all__ = ["list_workspace_packs_sql", "load_active_workspace_packs_for_run_conn"]
