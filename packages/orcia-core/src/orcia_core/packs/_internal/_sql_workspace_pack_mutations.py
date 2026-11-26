"""Transactional PG18 workspace pack activation & deactivation (`Story 31.4`, `<= 250 L`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
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
from orcia_core.packs._internal._sql_workspace_pack_reorder import map_pack_activation_db_error
from orcia_core.packs._internal._sql_workspace_slot_bindings import (
    bind_workspace_pack_slots_conn,
)
from orcia_core.packs.errors import PackActivationInvalidError, PackBundleNotFoundError
from orcia_core.packs.slot_guard import (
    SlotBindingInput,
    evaluate_pack_slot_readiness,
    is_binding_compatible_with_slot,
)


async def activate_workspace_pack_sql(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    pack_slug: str,
    bundle_id: str | None = None,
    version: str | None = None,
    priority_order: int | None = None,
    slot_bindings: Sequence[SlotBindingInput] = (),
    actor_id: str,
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Activate a pack in a workspace after checking required slots (`422` if unbound)."""
    if priority_order is not None and priority_order < 1:
        raise PackActivationInvalidError(
            detail_override="priority_order must be >= 1.",
            instance=instance,
        )
    try:
        async with engine.begin() as conn:
            ws_uuid, ws_ou_id = await resolve_workspace_identity_conn(
                conn, workspace_id, instance=instance
            )
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) FOR UPDATE"),
                {"ws": ws_uuid},
            )
            bundle_row = await resolve_bundle_for_workspace_conn(
                conn,
                ws_uuid=ws_uuid,
                ws_org_unit_id=ws_ou_id,
                pack_slug=pack_slug,
                bundle_id=bundle_id,
                version=version,
                instance=instance,
            )
            pslug = str(bundle_row["slug"]).strip().lower()
            bid = str(bundle_row["id"])
            if slot_bindings:
                await bind_workspace_pack_slots_conn(
                    conn,
                    ws_uuid=ws_uuid,
                    bundle_row=bundle_row,
                    bindings=slot_bindings,
                    actor_id=actor_id,
                    actor_email=actor_email,
                    trace_id=trace_id,
                    instance=instance,
                )
            bindings = await load_effective_slot_bindings_conn(conn, ws_uuid)
            declared = decode_declared_slots(bundle_row["declared_slots_jsonb"])
            evaluate_pack_slot_readiness(
                declared,
                bindings.get(pslug, {}),
                pack_slug=pslug,
                raise_on_missing=True,
                instance=instance,
            )
            # P1-3 + P2-2: migrate compatible slot bindings to new bundle & prune obsolete ones
            declared_by_key = {s.slot_key: s for s in declared}
            await conn.execute(
                sa.text(
                    "UPDATE workspace_pack_slot_bindings "
                    "SET pack_bundle_id = CAST(:bid AS uuid) "
                    "WHERE workspace_id = CAST(:ws AS uuid) AND LOWER(pack_slug) = LOWER(:slug)"
                ),
                {"bid": bid, "ws": ws_uuid, "slug": pslug},
            )
            for bound_key, existing_b in list(bindings.get(pslug, {}).items()):
                target_slot = declared_by_key.get(bound_key)
                if target_slot is None or not is_binding_compatible_with_slot(
                    existing_b, target_slot
                ):
                    await conn.execute(
                        sa.text(
                            "DELETE FROM workspace_pack_slot_bindings "
                            "WHERE workspace_id = CAST(:ws AS uuid) "
                            "AND LOWER(pack_slug) = LOWER(:slug) AND slot_key = :skey"
                        ),
                        {"ws": ws_uuid, "slug": pslug, "skey": bound_key},
                    )

            await conn.execute(sa.text("SET CONSTRAINTS uq_workspace_pack_priority DEFERRED"))
            existing = (
                await conn.execute(
                    sa.text(
                        "SELECT priority_order, is_active FROM workspace_pack_activations "
                        "WHERE workspace_id = CAST(:ws AS uuid) "
                        "AND LOWER(pack_slug) = LOWER(:slug) LIMIT 1 FOR UPDATE"
                    ),
                    {"ws": ws_uuid, "slug": pslug},
                )
            ).first()
            eff_prio = priority_order
            if eff_prio is None:
                if existing is not None and bool(existing[1]) and existing[0] is not None:
                    eff_prio = int(existing[0])
                else:
                    max_p = (
                        await conn.execute(
                            sa.text(
                                "SELECT COALESCE(MAX(priority_order), 0) "
                                "FROM workspace_pack_activations "
                                "WHERE workspace_id = CAST(:ws AS uuid) AND is_active = TRUE"
                            ),
                            {"ws": ws_uuid},
                        )
                    ).scalar_one()
                    eff_prio = int(max_p) + 1
            conflict_slug = (
                await conn.execute(
                    sa.text(
                        "SELECT pack_slug FROM workspace_pack_activations "
                        "WHERE workspace_id = CAST(:ws AS uuid) AND is_active = TRUE "
                        "AND priority_order = :prio AND LOWER(pack_slug) <> LOWER(:slug) LIMIT 1"
                    ),
                    {"ws": ws_uuid, "prio": eff_prio, "slug": pslug},
                )
            ).scalar()
            if conflict_slug is not None:
                raise PackActivationInvalidError(
                    detail_override=(
                        f"priority_order={eff_prio} already assigned to active pack "
                        f"{conflict_slug!r}."
                    ),
                    instance=instance,
                )
            row = (
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspace_pack_activations (
                            id, workspace_id, pack_bundle_id, pack_slug,
                            priority_order, is_active, activated_by, activated_at
                        )
                        VALUES (
                            CAST(:id AS uuid), CAST(:ws AS uuid), CAST(:bid AS uuid), :pslug,
                            :prio, TRUE, :actor, NOW()
                        )
                        ON CONFLICT (workspace_id, pack_slug) DO UPDATE SET
                            pack_bundle_id = EXCLUDED.pack_bundle_id,
                            priority_order = EXCLUDED.priority_order,
                            is_active = TRUE,
                            activated_by = EXCLUDED.activated_by,
                            activated_at = NOW()
                        RETURNING id::text, activated_at
                        """
                    ),
                    {
                        "id": str(uuid7()),
                        "ws": ws_uuid,
                        "bid": bid,
                        "pslug": pslug,
                        "prio": eff_prio,
                        "actor": actor_id,
                    },
                )
            ).first()
            await append_pack_audit_event(
                conn,
                event_type="PACK_ACTIVATED",
                summary=f"Activated pack {pslug}@{bundle_row['version']} in workspace {ws_uuid}",
                scope_path=f"WORKSPACE:{ws_uuid}",
                actor_id=actor_id,
                actor_email=actor_email,
                metadata={"workspace_id": ws_uuid, "pack_bundle_id": bid, "priority": eff_prio},
                trace_id=trace_id,
            )
            assert row is not None
            return {
                "activation_id": str(row[0]),
                "workspace_id": ws_uuid,
                "pack_bundle_id": bid,
                "pack_slug": pslug,
                "version": str(bundle_row["version"]),
                "priority_order": eff_prio,
                "is_active": True,
                "activated_at_iso": (
                    row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])
                ),
            }
    except DBAPIError as exc:
        raise map_pack_activation_db_error(exc, instance=instance) from exc


async def deactivate_workspace_pack_sql(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    pack_slug: str,
    actor_id: str,
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Deactivate a pack (`is_active=FALSE, priority_order=NULL` XOR constraint)."""
    try:
        async with engine.begin() as conn:
            ws_uuid, _ = await resolve_workspace_identity_conn(
                conn, workspace_id, instance=instance
            )
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) FOR UPDATE"),
                {"ws": ws_uuid},
            )
            pslug = pack_slug.strip().lower()
            row = (
                await conn.execute(
                    sa.text(
                        "UPDATE workspace_pack_activations "
                        "SET is_active = FALSE, priority_order = NULL "
                        "WHERE workspace_id = CAST(:ws AS uuid) "
                        "AND LOWER(pack_slug) = LOWER(:slug) "
                        "RETURNING id::text, pack_bundle_id::text"
                    ),
                    {"ws": ws_uuid, "slug": pslug},
                )
            ).first()
            if row is None:
                raise PackBundleNotFoundError(
                    detail_override=(
                        f"Pack activation for {pslug!r} not found in workspace {ws_uuid!r}."
                    ),
                    instance=instance,
                )
            await append_pack_audit_event(
                conn,
                event_type="PACK_DEACTIVATED",
                summary=f"Deactivated pack {pslug} in workspace {ws_uuid}",
                scope_path=f"WORKSPACE:{ws_uuid}",
                actor_id=actor_id,
                actor_email=actor_email,
                metadata={
                    "workspace_id": ws_uuid,
                    "pack_bundle_id": str(row[1]),
                    "pack_slug": pslug,
                },
                trace_id=trace_id,
            )
            return {
                "workspace_id": ws_uuid,
                "pack_bundle_id": str(row[1]),
                "pack_slug": pslug,
                "is_active": False,
            }
    except DBAPIError as exc:
        raise map_pack_activation_db_error(exc, instance=instance) from exc


__all__ = [
    "activate_workspace_pack_sql",
    "deactivate_workspace_pack_sql",
]
