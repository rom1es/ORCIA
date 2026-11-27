"""Ontology, DNA & policy target resolution helpers for Pack Composer (`Story 31.5`)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs._internal._sql_pack_composer_scope import (
    assert_bundle_visible_conn,
    is_ontology_level_visible,
)
from orcia_core.packs.composer_models import PackDraftMemberInput
from orcia_core.packs.models import PackDraftEntityType
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError

FK_COLUMN_BY_ENTITY_TYPE: dict[PackDraftEntityType, str] = {
    PackDraftEntityType.AGENT: "catalog_item_id",
    PackDraftEntityType.SKILL: "catalog_item_id",
    PackDraftEntityType.INSTRUCTION: "catalog_item_id",
    PackDraftEntityType.HELP_ARTICLE: "catalog_item_id",
    PackDraftEntityType.WORKFLOW_V2: "workflow_v2_id",
    PackDraftEntityType.VSM_V2: "vsm_v2_id",
    PackDraftEntityType.ONTOLOGY_CONCEPT: "ontology_concept_id",
    PackDraftEntityType.ONTOLOGY_RELATION: "ontology_relation_id",
    PackDraftEntityType.ONTOLOGY_AXIOM: "ontology_axiom_id",
    PackDraftEntityType.DNA_MECHANISM: "dna_mechanism_id",
    PackDraftEntityType.POLICY: "policy_id",
}

_ONTOLOGY_POLICY_SQL: dict[PackDraftEntityType, str] = {
    PackDraftEntityType.ONTOLOGY_CONCEPT: (
        "SELECT id::text AS uid, concept_key AS eid, canonical_term AS title, "
        "level, scope_id, snapshot_branch_status AS st, pack_bundle_id::text AS bid "
        "FROM ontology_concepts WHERE (id::text = :k OR concept_key = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC, id DESC LIMIT 20"
    ),
    PackDraftEntityType.ONTOLOGY_RELATION: (
        "SELECT r.id::text AS uid, r.relation_key AS eid, r.relation_type AS title, "
        "'ACTIVE' AS st, r.pack_bundle_id::text AS bid, "
        "src.level AS src_level, src.scope_id AS src_scope_id, "
        "src.pack_bundle_id::text AS src_bid, "
        "tgt.level AS tgt_level, tgt.scope_id AS tgt_scope_id, "
        "tgt.pack_bundle_id::text AS tgt_bid "
        "FROM ontology_relations r "
        "LEFT JOIN ontology_concepts src ON src.id = r.source_concept_id "
        "LEFT JOIN ontology_concepts tgt ON tgt.id = r.target_concept_id "
        "WHERE (r.id::text = :k OR r.relation_key = :k) "
        "ORDER BY (r.pack_bundle_id IS NULL) DESC, r.id DESC LIMIT 20"
    ),
    PackDraftEntityType.ONTOLOGY_AXIOM: (
        "SELECT id::text AS uid, axiom_key AS eid, axiom_key AS title, "
        "level, scope_id, 'ACTIVE' AS st, pack_bundle_id::text AS bid "
        "FROM ontology_axioms WHERE (id::text = :k OR axiom_key = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC, id DESC LIMIT 20"
    ),
    PackDraftEntityType.DNA_MECHANISM: (
        "SELECT id::text AS uid, mechanism_slug AS eid, name AS title, "
        "'ACTIVE' AS st, pack_bundle_id::text AS bid "
        "FROM pack_dna_mechanisms WHERE (id::text = :k OR mechanism_slug = :k) "
        "ORDER BY id DESC LIMIT 20"
    ),
    PackDraftEntityType.POLICY: (
        "SELECT id::text AS uid, policy_key AS eid, uri_pattern AS title, "
        "'ACTIVE' AS st, pack_bundle_id::text AS bid "
        "FROM permission_broker_policies WHERE (id::text = :k OR policy_key = :k) "
        "ORDER BY (pack_bundle_id IS NULL) DESC, id DESC LIMIT 20"
    ),
}


def _assert_policy_prefix_visible(
    policy_key: str, *, draft_scope_type: str, draft_scope_id: str, instance: str | None
) -> None:
    low = policy_key.strip().lower()
    for pfx in ("ws:", "workspace:"):
        if low.startswith(pfx):
            owner_ws = low[len(pfx) :].split(":", 1)[0]
            if draft_scope_type != "WORKSPACE" or owner_ws != draft_scope_id.lower():
                raise ScopeAccessDeniedError(
                    detail_override="Cannot add cross-workspace policy to draft pack.",
                    instance=instance,
                )


async def _validate_extra_row_visibility(
    conn: AsyncConnection,
    etype: PackDraftEntityType,
    row: dict[str, Any],
    *,
    draft_scope_type: str,
    draft_scope_id: str,
    ancestor_orgs: frozenset[str],
    instance: str | None,
) -> None:
    bid = str(row["bid"]) if row.get("bid") else None
    await assert_bundle_visible_conn(
        conn,
        pack_bundle_id=bid,
        draft_scope_type=draft_scope_type,
        draft_scope_id=draft_scope_id,
        ancestor_orgs=ancestor_orgs,
        instance=instance,
    )
    if (
        etype in (PackDraftEntityType.ONTOLOGY_CONCEPT, PackDraftEntityType.ONTOLOGY_AXIOM)
        and bid is None
    ):
        if not is_ontology_level_visible(
            level=row.get("level"),
            scope_id=row.get("scope_id"),
            draft_scope_type=draft_scope_type,
            draft_scope_id=draft_scope_id,
            ancestor_orgs=ancestor_orgs,
        ):
            raise ScopeAccessDeniedError(
                detail_override="Cannot add cross-scope ontology entity to draft pack.",
                instance=instance,
            )
    elif etype == PackDraftEntityType.ONTOLOGY_RELATION:
        for lp, sp, bp in (
            ("src_level", "src_scope_id", "src_bid"),
            ("tgt_level", "tgt_scope_id", "tgt_bid"),
        ):
            ep_bid = str(row[bp]) if row.get(bp) else None
            if ep_bid is not None:
                await assert_bundle_visible_conn(
                    conn,
                    pack_bundle_id=ep_bid,
                    draft_scope_type=draft_scope_type,
                    draft_scope_id=draft_scope_id,
                    ancestor_orgs=ancestor_orgs,
                    instance=instance,
                )
            elif row.get(lp) and not is_ontology_level_visible(
                level=row.get(lp),
                scope_id=row.get(sp),
                draft_scope_type=draft_scope_type,
                draft_scope_id=draft_scope_id,
                ancestor_orgs=ancestor_orgs,
            ):
                raise ScopeAccessDeniedError(
                    detail_override="Cannot add cross-scope ontology relation to draft pack.",
                    instance=instance,
                )
    elif etype == PackDraftEntityType.POLICY and bid is None:
        _assert_policy_prefix_visible(
            str(row.get("eid") or ""),
            draft_scope_type=draft_scope_type,
            draft_scope_id=draft_scope_id,
            instance=instance,
        )


async def resolve_ontology_or_policy_row_conn(
    conn: AsyncConnection,
    member: PackDraftMemberInput,
    *,
    draft_scope_type: str,
    draft_scope_id: str,
    ancestor_orgs: frozenset[str],
    instance: str | None,
) -> dict[str, Any]:
    """Query and scope-validate ontology, DNA mechanism, or policy target row."""
    etype = member.entity_type
    rows = (
        (
            await conn.execute(
                sa.text(_ONTOLOGY_POLICY_SQL[etype]),
                {"k": member.entity_id.strip()},
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        raise ResourceNotFoundError(
            detail_override=f"{etype.value} entity {member.entity_id!r} was not found.",
            instance=instance,
        )
    last_denied: ScopeAccessDeniedError | None = None
    for raw in rows:
        row = dict(raw)
        try:
            await _validate_extra_row_visibility(
                conn,
                etype,
                row,
                draft_scope_type=draft_scope_type,
                draft_scope_id=draft_scope_id,
                ancestor_orgs=ancestor_orgs,
                instance=instance,
            )
            return row
        except ScopeAccessDeniedError as exc:
            last_denied = exc
    if last_denied is not None:
        raise last_denied
    raise ResourceNotFoundError(
        detail_override=f"{etype.value} entity {member.entity_id!r} was not found.",
        instance=instance,
    )


__all__ = [
    "FK_COLUMN_BY_ENTITY_TYPE",
    "assert_bundle_visible_conn",
    "is_ontology_level_visible",
    "resolve_ontology_or_policy_row_conn",
]
