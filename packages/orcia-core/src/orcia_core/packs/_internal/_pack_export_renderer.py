"""Portable APM bundle synthesis, leak scan & deterministic `.zip` build (`Story 31.5`)."""

from __future__ import annotations

import json
from typing import Any

import yaml  # type: ignore[import-untyped]

from orcia_core.packs._internal._apm_bundle_synthesizer import synthesize_files_from_bundle
from orcia_core.packs._internal._apm_manifest_parser import (
    build_lockfile_dict,
    compute_archive_sha256,
    verify_lockfile,
)
from orcia_core.packs._internal._pack_export_loaders import RawExportEntities
from orcia_core.packs._internal._pack_export_scrubber import (
    TenantInfraIdentifiers,
    scan_rendered_files_for_leaks,
)
from orcia_core.packs._internal._pack_export_scrubber_mappers import build_scrubbed_catalog_specs
from orcia_core.packs._internal._pack_export_workflow_scrubber import (
    scrub_vsm_v2_spec,
    scrub_workflow_v2_spec,
)
from orcia_core.packs._internal._sql_pack_composer_hydration import decode_json_dict
from orcia_core.packs._internal._sql_workspace_pack_queries import decode_declared_slots
from orcia_core.packs._internal.apm_codec import ApmPackCodec
from orcia_core.packs.composer_models import ClosureMissingDependency
from orcia_core.packs.errors import PackClosureIncompleteError
from orcia_core.packs.models import (
    LoadedPackBundleV2,
    PackBundleKind,
    PackBundleStatus,
    PackDnaMechanismSpec,
    PackManifestV2,
    PackPolicySpec,
    PackQuickActionSpec,
    PackScopeType,
    PackSlotSpec,
    PackSourceOrigin,
)


def _decode_json_val(raw: object, default: Any) -> Any:
    if isinstance(raw, type(default)):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            dec = json.loads(raw)
            return dec if isinstance(dec, type(default)) else default
        except ValueError:
            return default
    return default


def _build_glossary_dict(
    pack_slug: str, entities: RawExportEntities, *, instance: str | None = None
) -> dict[str, Any]:
    concept_key_by_uuid: dict[str, str] = {}
    terms_out: list[dict[str, Any]] = []
    for c in entities.concepts:
        ck = str(c["concept_key"]).removeprefix(f"pack:{pack_slug}:")
        concept_key_by_uuid[str(c["id"])] = ck
        terms_out.append(
            {
                "key": ck,
                "label": str(c["canonical_term"]),
                "definition": str(c["definition_text"]),
                "synonyms": _decode_json_val(c.get("synonyms_jsonb"), []),
                "banned_terms": _decode_json_val(c.get("banned_terms_jsonb"), []),
                "profile_translations": _decode_json_val(c.get("profile_translations_jsonb"), {}),
                "expected_schema": _decode_json_val(c.get("expected_schema_jsonb"), {}),
            }
        )
    missing: list[ClosureMissingDependency] = []
    rels_out: list[dict[str, Any]] = []
    for r in entities.relations:
        src_id = str(r["source_concept_id"])
        tgt_id = str(r["target_concept_id"])
        if src_id not in concept_key_by_uuid or tgt_id not in concept_key_by_uuid:
            for ep in (src_id, tgt_id):
                if ep not in concept_key_by_uuid:
                    missing.append(
                        ClosureMissingDependency(
                            entity_type="ONTOLOGY_CONCEPT",
                            entity_id=ep,
                            reason="MISSING_FROM_DRAFT",
                            referenced_by=f"ONTOLOGY_RELATION:{r['relation_key']}",
                        )
                    )
            continue
        rels_out.append(
            {
                "relation_key": str(r["relation_key"]).removeprefix(f"pack:{pack_slug}:"),
                "source": concept_key_by_uuid[src_id],
                "target": concept_key_by_uuid[tgt_id],
                "relation_type": str(r["relation_type"]),
                "cardinality": str(r["cardinality"]),
            }
        )
    axioms_out: list[dict[str, Any]] = []
    for a in entities.axioms:
        cid = str(a["concept_id"])
        if cid not in concept_key_by_uuid:
            missing.append(
                ClosureMissingDependency(
                    entity_type="ONTOLOGY_CONCEPT",
                    entity_id=cid,
                    reason="MISSING_FROM_DRAFT",
                    referenced_by=f"ONTOLOGY_AXIOM:{a['axiom_key']}",
                )
            )
            continue
        axioms_out.append(
            {
                "axiom_key": str(a["axiom_key"]).removeprefix(f"pack:{pack_slug}:"),
                "concept_key": concept_key_by_uuid[cid],
                "rule_expression": str(a["rule_expression"]),
                "immutable": bool(a["immutable"]),
            }
        )
    if missing:
        raise PackClosureIncompleteError(
            missing_dependencies=[m.model_dump() for m in missing],
            instance=instance,
        )
    if not (terms_out or rels_out or axioms_out):
        return {}
    return {"terms": terms_out, "relations": rels_out, "axioms": axioms_out}


