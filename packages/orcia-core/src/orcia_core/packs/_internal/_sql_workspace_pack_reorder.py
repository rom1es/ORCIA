"""Atomic DEFERRABLE reorder & DBAPI error mapping (`Story 31.4`, `<= 150 L`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import resolve_workspace_identity_conn
from orcia_core.packs.errors import PackActivationInvalidError
from orcia_core.permissions.errors import ScopeAccessDeniedError


def map_pack_activation_db_error(exc: DBAPIError, *, instance: str | None) -> Exception:
    """Translate PG18 trigger or constraint violations into RFC 9457 domain errors."""
    msg = str(exc)
    if "Cross-workspace pack activation forbidden" in msg:
        return ScopeAccessDeniedError(
            detail_override="Cross-workspace pack activation is forbidden.",
            instance=instance,
        )
    return PackActivationInvalidError(
        detail_override=f"Workspace pack priority/constraint conflict: {exc.orig}",
        instance=instance,
    )


async def reorder_workspace_packs_sql(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    ordered_pack_slugs: Sequence[str],
    actor_id: str,
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Atomically reorder active workspace packs using `DEFERRABLE` priority uniqueness."""
    norm = [s.strip().lower() for s in ordered_pack_slugs if s.strip()]
    if not norm or len(norm) != len(set(norm)):
        raise PackActivationInvalidError(
            detail_override="ordered_pack_slugs must be non-empty without duplicates.",
            instance=instance,
        )
    try:
        async with engine.begin() as conn:
            ws_uuid, _ = await resolve_workspace_identity_conn(
                conn, workspace_id, instance=instance
            )
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) FOR UPDATE"),
                {"ws": ws_uuid},
            )
            active_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT pack_slug, pack_bundle_id::text FROM workspace_pack_activations "
                        "WHERE workspace_id = CAST(:ws AS uuid) AND is_active = TRUE FOR UPDATE"
                    ),
                    {"ws": ws_uuid},
                )
            ).fetchall()
            active_map = {str(r[0]).strip().lower(): str(r[1]) for r in active_rows}
            if set(norm) != set(active_map.keys()):
                raise PackActivationInvalidError(
                    detail_override=(
                        f"ordered_pack_slugs {norm!r} must match active packs "
                        f"{sorted(active_map.keys())!r}."
                    ),
                    instance=instance,
                )
            await conn.execute(sa.text("SET CONSTRAINTS uq_workspace_pack_priority DEFERRED"))
            out: list[dict[str, Any]] = []
            for idx, pslug in enumerate(norm, start=1):
                await conn.execute(
                    sa.text(
                        "UPDATE workspace_pack_activations SET priority_order = :prio "
                        "WHERE workspace_id = CAST(:ws AS uuid) "
                        "AND LOWER(pack_slug) = LOWER(:slug) AND is_active = TRUE"
                    ),
                    {"prio": idx, "ws": ws_uuid, "slug": pslug},
                )
                out.append(
                    {
                        "pack_slug": pslug,
                        "pack_bundle_id": active_map[pslug],
                        "priority_order": idx,
                    }
                )
            await append_pack_audit_event(
                conn,
                event_type="PACKS_REORDERED",
                summary=f"Reordered {len(out)} active pack(s) in workspace {ws_uuid}",
                scope_path=f"WORKSPACE:{ws_uuid}",
                actor_id=actor_id,
                actor_email=actor_email,
                metadata={"workspace_id": ws_uuid, "order": norm},
                trace_id=trace_id,
            )
            return out
    except DBAPIError as exc:
        raise map_pack_activation_db_error(exc, instance=instance) from exc


__all__ = ["map_pack_activation_db_error", "reorder_workspace_packs_sql"]
