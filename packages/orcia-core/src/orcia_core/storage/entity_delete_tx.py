"""Shared transactional guarded entity deletion for PG18 (`AD-19`, `Story 31.5`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.kernel.errors import (
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.storage.pack_draft_guard import (
    ENTITY_TYPE_TO_FK_COLUMN,
    DraftAuthCallback,
    guard_or_unlink_pack_drafts_conn,
)

TargetAuthCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class EntityDeleteOutcome:
    """Result returned after a guarded transactional PG18 entity deletion."""

    entity_type: str
    deleted_id: str
    deleted_uuid: str
    unlinked_draft_packs: tuple[dict[str, str], ...]


_TARGET_SELECT_SQL: dict[str, tuple[str, str, str]] = {
    "WORKFLOW_V2": (
        "workflow_definitions_v2",
        "workflow_id",
        "SELECT id::text AS uid, workflow_id::text AS key_val, slug::text AS label_val, "
        "pack_bundle_id::text AS bid, pack_id, spec_jsonb "
        "FROM workflow_definitions_v2 "
        "WHERE (id::text = :k OR workflow_id::text = :k OR slug::text = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE",
    ),
    "VSM_V2": (
        "vsm_definitions_v2",
        "vsm_id",
        "SELECT id::text AS uid, vsm_id::text AS key_val, slug::text AS label_val, "
        "pack_bundle_id::text AS bid, pack_id, spec_jsonb "
        "FROM vsm_definitions_v2 "
        "WHERE (id::text = :k OR vsm_id::text = :k OR slug::text = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE",
    ),
    "ONTOLOGY_CONCEPT": (
        "ontology_concepts",
        "concept_key",
        "SELECT id::text AS uid, concept_key::text AS key_val, canonical_term::text AS label_val, "
        "pack_bundle_id::text AS bid, level, scope_id "
        "FROM ontology_concepts "
        "WHERE (id::text = :k OR concept_key::text = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE",
    ),
    "ONTOLOGY_RELATION": (
        "ontology_relations",
        "relation_key",
        "SELECT r.id::text AS uid, r.relation_key::text AS key_val, "
        "r.relation_type::text AS label_val, r.pack_bundle_id::text AS bid, "
        "src.level AS src_level, src.scope_id AS src_scope_id, "
        "tgt.level AS tgt_level, tgt.scope_id AS tgt_scope_id "
        "FROM ontology_relations r "
        "LEFT JOIN ontology_concepts src ON src.id = r.source_concept_id "
        "LEFT JOIN ontology_concepts tgt ON tgt.id = r.target_concept_id "
        "WHERE (r.id::text = :k OR r.relation_key::text = :k) "
        "ORDER BY (r.pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE OF r",
    ),
    "ONTOLOGY_AXIOM": (
        "ontology_axioms",
        "axiom_key",
        "SELECT id::text AS uid, axiom_key::text AS key_val, scope_id::text AS label_val, "
        "pack_bundle_id::text AS bid, level, scope_id "
        "FROM ontology_axioms "
        "WHERE (id::text = :k OR axiom_key::text = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE",
    ),
    "DNA_MECHANISM": (
        "pack_dna_mechanisms",
        "mechanism_slug",
        "SELECT d.id::text AS uid, d.mechanism_slug::text AS key_val, d.name::text AS label_val, "
        "d.pack_bundle_id::text AS bid, b.bundle_kind AS bundle_kind, b.status AS bundle_status, "
        "b.scope_type AS scope_type, b.scope_id AS scope_id "
        "FROM pack_dna_mechanisms d "
        "LEFT JOIN declarative_pack_bundles b ON b.id = d.pack_bundle_id "
        "WHERE (d.id::text = :k OR d.mechanism_slug::text = :k) LIMIT 1 FOR UPDATE OF d",
    ),
    "POLICY": (
        "permission_broker_policies",
        "policy_key",
        "SELECT id::text AS uid, policy_key::text AS key_val, uri_pattern::text AS label_val, "
        "pack_bundle_id::text AS bid, policy_key, uri_pattern "
        "FROM permission_broker_policies "
        "WHERE (id::text = :k OR policy_key::text = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE",
    ),
}


async def _enforce_pack_ownership_guard(
    etype: str, row: dict[str, Any], *, instance: str | None
) -> None:
    bid = row.get("bid")
    if not bid:
        return
    if (
        etype == "DNA_MECHANISM"
        and str(row.get("bundle_kind") or "") == "CUSTOM"
        and str(row.get("bundle_status") or "") == "DRAFT"
    ):
        return
    raise ScopeAccessDeniedError(
        detail_override="Installed or published pack assets cannot be deleted individually.",
        instance=instance,
    )


async def _guard_concept_children_conn(
    conn: AsyncConnection,
    *,
    target_uuid: str,
    unlink_from_draft_packs: bool,
    authorize_draft_cb: DraftAuthCallback | None,
    actor_id: str,
    actor_email: str | None,
    trace_id: str | None,
    scope_path: str,
    instance: str | None,
) -> list[dict[str, str]]:
    unlinked: list[dict[str, str]] = []
    for table, etype, fk_col, where_col in (
        (
            "ontology_relations",
            "ONTOLOGY_RELATION",
            "ontology_relation_id",
            "(source_concept_id = CAST(:cid AS uuid) OR target_concept_id = CAST(:cid AS uuid))",
        ),
        (
            "ontology_axioms",
            "ONTOLOGY_AXIOM",
            "ontology_axiom_id",
            "concept_id = CAST(:cid AS uuid)",
        ),
    ):
        rows = (
            (
                await conn.execute(
                    sa.text(
                        f"SELECT id::text AS uid, pack_bundle_id::text AS bid "
                        f"FROM {table} WHERE {where_col}"
                    ),
                    {"cid": target_uuid},
                )
            )
            .mappings()
            .all()
        )
        for r in rows:
            if r.get("bid") is not None:
                raise ScopeAccessDeniedError(
                    detail_override="Concept has child ontology rules owned by an installed pack.",
                    instance=instance,
                )
            unlinked.extend(
                await guard_or_unlink_pack_drafts_conn(
                    conn,
                    fk_column=fk_col,
                    target_uuid=str(r["uid"]),
                    entity_type=etype,
                    entity_label=str(r["uid"]),
                    unlink_from_draft_packs=unlink_from_draft_packs,
                    authorize_draft_cb=authorize_draft_cb,
                    actor_id=actor_id,
                    actor_email=actor_email,
                    trace_id=trace_id,
                    scope_path=scope_path,
                    instance=instance,
                )
            )
    return unlinked


async def delete_entity_guarded_tx(
    engine: AsyncEngine,
    *,
    entity_type: str,
    entity_id_or_key: str,
    unlink_from_draft_packs: bool = False,
    authorize_target_cb: TargetAuthCallback | None = None,
    authorize_draft_cb: DraftAuthCallback | None = None,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    scope_path: str = "GLOBAL",
    instance: str | None = None,
) -> EntityDeleteOutcome:
    """Delete a non-catalog PG18 entity with pack immutability, RBAC & anti-hostage guard."""
    etype = entity_type.strip().upper()
    if etype not in _TARGET_SELECT_SQL:
        raise ValidationDomainError(
            detail_override=f"Unsupported guarded delete entity type: {entity_type!r}",
            instance=instance,
        )
    table_name, _key_col, select_sql = _TARGET_SELECT_SQL[etype]
    fk_col = ENTITY_TYPE_TO_FK_COLUMN[etype]
    clean = entity_id_or_key.strip()
    if not clean:
        raise ResourceNotFoundError(
            detail_override=f"{etype} identifier must be non-empty.",
            instance=instance,
        )

    async with engine.begin() as conn:
        raw_row = (await conn.execute(sa.text(select_sql), {"k": clean})).mappings().first()
        if raw_row is None:
            raise ResourceNotFoundError(
                detail_override=f"{etype} {entity_id_or_key!r} not found.",
                instance=instance,
            )
        row = dict(raw_row)
        await _enforce_pack_ownership_guard(etype, row, instance=instance)
        if authorize_target_cb is not None:
            maybe_coro = authorize_target_cb(row)
            if maybe_coro is not None:
                await maybe_coro

        target_uuid = str(row["uid"])
        key_val = str(row["key_val"])
        unlinked = await guard_or_unlink_pack_drafts_conn(
            conn,
            fk_column=fk_col,
            target_uuid=target_uuid,
            entity_type=etype,
            entity_label=key_val,
            unlink_from_draft_packs=unlink_from_draft_packs,
            authorize_draft_cb=authorize_draft_cb,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            scope_path=scope_path,
            instance=instance,
        )
        if etype == "ONTOLOGY_CONCEPT":
            unlinked.extend(
                await _guard_concept_children_conn(
                    conn,
                    target_uuid=target_uuid,
                    unlink_from_draft_packs=unlink_from_draft_packs,
                    authorize_draft_cb=authorize_draft_cb,
                    actor_id=actor_id,
                    actor_email=actor_email,
                    trace_id=trace_id,
                    scope_path=scope_path,
                    instance=instance,
                )
            )
        await conn.execute(
            sa.text(f"DELETE FROM {table_name} WHERE id = CAST(:uid AS uuid)"),
            {"uid": target_uuid},
        )
    deduped = list({p["bundle_id"]: p for p in unlinked}.values())
    return EntityDeleteOutcome(
        entity_type=etype,
        deleted_id=key_val,
        deleted_uuid=target_uuid,
        unlinked_draft_packs=tuple(deduped),
    )


__all__ = ["EntityDeleteOutcome", "TargetAuthCallback", "delete_entity_guarded_tx"]
