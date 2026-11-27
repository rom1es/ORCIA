"""Transactional PG18 pack import helper (`Story 31.2`, `<= 300 L`)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_entity_materializer import (
    materialize_pack_catalog_items,
)
from orcia_core.packs._internal._sql_pack_ontology_materializer import (
    materialize_pack_ontology,
)
from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
    materialize_pack_mechanisms_and_policies,
)
from orcia_core.packs._internal._sql_pack_workflows_materializer import (
    materialize_pack_workflows_and_vsms,
)
from orcia_core.packs.errors import PackVersionConflictError
from orcia_core.packs.models import LoadedPackBundleV2, PackBundleStatus


def _build_manifest_json(bundle: LoadedPackBundleV2) -> str:
    m = bundle.manifest
    payload = {
        **m.model_dump(mode="json"),
        "counts": {
            "agents": len(bundle.agents),
            "skills": len(bundle.skills),
            "instructions": len(bundle.instructions),
            "vsm": len(bundle.vsm_specs),
            "workflows": len(bundle.workflows),
            "ontology_terms": len((bundle.glossary or {}).get("terms") or []),
            "dna_mechanisms": len(bundle.dna_mechanisms),
            "gates": len(bundle.gates_specs),
            "policies": len(bundle.policies),
            "help_articles": len(bundle.help_articles),
        },
        "agents_slugs": sorted(a.slug for a in bundle.agents),
        "skills_slugs": sorted(s.slug for s in bundle.skills),
        "gates_slugs": sorted(bundle.gates_specs.keys()),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


async def import_bundle_transactional(
    engine: AsyncEngine,
    bundle: LoadedPackBundleV2,
    *,
    replace_draft: bool = False,
    allow_system_kind: bool = False,
    cas_upload_cb: Callable[[], Awaitable[str | None]] | None = None,
    record_audit: bool = True,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Atomically upsert a pack bundle and all constituent entities in PostgreSQL 18."""
    m = bundle.manifest
    pack_id = (m.id or f"orcia-pack-{m.slug}")[:128]
    sha_val = bundle.archive_sha256.strip().lower()[:64].ljust(64, "0")
    slots_json = json.dumps(
        [slot.model_dump(mode="json") for slot in m.declared_slots],
        ensure_ascii=False,
        sort_keys=True,
    )
    manifest_json = _build_manifest_json(bundle)
    is_pub = m.status == PackBundleStatus.PUBLISHED

    async with engine.begin() as conn:
        existing = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, bundle_kind, status, archive_sha256, cas_object_key "
                        "FROM declarative_pack_bundles "
                        "WHERE scope_type = :scope_type AND scope_id = :scope_id "
                        "AND slug = :slug AND version = :version FOR UPDATE"
                    ),
                    {
                        "scope_type": m.scope_type.value,
                        "scope_id": m.scope_id,
                        "slug": m.slug[:128],
                        "version": m.version[:64],
                    },
                )
            )
            .mappings()
            .first()
        )

        idempotent_noop = False
        if existing is not None:
            existing_sha = str(existing["archive_sha256"]).strip().lower()
            if existing_sha == sha_val:
                idempotent_noop = True
            else:
                can_replace_draft = (
                    replace_draft
                    and str(existing["bundle_kind"]) == "CUSTOM"
                    and str(existing["status"]) == "DRAFT"
                )
                can_replace_system = allow_system_kind and str(existing["bundle_kind"]) == "SYSTEM"
                if not (can_replace_draft or can_replace_system):
                    raise PackVersionConflictError(
                        detail_override=(
                            f"Pack {m.slug!r} version {m.version!r} already exists in scope "
                            f"{m.scope_type.value}:{m.scope_id} with a different SHA-256."
                        )
                    )

        cas_key = await cas_upload_cb() if cas_upload_cb is not None else None
        bundle_id = str(
            (
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
                            pack_id = EXCLUDED.pack_id, name = EXCLUDED.name,
                            rbac_namespace = EXCLUDED.rbac_namespace,
                            bundle_sha256 = EXCLUDED.bundle_sha256,
                            manifest_jsonb = EXCLUDED.manifest_jsonb,
                            bundle_kind = EXCLUDED.bundle_kind, status = EXCLUDED.status,
                            archive_sha256 = EXCLUDED.archive_sha256,
                            cas_object_key = COALESCE(
                                EXCLUDED.cas_object_key, declarative_pack_bundles.cas_object_key
                            ),
                            manifest_yaml = EXCLUDED.manifest_yaml,
                            source_origin = EXCLUDED.source_origin,
                            declared_slots_jsonb = EXCLUDED.declared_slots_jsonb,
                            author = EXCLUDED.author, description = EXCLUDED.description,
                            published_at = COALESCE(
                                declarative_pack_bundles.published_at, EXCLUDED.published_at
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
                        "cas_object_key": cas_key,
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
        )

        await materialize_pack_catalog_items(conn, bundle_id=bundle_id, bundle=bundle)
        await materialize_pack_workflows_and_vsms(conn, bundle_id=bundle_id, bundle=bundle)
        await materialize_pack_ontology(conn, bundle_id=bundle_id, bundle=bundle)
        await materialize_pack_mechanisms_and_policies(conn, bundle_id=bundle_id, bundle=bundle)

        if record_audit:
            await append_pack_audit_event(
                conn,
                event_type="PACK_IMPORTED",
                summary=f"Imported pack {m.slug}@{m.version} ({m.bundle_kind.value})",
                scope_path=f"{m.scope_type.value}:{m.scope_id}",
                actor_id=actor_id,
                actor_email=actor_email,
                metadata={
                    "bundle_id": bundle_id,
                    "slug": m.slug,
                    "version": m.version,
                    "archive_sha256": sha_val,
                    "idempotent_noop": idempotent_noop,
                },
                cas_references=[cas_key] if cas_key else [],
                trace_id=trace_id,
            )

    return {
        "bundle_id": bundle_id,
        "pack_id": pack_id,
        "slug": m.slug,
        "name": m.name,
        "version": m.version,
        "bundle_kind": m.bundle_kind.value,
        "scope_type": m.scope_type.value,
        "scope_id": m.scope_id,
        "status": m.status.value,
        "archive_sha256": sha_val,
        "cas_object_key": cas_key or (str(existing["cas_object_key"]) if existing else None),
        "idempotent_noop": idempotent_noop,
        "counts": {
            "agents": len(bundle.agents),
            "skills": len(bundle.skills),
            "instructions": len(bundle.instructions),
            "workflows": len(bundle.workflows),
            "vsm": len(bundle.vsm_specs),
            "ontology_terms": len((bundle.glossary or {}).get("terms") or []),
            "dna_mechanisms": len(bundle.dna_mechanisms),
            "policies": len(bundle.policies),
            "help_articles": len(bundle.help_articles),
        },
    }


__all__ = ["import_bundle_transactional"]
