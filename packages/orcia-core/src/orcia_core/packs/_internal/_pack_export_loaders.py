"""Batch PG18 entity loaders for Pack Composer export & publish (`Story 31.5`, `<= 190 L`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs.composer_models import PackDraftMemberView
from orcia_core.packs.models import PackDraftEntityType


@dataclass(slots=True)
class RawExportEntities:
    """Raw PG18 entity rows gathered for pack export or publish rendering."""

    catalog_items: list[dict[str, Any]] = field(default_factory=list)
    workflows_v2: list[dict[str, Any]] = field(default_factory=list)
    vsms_v2: list[dict[str, Any]] = field(default_factory=list)
    concepts: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    axioms: list[dict[str, Any]] = field(default_factory=list)
    dna_mechanisms: list[dict[str, Any]] = field(default_factory=list)
    policies: list[dict[str, Any]] = field(default_factory=list)


async def _fetch_by_ids(
    conn: AsyncConnection, sql_text: str, ids: list[str]
) -> list[dict[str, Any]]:
    if not ids:
        return []
    rows = (await conn.execute(sa.text(sql_text), {"ids": ids})).mappings().all()
    return [dict(r) for r in rows]


async def load_entities_for_export_conn(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    is_custom_draft: bool,
    members: list[PackDraftMemberView],
) -> RawExportEntities:
    """Load all constituent entity rows from `pack_draft_memberships` or `pack_bundle_id`."""
    if is_custom_draft:
        cat_ids = [
            m.catalog_item_id
            for m in members
            if m.catalog_item_id
            and m.entity_type
            in (
                PackDraftEntityType.AGENT,
                PackDraftEntityType.SKILL,
                PackDraftEntityType.INSTRUCTION,
                PackDraftEntityType.HELP_ARTICLE,
            )
        ]
        wf_ids = [m.workflow_v2_id for m in members if m.workflow_v2_id]
        vsm_ids = [m.vsm_v2_id for m in members if m.vsm_v2_id]
        con_ids = [m.ontology_concept_id for m in members if m.ontology_concept_id]
        rel_ids = [m.ontology_relation_id for m in members if m.ontology_relation_id]
        ax_ids = [m.ontology_axiom_id for m in members if m.ontology_axiom_id]
        dna_ids = [m.dna_mechanism_id for m in members if m.dna_mechanism_id]
        pol_ids = [m.policy_id for m in members if m.policy_id]
        return RawExportEntities(
            catalog_items=await _fetch_by_ids(
                conn,
                "SELECT id::text, resource_id, uri, title, description, resource_type, "
                "item_type, metadata_jsonb FROM catalog_items "
                "WHERE id::text = ANY(:ids) ORDER BY resource_id ASC",
                cat_ids,
            ),
            workflows_v2=await _fetch_by_ids(
                conn,
                "SELECT id::text, workflow_id, slug, version, status, spec_jsonb "
                "FROM workflow_definitions_v2 WHERE id::text = ANY(:ids) ORDER BY slug ASC",
                wf_ids,
            ),
            vsms_v2=await _fetch_by_ids(
                conn,
                "SELECT id::text, vsm_id, slug, title, spec_jsonb "
                "FROM vsm_definitions_v2 WHERE id::text = ANY(:ids) ORDER BY slug ASC",
                vsm_ids,
            ),
            concepts=await _fetch_by_ids(
                conn,
                "SELECT id::text, concept_key, canonical_term, level, scope_id, "
                "definition_text, synonyms_jsonb, banned_terms_jsonb, "
                "profile_translations_jsonb, expected_schema_jsonb "
                "FROM ontology_concepts WHERE id::text = ANY(:ids) ORDER BY concept_key ASC",
                con_ids,
            ),
            relations=await _fetch_by_ids(
                conn,
                "SELECT id::text, relation_key, source_concept_id::text, "
                "target_concept_id::text, relation_type, cardinality "
                "FROM ontology_relations WHERE id::text = ANY(:ids) ORDER BY relation_key ASC",
                rel_ids,
            ),
            axioms=await _fetch_by_ids(
                conn,
                "SELECT id::text, axiom_key, concept_id::text, level, scope_id, "
                "rule_expression, immutable FROM ontology_axioms "
                "WHERE id::text = ANY(:ids) ORDER BY axiom_key ASC",
                ax_ids,
            ),
            dna_mechanisms=await _fetch_by_ids(
                conn,
                "SELECT id::text, mechanism_slug, name, starlark_source, source_sha256, "
                "input_schema_jsonb, output_schema_jsonb, passing_test_payload_jsonb, "
                "failing_test_payload_jsonb FROM pack_dna_mechanisms "
                "WHERE id::text = ANY(:ids) ORDER BY mechanism_slug ASC",
                dna_ids,
            ),
            policies=await _fetch_by_ids(
                conn,
                "SELECT id::text, policy_key, uri_pattern, connector_scheme, required_role, "
                "approver_team, request_url_template, sla_hours, procedure_markdown "
                "FROM permission_broker_policies WHERE id::text = ANY(:ids) "
                "ORDER BY policy_key ASC",
                pol_ids,
            ),
        )

    bid = bundle_id
    return RawExportEntities(
        catalog_items=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, resource_id, uri, title, description, resource_type, "
                        "item_type, metadata_jsonb FROM catalog_items "
                        "WHERE pack_bundle_id = CAST(:bid AS uuid) ORDER BY resource_id ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        workflows_v2=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, workflow_id, slug, version, status, spec_jsonb "
                        "FROM workflow_definitions_v2 "
                        "WHERE pack_bundle_id = CAST(:bid AS uuid) ORDER BY slug ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        vsms_v2=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, vsm_id, slug, title, spec_jsonb "
                        "FROM vsm_definitions_v2 WHERE pack_bundle_id = CAST(:bid AS uuid) "
                        "ORDER BY slug ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        concepts=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, concept_key, canonical_term, level, scope_id, "
                        "definition_text, synonyms_jsonb, banned_terms_jsonb, "
                        "profile_translations_jsonb, expected_schema_jsonb "
                        "FROM ontology_concepts WHERE pack_bundle_id = CAST(:bid AS uuid) "
                        "ORDER BY concept_key ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        relations=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, relation_key, source_concept_id::text, "
                        "target_concept_id::text, relation_type, cardinality "
                        "FROM ontology_relations WHERE pack_bundle_id = CAST(:bid AS uuid) "
                        "ORDER BY relation_key ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        axioms=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, axiom_key, concept_id::text, level, scope_id, "
                        "rule_expression, immutable FROM ontology_axioms "
                        "WHERE pack_bundle_id = CAST(:bid AS uuid) ORDER BY axiom_key ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        dna_mechanisms=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, mechanism_slug, name, starlark_source, source_sha256, "
                        "input_schema_jsonb, output_schema_jsonb, passing_test_payload_jsonb, "
                        "failing_test_payload_jsonb FROM pack_dna_mechanisms "
                        "WHERE pack_bundle_id = CAST(:bid AS uuid) ORDER BY mechanism_slug ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
        policies=[
            dict(r)
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, policy_key, uri_pattern, connector_scheme, "
                        "required_role, approver_team, request_url_template, sla_hours, "
                        "procedure_markdown FROM permission_broker_policies "
                        "WHERE pack_bundle_id = CAST(:bid AS uuid) ORDER BY policy_key ASC"
                    ),
                    {"bid": bid},
                )
            )
            .mappings()
            .all()
        ],
    )


__all__ = ["RawExportEntities", "load_entities_for_export_conn"]
