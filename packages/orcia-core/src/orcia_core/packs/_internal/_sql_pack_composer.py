"""PostgreSQL 18 create/update mutations for Pack Composer (`Story 31.5`, `<= 195 L`)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_composer_hydration import (
    decode_json_dict,
    load_draft_members_hydrated_conn,
)
from orcia_core.packs._internal._sql_pack_composer_reads import (
    BUNDLE_SELECT_COLS,
    fetch_bundle_row_conn,
    row_to_draft_detail,
)
from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
)
from orcia_core.packs.composer_models import PackDraftDetail
from orcia_core.packs.errors import (
    PackScopeEscalationForbiddenError,
    PackVersionConflictError,
)
from orcia_core.packs.models import PackQuickActionSpec, PackScopeType, PackSlotSpec


async def create_draft_pack_sql(
    engine: AsyncEngine,
    *,
    slug: str,
    name: str,
    version: str,
    description: str,
    author: str,
    maintainers: Sequence[str],
    license_name: str,
    scope_type: PackScopeType,
    scope_id: str,
    declared_slots: Sequence[PackSlotSpec],
    quick_actions: Sequence[PackQuickActionSpec],
    actor_id: str,
    actor_email: str | None,
    trace_id: str | None,
    instance: str | None = None,
) -> PackDraftDetail:
    """Create a `CUSTOM` `DRAFT` bundle in `declarative_pack_bundles`."""
    if scope_type == PackScopeType.GLOBAL:
        raise PackScopeEscalationForbiddenError(
            detail_override="Composer drafts cannot target GLOBAL scope.",
            instance=instance,
        )
    clean_slug = slug.strip().lower()[:128]
    clean_ver = version.strip()[:64]
    pack_id = f"orcia-pack-{clean_slug}"[:128]
    manifest_dict = {
        "id": pack_id,
        "slug": clean_slug,
        "name": name.strip(),
        "version": clean_ver,
        "description": description,
        "author": author,
        "maintainers": list(maintainers),
        "license": license_name,
        "bundle_kind": "CUSTOM",
        "scope_type": scope_type.value,
        "scope_id": scope_id.strip(),
        "status": "DRAFT",
        "quick_actions": [q.model_dump(mode="json") for q in quick_actions],
    }
    manifest_json = json.dumps(manifest_dict, ensure_ascii=False, sort_keys=True)
    slots_json = json.dumps(
        [s.model_dump(mode="json") for s in declared_slots], ensure_ascii=False, sort_keys=True
    )
    sha = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    bundle_id = str(uuid7())
    created_by = actor_id if len(actor_id) == 36 and "-" in actor_id else None

    async with engine.begin() as conn:
        exists = (
            await conn.execute(
                sa.text(
                    "SELECT 1 FROM declarative_pack_bundles "
                    "WHERE scope_type = :st AND scope_id = :sid AND slug = :slug AND version = :v"
                ),
                {
                    "st": scope_type.value,
                    "sid": scope_id.strip(),
                    "slug": clean_slug,
                    "v": clean_ver,
                },
            )
        ).scalar()
        if exists is not None:
            raise PackVersionConflictError(
                detail_override=(
                    f"Draft/pack {clean_slug!r}@{clean_ver!r} already exists in {scope_id!r}."
                ),
                instance=instance,
            )
        row = (
            (
                await conn.execute(
                    sa.text(
                        f"""
                        INSERT INTO declarative_pack_bundles (
                            id, pack_id, slug, name, version, rbac_namespace,
                            bundle_sha256, manifest_jsonb, bundle_kind, scope_type, scope_id,
                            status, archive_sha256, source_origin, declared_slots_jsonb,
                            author, description, created_by_user_id, loaded_at, updated_at
                        )
                        VALUES (
                            CAST(:id AS uuid), :pack_id, :slug, :name, :version, :rbac,
                            :sha, CAST(:mjson AS jsonb), 'CUSTOM', :st, :sid,
                            'DRAFT', :sha, 'ORCIA_COMPOSER', CAST(:slots AS jsonb),
                            :author, :desc, CAST(:creator AS uuid), NOW(), NOW()
                        )
                        RETURNING {BUNDLE_SELECT_COLS}
                        """
                    ),
                    {
                        "id": bundle_id,
                        "pack_id": pack_id,
                        "slug": clean_slug,
                        "name": name.strip()[:255],
                        "version": clean_ver,
                        "rbac": clean_slug[:64],
                        "sha": sha,
                        "mjson": manifest_json,
                        "st": scope_type.value,
                        "sid": scope_id.strip(),
                        "slots": slots_json,
                        "author": author or None,
                        "desc": description or None,
                        "creator": created_by,
                    },
                )
            )
            .mappings()
            .one()
        )
        await append_pack_audit_event(
            conn,
            event_type="PACK_DRAFT_CREATED",
            summary=f"Created CUSTOM DRAFT pack {clean_slug}@{clean_ver}",
            scope_path=f"{scope_type.value}:{scope_id.strip()}",
            actor_id=actor_id,
            actor_email=actor_email,
            metadata={"bundle_id": bundle_id, "slug": clean_slug, "version": clean_ver},
            trace_id=trace_id,
        )
    return row_to_draft_detail(row, [])


async def update_draft_pack_sql(
    engine: AsyncEngine,
    draft_id: str,
    *,
    name: str | None = None,
    version: str | None = None,
    description: str | None = None,
    author: str | None = None,
    maintainers: Sequence[str] | None = None,
    license_name: str | None = None,
    declared_slots: Sequence[PackSlotSpec] | None = None,
    quick_actions: Sequence[PackQuickActionSpec] | None = None,
    instance: str | None = None,
) -> PackDraftDetail:
    """Update metadata on a mutable `CUSTOM` `DRAFT` pack bundle."""
    async with engine.begin() as conn:
        row = await fetch_bundle_row_conn(conn, draft_id, for_update=True, instance=instance)
        if str(row["bundle_kind"]) != "CUSTOM" or str(row["status"]) != "DRAFT":
            raise PackVersionConflictError(
                detail_override="Only CUSTOM DRAFT packs can be modified in the Composer.",
                instance=instance,
            )
        manifest = decode_json_dict(row["manifest_jsonb"])
        new_name = name.strip() if name is not None else str(row["name"])
        new_ver = version.strip() if version is not None else str(row["version"])
        new_desc = description if description is not None else str(row["description"] or "")
        new_author = author if author is not None else str(row["author"] or "")
        if maintainers is not None:
            manifest["maintainers"] = list(maintainers)
        if license_name is not None:
            manifest["license"] = license_name
        if quick_actions is not None:
            manifest["quick_actions"] = [q.model_dump(mode="json") for q in quick_actions]
        manifest.update(
            {"name": new_name, "version": new_ver, "description": new_desc, "author": new_author}
        )
        slots_json = (
            json.dumps([s.model_dump(mode="json") for s in declared_slots], sort_keys=True)
            if declared_slots is not None
            else json.dumps(row["declared_slots_jsonb"] or [], sort_keys=True)
        )
        updated = (
            (
                await conn.execute(
                    sa.text(
                        f"UPDATE declarative_pack_bundles SET name = :n, version = :v, "
                        f"description = :d, author = :a, manifest_jsonb = CAST(:mj AS jsonb), "
                        f"declared_slots_jsonb = CAST(:sj AS jsonb), updated_at = NOW() "
                        f"WHERE id = CAST(:bid AS uuid) RETURNING {BUNDLE_SELECT_COLS}"
                    ),
                    {
                        "bid": str(row["id"]),
                        "n": new_name[:255],
                        "v": new_ver[:64],
                        "d": new_desc or None,
                        "a": new_author or None,
                        "mj": json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                        "sj": slots_json,
                    },
                )
            )
            .mappings()
            .one()
        )
        members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=str(row["id"]))
        return row_to_draft_detail(updated, members)


__all__ = ["create_draft_pack_sql", "update_draft_pack_sql"]
