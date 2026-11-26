"""Read queries & row mappers for Pack Composer (`Story 31.5`, `<= 160 L`)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.packs._internal._sql_pack_composer_hydration import (
    decode_json_dict,
    load_draft_members_hydrated_conn,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import decode_declared_slots
from orcia_core.packs.composer_models import PackDraftDetail
from orcia_core.packs.errors import PackBundleNotFoundError
from orcia_core.packs.models import PackQuickActionSpec, PackScopeType

BUNDLE_SELECT_COLS = (
    "id::text, pack_id, slug, name, version, rbac_namespace, bundle_kind, scope_type, "
    "scope_id, status, source_origin, archive_sha256, cas_object_key, manifest_jsonb, "
    "declared_slots_jsonb, author, description, created_by_user_id::text, published_at, updated_at"
)


def row_to_draft_detail(row: Any, members: list[Any]) -> PackDraftDetail:
    """Map a `declarative_pack_bundles` row + hydrated members into `PackDraftDetail`."""
    manifest = decode_json_dict(row["manifest_jsonb"])
    slots = decode_declared_slots(row["declared_slots_jsonb"])
    qa_raw = manifest.get("quick_actions") or []
    quick_actions = (
        [PackQuickActionSpec.model_validate(q) for q in qa_raw if isinstance(q, dict)]
        if isinstance(qa_raw, list)
        else []
    )
    maint_raw = manifest.get("maintainers") or []
    maintainers = [str(m) for m in maint_raw] if isinstance(maint_raw, list) else []
    pub = row["published_at"].isoformat() if hasattr(row["published_at"], "isoformat") else None
    upd = row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else ""
    return PackDraftDetail(
        bundle_id=str(row["id"]),
        pack_id=str(row["pack_id"]),
        slug=str(row["slug"]),
        name=str(row["name"]),
        version=str(row["version"]),
        description=str(row["description"] or manifest.get("description") or ""),
        author=str(row["author"] or manifest.get("author") or ""),
        maintainers=maintainers,
        license=str(manifest.get("license") or ""),
        bundle_kind=str(row["bundle_kind"]),
        scope_type=str(row["scope_type"]),
        scope_id=str(row["scope_id"]),
        status=str(row["status"]),
        source_origin=str(row["source_origin"]),
        archive_sha256=str(row["archive_sha256"] or "").strip(),
        cas_object_key=str(row["cas_object_key"]) if row["cas_object_key"] else None,
        declared_slots=slots,
        quick_actions=quick_actions,
        members=members,
        created_by_user_id=(str(row["created_by_user_id"]) if row["created_by_user_id"] else None),
        published_at_iso=pub,
        updated_at_iso=upd,
    )


async def fetch_bundle_row_conn(
    conn: AsyncConnection,
    draft_id: str,
    *,
    for_update: bool = False,
    instance: str | None = None,
) -> Any:
    """Fetch a single `declarative_pack_bundles` row by `id` or `pack_id`."""
    suffix = " FOR UPDATE" if for_update else ""
    row = (
        (
            await conn.execute(
                sa.text(
                    f"SELECT {BUNDLE_SELECT_COLS} FROM declarative_pack_bundles "
                    f"WHERE (id::text = :k OR pack_id = :k) LIMIT 1{suffix}"
                ),
                {"k": draft_id.strip()},
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise PackBundleNotFoundError(
            detail_override=f"Pack bundle {draft_id!r} was not found.",
            instance=instance,
        )
    return row


async def list_draft_packs_sql(
    engine: AsyncEngine,
    *,
    scope_type: PackScopeType | None = None,
    scope_id: str | None = None,
    status_filter: str | None = "DRAFT",
    unrestricted: bool = True,
    allowed_workspace_ids: frozenset[str] = frozenset(),
    allowed_org_ids: frozenset[str] = frozenset(),
    allow_global: bool = False,
) -> list[PackDraftDetail]:
    """List `CUSTOM` composer pack bundles filtered strictly by authorized scopes."""
    clauses = ["bundle_kind = 'CUSTOM'"]
    params: dict[str, Any] = {}
    if status_filter and status_filter.upper() != "ALL":
        clauses.append("status = :status")
        params["status"] = status_filter.upper()
    if scope_type is not None:
        clauses.append("scope_type = :scope_type")
        params["scope_type"] = scope_type.value
    if scope_id is not None:
        clauses.append("scope_id = :scope_id")
        params["scope_id"] = scope_id.strip()
    where_sql = " AND ".join(clauses)
    async with engine.connect() as conn:
        rows = (
            (
                await conn.execute(
                    sa.text(
                        f"SELECT {BUNDLE_SELECT_COLS} FROM declarative_pack_bundles "
                        f"WHERE {where_sql} ORDER BY updated_at DESC, slug ASC"
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        out: list[PackDraftDetail] = []
        for r in rows:
            if not unrestricted:
                st = str(r["scope_type"]).upper()
                sid = str(r["scope_id"])
                if st == "WORKSPACE" and sid not in allowed_workspace_ids:
                    continue
                if st in ("BU", "TEAM") and sid not in allowed_org_ids:
                    continue
                if st == "GLOBAL" and not allow_global:
                    continue
            members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=str(r["id"]))
            out.append(row_to_draft_detail(r, members))
        return out


async def get_draft_pack_sql(
    engine: AsyncEngine,
    draft_id: str,
    *,
    instance: str | None = None,
) -> PackDraftDetail:
    """Fetch a composer pack bundle + hydrated `pack_draft_memberships`."""
    async with engine.connect() as conn:
        row = await fetch_bundle_row_conn(conn, draft_id, instance=instance)
        members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=str(row["id"]))
        return row_to_draft_detail(row, members)


__all__ = [
    "BUNDLE_SELECT_COLS",
    "fetch_bundle_row_conn",
    "get_draft_pack_sql",
    "list_draft_packs_sql",
    "row_to_draft_detail",
]
