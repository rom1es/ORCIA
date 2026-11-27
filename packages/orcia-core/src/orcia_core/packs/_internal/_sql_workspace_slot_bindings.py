"""Transactional PG18 slot binding mutations (`Story 31.4`, `<= 300 L`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import (
    decode_declared_slots,
    load_effective_slot_bindings_conn,
    resolve_bundle_for_workspace_conn,
    resolve_workspace_identity_conn,
)
from orcia_core.packs.errors import PackSlotBindingInvalidError
from orcia_core.packs.models import PackSlotSpec, PackSlotTargetKind
from orcia_core.packs.slot_guard import EffectiveSlotBindingView, SlotBindingInput

_UPSERT_SLOT_SQL = """
INSERT INTO workspace_pack_slot_bindings (
    id, workspace_id, pack_bundle_id, pack_slug, slot_key, target_kind, target_id,
    bound_datasource_id, bound_connector_id, connector_scheme, bound_by, bound_at
) VALUES (
    CAST(:id AS uuid), CAST(:ws AS uuid), CAST(:bid AS uuid), :pslug, :skey, :tkind, :tid,
    CAST(:ds_id AS uuid), CAST(:ec_id AS uuid), :scheme, :actor, NOW()
) ON CONFLICT (workspace_id, pack_slug, slot_key) DO UPDATE SET
    pack_bundle_id = EXCLUDED.pack_bundle_id, target_kind = EXCLUDED.target_kind,
    target_id = EXCLUDED.target_id, bound_datasource_id = EXCLUDED.bound_datasource_id,
    bound_connector_id = EXCLUDED.bound_connector_id,
    connector_scheme = EXCLUDED.connector_scheme, bound_by = EXCLUDED.bound_by, bound_at = NOW()
