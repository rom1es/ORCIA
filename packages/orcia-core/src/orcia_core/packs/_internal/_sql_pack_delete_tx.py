"""Guarded transactional pack bundle deletion SQL helper (`Story 31.2`, `<= 300 L`)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs._internal._sql_pack_lifecycle import _OWNED_CHILD_TABLES
from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
)
from orcia_core.packs.errors import (
    EntityReferencedByPackDraftError,
    PackBundleNotFoundError,
    PackSystemDeleteForbiddenError,
    ResourcePinnedByActiveRunsError,
)
from orcia_core.storage.run_lock_guard import assert_pack_bundle_not_pinned_by_active_runs_conn


async def delete_bundle_transactional(
    engine: AsyncEngine,
    *,
    bundle_id_or_pack_id: str,
    allow_system_delete: bool = False,
    record_audit: bool = True,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
) -> dict[str, str]:
    """Safely delete a pack bundle after checking SYSTEM kind, run pinning, and draft links."""
    clean = bundle_id_or_pack_id.strip()
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, pack_id, slug, version, bundle_kind, "
                        "scope_type, scope_id "
                        "FROM declarative_pack_bundles "
                        "WHERE id::text = :key OR pack_id = :key LIMIT 1 FOR UPDATE"
                    ),
                    {"key": clean},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise PackBundleNotFoundError(
                detail_override=f"Pack bundle {bundle_id_or_pack_id!r} was not found."
            )
        bundle_id = str(row["id"])
        slug = str(row["slug"])
        version = str(row["version"])
        if str(row["bundle_kind"]) == "SYSTEM" and not allow_system_delete:
            raise PackSystemDeleteForbiddenError(
                detail_override=f"Built-in SYSTEM pack {slug!r} cannot be deleted."
            )

        active_act = (
            await conn.execute(
                sa.text(
                    "SELECT 1 FROM workspace_pack_activations "
                    "WHERE pack_bundle_id = CAST(:bid AS uuid) AND is_active = TRUE LIMIT 1"
                ),
                {"bid": bundle_id},
            )
        ).scalar()
        if active_act is not None:
            raise ResourcePinnedByActiveRunsError(
                detail_override=f"Pack bundle {bundle_id!r} has active workspace activations."
            )
        await assert_pack_bundle_not_pinned_by_active_runs_conn(
            conn, bundle_id=bundle_id, slug=slug, version=version
        )

        for tbl, fk_col in _OWNED_CHILD_TABLES:
            ref = (
                await conn.execute(
                    sa.text(
                        f"SELECT 1 FROM pack_draft_memberships m "
                        f"JOIN {tbl} c ON c.id = m.{fk_col} "
                        f"WHERE c.pack_bundle_id = CAST(:bid AS uuid) "
                        f"AND m.draft_bundle_id <> CAST(:bid AS uuid) LIMIT 1"
                    ),
                    {"bid": bundle_id},
                )
            ).scalar()
            if ref is not None:
                raise EntityReferencedByPackDraftError(
                    detail_override=(
                        f"Entities in bundle {bundle_id!r} are referenced by another pack draft."
                    )
                )

        mech_ref = (
            await conn.execute(
                sa.text(
                    "SELECT 1 FROM pack_draft_memberships m "
                    "JOIN pack_dna_mechanisms d ON d.id = m.dna_mechanism_id "
                    "WHERE d.pack_bundle_id = CAST(:bid AS uuid) "
                    "AND m.draft_bundle_id <> CAST(:bid AS uuid) LIMIT 1"
                ),
                {"bid": bundle_id},
            )
        ).scalar()
        if mech_ref is not None:
            raise EntityReferencedByPackDraftError(
                detail_override=(
                    f"DNA mechanisms in bundle {bundle_id!r} are referenced by another pack draft."
                )
            )

        await conn.execute(
            sa.text(
                "DELETE FROM pack_draft_memberships WHERE draft_bundle_id = CAST(:bid AS uuid)"
            ),
            {"bid": bundle_id},
        )
        await conn.execute(
            sa.text(
                "DELETE FROM workspace_pack_activations "
                "WHERE pack_bundle_id = CAST(:bid AS uuid) AND is_active = FALSE"
            ),
            {"bid": bundle_id},
        )
        await conn.execute(
            sa.text("DELETE FROM declarative_pack_bundles WHERE id = CAST(:bid AS uuid)"),
            {"bid": bundle_id},
        )
        if record_audit:
            await append_pack_audit_event(
                conn,
                event_type="PACK_BUNDLE_DELETED",
                summary=f"Deleted pack bundle {slug}@{version} ({bundle_id})",
                scope_path=f"{row['scope_type']}:{row['scope_id']}",
                actor_id=actor_id,
                actor_email=actor_email,
                metadata={"bundle_id": bundle_id, "slug": slug, "version": version},
                trace_id=trace_id,
            )
        return {"bundle_id": bundle_id, "slug": slug, "version": version}


__all__ = ["delete_bundle_transactional"]
