"""Transactional Pack Composer publish & scrubbed `.zip` export (`Story 31.5`, `<= 220 L`)."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs._internal._pack_closure_analyzer import (
    analyze_and_optionally_expand_closure_conn,
)
from orcia_core.packs._internal._pack_export_loaders import load_entities_for_export_conn
from orcia_core.packs._internal._pack_export_renderer import build_and_scan_export_archive
from orcia_core.packs._internal._pack_export_scrubber import load_tenant_infra_identifiers_conn
from orcia_core.packs._internal._pack_export_views import views_from_non_draft_entities
from orcia_core.packs._internal._sql_pack_composer_hydration import (
    decode_json_dict,
    load_draft_members_hydrated_conn,
)
from orcia_core.packs._internal._sql_pack_composer_reads import (
    BUNDLE_SELECT_COLS,
    fetch_bundle_row_conn,
    row_to_draft_detail,
)
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
from orcia_core.packs.composer_models import (
    PackClosureReport,
    PackDraftDetail,
    PackExportResult,
)
from orcia_core.packs.errors import PackVersionConflictError
from orcia_core.packs.models import (
    PackBundleKind,
    PackScopeType,
)
from orcia_core.packs.ports import PackCasStoragePort


async def export_bundle_tx(
    engine: AsyncEngine,
    *,
    bundle_id: str,
    auto_include_dependencies: bool = False,
    require_active: bool = False,
    instance: str | None = None,
) -> PackExportResult:
    """Validate closure, scrub PII/infra, scan, and render deterministic `.zip` + lockfile."""
    async with engine.begin() as conn:
        row = await fetch_bundle_row_conn(
            conn, bundle_id, for_update=auto_include_dependencies, instance=instance
        )
        bid = str(row["id"])
        is_draft = str(row["bundle_kind"]) == "CUSTOM" and str(row["status"]) == "DRAFT"
        if is_draft:
            members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=bid)
            closure = await analyze_and_optionally_expand_closure_conn(
                conn,
                bundle_id=bid,
                scope_type=str(row["scope_type"]),
                scope_id=str(row["scope_id"]),
                members=members,
                auto_include_dependencies=auto_include_dependencies,
                can_mutate_draft=True,
                require_active=require_active,
                fail_on_incomplete=True,
                instance=instance,
            )
            if closure.auto_included_count > 0:
                members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=bid)
            entities = await load_entities_for_export_conn(
                conn, bundle_id=bid, is_custom_draft=True, members=members
            )
        else:
            entities = await load_entities_for_export_conn(
                conn, bundle_id=bid, is_custom_draft=False, members=[]
            )
            views = views_from_non_draft_entities(bid, entities)
            closure = await analyze_and_optionally_expand_closure_conn(
                conn,
                bundle_id=bid,
                scope_type=str(row["scope_type"]),
                scope_id=str(row["scope_id"]),
                members=views,
                auto_include_dependencies=False,
                can_mutate_draft=False,
                require_active=require_active,
                fail_on_incomplete=True,
                instance=instance,
            )

        infra = await load_tenant_infra_identifiers_conn(conn)
        bundle_v2, _files, lock_dict, zip_bytes, archive_sha = build_and_scan_export_archive(
            bundle_row=dict(row), entities=entities, infra=infra, instance=instance
        )
        return PackExportResult(
            bundle_id=bid,
            slug=bundle_v2.manifest.slug,
            version=bundle_v2.manifest.version,
            archive_sha256=archive_sha,
            lockfile_bundle_sha256=str(lock_dict.get("bundle_sha256") or ""),
            zip_bytes=zip_bytes,
            included_dependencies_count=closure.auto_included_count,
            prose_lint_warnings=closure.prose_lint_warnings,
            declared_slots=list(bundle_v2.manifest.declared_slots),
        )


async def publish_draft_pack_tx(
    engine: AsyncEngine,
    *,
    draft_id: str,
    auto_include_dependencies: bool = False,
    cas_storage: PackCasStoragePort | None = None,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> PackDraftDetail:
    """Validate closure & ACTIVE readiness, scrub, snapshot to CAS, and publish `CUSTOM` pack."""
    async with engine.begin() as conn:
        row = await fetch_bundle_row_conn(conn, draft_id, for_update=True, instance=instance)
        if str(row["bundle_kind"]) != "CUSTOM" or str(row["status"]) != "DRAFT":
            raise PackVersionConflictError(
                detail_override="Only CUSTOM DRAFT packs can be published.",
                instance=instance,
            )
        bid = str(row["id"])
        members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=bid)
        closure: PackClosureReport = await analyze_and_optionally_expand_closure_conn(
            conn,
            bundle_id=bid,
            scope_type=str(row["scope_type"]),
            scope_id=str(row["scope_id"]),
            members=members,
            auto_include_dependencies=auto_include_dependencies,
            can_mutate_draft=True,
            require_active=True,
            fail_on_incomplete=True,
            instance=instance,
        )
        if closure.auto_included_count > 0:
            members = await load_draft_members_hydrated_conn(conn, draft_bundle_id=bid)
        entities = await load_entities_for_export_conn(
            conn, bundle_id=bid, is_custom_draft=True, members=members
        )
        infra = await load_tenant_infra_identifiers_conn(conn)
        bundle_v2, files, _lock, zip_bytes, archive_sha = build_and_scan_export_archive(
            bundle_row=dict(row), entities=entities, infra=infra, instance=instance
        )
        cas_key: str | None = None
        if cas_storage is not None:
            cas_key = await cas_storage.put_archive_zip(
                slug=bundle_v2.manifest.slug,
                version=bundle_v2.manifest.version,
                archive_sha256=archive_sha,
                zip_bytes=zip_bytes,
            )
        mat_bundle = bundle_v2.model_copy(
            update={
                "manifest": bundle_v2.manifest.model_copy(
                    update={
                        "bundle_kind": PackBundleKind.CUSTOM,
                        "scope_type": PackScopeType(str(row["scope_type"])),
                        "scope_id": str(row["scope_id"]),
                    }
                )
            }
        )
        old_meta = decode_json_dict(row["manifest_jsonb"])
        pub_meta = {
            **old_meta,
            **mat_bundle.manifest.model_dump(mode="json"),
            "counts": {
                "agents": len(mat_bundle.agents),
                "skills": len(mat_bundle.skills),
                "instructions": len(mat_bundle.instructions),
                "vsm": len(mat_bundle.vsm_specs),
                "workflows": len(mat_bundle.workflows),
                "ontology_terms": len((mat_bundle.glossary or {}).get("terms") or []),
                "dna_mechanisms": len(mat_bundle.dna_mechanisms),
                "policies": len(mat_bundle.policies),
                "help_articles": len(mat_bundle.help_articles),
            },
            "agents_slugs": sorted(a.slug for a in mat_bundle.agents),
            "skills_slugs": sorted(s.slug for s in mat_bundle.skills),
        }
        slots_json = json.dumps(
            [s.model_dump(mode="json") for s in mat_bundle.manifest.declared_slots], sort_keys=True
        )
        updated = (
            (
                await conn.execute(
                    sa.text(
                        f"UPDATE declarative_pack_bundles SET status = 'PUBLISHED', "
                        f"published_at = COALESCE(published_at, NOW()), archive_sha256 = :sha, "
                        f"bundle_sha256 = :sha, cas_object_key = COALESCE(:ckey, cas_object_key), "
                        f"manifest_yaml = :myaml, manifest_jsonb = CAST(:mjson AS jsonb), "
                        f"declared_slots_jsonb = CAST(:sj AS jsonb), updated_at = NOW() "
                        f"WHERE id = CAST(:bid AS uuid) RETURNING {BUNDLE_SELECT_COLS}"
                    ),
                    {
                        "bid": bid,
                        "sha": archive_sha,
                        "ckey": cas_key,
                        "myaml": files["apm.yml"].decode("utf-8"),
                        "mjson": json.dumps(pub_meta, ensure_ascii=False, sort_keys=True),
                        "sj": slots_json,
                    },
                )
            )
            .mappings()
            .one()
        )
        await materialize_pack_catalog_items(conn, bundle_id=bid, bundle=mat_bundle)
        await materialize_pack_workflows_and_vsms(conn, bundle_id=bid, bundle=mat_bundle)
        await materialize_pack_ontology(conn, bundle_id=bid, bundle=mat_bundle)
        await materialize_pack_mechanisms_and_policies(conn, bundle_id=bid, bundle=mat_bundle)
        await conn.execute(
            sa.text(
                "DELETE FROM pack_draft_memberships WHERE draft_bundle_id = CAST(:bid AS uuid)"
            ),
            {"bid": bid},
        )
        slug_ver = f"{mat_bundle.manifest.slug}@{mat_bundle.manifest.version}"
        await append_pack_audit_event(
            conn,
            event_type="PACK_DRAFT_PUBLISHED",
            summary=f"Published CUSTOM pack {slug_ver}",
            scope_path=f"{row['scope_type']}:{row['scope_id']}",
            actor_id=actor_id,
            actor_email=actor_email,
            metadata={"bundle_id": bid, "archive_sha256": archive_sha, "cas_object_key": cas_key},
            cas_references=[cas_key] if cas_key else [],
            trace_id=trace_id,
        )
        detail = row_to_draft_detail(updated, members)
        return detail.model_copy(update={"closure": closure})


__all__ = ["export_bundle_tx", "publish_draft_pack_tx"]
