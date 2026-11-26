"""Batch hydration of `pack_draft_memberships` rows (`Story 31.5`, `<= 160 L`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs.composer_models import PackDraftMemberView
from orcia_core.packs.models import PackDraftEntityType


def decode_json_dict(raw: object) -> dict[str, Any]:
    """Decode dict/JSON string safely to a Python dictionary."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


async def _batch_load_member_labels(
    conn: AsyncConnection, rows: list[Any]
) -> tuple[dict[str, str], dict[str, str]]:
    titles: dict[str, str] = {}
    statuses: dict[str, str] = {}
    cat_ids = [str(r["catalog_item_id"]) for r in rows if r["catalog_item_id"]]
    if cat_ids:
        for cr in (
            await conn.execute(
                sa.text(
                    "SELECT id::text, title, metadata_jsonb FROM catalog_items "
                    "WHERE id::text = ANY(:ids)"
                ),
                {"ids": cat_ids},
            )
        ).fetchall():
            meta = decode_json_dict(cr[2])
            titles[str(cr[0])] = str(cr[1])
            statuses[str(cr[0])] = str(meta.get("lifecycle_status") or "ACTIVE").upper()
    wf_ids = [str(r["workflow_v2_id"]) for r in rows if r["workflow_v2_id"]]
    if wf_ids:
        for wr in (
            await conn.execute(
                sa.text(
                    "SELECT id::text, slug, status, spec_jsonb FROM workflow_definitions_v2 "
                    "WHERE id::text = ANY(:ids)"
                ),
                {"ids": wf_ids},
            )
        ).fetchall():
            spec = decode_json_dict(wr[3])
            titles[str(wr[0])] = str(spec.get("title") or wr[1])
            statuses[str(wr[0])] = str(wr[2] or "published").upper()
    vsm_ids = [str(r["vsm_v2_id"]) for r in rows if r["vsm_v2_id"]]
    if vsm_ids:
        for vr in (
            await conn.execute(
                sa.text(
                    "SELECT id::text, title FROM vsm_definitions_v2 WHERE id::text = ANY(:ids)"
                ),
                {"ids": vsm_ids},
            )
        ).fetchall():
            titles[str(vr[0])] = str(vr[1])
    return titles, statuses


async def load_draft_members_hydrated_conn(
    conn: AsyncConnection,
    *,
    draft_bundle_id: str,
) -> list[PackDraftMemberView]:
    """Load `pack_draft_memberships` rows hydrated with title & lifecycle status (batch)."""
    rows = (
        (
            await conn.execute(
                sa.text(
                    "SELECT id::text, draft_bundle_id::text, entity_type, entity_id, entity_slug, "
                    "catalog_item_id::text, workflow_v2_id::text, vsm_v2_id::text, "
                    "ontology_concept_id::text, ontology_relation_id::text, "
                    "ontology_axiom_id::text, dna_mechanism_id::text, policy_id::text, created_at "
                    "FROM pack_draft_memberships WHERE draft_bundle_id = CAST(:bid AS uuid) "
                    "ORDER BY created_at ASC, entity_type ASC, entity_slug ASC"
                ),
                {"bid": draft_bundle_id},
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return []
    titles, statuses = await _batch_load_member_labels(conn, list(rows))
    views: list[PackDraftMemberView] = []
    for r in rows:
        uid = (
            r["catalog_item_id"]
            or r["workflow_v2_id"]
            or r["vsm_v2_id"]
            or r["ontology_concept_id"]
            or r["ontology_relation_id"]
            or r["ontology_axiom_id"]
            or r["dna_mechanism_id"]
            or r["policy_id"]
            or ""
        )
        created = r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else ""
        views.append(
            PackDraftMemberView(
                id=str(r["id"]),
                draft_bundle_id=str(r["draft_bundle_id"]),
                entity_type=PackDraftEntityType(str(r["entity_type"])),
                entity_id=str(r["entity_id"]),
                entity_slug=str(r["entity_slug"]),
                title=titles.get(str(uid), str(r["entity_slug"])),
                lifecycle_status=statuses.get(str(uid), "ACTIVE"),
                catalog_item_id=str(r["catalog_item_id"]) if r["catalog_item_id"] else None,
                workflow_v2_id=str(r["workflow_v2_id"]) if r["workflow_v2_id"] else None,
                vsm_v2_id=str(r["vsm_v2_id"]) if r["vsm_v2_id"] else None,
                ontology_concept_id=(
                    str(r["ontology_concept_id"]) if r["ontology_concept_id"] else None
                ),
                ontology_relation_id=(
                    str(r["ontology_relation_id"]) if r["ontology_relation_id"] else None
                ),
                ontology_axiom_id=(str(r["ontology_axiom_id"]) if r["ontology_axiom_id"] else None),
                dna_mechanism_id=str(r["dna_mechanism_id"]) if r["dna_mechanism_id"] else None,
                policy_id=str(r["policy_id"]) if r["policy_id"] else None,
                created_at_iso=created,
            )
        )
    return views


__all__ = ["decode_json_dict", "load_draft_members_hydrated_conn"]
