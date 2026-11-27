"""PostgreSQL 18 persistence adapter for `declarative_pack_bundles` (`Story 22.5`, `REM-14`).

Pure asynchronous SQL repository — zero cross-domain `orcia_core.packs` imports (`AD-19`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7


class DeclarativePackManifestLike(Protocol):
    """Structural protocol matching `DeclarativePackManifest` without `orcia_core.packs` import."""

    @property
    def id(self) -> str: ...
    @property
    def slug(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def rbac_namespace(self) -> str: ...
    def model_dump(self, *, mode: str = "json") -> dict[str, Any]: ...


class DeclarativePackBundleLike(Protocol):
    """Structural protocol matching `LoadedPackBundle` without `orcia_core.packs` import."""

    @property
    def manifest(self) -> DeclarativePackManifestLike: ...
    @property
    def bundle_sha256(self) -> str: ...
    @property
    def agents_markdown(self) -> Mapping[str, str]: ...
    @property
    def skills_markdown(self) -> Mapping[str, str]: ...
    @property
    def gates_specs(self) -> Mapping[str, Any]: ...
    @property
    def vsm_specs(self) -> Sequence[Any]: ...
    @property
    def workflows(self) -> Sequence[Any]: ...


@dataclass(frozen=True, slots=True)
class DeclarativePackBundleRecord:
    """Persisted row in PostgreSQL 18 `declarative_pack_bundles`."""

    id: str
    pack_id: str
    slug: str
    name: str
    version: str
    rbac_namespace: str
    bundle_sha256: str
    manifest_jsonb: dict[str, Any]
    loaded_at_iso: str


def _parse_json_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            return dict(decoded) if isinstance(decoded, dict) else {}
        except ValueError:
            return {}
    return {}


def _row_to_record(row: Any) -> DeclarativePackBundleRecord:
    ts = row[8]
    loaded_iso = (
        ts.isoformat().replace("+00:00", "Z") if isinstance(ts, datetime) else str(ts or "")
    )
    return DeclarativePackBundleRecord(
        id=str(row[0]),
        pack_id=str(row[1]),
        slug=str(row[2]),
        name=str(row[3]),
        version=str(row[4]),
        rbac_namespace=str(row[5]),
        bundle_sha256=str(row[6]).strip(),
        manifest_jsonb=_parse_json_dict(row[7]),
        loaded_at_iso=loaded_iso,
    )


def _serialize_bundle_manifest_json(bundle: DeclarativePackBundleLike) -> str:
    payload = bundle.manifest.model_dump(mode="json")
    payload["counts"] = {
        "agents": len(bundle.agents_markdown),
        "skills": len(bundle.skills_markdown),
        "gates": len(bundle.gates_specs),
        "vsm": len(bundle.vsm_specs),
        "workflows": len(bundle.workflows),
    }
    payload["agents_slugs"] = sorted(bundle.agents_markdown.keys())
    payload["skills_slugs"] = sorted(bundle.skills_markdown.keys())
    payload["gates_slugs"] = sorted(bundle.gates_specs.keys())
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


_COLS = (
    "id::text, pack_id, slug, name, version, rbac_namespace, "
    "bundle_sha256, manifest_jsonb, loaded_at"
)


async def upsert_declarative_pack_bundles_sql(
    engine: AsyncEngine,
    bundles: Mapping[str, DeclarativePackBundleLike] | Sequence[DeclarativePackBundleLike],
) -> list[DeclarativePackBundleRecord]:
    """Idempotently upsert declarative packs into PostgreSQL 18 `declarative_pack_bundles`."""
    bundle_list = list(bundles.values()) if isinstance(bundles, Mapping) else list(bundles)
    if not bundle_list:
        return []
    records: list[DeclarativePackBundleRecord] = []
    async with engine.begin() as conn:
        exists = (
            await conn.execute(sa.text("SELECT to_regclass('public.declarative_pack_bundles')"))
        ).scalar()
        if exists is None:
            return []
        has_v2_cols = bool(
            (
                await conn.execute(
                    sa.text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'declarative_pack_bundles' "
                        "AND column_name = 'archive_sha256')"
                    )
                )
            ).scalar()
        )
        for bundle in bundle_list:
            m = bundle.manifest
            sha256_val = str(bundle.bundle_sha256).strip()[:64].ljust(64, "0")
            insert_sql = (
                f"""
                INSERT INTO declarative_pack_bundles (
                    id, pack_id, slug, name, version, rbac_namespace,
                    bundle_sha256, archive_sha256, manifest_jsonb, description,
                    bundle_kind, scope_type, scope_id, source_origin, status,
                    published_at, loaded_at, updated_at
                )
                VALUES (
                    CAST(:id AS uuid), :pack_id, :slug, :name, :version,
                    :rbac_namespace, :bundle_sha256, :bundle_sha256,
                    CAST(:manifest_jsonb AS jsonb), :description,
                    'SYSTEM', 'GLOBAL', 'global', 'LOCAL_SYSTEM', 'PUBLISHED',
                    NOW(), NOW(), NOW()
                )
                ON CONFLICT (scope_type, scope_id, slug, version) DO UPDATE SET
                    pack_id = EXCLUDED.pack_id, name = EXCLUDED.name,
                    rbac_namespace = EXCLUDED.rbac_namespace,
                    bundle_sha256 = EXCLUDED.bundle_sha256,
                    archive_sha256 = EXCLUDED.archive_sha256,
                    manifest_jsonb = EXCLUDED.manifest_jsonb,
                    description = EXCLUDED.description,
                    bundle_kind = 'SYSTEM', source_origin = 'LOCAL_SYSTEM',
                    status = 'PUBLISHED',
                    published_at = COALESCE(declarative_pack_bundles.published_at, NOW()),
                    loaded_at = NOW(), updated_at = NOW()
                RETURNING {_COLS}
                """
                if has_v2_cols
                else f"""
                INSERT INTO declarative_pack_bundles (
                    id, pack_id, slug, name, version, rbac_namespace,
                    bundle_sha256, manifest_jsonb, loaded_at
                )
                VALUES (
                    CAST(:id AS uuid), :pack_id, :slug, :name, :version,
                    :rbac_namespace, :bundle_sha256, CAST(:manifest_jsonb AS jsonb), NOW()
                )
                ON CONFLICT (pack_id) DO UPDATE SET
                    slug = EXCLUDED.slug, name = EXCLUDED.name,
                    version = EXCLUDED.version, rbac_namespace = EXCLUDED.rbac_namespace,
                    bundle_sha256 = EXCLUDED.bundle_sha256,
                    manifest_jsonb = EXCLUDED.manifest_jsonb, loaded_at = NOW()
                RETURNING {_COLS}
                """
            )
            params: dict[str, Any] = {
                "id": str(uuid7()),
                "pack_id": m.id[:128],
                "slug": m.slug[:128],
                "name": m.name[:255],
                "version": m.version[:64],
                "rbac_namespace": m.rbac_namespace[:64],
                "bundle_sha256": sha256_val,
                "manifest_jsonb": _serialize_bundle_manifest_json(bundle),
            }
            if has_v2_cols:
                params["description"] = m.description
            row = (await conn.execute(sa.text(insert_sql), params)).fetchone()
            if row is not None:
                records.append(_row_to_record(row))
    return records


async def list_declarative_pack_bundles_sql(
    engine: AsyncEngine,
) -> list[DeclarativePackBundleRecord]:
    """List persisted declarative pack bundles ordered by `slug`."""
    async with engine.connect() as conn:
        exists = (
            await conn.execute(sa.text("SELECT to_regclass('public.declarative_pack_bundles')"))
        ).scalar()
        if exists is None:
            return []
        rows = (
            await conn.execute(
                sa.text(f"SELECT {_COLS} FROM declarative_pack_bundles ORDER BY slug ASC")
            )
        ).fetchall()
    return [_row_to_record(row) for row in rows]


async def get_declarative_pack_bundle_sql(
    engine: AsyncEngine,
    pack_id_or_slug: str,
) -> DeclarativePackBundleRecord | None:
    """Fetch a single persisted declarative pack bundle by `pack_id` or `slug`."""
    clean_key = pack_id_or_slug.strip()
    if not clean_key:
        return None
    async with engine.connect() as conn:
        exists = (
            await conn.execute(sa.text("SELECT to_regclass('public.declarative_pack_bundles')"))
        ).scalar()
        if exists is None:
            return None
        row = (
            await conn.execute(
                sa.text(
                    f"SELECT {_COLS} FROM declarative_pack_bundles "
                    "WHERE pack_id = :key OR slug = :key LIMIT 1"
                ),
                {"key": clean_key},
            )
        ).fetchone()
    return _row_to_record(row) if row is not None else None


__all__ = [
    "DeclarativePackBundleLike",
    "DeclarativePackBundleRecord",
    "DeclarativePackManifestLike",
    "get_declarative_pack_bundle_sql",
    "list_declarative_pack_bundles_sql",
    "upsert_declarative_pack_bundles_sql",
]
