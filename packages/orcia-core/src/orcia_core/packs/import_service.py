"""Transactional `PackImportService` facade (`Story 31.2`, `<= 300 L`)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs._internal._sql_pack_delete_tx import delete_bundle_transactional
from orcia_core.packs._internal._sql_pack_import_tx import import_bundle_transactional
from orcia_core.packs._internal.apm_codec import ApmPackCodec
from orcia_core.packs._internal.sql_declarative_packs import SqlPackBundleV2Repository
from orcia_core.packs.errors import PackScopeEscalationForbiddenError
from orcia_core.packs.models import (
    LoadedPackBundleV2,
    PackBundleKind,
    PackScopeType,
    PackSourceOrigin,
)
from orcia_core.packs.ports import PackCasStoragePort


@dataclass(frozen=True, slots=True)
class PackImportOutcome:
    """Result of an atomic `PackImportService` import execution."""

    bundle_id: str
    pack_id: str
    slug: str
    name: str
    version: str
    bundle_kind: str
    scope_type: str
    scope_id: str
    status: str
    archive_sha256: str
    cas_object_key: str | None
    idempotent_noop: bool
    counts: dict[str, int]


class PackImportService:
    """Orchestrates APM validation, SeaweedFS CAS upload, and PG18 bundle materialization."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None = None,
        cas_storage: PackCasStoragePort | None = None,
        codec: ApmPackCodec | None = None,
        bundle_repository: SqlPackBundleV2Repository | None = None,
    ) -> None:
        self._engine = engine
        self._cas_storage = cas_storage
        self._codec = codec or ApmPackCodec()
        self._repo = bundle_repository or SqlPackBundleV2Repository(engine)

    def set_engine(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._repo.set_engine(engine)

    def set_cas_storage(self, cas_storage: PackCasStoragePort | None) -> None:
        self._cas_storage = cas_storage

    def _require_engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("PackImportService requires a configured PG18 AsyncEngine.")
        return self._engine

    async def import_zip_bytes(
        self,
        zip_bytes: bytes,
        *,
        scope_type: PackScopeType | None = None,
        scope_id: str | None = None,
        replace_draft: bool = False,
        allow_system_kind: bool = False,
        record_audit: bool = True,
        actor_id: str = "system",
        actor_email: str | None = None,
        trace_id: str | None = None,
    ) -> PackImportOutcome:
        """Validate `.zip` archive, persist CAS blob, and materialize entities in PG18."""
        bundle = self._codec.decode_zip_bytes(
            zip_bytes,
            source_origin=PackSourceOrigin.APM_ZIP,
            allow_system_kind=allow_system_kind,
        )
        effective = self._apply_scope_overrides(
            bundle,
            scope_type=scope_type,
            scope_id=scope_id,
            allow_system_kind=allow_system_kind,
        )
        canonical_zip = self._codec.encode_zip_bytes(effective)
        return await self._persist_bundle(
            effective,
            archive_bytes=canonical_zip,
            replace_draft=replace_draft,
            allow_system_kind=allow_system_kind,
            record_audit=record_audit,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
        )

    async def import_directory(
        self,
        pack_dir: Path,
        *,
        bundle_kind: PackBundleKind = PackBundleKind.SYSTEM,
        scope_type: PackScopeType = PackScopeType.GLOBAL,
        scope_id: str = "global",
        allow_system_kind: bool = True,
        record_audit: bool = False,
        actor_id: str = "system",
        trace_id: str | None = None,
    ) -> PackImportOutcome:
        """Import an on-disk pack directory (Day-0 bootstrap/reset seed path)."""
        bundle = self._codec.decode_directory(pack_dir, source_origin=PackSourceOrigin.LOCAL_SYSTEM)
        updated_manifest = bundle.manifest.model_copy(
            update={
                "bundle_kind": bundle_kind,
                "scope_type": scope_type,
                "scope_id": scope_id,
            }
        )
        effective = bundle.model_copy(update={"manifest": updated_manifest})
        canonical_zip = self._codec.encode_zip_bytes(effective)
        return await self._persist_bundle(
            effective,
            archive_bytes=canonical_zip,
            replace_draft=False,
            allow_system_kind=allow_system_kind,
            record_audit=record_audit,
            actor_id=actor_id,
            actor_email=None,
            trace_id=trace_id,
        )

    async def delete_bundle(
        self,
        bundle_id_or_pack_id: str,
        *,
        allow_system_delete: bool = False,
        record_audit: bool = True,
        actor_id: str = "system",
        actor_email: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, str]:
        """Safely delete an unused non-SYSTEM pack bundle (`403`/`409` guarded)."""
        return await delete_bundle_transactional(
            self._require_engine(),
            bundle_id_or_pack_id=bundle_id_or_pack_id,
            allow_system_delete=allow_system_delete,
            record_audit=record_audit,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
        )

    async def list_bundles(
        self,
        *,
        scope_type: PackScopeType | None = None,
        scope_id: str | None = None,
    ) -> list[dict[str, object]]:
        """List v2 pack bundles from PostgreSQL 18."""
        return await self._repo.list_bundles_v2(scope_type=scope_type, scope_id=scope_id)

    async def get_bundle(self, bundle_id_or_slug: str) -> dict[str, object] | None:
        """Fetch a single v2 pack bundle from PostgreSQL 18."""
        return await self._repo.get_bundle_v2(bundle_id_or_slug)

    def _apply_scope_overrides(
        self,
        bundle: LoadedPackBundleV2,
        *,
        scope_type: PackScopeType | None,
        scope_id: str | None,
        allow_system_kind: bool,
    ) -> LoadedPackBundleV2:
        m = bundle.manifest
        next_scope = scope_type or m.scope_type
        next_scope_id = (scope_id or m.scope_id).strip() or "global"
        if not allow_system_kind and (
            m.bundle_kind == PackBundleKind.SYSTEM or next_scope == PackScopeType.GLOBAL
        ):
            raise PackScopeEscalationForbiddenError(
                detail_override=(
                    "User API imports cannot target SYSTEM bundle_kind or GLOBAL scope_type."
                )
            )
        if next_scope == m.scope_type and next_scope_id == m.scope_id:
            return bundle
        return bundle.model_copy(
            update={
                "manifest": m.model_copy(
                    update={"scope_type": next_scope, "scope_id": next_scope_id}
                )
            }
        )

    async def _persist_bundle(
        self,
        bundle: LoadedPackBundleV2,
        *,
        archive_bytes: bytes,
        replace_draft: bool,
        allow_system_kind: bool,
        record_audit: bool,
        actor_id: str,
        actor_email: str | None,
        trace_id: str | None,
    ) -> PackImportOutcome:
        engine = self._require_engine()

        async def _upload_cas() -> str | None:
            if self._cas_storage is None:
                return None
            return await self._cas_storage.put_archive_zip(
                slug=bundle.manifest.slug,
                version=bundle.manifest.version,
                archive_sha256=bundle.archive_sha256,
                zip_bytes=archive_bytes,
            )

        res: dict[str, Any] = await import_bundle_transactional(
            engine,
            bundle,
            replace_draft=replace_draft,
            allow_system_kind=allow_system_kind,
            cas_upload_cb=_upload_cas,
            record_audit=record_audit,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
        )
        return PackImportOutcome(
            bundle_id=str(res["bundle_id"]),
            pack_id=str(res["pack_id"]),
            slug=str(res["slug"]),
            name=str(res["name"]),
            version=str(res["version"]),
            bundle_kind=str(res["bundle_kind"]),
            scope_type=str(res["scope_type"]),
            scope_id=str(res["scope_id"]),
            status=str(res["status"]),
            archive_sha256=str(res["archive_sha256"]),
            cas_object_key=res["cas_object_key"],
            idempotent_noop=bool(res["idempotent_noop"]),
            counts=dict(res["counts"]),
        )


async def seed_system_packs_on_engine(
    engine: AsyncEngine,
    *,
    packs_root: Path | None = None,
    cas_storage: PackCasStoragePort | None = None,
    import_service: PackImportService | None = None,
) -> list[PackImportOutcome]:
    """Idempotently seed Day-0 `SYSTEM` packs (`packs/sdlc`, `packs/orcia-docs`) into PG18."""
    from orcia_core.packs.loader import resolve_default_packs_root

    root = packs_root or resolve_default_packs_root()
    if not root.exists() or not root.is_dir():
        return []
    svc = import_service or PackImportService(engine=engine, cas_storage=cas_storage)
    if getattr(svc, "_engine", None) is None:
        svc.set_engine(engine)
    if cas_storage is not None and getattr(svc, "_cas_storage", None) is None:
        svc.set_cas_storage(cas_storage)
    outcomes: list[PackImportOutcome] = []
    for pack_dir in sorted(root.iterdir()):
        if not pack_dir.is_dir():
            continue
        if not ((pack_dir / "apm.yml").exists() or (pack_dir / "pack.yaml").exists()):
            continue
        outcomes.append(
            await svc.import_directory(
                pack_dir,
                bundle_kind=PackBundleKind.SYSTEM,
                scope_type=PackScopeType.GLOBAL,
                scope_id="global",
                allow_system_kind=True,
                record_audit=False,
            )
        )
    return outcomes


__all__ = ["PackImportOutcome", "PackImportService", "seed_system_packs_on_engine"]
