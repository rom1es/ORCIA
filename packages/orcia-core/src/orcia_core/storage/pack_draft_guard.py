"""Shared transactional anti-hostage pack-draft unlink guard (`AD-19`, `Story 31.5`)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection
from uuid_utils import uuid7

from orcia_core.kernel.errors import EntityReferencedByPackDraftError

DraftAuthCallback = Callable[[str, str, str], None]

ENTITY_TYPE_TO_FK_COLUMN: dict[str, str] = {
    "AGENT": "catalog_item_id",
    "SKILL": "catalog_item_id",
    "INSTRUCTION": "catalog_item_id",
    "HELP_ARTICLE": "catalog_item_id",
    "WORKFLOW_V2": "workflow_v2_id",
    "VSM_V2": "vsm_v2_id",
    "ONTOLOGY_CONCEPT": "ontology_concept_id",
    "ONTOLOGY_RELATION": "ontology_relation_id",
    "ONTOLOGY_AXIOM": "ontology_axiom_id",
    "DNA_MECHANISM": "dna_mechanism_id",
    "POLICY": "policy_id",
}
_ALLOWED_FK_COLUMNS: frozenset[str] = frozenset(ENTITY_TYPE_TO_FK_COLUMN.values())


def _validated_fk_column(fk_column: str) -> str:
    if fk_column not in _ALLOWED_FK_COLUMNS:
        raise ValueError(f"Unsupported pack_draft_memberships FK column: {fk_column!r}")
    return fk_column


async def _has_draft_tables_conn(conn: AsyncConnection) -> bool:
    return bool(
        (
            await conn.execute(
                sa.text(
                    "SELECT (to_regclass('public.pack_draft_memberships') IS NOT NULL "
                    "AND to_regclass('public.declarative_pack_bundles') IS NOT NULL)"
                )
            )
        ).scalar()
    )


async def _list_referencing_draft_rows_conn(
    conn: AsyncConnection,
    *,
    col: str,
    target_uuid: str,
) -> list[dict[str, str]]:
    if not await _has_draft_tables_conn(conn):
        return []
    rows = (
        (
            await conn.execute(
                sa.text(
                    f"SELECT DISTINCT b.id::text AS bundle_id, b.slug AS pack_slug, "
                    f"b.version AS version, b.name AS title, "
                    f"b.scope_type AS scope_type, b.scope_id AS scope_id "
                    f"FROM pack_draft_memberships m "
                    f"JOIN declarative_pack_bundles b ON b.id = m.draft_bundle_id "
                    f"WHERE m.{col} = CAST(:tid AS uuid) "
                    f"AND b.status = 'DRAFT' AND b.bundle_kind = 'CUSTOM' "
                    f"ORDER BY b.slug ASC, b.version ASC"
                ),
                {"tid": target_uuid},
            )
        )
        .mappings()
        .all()
    )
    return [
        {
            "bundle_id": str(r["bundle_id"]),
            "pack_slug": str(r["pack_slug"]),
            "version": str(r["version"]),
            "title": str(r["title"]),
            "scope_type": str(r.get("scope_type") or "WORKSPACE"),
            "scope_id": str(r.get("scope_id") or ""),
        }
        for r in rows
    ]


async def list_referencing_pack_drafts_conn(
    conn: AsyncConnection,
    *,
    fk_column: str,
    target_uuid: str,
) -> list[dict[str, str]]:
    """Return referencing `CUSTOM DRAFT` packs (`[{bundle_id, pack_slug, version, title}]`)."""
    col = _validated_fk_column(fk_column)
    rows = await _list_referencing_draft_rows_conn(conn, col=col, target_uuid=target_uuid)
    return [{k: r[k] for k in ("bundle_id", "pack_slug", "version", "title")} for r in rows]


async def _append_unlink_audit_conn(
    conn: AsyncConnection,
    *,
    scope_path: str,
    actor_id: str,
    actor_email: str | None,
    summary: str,
    metadata: dict[str, Any],
    trace_id: str | None,
) -> None:
    reg = (await conn.execute(sa.text("SELECT to_regclass('public.audit_ledger')"))).scalar()
    if reg is None:
        return
    await conn.execute(
        sa.text(
            """
            INSERT INTO audit_ledger (
                id, source_event_id, scope_path, actor_type, actor_id, actor_email,
                event_type, summary, trace_id, cas_references_jsonb, metadata_jsonb
            )
            VALUES (
                CAST(:id AS uuid), CAST(:src_id AS uuid), :scope_path, 'HUMAN',
                :actor_id, :actor_email, 'PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE',
                :summary, :trace_id, '[]'::jsonb, CAST(:meta AS jsonb)
            )
            """
        ),
        {
            "id": str(uuid7()),
            "src_id": str(uuid7()),
            "scope_path": scope_path[:256] or "GLOBAL",
            "actor_id": actor_id[:128],
            "actor_email": actor_email,
            "summary": summary,
            "trace_id": (trace_id or str(uuid7()).replace("-", ""))[:64],
            "meta": json.dumps(metadata, ensure_ascii=False),
        },
    )


async def guard_or_unlink_pack_drafts_conn(
    conn: AsyncConnection,
    *,
    fk_column: str,
    target_uuid: str,
    entity_type: str,
    entity_label: str,
    unlink_from_draft_packs: bool = False,
    authorize_draft_cb: DraftAuthCallback | None = None,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    scope_path: str = "GLOBAL",
    instance: str | None = None,
) -> list[dict[str, str]]:
    """Enforce `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` or atomically unlink + audit."""
    col = _validated_fk_column(fk_column)
    raw_rows = await _list_referencing_draft_rows_conn(conn, col=col, target_uuid=target_uuid)
    if not raw_rows:
        return []
    draft_packs = [
        {k: r[k] for k in ("bundle_id", "pack_slug", "version", "title")} for r in raw_rows
    ]
    if not unlink_from_draft_packs:
        raise EntityReferencedByPackDraftError(draft_packs=draft_packs, instance=instance)
    if authorize_draft_cb is not None:
        for r in raw_rows:
            authorize_draft_cb(r["bundle_id"], r["scope_type"], r["scope_id"])
    unlinked_rows = (
        (
            await conn.execute(
                sa.text(
                    f"DELETE FROM pack_draft_memberships "
                    f"WHERE {col} = CAST(:tid AS uuid) "
                    f"AND draft_bundle_id IN ("
                    f"SELECT id FROM declarative_pack_bundles "
                    f"WHERE status = 'DRAFT' AND bundle_kind = 'CUSTOM'"
                    f") RETURNING id::text, draft_bundle_id::text"
                ),
                {"tid": target_uuid},
            )
        )
        .mappings()
        .all()
    )
    await _append_unlink_audit_conn(
        conn,
        scope_path=scope_path,
        actor_id=actor_id,
        actor_email=actor_email,
        summary=(
            f"Unlinked {entity_type} {entity_label} ({target_uuid}) from "
            f"{len(draft_packs)} draft pack(s) on entity deletion"
        ),
        metadata={
            "entity_type": entity_type,
            "target_uuid": target_uuid,
            "entity_label": entity_label,
            "unlinked_membership_ids": [str(r["id"]) for r in unlinked_rows],
            "draft_packs": draft_packs,
        },
        trace_id=trace_id,
    )
    return draft_packs


__all__ = [
    "DraftAuthCallback",
    "ENTITY_TYPE_TO_FK_COLUMN",
    "guard_or_unlink_pack_drafts_conn",
    "list_referencing_pack_drafts_conn",
]
