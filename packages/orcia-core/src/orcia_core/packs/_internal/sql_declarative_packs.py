"""PostgreSQL 18 v2 persistence adapter for `declarative_pack_bundles` (`Story 31.1`)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_lifecycle import (
    delete_pack_bundle_sql,
    list_pack_dna_mechanisms_sql,
    upsert_pack_dna_mechanisms_sql,
)
from orcia_core.packs.models import (
    LoadedPackBundleV2,
    PackBundleStatus,
    PackDnaMechanismSpec,
    PackManifestV2,
    PackScopeType,
)

_SELECT_V2_COLS = (
    "id::text, pack_id, slug, name, version, rbac_namespace, bundle_sha256, "
    "bundle_kind, scope_type, scope_id, status, archive_sha256, cas_object_key, "
    "source_origin, declared_slots_jsonb, author, description, published_at, "
    "created_by_user_id::text, loaded_at, updated_at"
)


def _row_to_v2_dict(row: Any) -> dict[str, object]:
    slots_raw = row[14]
    slots: list[Any]
    if isinstance(slots_raw, list):
        slots = slots_raw
    elif isinstance(slots_raw, str):
        try:
            decoded = json.loads(slots_raw)
            slots = decoded if isinstance(decoded, list) else []
        except ValueError:
            slots = []
    else:
        slots = []
    return {
        "id": str(row[0]),
        "pack_id": str(row[1]),
        "slug": str(row[2]),
        "name": str(row[3]),
        "version": str(row[4]),
        "rbac_namespace": str(row[5]),
        "bundle_sha256": str(row[6]).strip(),
        "bundle_kind": str(row[7]),
        "scope_type": str(row[8]),
        "scope_id": str(row[9]),
        "status": str(row[10]),
        "archive_sha256": str(row[11]).strip(),
        "cas_object_key": str(row[12]) if row[12] is not None else None,
        "source_origin": str(row[13]),
        "declared_slots": slots,
        "author": str(row[15]) if row[15] is not None else None,
        "description": str(row[16]) if row[16] is not None else None,
        "published_at": row[17].isoformat() if hasattr(row[17], "isoformat") else row[17],
        "created_by_user_id": str(row[18]) if row[18] is not None else None,
        "loaded_at": row[19].isoformat() if hasattr(row[19], "isoformat") else str(row[19] or ""),
        "updated_at": row[20].isoformat() if hasattr(row[20], "isoformat") else str(row[20] or ""),
    }


class SqlPackBundleV2Repository:
    """PostgreSQL 18 repository implementing `PackBundleRepositoryPort` for v2 packs."""

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self._engine = engine

    def set_engine(self, engine: AsyncEngine) -> None:
        self._engine = engine

    def _require_engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("SqlPackBundleV2Repository requires a configured PG18 AsyncEngine.")
        return self._engine

    async def upsert_bundle_v2(
        self,
        bundle: LoadedPackBundleV2,
        *,
        cas_object_key: str | None = None,
    ) -> PackManifestV2:
        """Idempotently persist a validated v2 bundle into `declarative_pack_bundles`."""
        engine = self._require_engine()
        m = bundle.manifest
        pack_id = (m.id or f"orcia-pack-{m.slug}")[:128]
        manifest_json = json.dumps(
            {
                **m.model_dump(mode="json"),
                "counts": {
                    "agents": len(bundle.agents),
                    "skills": len(bundle.skills),
                    "instructions": len(bundle.instructions),
                    "vsm": len(bundle.vsm_specs),
                    "workflows": len(bundle.workflows),
                    "dna_mechanisms": len(bundle.dna_mechanisms),
                    "gates": len(bundle.gates_specs),
                    "policies": len(bundle.policies),
                    "help_articles": len(bundle.help_articles),
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        slots_json = json.dumps(
            [slot.model_dump(mode="json") for slot in m.declared_slots],
            ensure_ascii=False,
            sort_keys=True,
        )
        sha_val = bundle.archive_sha256.strip()[:64].ljust(64, "0")
        is_pub = m.status == PackBundleStatus.PUBLISHED
        async with engine.begin() as conn:
            persisted_id = (
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO declarative_pack_bundles (
                            id, pack_id, slug, name, version, rbac_namespace,
                            bundle_sha256, manifest_jsonb, bundle_kind, scope_type, scope_id,
                            status, archive_sha256, cas_object_key, manifest_yaml, source_origin,
                            declared_slots_jsonb, author, description, published_at,
                            created_by_user_id, loaded_at, updated_at
                        )
                        VALUES (
                            CAST(:id AS uuid), :pack_id, :slug, :name, :version, :rbac_namespace,
                            :bundle_sha256, CAST(:manifest_jsonb AS jsonb), :bundle_kind,
                            :scope_type, :scope_id, :status, :archive_sha256, :cas_object_key,
                            :manifest_yaml, :source_origin, CAST(:declared_slots_jsonb AS jsonb),
                            :author, :description, CASE WHEN :is_pub THEN NOW() ELSE NULL END,
                            CAST(:created_by_user_id AS uuid), NOW(), NOW()
                        )
                        ON CONFLICT (scope_type, scope_id, slug, version) DO UPDATE SET
                            pack_id = EXCLUDED.pack_id,
                            name = EXCLUDED.name,
                            rbac_namespace = EXCLUDED.rbac_namespace,
                            bundle_sha256 = EXCLUDED.bundle_sha256,
                            manifest_jsonb = EXCLUDED.manifest_jsonb,
                            bundle_kind = EXCLUDED.bundle_kind,
                            status = EXCLUDED.status,
                            archive_sha256 = EXCLUDED.archive_sha256,
                            cas_object_key = COALESCE(
                                EXCLUDED.cas_object_key,
                                declarative_pack_bundles.cas_object_key
                            ),
                            manifest_yaml = EXCLUDED.manifest_yaml,
                            source_origin = EXCLUDED.source_origin,
                            declared_slots_jsonb = EXCLUDED.declared_slots_jsonb,
                            author = EXCLUDED.author,
                            description = EXCLUDED.description,
                            published_at = COALESCE(
                                declarative_pack_bundles.published_at,
                                EXCLUDED.published_at
                            ),
                            updated_at = NOW()
                        RETURNING id::text
                        """
                    ),
                    {
                        "id": str(uuid7()),
                        "pack_id": pack_id,
                        "slug": m.slug[:128],
                        "name": m.name[:255],
                        "version": m.version[:64],
                        "rbac_namespace": m.rbac_namespace[:64],
                        "bundle_sha256": sha_val,
                        "manifest_jsonb": manifest_json,
                        "bundle_kind": m.bundle_kind.value,
                        "scope_type": m.scope_type.value,
                        "scope_id": m.scope_id,
                        "status": m.status.value,
                        "archive_sha256": sha_val,
                        "cas_object_key": cas_object_key,
                        "manifest_yaml": bundle.manifest_yaml,
                        "source_origin": m.source_origin.value,
                        "declared_slots_jsonb": slots_json,
                        "author": m.author or None,
                        "description": m.description or None,
                        "is_pub": is_pub,
                        "created_by_user_id": m.created_by_user_id,
                    },
                )
            ).scalar_one()
        if bundle.dna_mechanisms:
            await self.upsert_dna_mechanisms(
                pack_bundle_id=str(persisted_id), mechanisms=bundle.dna_mechanisms
            )
        return m.model_copy(update={"id": pack_id})

    async def list_bundles_v2(
        self,
        *,
        scope_type: PackScopeType | None = None,
        scope_id: str | None = None,
    ) -> list[dict[str, object]]:
        """List v2 bundle metadata rows optionally filtered by scope."""
        engine = self._require_engine()
        clauses = []
        params: dict[str, Any] = {}
        if scope_type is not None:
            clauses.append("scope_type = :scope_type")
            params["scope_type"] = scope_type.value
        if scope_id is not None:
            clauses.append("scope_id = :scope_id")
            params["scope_id"] = scope_id
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    sa.text(
                        f"SELECT {_SELECT_V2_COLS} FROM declarative_pack_bundles "
                        f"{where_sql} ORDER BY slug ASC, version DESC"
                    ),
                    params,
                )
            ).fetchall()
        return [_row_to_v2_dict(r) for r in rows]

    async def get_bundle_v2(self, bundle_id_or_slug: str) -> dict[str, object] | None:
        """Fetch a v2 bundle metadata row by UUID `id`, `pack_id`, or `slug`."""
        engine = self._require_engine()
        clean = bundle_id_or_slug.strip()
        if not clean:
            return None
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"SELECT {_SELECT_V2_COLS} FROM declarative_pack_bundles "
                        "WHERE id::text = :key OR pack_id = :key OR slug = :key "
                        "ORDER BY updated_at DESC LIMIT 1"
                    ),
                    {"key": clean},
                )
            ).fetchone()
        return _row_to_v2_dict(row) if row is not None else None

    async def upsert_dna_mechanisms(
        self, *, pack_bundle_id: str, mechanisms: Sequence[PackDnaMechanismSpec]
    ) -> None:
        """Persist `pack_dna_mechanisms` including test payloads."""
        await upsert_pack_dna_mechanisms_sql(
            self._require_engine(), pack_bundle_id=pack_bundle_id, mechanisms=mechanisms
        )

    async def list_dna_mechanisms(self, *, pack_bundle_id: str) -> list[PackDnaMechanismSpec]:
        """List `pack_dna_mechanisms` for `pack_bundle_id`."""
        return await list_pack_dna_mechanisms_sql(
            self._require_engine(), pack_bundle_id=pack_bundle_id
        )

    async def delete_bundle(self, bundle_id: str) -> None:
        """Safely delete a pack bundle verifying active runs and cross-draft references."""
        await delete_pack_bundle_sql(self._require_engine(), bundle_id=bundle_id)


__all__ = ["SqlPackBundleV2Repository"]
