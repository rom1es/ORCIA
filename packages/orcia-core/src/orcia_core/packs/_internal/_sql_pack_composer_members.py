"""PostgreSQL 18 member & delete mutations for Pack Composer (`Story 31.5`, `<= 190 L`)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_composer_hydration import (
    load_draft_members_hydrated_conn,
)
from orcia_core.packs._internal._sql_pack_composer_reads import (
    fetch_bundle_row_conn,
    row_to_draft_detail,
)
from orcia_core.packs._internal._sql_pack_composer_targets import (
    ResolvedDraftTarget,
    resolve_draft_target_conn,
)
from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import (
    load_ancestor_org_unit_ids_conn,
    resolve_workspace_identity_conn,
)
from orcia_core.packs.composer_models import PackDraftDetail, PackDraftMemberInput
from orcia_core.packs.errors import PackSystemDeleteForbiddenError, PackVersionConflictError


async def insert_draft_membership_conn(
    conn: AsyncConnection, *, draft_bundle_id: str, target: ResolvedDraftTarget
) -> None:
    """Insert one `pack_draft_memberships` row populating the exact typed FK column."""
    fk_vals: dict[str, str | None] = {
        "catalog_item_id": None,
        "workflow_v2_id": None,
        "vsm_v2_id": None,
        "ontology_concept_id": None,
        "ontology_relation_id": None,
        "ontology_axiom_id": None,
        "dna_mechanism_id": None,
        "policy_id": None,
    }
    fk_vals[target.fk_column] = target.fk_uuid
    await conn.execute(
        sa.text(
            """
            INSERT INTO pack_draft_memberships (
                id, draft_bundle_id, entity_type, entity_id, entity_slug,
                catalog_item_id, workflow_v2_id, vsm_v2_id, ontology_concept_id,
                ontology_relation_id, ontology_axiom_id, dna_mechanism_id, policy_id
            )
            VALUES (
                CAST(:id AS uuid), CAST(:draft_id AS uuid), :etype, :eid, :eslug,
                CAST(:catalog_item_id AS uuid), CAST(:workflow_v2_id AS uuid),
                CAST(:vsm_v2_id AS uuid), CAST(:ontology_concept_id AS uuid),
                CAST(:ontology_relation_id AS uuid), CAST(:ontology_axiom_id AS uuid),
                CAST(:dna_mechanism_id AS uuid), CAST(:policy_id AS uuid)
            )
            ON CONFLICT (draft_bundle_id, entity_type, entity_id) DO NOTHING
            """
        ),
        {
            "id": str(uuid7()),
            "draft_id": draft_bundle_id,
            "etype": target.entity_type.value,
            "eid": target.entity_id[:128],
            "eslug": target.entity_slug[:128],
            **fk_vals,
        },
    )


async def set_draft_pack_members_sql(
    engine: AsyncEngine,
    draft_id: str,
    members: Sequence[PackDraftMemberInput],
    *,
    actor_id: str,
    actor_email: str | None,
    trace_id: str | None,
    instance: str | None = None,
) -> PackDraftDetail:
    """Atomically set `pack_draft_memberships` for a `CUSTOM` `DRAFT` resolving 8 typed FKs."""
    async with engine.begin() as conn:
        row = await fetch_bundle_row_conn(conn, draft_id, for_update=True, instance=instance)
        if str(row["bundle_kind"]) != "CUSTOM" or str(row["status"]) != "DRAFT":
            raise PackVersionConflictError(
                detail_override="Only CUSTOM DRAFT packs allow editing memberships.",
                instance=instance,
            )
        bid, st, sid = str(row["id"]), str(row["scope_type"]), str(row["scope_id"])
        orgs: frozenset[str] = frozenset()
        if st == "WORKSPACE":
            _, ws_org = await resolve_workspace_identity_conn(conn, sid, instance=instance)
            orgs = await load_ancestor_org_unit_ids_conn(conn, ws_org)
        elif st in ("BU", "TEAM"):
            orgs = await load_ancestor_org_unit_ids_conn(conn, sid)
        resolved: dict[tuple[str, str], ResolvedDraftTarget] = {}
        for item in members:
            target = await resolve_draft_target_conn(
                conn,
                item,
                draft_scope_type=st,
                draft_scope_id=sid,
                ancestor_orgs=orgs,
                instance=instance,
            )
            resolved[(target.entity_type.value, target.entity_id)] = target
        await conn.execute(
            sa.text(
                "DELETE FROM pack_draft_memberships WHERE draft_bundle_id = CAST(:bid AS uuid)"
            ),
            {"bid": bid},
        )
        for target in resolved.values():
            await insert_draft_membership_conn(conn, draft_bundle_id=bid, target=target)
        await conn.execute(
            sa.text(
                "UPDATE declarative_pack_bundles SET updated_at = NOW() "
                "WHERE id = CAST(:bid AS uuid)"
            ),
            {"bid": bid},
        )
        await append_pack_audit_event(
            conn,
            event_type="PACK_DRAFT_MEMBERS_UPDATED",
            summary=f"Set {len(resolved)} member(s) on draft pack {row['slug']}@{row['version']}",
            scope_path=f"{st}:{sid}",
            actor_id=actor_id,
            actor_email=actor_email,
            metadata={"bundle_id": bid, "members_count": len(resolved)},
            trace_id=trace_id,
        )
        hydrated = await load_draft_members_hydrated_conn(conn, draft_bundle_id=bid)
        return row_to_draft_detail(row, hydrated)


async def delete_draft_pack_sql(
    engine: AsyncEngine,
    draft_id: str,
    *,
    actor_id: str,
    actor_email: str | None,
    trace_id: str | None,
    instance: str | None = None,
) -> dict[str, str]:
    """Delete a `CUSTOM` `DRAFT` pack (`ON DELETE CASCADE` on `pack_draft_memberships`)."""
    async with engine.begin() as conn:
        row = await fetch_bundle_row_conn(conn, draft_id, for_update=True, instance=instance)
        if str(row["bundle_kind"]) == "SYSTEM":
            raise PackSystemDeleteForbiddenError(instance=instance)
        if str(row["bundle_kind"]) != "CUSTOM" or str(row["status"]) != "DRAFT":
            raise PackVersionConflictError(
                detail_override="Only CUSTOM DRAFT bundles can be deleted via composer.",
                instance=instance,
            )
        bid, slug, version = str(row["id"]), str(row["slug"]), str(row["version"])
        await conn.execute(
            sa.text("DELETE FROM declarative_pack_bundles WHERE id = CAST(:bid AS uuid)"),
            {"bid": bid},
        )
        await append_pack_audit_event(
            conn,
            event_type="PACK_DRAFT_DELETED",
            summary=f"Deleted CUSTOM DRAFT pack {slug}@{version}",
            scope_path=f"{row['scope_type']}:{row['scope_id']}",
            actor_id=actor_id,
            actor_email=actor_email,
            metadata={"bundle_id": bid, "slug": slug, "version": version},
            trace_id=trace_id,
        )
        return {"bundle_id": bid, "slug": slug, "version": version}


__all__ = [
    "delete_draft_pack_sql",
    "insert_draft_membership_conn",
    "set_draft_pack_members_sql",
]
