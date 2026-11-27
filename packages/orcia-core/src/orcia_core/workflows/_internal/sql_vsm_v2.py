"""PostgreSQL 18 `AsyncSession` store & idempotent seeder for `vsm_definitions_v2` (`Story 24.1`).

Persists Value Stream Map specifications (`ValueStreamMapSpec`) loaded from declarative packs
and runtime updates into PostgreSQL 18 `vsm_definitions_v2`, guaranteeing cold `F5` reload
without relying on YAML-only in-memory dictionaries (`ARCH24-02`, `20#1 #48`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.workflows.schemas_v2 import ValueStreamMapSpec

logger = get_logger("orcia.workflows.sql_vsm_v2")


def _extract_vsm_specs_from_bundles(
    bundles: Mapping[str, Any] | Sequence[Any],
) -> list[ValueStreamMapSpec]:
    items = list(bundles.values()) if isinstance(bundles, Mapping) else list(bundles)
    specs: list[ValueStreamMapSpec] = []
    for item in items:
        if isinstance(item, ValueStreamMapSpec):
            specs.append(item)
            continue
        vsm_list = getattr(item, "vsm_specs", None)
        if vsm_list:
            for vsm in vsm_list:
                if isinstance(vsm, ValueStreamMapSpec):
                    specs.append(vsm)
                else:
                    specs.append(ValueStreamMapSpec.model_validate(vsm))
    return specs


class SqlVsmDefinitionsV2Store:
    """PostgreSQL 18 repository (`AsyncSession`) for `vsm_definitions_v2`."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        *,
        strict_sql: bool = False,
    ) -> None:
        self._session_maker = session_maker
        self._strict_sql = strict_sql
        self._memory_fallback: dict[str, dict[str, Any]] = {}

    async def upsert_vsm(self, vsm: ValueStreamMapSpec) -> ValueStreamMapSpec:
        """Persist `vsm` idempotently into `vsm_definitions_v2` keyed by `vsm_id`."""
        res = await self.upsert_many_vsm([vsm])
        return res[0] if res else vsm

    async def upsert_many_vsm(
        self,
        vsm_specs: Sequence[ValueStreamMapSpec],
    ) -> list[ValueStreamMapSpec]:
        """Idempotently upsert `ValueStreamMapSpec` definitions into `vsm_definitions_v2`."""
        specs = list(vsm_specs)
        if not specs:
            return []
        if not self._strict_sql:
            for spec in specs:
                self._memory_fallback[spec.id] = spec.model_dump(mode="json")
        if self._session_maker is None:
            if self._strict_sql:
                raise RuntimeError(
                    "SqlVsmDefinitionsV2Store requires session_maker when strict_sql=True."
                )
            return specs

        delete_slug_stmt = sa.text(
            "DELETE FROM vsm_definitions_v2 "
            "WHERE slug = :slug AND vsm_id <> :vsm_id AND pack_bundle_id IS NULL"
        )
        upsert_stmt = sa.text(
            """
            INSERT INTO vsm_definitions_v2 (
                id,
                vsm_id,
                slug,
                pack_id,
                title,
                spec_jsonb,
                updated_at
            )
            VALUES (
                CAST(:id AS UUID),
                :vsm_id,
                :slug,
                :pack_id,
                :title,
                CAST(:spec_jsonb AS JSONB),
                NOW()
            )
            ON CONFLICT (vsm_id) WHERE pack_bundle_id IS NULL DO UPDATE SET
                slug = EXCLUDED.slug,
                pack_id = EXCLUDED.pack_id,
                title = EXCLUDED.title,
                spec_jsonb = EXCLUDED.spec_jsonb,
                updated_at = NOW()
            """
        )
        try:
            async with self._session_maker() as session:
                exists = (
                    await session.execute(
                        sa.text("SELECT to_regclass('public.vsm_definitions_v2')")
                    )
                ).scalar()
                if exists is None:
                    if self._strict_sql:
                        raise RuntimeError("Table 'vsm_definitions_v2' does not exist in PG18.")
                    return specs
                for spec in specs:
                    payload = spec.model_dump(mode="json")
                    await session.execute(
                        delete_slug_stmt,
                        {"slug": spec.slug[:128], "vsm_id": spec.id[:128]},
                    )
                    await session.execute(
                        upsert_stmt,
                        {
                            "id": new_uuid7_str(),
                            "vsm_id": spec.id[:128],
                            "slug": spec.slug[:128],
                            "pack_id": spec.pack_id[:128],
                            "title": spec.title[:255],
                            "spec_jsonb": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        },
                    )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "vsm_v2_sql_upsert_failed",
                count=len(specs),
                error_type=type(exc).__name__,
            )
            if self._strict_sql:
                raise
        return specs

    async def list_vsm(self) -> list[ValueStreamMapSpec]:
        """List all persisted `ValueStreamMapSpec` definitions from `vsm_definitions_v2`."""
        if self._session_maker is None:
            if self._strict_sql:
                raise RuntimeError(
                    "SqlVsmDefinitionsV2Store requires session_maker when strict_sql=True."
                )
            return [
                ValueStreamMapSpec.model_validate(item) for item in self._memory_fallback.values()
            ]

        stmt = sa.text(
            """
            SELECT spec_jsonb
            FROM vsm_definitions_v2
            ORDER BY updated_at ASC, vsm_id ASC
            """
        )
        try:
            async with self._session_maker() as session:
                rows = (await session.execute(stmt)).fetchall()
            results: list[ValueStreamMapSpec] = []
            for row in rows:
                raw = row[0]
                data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                results.append(ValueStreamMapSpec.model_validate(data))
            return results
        except Exception as exc:
            logger.warning(
                "vsm_v2_sql_list_failed",
                error_type=type(exc).__name__,
            )
            if self._strict_sql:
                raise
            return [
                ValueStreamMapSpec.model_validate(item) for item in self._memory_fallback.values()
            ]

    async def get_vsm(self, vsm_id_or_slug: str) -> ValueStreamMapSpec | None:
        """Fetch one `ValueStreamMapSpec` by `vsm_id` or `slug` from `vsm_definitions_v2`."""
        clean_key = vsm_id_or_slug.strip()
        if not clean_key:
            return None
        if self._session_maker is None:
            if self._strict_sql:
                raise RuntimeError(
                    "SqlVsmDefinitionsV2Store requires session_maker when strict_sql=True."
                )
            for item in self._memory_fallback.values():
                if item.get("id") == clean_key or item.get("slug") == clean_key:
                    return ValueStreamMapSpec.model_validate(item)
            return None

        stmt = sa.text(
            """
            SELECT spec_jsonb
            FROM vsm_definitions_v2
            WHERE vsm_id = :key OR slug = :key
            LIMIT 1
            """
        )
        try:
            async with self._session_maker() as session:
                row = (await session.execute(stmt, {"key": clean_key})).first()
            if row is None:
                return None
            raw = row[0]
            data = json.loads(raw) if isinstance(raw, str) else dict(raw)
            return ValueStreamMapSpec.model_validate(data)
        except Exception as exc:
            logger.warning(
                "vsm_v2_sql_get_failed",
                vsm_key=clean_key,
                error_type=type(exc).__name__,
            )
            if self._strict_sql:
                raise
            for item in self._memory_fallback.values():
                if item.get("id") == clean_key or item.get("slug") == clean_key:
                    return ValueStreamMapSpec.model_validate(item)
            return None


async def upsert_vsm_definitions_v2_sql(
    engine: AsyncEngine,
    bundles: Mapping[str, Any] | Sequence[Any],
) -> list[ValueStreamMapSpec]:
    """Idempotently seed pack `ValueStreamMapSpec` items into PG18 `vsm_definitions_v2`."""
    if not hasattr(engine, "connect"):
        return []
    specs = _extract_vsm_specs_from_bundles(bundles)
    if not specs:
        return []
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as check_session:
        exists = (
            await check_session.execute(sa.text("SELECT to_regclass('public.vsm_definitions_v2')"))
        ).scalar()
        if exists is None:
            return []
    store = SqlVsmDefinitionsV2Store(session_maker=maker, strict_sql=True)
    return await store.upsert_many_vsm(specs)
