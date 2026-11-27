"""Target UUID FK resolution for `pack_draft_memberships` (`Story 31.5`, `<= 270 L`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs._internal._sql_pack_composer_hydration import decode_json_dict
from orcia_core.packs._internal._sql_pack_composer_scope import (
    assert_bundle_visible_conn,
    assert_standalone_wf_vsm_visible,
    pick_first_visible,
)
from orcia_core.packs._internal._sql_pack_composer_target_extra import (
    FK_COLUMN_BY_ENTITY_TYPE,
    resolve_ontology_or_policy_row_conn,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import (
    load_ancestor_org_unit_ids_conn,
    resolve_workspace_identity_conn,
)
from orcia_core.packs.composer_models import PackDraftMemberInput
from orcia_core.packs.models import PackDraftEntityType
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError

_CATALOG_ITEM_TYPES: dict[PackDraftEntityType, tuple[str, ...]] = {
    PackDraftEntityType.AGENT: ("USER_AGENT", "agent"),
    PackDraftEntityType.SKILL: ("USER_SKILL", "skill"),
    PackDraftEntityType.INSTRUCTION: ("INSTRUCTION", "instruction"),
    PackDraftEntityType.HELP_ARTICLE: ("HELP_ARTICLE", "help_article"),
}


@dataclass(frozen=True, slots=True)
class ResolvedDraftTarget:
    """Resolved target entity row with surrogate UUID FK and visibility metadata."""

    entity_type: PackDraftEntityType
    entity_id: str
    entity_slug: str
    title: str
    lifecycle_status: str
    fk_column: str
    fk_uuid: str
    pack_bundle_id: str | None
    owner_workspace_id: str | None


async def resolve_draft_target_conn(
    conn: AsyncConnection,
    member: PackDraftMemberInput,
    *,
    draft_scope_type: str,
    draft_scope_id: str,
    ancestor_orgs: frozenset[str] | None = None,
    instance: str | None = None,
) -> ResolvedDraftTarget:
    """Resolve `PackDraftMemberInput` to an exact surrogate UUID FK in PostgreSQL 18."""
    clean_id = member.entity_id.strip()
    etype = member.entity_type
    fk_col = FK_COLUMN_BY_ENTITY_TYPE[etype]
    if ancestor_orgs is None:
        if draft_scope_type == "WORKSPACE":
            _, ws_org = await resolve_workspace_identity_conn(
                conn, draft_scope_id, instance=instance
            )
            ancestor_orgs = await load_ancestor_org_unit_ids_conn(conn, ws_org)
        elif draft_scope_type in ("BU", "TEAM"):
            ancestor_orgs = await load_ancestor_org_unit_ids_conn(conn, draft_scope_id)
    orgs = ancestor_orgs or frozenset()

    if etype in _CATALOG_ITEM_TYPES:
        it, rt = _CATALOG_ITEM_TYPES[etype]
        rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text AS uid, resource_id AS eid, title, "
                        "pack_bundle_id::text AS bid, owner_workspace_id::text AS ws_id, "
                        "metadata_jsonb FROM catalog_items "
                        "WHERE (id::text = :k OR resource_id = :k) "
                        "AND (item_type = :it OR resource_type = :rt) "
                        "ORDER BY (pack_bundle_id IS NULL) DESC, id DESC LIMIT 20"
                    ),
                    {"k": clean_id, "it": it, "rt": rt},
                )
            )
            .mappings()
            .all()
        )
        if rows:

            async def _val_cat(r: Any) -> None:
                ws_id = str(r["ws_id"]) if r["ws_id"] else None
                if ws_id and (draft_scope_type != "WORKSPACE" or ws_id != draft_scope_id):
                    raise ScopeAccessDeniedError(
                        detail_override="Cannot add cross-workspace catalog item to draft pack.",
                        instance=instance,
                    )
                bid = str(r["bid"]) if r["bid"] else None
                await assert_bundle_visible_conn(
                    conn,
                    pack_bundle_id=bid,
                    draft_scope_type=draft_scope_type,
                    draft_scope_id=draft_scope_id,
                    ancestor_orgs=orgs,
                    instance=instance,
                )

            row = await pick_first_visible(rows, _val_cat)
            meta = decode_json_dict(row["metadata_jsonb"])
            ws_id = str(row["ws_id"]) if row["ws_id"] else None
            bid = str(row["bid"]) if row["bid"] else None
            slug = str(member.entity_slug or meta.get("slug") or row["eid"]).strip()
            return ResolvedDraftTarget(
                entity_type=etype,
                entity_id=str(row["eid"]),
                entity_slug=slug[:128],
                title=str(row["title"]),
                lifecycle_status=str(meta.get("lifecycle_status") or "ACTIVE").upper(),
                fk_column=fk_col,
                fk_uuid=str(row["uid"]),
                pack_bundle_id=bid,
                owner_workspace_id=ws_id,
            )
    elif etype == PackDraftEntityType.WORKFLOW_V2:
        rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text AS uid, workflow_id AS eid, slug, status, pack_id, "
                        "pack_bundle_id::text AS bid, spec_jsonb FROM workflow_definitions_v2 "
                        "WHERE (id::text = :k OR workflow_id = :k OR slug = :k) "
                        "ORDER BY (pack_bundle_id IS NULL) DESC, updated_at DESC LIMIT 20"
                    ),
                    {"k": clean_id},
                )
            )
            .mappings()
            .all()
        )
        if rows:

            async def _val_wf(r: Any) -> None:
                bid = str(r["bid"]) if r["bid"] else None
                await assert_bundle_visible_conn(
                    conn,
                    pack_bundle_id=bid,
                    draft_scope_type=draft_scope_type,
                    draft_scope_id=draft_scope_id,
                    ancestor_orgs=orgs,
                    instance=instance,
                )
                if bid is None:
                    assert_standalone_wf_vsm_visible(
                        pack_id=str(r.get("pack_id") or ""),
                        spec=decode_json_dict(r.get("spec_jsonb")),
                        draft_scope_type=draft_scope_type,
                        draft_scope_id=draft_scope_id,
                        ancestor_orgs=orgs,
                        instance=instance,
                    )

            row = await pick_first_visible(rows, _val_wf)
            spec = decode_json_dict(row["spec_jsonb"])
            return ResolvedDraftTarget(
                entity_type=etype,
                entity_id=str(row["eid"]),
                entity_slug=str(member.entity_slug or row["slug"])[:128],
                title=str(spec.get("title") or row["slug"]),
                lifecycle_status=str(row["status"] or "published").upper(),
                fk_column=fk_col,
                fk_uuid=str(row["uid"]),
                pack_bundle_id=str(row["bid"]) if row["bid"] else None,
                owner_workspace_id=None,
            )
    elif etype == PackDraftEntityType.VSM_V2:
        rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text AS uid, vsm_id AS eid, slug, title, pack_id, "
                        "pack_bundle_id::text AS bid, spec_jsonb FROM vsm_definitions_v2 "
                        "WHERE (id::text = :k OR vsm_id = :k OR slug = :k) "
                        "ORDER BY (pack_bundle_id IS NULL) DESC, updated_at DESC LIMIT 20"
                    ),
                    {"k": clean_id},
                )
            )
            .mappings()
            .all()
        )
        if rows:

            async def _val_vsm(r: Any) -> None:
                bid = str(r["bid"]) if r["bid"] else None
                await assert_bundle_visible_conn(
                    conn,
                    pack_bundle_id=bid,
                    draft_scope_type=draft_scope_type,
                    draft_scope_id=draft_scope_id,
                    ancestor_orgs=orgs,
                    instance=instance,
                )
                if bid is None:
                    assert_standalone_wf_vsm_visible(
                        pack_id=str(r.get("pack_id") or ""),
                        spec=decode_json_dict(r.get("spec_jsonb")),
                        draft_scope_type=draft_scope_type,
                        draft_scope_id=draft_scope_id,
                        ancestor_orgs=orgs,
                        instance=instance,
                    )

            row = await pick_first_visible(rows, _val_vsm)
            return ResolvedDraftTarget(
                entity_type=etype,
                entity_id=str(row["eid"]),
                entity_slug=str(member.entity_slug or row["slug"])[:128],
                title=str(row["title"]),
                lifecycle_status="ACTIVE",
                fk_column=fk_col,
                fk_uuid=str(row["uid"]),
                pack_bundle_id=str(row["bid"]) if row["bid"] else None,
                owner_workspace_id=None,
            )
    else:
        extra = await resolve_ontology_or_policy_row_conn(
            conn,
            member,
            draft_scope_type=draft_scope_type,
            draft_scope_id=draft_scope_id,
            ancestor_orgs=orgs,
            instance=instance,
        )
        eid = str(extra["eid"])
        return ResolvedDraftTarget(
            entity_type=etype,
            entity_id=eid,
            entity_slug=str(member.entity_slug or eid.rsplit(":", 1)[-1])[:128],
            title=str(extra["title"]),
            lifecycle_status=str(extra.get("st") or "ACTIVE").upper(),
            fk_column=fk_col,
            fk_uuid=str(extra["uid"]),
            pack_bundle_id=str(extra["bid"]) if extra.get("bid") else None,
            owner_workspace_id=None,
        )

    raise ResourceNotFoundError(
        detail_override=f"{etype.value} entity {member.entity_id!r} was not found.",
        instance=instance,
    )


__all__ = [
    "FK_COLUMN_BY_ENTITY_TYPE",
    "ResolvedDraftTarget",
    "resolve_draft_target_conn",
]