"""


def _parse_uuid_or_raise(raw_id: str | None, *, label: str, instance: str | None) -> str:
    clean = (raw_id or "").strip()
    try:
        return str(UUID(clean))
    except (ValueError, TypeError) as exc:
        raise PackSlotBindingInvalidError(
            detail_override=f"Invalid UUID for {label}: {raw_id!r}.",
            instance=instance,
        ) from exc


async def _validate_and_resolve_scheme(
    conn: AsyncConnection,
    candidate: str | None,
    *,
    instance: str | None,
) -> str | None:
    clean = (candidate or "").strip().lower()
    if not clean or clean in ("*", "any"):
        return None
    found = (
        await conn.execute(
            sa.text("SELECT scheme FROM connector_schemes WHERE scheme = :s LIMIT 1"),
            {"s": clean},
        )
    ).scalar()
    if found is None:
        raise PackSlotBindingInvalidError(
            detail_override=f"Unknown connector scheme {clean!r}.",
            instance=instance,
        )
    return str(found)


def _is_connector_kind_compatible(connector_kind: str, target_scheme: str) -> bool:
    kind = connector_kind.strip().lower()
    scheme = target_scheme.strip().lower()
    if not scheme or scheme in ("*", "any"):
        return True
    if kind == scheme:
        return True
    if kind == "gitlab" and scheme == "git":
        return True
    return kind.startswith(f"{scheme}_") or scheme.startswith(f"{kind}_")


async def _resolve_slot_target(
    conn: AsyncConnection,
    *,
    ws_uuid: str,
    item: SlotBindingInput,
    slot_spec: PackSlotSpec,
    instance: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    ds_id: str | None = None
    ec_id: str | None = None
    target_id: str | None = None
    slot_scheme = (slot_spec.scheme or "").strip().lower()
    override_scheme = (item.connector_scheme or "").strip().lower()
    scheme_cand: str | None = None

    if item.target_kind == PackSlotTargetKind.WORKSPACE_DATASOURCE:
        ds_id = _parse_uuid_or_raise(item.target_id, label="datasource_id", instance=instance)
        ds_row = (
            await conn.execute(
                sa.text(
                    "SELECT id::text, scheme FROM workspace_datasources "
                    "WHERE id = CAST(:ds AS uuid) AND workspace_id = CAST(:ws AS uuid) LIMIT 1"
                ),
                {"ds": ds_id, "ws": ws_uuid},
            )
        ).first()
        if ds_row is None:
            raise PackSlotBindingInvalidError(
                detail_override=f"Datasource {ds_id!r} not found inside workspace {ws_uuid!r}.",
                instance=instance,
            )
        ds_scheme = str(ds_row[1]).strip().lower()
        if slot_scheme and slot_scheme not in ("*", "any") and ds_scheme != slot_scheme:
            raise PackSlotBindingInvalidError(
                detail_override=(
                    f"Slot {slot_spec.slot_key!r} requires scheme {slot_scheme!r}, "
                    f"got datasource scheme {ds_scheme!r}."
                ),
                instance=instance,
            )
        if override_scheme and override_scheme != ds_scheme:
            raise PackSlotBindingInvalidError(
                detail_override=(
                    f"Requested scheme {override_scheme!r} conflicts with datasource "
                    f"scheme {ds_scheme!r}."
                ),
                instance=instance,
            )
        target_id = str(ds_row[0])
        scheme_cand = ds_scheme
    elif item.target_kind == PackSlotTargetKind.ENTERPRISE_CONNECTOR:
        ec_id = _parse_uuid_or_raise(item.target_id, label="connector_id", instance=instance)
        ec_row = (
            await conn.execute(
                sa.text(
                    "SELECT id::text, enabled, connector_kind FROM enterprise_connectors "
                    "WHERE id = CAST(:ec AS uuid) LIMIT 1"
                ),
                {"ec": ec_id},
            )
        ).first()
        if ec_row is None or not bool(ec_row[1]):
            raise PackSlotBindingInvalidError(
                detail_override=f"Enterprise connector {ec_id!r} not found or disabled.",
                instance=instance,
            )
        ec_kind = str(ec_row[2])
        if not _is_connector_kind_compatible(ec_kind, slot_scheme):
            raise PackSlotBindingInvalidError(
                detail_override=(
                    f"Connector kind {ec_kind!r} is incompatible with slot scheme {slot_scheme!r}."
                ),
                instance=instance,
            )
        if override_scheme and not _is_connector_kind_compatible(ec_kind, override_scheme):
            raise PackSlotBindingInvalidError(
                detail_override=(
                    f"Scheme {override_scheme!r} is incompatible with connector kind {ec_kind!r}."
                ),
                instance=instance,
            )
        target_id = str(ec_row[0])
        scheme_cand = override_scheme or slot_scheme or ec_kind.lower()
    elif item.target_kind == PackSlotTargetKind.INTERNAL:
        if slot_scheme != "internal":
            raise PackSlotBindingInvalidError(
                detail_override=(
                    f"Slot {slot_spec.slot_key!r} has scheme {slot_scheme!r} and cannot use "
                    "INTERNAL target_kind."
                ),
                instance=instance,
            )
        target_id = (item.target_id or f"internal:{item.slot_key}")[:128]
        scheme_cand = None

    resolved_scheme = await _validate_and_resolve_scheme(conn, scheme_cand, instance=instance)
    return ds_id, ec_id, target_id, resolved_scheme


async def bind_workspace_pack_slots_conn(
    conn: AsyncConnection,
    *,
    ws_uuid: str,
    bundle_row: dict[str, Any],
    bindings: Sequence[SlotBindingInput],
    actor_id: str,
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> list[EffectiveSlotBindingView]:
    """Validate and upsert `workspace_pack_slot_bindings`, emitting `PACK_SLOTS_BOUND`."""
    bundle_id = str(bundle_row["id"])
    pslug = str(bundle_row["slug"]).strip().lower()
    declared = decode_declared_slots(bundle_row["declared_slots_jsonb"])
    declared_by_key = {s.slot_key: s for s in declared}

    bound_keys: list[str] = []
    for item in bindings:
        slot_spec = declared_by_key.get(item.slot_key)
        if slot_spec is None:
            raise PackSlotBindingInvalidError(
                detail_override=f"Unknown slot {item.slot_key!r} for pack {pslug!r}.",
                instance=instance,
            )
        ds_id, ec_id, target_id, eff_scheme = await _resolve_slot_target(
            conn, ws_uuid=ws_uuid, item=item, slot_spec=slot_spec, instance=instance
        )
        slot_params = {
            "id": str(uuid7()),
            "ws": ws_uuid,
            "bid": bundle_id,
            "pslug": pslug,
            "skey": item.slot_key,
            "tkind": item.target_kind.value,
            "tid": target_id,
            "ds_id": ds_id,
            "ec_id": ec_id,
            "scheme": eff_scheme,
            "actor": actor_id,
        }
        await conn.execute(sa.text(_UPSERT_SLOT_SQL), slot_params)
        bound_keys.append(item.slot_key)

    await append_pack_audit_event(
        conn,
        event_type="PACK_SLOTS_BOUND",
        summary=f"Bound {len(bound_keys)} slot(s) for pack {pslug} in workspace {ws_uuid}",
        scope_path=f"WORKSPACE:{ws_uuid}",
        actor_id=actor_id,
        actor_email=actor_email,
        metadata={
            "workspace_id": ws_uuid,
            "pack_bundle_id": bundle_id,
            "pack_slug": pslug,
            "bound_slots": bound_keys,
        },
        trace_id=trace_id,
    )
    refreshed = await load_effective_slot_bindings_conn(conn, ws_uuid)
    return list(refreshed.get(pslug, {}).values())


async def bind_workspace_pack_slots_sql(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    pack_slug: str,
    bindings: Sequence[SlotBindingInput],
    bundle_id: str | None = None,
    actor_id: str,
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> list[EffectiveSlotBindingView]:
    """Persist workspace pack slot bindings and emit `PACK_SLOTS_BOUND` in PG18."""
    try:
        async with engine.begin() as conn:
            ws_uuid, ws_ou_id = await resolve_workspace_identity_conn(
                conn, workspace_id, instance=instance
            )
            bundle_row = await resolve_bundle_for_workspace_conn(
                conn,
                ws_uuid=ws_uuid,
                ws_org_unit_id=ws_ou_id,
                pack_slug=pack_slug,
                bundle_id=bundle_id,
                instance=instance,
            )
            return await bind_workspace_pack_slots_conn(
                conn,
                ws_uuid=ws_uuid,
                bundle_row=bundle_row,
                bindings=bindings,
                actor_id=actor_id,
                actor_email=actor_email,
                trace_id=trace_id,
                instance=instance,
            )
    except DBAPIError as exc:
        raise PackSlotBindingInvalidError(
            detail_override=f"Invalid slot binding mutation: {exc.orig}",
            instance=instance,
        ) from exc


__all__ = ["bind_workspace_pack_slots_conn", "bind_workspace_pack_slots_sql"]
