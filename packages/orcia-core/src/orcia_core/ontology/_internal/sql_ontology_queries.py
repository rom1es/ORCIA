"""SQL query constants and audit helper for Ontology PG18 repository."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.ontology._internal.sql_ontology_mappers import maybe_uuid
from orcia_core.ontology.models import OntologyLevel
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

SQL_LIST_ACTIVE_CONCEPTS = sa.text(
    "SELECT c.id, c.concept_key, c.canonical_term, c.level, c.scope_id, c.parent_concept_id, "
    "c.definition_text, c.synonyms_jsonb, c.banned_terms_jsonb, c.profile_translations_jsonb, "
    "c.expected_schema_jsonb, c.introduced_in_snapshot_id, c.snapshot_branch_status, "
    "c.pack_bundle_id, dpb.slug AS pack_slug, dpb.bundle_kind AS pack_bundle_kind "
    "FROM ontology_concepts c "
    "LEFT JOIN declarative_pack_bundles dpb ON dpb.id = c.pack_bundle_id "
    "WHERE c.snapshot_branch_status = 'ACTIVE' "
    "ORDER BY c.level ASC, c.created_at ASC"
)

SQL_LIST_RELATIONS = sa.text(
    "SELECT r.id, r.relation_key, src.concept_key, tgt.concept_key, "
    "r.relation_type, r.cardinality, r.pack_bundle_id, dpb.slug AS pack_slug "
    "FROM ontology_relations r "
    "JOIN ontology_concepts src ON src.id = r.source_concept_id "
    "JOIN ontology_concepts tgt ON tgt.id = r.target_concept_id "
    "LEFT JOIN declarative_pack_bundles dpb ON dpb.id = r.pack_bundle_id "
    "ORDER BY r.created_at ASC"
)

SQL_LIST_AXIOMS = sa.text(
    "SELECT a.id, a.axiom_key, c.concept_key, a.level, a.scope_id, "
    "a.rule_expression, a.immutable, a.pack_bundle_id, dpb.slug AS pack_slug "
    "FROM ontology_axioms a "
    "JOIN ontology_concepts c ON c.id = a.concept_id "
    "LEFT JOIN declarative_pack_bundles dpb ON dpb.id = a.pack_bundle_id "
    "ORDER BY a.immutable DESC, a.created_at ASC"
)

SQL_FIND_CONCEPT_FOR_UPSERT = sa.text(
    "SELECT id, concept_key, level, scope_id FROM ontology_concepts "
    "WHERE pack_bundle_id IS NULL AND ("
    "concept_key = :concept_key "
    "OR (level = :level AND COALESCE(scope_id, '') = COALESCE(:scope_id, '') "
    "AND LOWER(canonical_term) = LOWER(:term))"
    ") "
    "ORDER BY CASE WHEN concept_key = :concept_key THEN 0 ELSE 1 END "
    "LIMIT 1"
)

SQL_UPDATE_CONCEPT = sa.text(
    "UPDATE ontology_concepts SET canonical_term = :canonical_term, level = :level, "
    "scope_id = :scope_id, parent_concept_id = CAST(:parent_concept_id AS uuid), "
    "definition_text = :definition_text, synonyms_jsonb = CAST(:synonyms_jsonb AS jsonb), "
    "banned_terms_jsonb = CAST(:banned_terms_jsonb AS jsonb), "
    "profile_translations_jsonb = CAST(:profile_translations_jsonb AS jsonb), "
    "expected_schema_jsonb = CAST(:expected_schema_jsonb AS jsonb), "
    "introduced_in_snapshot_id = :introduced_in_snapshot_id, "
    "snapshot_branch_status = :snapshot_branch_status WHERE id = CAST(:id AS uuid)"
)

SQL_INSERT_CONCEPT = sa.text(
    "INSERT INTO ontology_concepts (id, concept_key, canonical_term, level, scope_id, "
    "parent_concept_id, definition_text, synonyms_jsonb, banned_terms_jsonb, "
    "profile_translations_jsonb, expected_schema_jsonb, introduced_in_snapshot_id, "
    "snapshot_branch_status) VALUES (CAST(:id AS uuid), :concept_key, :canonical_term, "
    ":level, :scope_id, CAST(:parent_concept_id AS uuid), :definition_text, "
    "CAST(:synonyms_jsonb AS jsonb), CAST(:banned_terms_jsonb AS jsonb), "
    "CAST(:profile_translations_jsonb AS jsonb), CAST(:expected_schema_jsonb AS jsonb), "
    ":introduced_in_snapshot_id, :snapshot_branch_status)"
)

SQL_INSERT_PROPOSAL = sa.text(
    "INSERT INTO ontology_promotion_proposals (id, proposal_key, concept_id, "
    "source_concept_id, term, definition, source_level, source_scope_id, "
    "target_level, target_scope_id, proposed_by_user_id, status, impact_report_jsonb) "
    "VALUES (CAST(:id AS uuid), :proposal_key, CAST(:concept_id AS uuid), "
    "CAST(:source_concept_id AS uuid), :term, :definition, :source_level, "
    ":source_scope_id, :target_level, :target_scope_id, "
    "CAST(:proposed_by_user_id AS uuid), 'PENDING_REVIEW', CAST(:impact_json AS jsonb))"
)

SQL_SELECT_COLLIDING_DEF = sa.text(
    "SELECT definition_text FROM ontology_concepts "
    "WHERE pack_bundle_id IS NULL "
    "AND level = :target_level AND scope_id = :target_scope_id "
    "AND LOWER(canonical_term) = LOWER(:term) "
    "AND snapshot_branch_status = 'ACTIVE' LIMIT 1"
)

SQL_SELECT_CONCEPT_BY_ID = sa.text(
    "SELECT id, concept_key, canonical_term, level, scope_id, "
    "parent_concept_id, definition_text, synonyms_jsonb, banned_terms_jsonb, "
    "profile_translations_jsonb, expected_schema_jsonb, "
    "introduced_in_snapshot_id, snapshot_branch_status "
    "FROM ontology_concepts WHERE id = CAST(:src_id AS uuid) LIMIT 1"
)

SQL_UPDATE_PROPOSAL_DECISION = sa.text(
    "UPDATE ontology_promotion_proposals SET status = :status, "
    "reviewed_by_user_id = :reviewer, review_comment = :comment, reviewed_at = NOW() "
    "WHERE id = CAST(:id AS uuid)"
)


def resolve_ontology_audit_scope_uuids(
    *,
    level: OntologyLevel | None,
    scope_id: str,
    owner_org_unit_id: str | None = None,
) -> tuple[str | None, str | None]:
    """Return `(workspace_id, org_unit_id)` UUID strings strictly matching ontology level."""
    if level in ("4_WORKSPACE", "3_WORKSPACE"):
        return maybe_uuid(scope_id), maybe_uuid(owner_org_unit_id)
    if level in ("2_DOMAIN", "3_TEAM"):
        return None, maybe_uuid(scope_id)
    if level == "1_ENTERPRISE":
        return None, None
    return maybe_uuid(scope_id), maybe_uuid(owner_org_unit_id)


async def record_ontology_audit_event_pg(
    engine: AsyncEngine,
    *,
    actor: UserIdentity,
    event_type: str,
    summary: str,
    scope_id: str,
    metadata: dict[str, Any],
    level: OntologyLevel | None = None,
    owner_org_unit_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Append an immutable audit ledger row for ontology governance mutations."""
    workspace_uuid, org_unit_uuid = resolve_ontology_audit_scope_uuids(
        level=level,
        scope_id=scope_id,
        owner_org_unit_id=owner_org_unit_id,
    )
    async with engine.begin() as conn:
        reg = (await conn.execute(sa.text("SELECT to_regclass('public.audit_ledger')"))).scalar()
        if reg is None:
            return
        await conn.execute(
            sa.text(
                "INSERT INTO audit_ledger (id, source_event_id, workspace_id, org_unit_id, "
                "scope_path, actor_type, actor_id, actor_display_name, actor_email, event_type, "
                "summary, trace_id, metadata_jsonb) VALUES (CAST(:id AS uuid), "
                "CAST(:source_event_id AS uuid), "
                "CAST(:workspace_id AS uuid), CAST(:org_unit_id AS uuid), "
                ":scope_path, 'HUMAN', :actor_id, :actor_name, "
                ":actor_email, :event_type, :summary, :trace_id, CAST(:metadata_jsonb AS jsonb))"
            ),
            {
                "id": new_uuid7_str(),
                "source_event_id": new_uuid7_str(),
                "workspace_id": workspace_uuid,
                "org_unit_id": org_unit_uuid,
                "scope_path": scope_id or "GLOBAL",
                "actor_id": actor.id,
                "actor_name": actor.display_name,
                "actor_email": actor.email,
                "event_type": event_type,
                "summary": summary,
                "trace_id": (trace_id or new_uuid7_str())[:64],
                "metadata_jsonb": json.dumps(metadata),
            },
        )