def build_and_scan_export_archive(
    *,
    bundle_row: dict[str, Any],
    entities: RawExportEntities,
    infra: TenantInfraIdentifiers,
    instance: str | None = None,
) -> tuple[LoadedPackBundleV2, dict[str, bytes], dict[str, Any], bytes, str]:
    """Synthesize portable scrubbed `LoadedPackBundleV2`, scan for leaks, and build `.zip`."""
    pack_slug = str(bundle_row["slug"]).strip()
    manifest_meta = decode_json_dict(bundle_row.get("manifest_jsonb"))
    existing_slots = decode_declared_slots(bundle_row.get("declared_slots_jsonb"))
    slots_by_key: dict[str, PackSlotSpec] = {s.slot_key: s for s in existing_slots}

    agents, skills, instructions, help_articles = build_scrubbed_catalog_specs(
        entities, pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
    )
    workflows = [
        scrub_workflow_v2_spec(
            decode_json_dict(w.get("spec_jsonb")),
            pack_slug=pack_slug,
            infra=infra,
            slots_by_key=slots_by_key,
        )
        for w in entities.workflows_v2
    ]
    vsms = [
        scrub_vsm_v2_spec(
            decode_json_dict(v.get("spec_jsonb")),
            pack_slug=pack_slug,
            infra=infra,
            slots_by_key=slots_by_key,
        )
        for v in entities.vsms_v2
    ]
    dna_mechs = [
        PackDnaMechanismSpec(
            mechanism_slug=str(d["mechanism_slug"]),
            name=str(d["name"]),
            starlark_source=str(d["starlark_source"]),
            source_sha256=str(d["source_sha256"]).strip(),
            input_schema=_decode_json_val(d.get("input_schema_jsonb"), {}),
            output_schema=_decode_json_val(d.get("output_schema_jsonb"), {}),
            passing_test_payload=_decode_json_val(d.get("passing_test_payload_jsonb"), {}) or None,
            failing_test_payload=_decode_json_val(d.get("failing_test_payload_jsonb"), {}) or None,
        )
        for d in entities.dna_mechanisms
    ]
    policies = [
        PackPolicySpec(
            policy_key=str(p["policy_key"]).removeprefix(f"{pack_slug}:"),
            uri_pattern=str(p["uri_pattern"]),
            connector_scheme=str(p["connector_scheme"]),
            required_role=str(p["required_role"]),
            approver_team=str(p.get("approver_team") or ""),
            sla_hours=int(p.get("sla_hours") or 24),
            procedure_markdown=str(p.get("procedure_markdown") or ""),
        )
        for p in entities.policies
    ]
    raw_author = str(bundle_row.get("author") or manifest_meta.get("author") or "").strip()
    author_out = "" if raw_author.lower() in infra.tenant_emails else raw_author
    maintainers_out = [
        str(m)
        for m in (manifest_meta.get("maintainers") or [])
        if str(m).strip().lower() not in infra.tenant_emails
    ]
    qa_raw = manifest_meta.get("quick_actions") or []
    quick_actions = [PackQuickActionSpec.model_validate(q) for q in qa_raw if isinstance(q, dict)]
    manifest = PackManifestV2(
        id=str(bundle_row.get("pack_id") or f"orcia-pack-{pack_slug}"),
        slug=pack_slug,
        name=str(bundle_row["name"]),
        version=str(bundle_row["version"]),
        description=str(bundle_row.get("description") or manifest_meta.get("description") or ""),
        author=author_out,
        maintainers=maintainers_out,
        license=str(manifest_meta.get("license") or ""),
        rbac_namespace=str(bundle_row.get("rbac_namespace") or pack_slug),
        bundle_kind=PackBundleKind.IMPORTED,
        scope_type=PackScopeType.WORKSPACE,
        scope_id="portable",
        status=PackBundleStatus.PUBLISHED,
        source_origin=PackSourceOrigin.APM_ZIP,
        declared_slots=list(slots_by_key.values()),
        quick_actions=quick_actions,
    )
    provisional = LoadedPackBundleV2(
        manifest=manifest,
        archive_sha256="0" * 64,
        agents=agents,
        skills=skills,
        instructions=instructions,
        vsm_specs=vsms,
        workflows=workflows,
        glossary=_build_glossary_dict(pack_slug, entities, instance=instance),
        dna_mechanisms=dna_mechs,
        policies=policies,
        help_articles=help_articles,
    )
    files = synthesize_files_from_bundle(provisional)
    scan_rendered_files_for_leaks(files, infra, instance=instance)
    lock_dict = build_lockfile_dict(files)
    files["apm.lock.yaml"] = yaml.safe_dump(lock_dict, allow_unicode=True, sort_keys=True).encode(
        "utf-8"
    )
    final_bundle = provisional.model_copy(
        update={
            "manifest_yaml": files["apm.yml"].decode("utf-8"),
            "lockfile": verify_lockfile(files),
            "raw_files": files,
        }
    )
    zip_bytes = ApmPackCodec().encode_zip_bytes(final_bundle)
    archive_sha = compute_archive_sha256(zip_bytes)
    final_bundle = final_bundle.model_copy(update={"archive_sha256": archive_sha})
    return final_bundle, files, lock_dict, zip_bytes, archive_sha


__all__ = ["build_and_scan_export_archive"]
