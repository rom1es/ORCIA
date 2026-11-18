"""PostgreSQL 18 repository for 4-Level Ontology Concepts & Promotions (Story 20.2)."""

from __future__ import annotations

import json
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.ontology._internal.sql_ontology_mappers import (
    PROPOSAL_SELECT_SQL,
    maybe_uuid,
    row_to_concept,
    row_to_proposal,
)
from orcia_core.ontology._internal.sql_ontology_queries import (
    SQL_FIND_CONCEPT_FOR_UPSERT,
    SQL_INSERT_CONCEPT,
    SQL_INSERT_PROPOSAL,
    SQL_LIST_ACTIVE_CONCEPTS,
    SQL_SELECT_COLLIDING_DEF,
    SQL_SELECT_CONCEPT_BY_ID,
    SQL_UPDATE_CONCEPT,
    SQL_UPDATE_PROPOSAL_DECISION,
    record_ontology_audit_event_pg,
)
from orcia_core.ontology.errors import (
    OntologyConflictError,
    OntologyScopeConflictError,
    ResourceNotFoundError,
)
from orcia_core.ontology.models import (
    OntologyConceptEntity,
    OntologyLevel,
    OntologyPromotionProposal,
    PromotionStatus,
    WhatIfImpactReport,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

__all__ = [
    "create_proposal_pg",
    "decide_proposal_pg",
    "get_proposal_pg",
    "list_concepts_pg",
    "list_proposals_pg",
    "record_ontology_audit_event_pg",
    "upsert_concept_pg",
]


async def list_concepts_pg(engine: AsyncEngine) -> list[OntologyConceptEntity]:
    """Return all active ontology concepts persisted in PostgreSQL 18."""
    async with engine.connect() as conn:
        reg = (
            await conn.execute(sa.text("SELECT to_regclass('public.ontology_concepts')"))
        ).scalar()
        if reg is None:
            return []
        rows = (await conn.execute(SQL_LIST_ACTIVE_CONCEPTS)).fetchall()
        return [row_to_concept(r) for r in rows]


async def _upsert_concept_on_conn(
    conn: AsyncConnection,
    concept: OntologyConceptEntity,
) -> OntologyConceptEntity:
    existing = (
        await conn.execute(
            SQL_FIND_CONCEPT_FOR_UPSERT,
            {
                "concept_key": concept.concept_key,
                "level": concept.level,
                "scope_id": concept.scope_id,
                "term": concept.canonical_term,
            },
        )
    ).first()
    if existing is not None:
        existing_level = str(existing[2])
        existing_scope = str(existing[3] or "")
        target_scope = str(concept.scope_id or "")
        if (existing_level, existing_scope) != (concept.level, target_scope):
            raise OntologyScopeConflictError(
                detail_override=(
                    f"La clé '{concept.concept_key}' appartient déjà au périmètre "
                    f"({existing_level}, '{existing_scope}') et ne peut être écrasée "
                    f"depuis ({concept.level}, '{target_scope}')."
                )
            )
    cid: str = str(existing[0]) if existing else (maybe_uuid(concept.id) or new_uuid7_str())
    ckey: str = str(existing[1]) if existing else concept.concept_key
    parent_cid = maybe_uuid(concept.parent_concept_id)
    params = {
        "id": cid,
        "concept_key": ckey,
        "canonical_term": concept.canonical_term,
        "level": concept.level,
        "scope_id": concept.scope_id,
        "parent_concept_id": parent_cid,
        "definition_text": concept.definition_text,
        "synonyms_jsonb": json.dumps(list(concept.synonyms)),
        "banned_terms_jsonb": json.dumps(list(concept.banned_terms)),
        "profile_translations_jsonb": json.dumps(dict(concept.profile_translations)),
        "expected_schema_jsonb": json.dumps(dict(concept.expected_schema)),
        "introduced_in_snapshot_id": concept.introduced_in_snapshot_id,
        "snapshot_branch_status": concept.snapshot_branch_status,
    }
    await conn.execute(SQL_UPDATE_CONCEPT if existing is not None else SQL_INSERT_CONCEPT, params)
    return OntologyConceptEntity(
        id=cid,
        concept_key=ckey,
        canonical_term=concept.canonical_term,
        level=concept.level,
        scope_id=concept.scope_id,
        definition_text=concept.definition_text,
        parent_concept_id=parent_cid,
        synonyms=concept.synonyms,
        banned_terms=concept.banned_terms,
        profile_translations=concept.profile_translations,
        expected_schema=concept.expected_schema,
        introduced_in_snapshot_id=concept.introduced_in_snapshot_id,
        snapshot_branch_status=concept.snapshot_branch_status,
    )


async def upsert_concept_pg(
    engine: AsyncEngine,
    concept: OntologyConceptEntity,
) -> OntologyConceptEntity:
    """Persist or update an ontology concept in PG18."""
    async with engine.begin() as conn:
        return await _upsert_concept_on_conn(conn, concept)


async def list_proposals_pg(
    engine: AsyncEngine,
    *,
    status: str | None = None,
) -> list[OntologyPromotionProposal]:
    """List ontology promotion proposals from PG18."""
    async with engine.connect() as conn:
        reg = (
            await conn.execute(sa.text("SELECT to_regclass('public.ontology_promotion_proposals')"))
        ).scalar()
        if reg is None:
            return []
        where_clause = "WHERE p.status = :status" if status else ""
        params = {"status": status} if status else {}
        rows = (
            await conn.execute(
                sa.text(f"{PROPOSAL_SELECT_SQL} {where_clause} ORDER BY p.created_at DESC"),
                params,
            )
        ).fetchall()
        return [row_to_proposal(r) for r in rows]


async def get_proposal_pg(
    engine: AsyncEngine,
    proposal_id_or_key: str,
) -> OntologyPromotionProposal | None:
    """Fetch a single promotion proposal by UUID or `proposal_key`."""
    async with engine.connect() as conn:
        reg = (
            await conn.execute(sa.text("SELECT to_regclass('public.ontology_promotion_proposals')"))
        ).scalar()
        if reg is None:
            return None
        row = (
            await conn.execute(
                sa.text(
                    f"{PROPOSAL_SELECT_SQL} "
                    "WHERE p.proposal_key = :ref OR CAST(p.id AS TEXT) = :ref LIMIT 1"
                ),
                {"ref": proposal_id_or_key},
            )
        ).first()
        return row_to_proposal(row) if row is not None else None


async def create_proposal_pg(
    engine: AsyncEngine,
    *,
    source_concept: OntologyConceptEntity,
    target_level: OntologyLevel,
    target_scope_id: str,
    proposed_by: UserIdentity,
    impact_report: WhatIfImpactReport,
) -> OntologyPromotionProposal:
    """Insert a promotion proposal into PG18 with collision detection at target level."""
    async with engine.begin() as conn:
        persisted_src = await _upsert_concept_on_conn(conn, source_concept)
        coll_row = (
            await conn.execute(
                SQL_SELECT_COLLIDING_DEF,
                {
                    "target_level": target_level,
                    "target_scope_id": target_scope_id,
                    "term": persisted_src.canonical_term,
                },
            )
        ).first()
        user_uuid: str | None = None
        if (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar() is not None:
            u_row = (
                await conn.execute(
                    sa.text(
                        "SELECT id FROM users WHERE CAST(id AS TEXT) = :uid "
                        "OR LOWER(email) = LOWER(:email) LIMIT 1"
                    ),
                    {"uid": proposed_by.id, "email": proposed_by.email},
                )
            ).first()
            user_uuid = str(u_row[0]) if u_row is not None else None

        proposal_id = new_uuid7_str()
        proposal_key = (
            f"prop-{persisted_src.concept_key}-to-{target_level.lower()}-{proposal_id[-6:]}"
        )
        report_payload = {
            "concept_key": persisted_src.concept_key,
            "canonical_term": persisted_src.canonical_term,
            "proposed_change": impact_report.proposed_change,
            "transitively_affected_concepts": list(impact_report.transitively_affected_concepts),
            "impacted_artifact_templates": list(impact_report.impacted_artifact_templates),
            "impacted_workflow_uris": list(impact_report.impacted_workflow_uris),
            "impacted_active_run_ids": list(impact_report.impacted_active_run_ids),
            "has_immutable_axiom_conflict": impact_report.has_immutable_axiom_conflict,
            "collision_detected": coll_row is not None,
            "colliding_definition": str(coll_row[0]) if coll_row is not None else None,
            "proposed_by_actor": proposed_by.email or proposed_by.id,
            "badge_color_token": "ontology-cyan",
        }
        await conn.execute(
            SQL_INSERT_PROPOSAL,
            {
                "id": proposal_id,
                "proposal_key": proposal_key,
                "concept_id": persisted_src.id,
                "source_concept_id": persisted_src.id,
                "term": persisted_src.canonical_term,
                "definition": persisted_src.definition_text,
                "source_level": persisted_src.level,
                "source_scope_id": persisted_src.scope_id,
                "target_level": target_level,
                "target_scope_id": target_scope_id,
                "proposed_by_user_id": user_uuid,
                "impact_json": json.dumps(report_payload),
            },
        )
        row = (
            await conn.execute(
                sa.text(f"{PROPOSAL_SELECT_SQL} WHERE p.id = CAST(:id AS uuid)"),
                {"id": proposal_id},
            )
        ).one()
        return row_to_proposal(row)


async def decide_proposal_pg(
    engine: AsyncEngine,
    *,
    proposal_id_or_key: str,
    decision: Literal["APPROVE", "REJECT"],
    reviewer: UserIdentity,
    review_comment: str | None = None,
) -> tuple[OntologyPromotionProposal, OntologyConceptEntity | None]:
    """Approve or reject a proposal atomically in PG18, upserting target concept on APPROVE."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text(
                    f"{PROPOSAL_SELECT_SQL} "
                    "WHERE p.proposal_key = :ref OR CAST(p.id AS TEXT) = :ref FOR UPDATE OF p"
                ),
                {"ref": proposal_id_or_key},
            )
        ).first()
        if row is None:
            raise ResourceNotFoundError(
                detail_override=f"Proposition '{proposal_id_or_key}' introuvable."
            )
        proposal = row_to_proposal(row)
        if proposal.status != "PENDING_REVIEW":
            raise OntologyConflictError(
                detail_override=(
                    f"La proposition '{proposal.proposal_key}' "
                    f"a déjà le statut '{proposal.status}'."
                )
            )
        promoted_concept: OntologyConceptEntity | None = None
        if decision == "APPROVE":
            src_row = (
                await conn.execute(
                    SQL_SELECT_CONCEPT_BY_ID,
                    {"src_id": proposal.source_concept_id or str(row[2])},
                )
            ).first()
            src = row_to_concept(src_row) if src_row is not None else None
            target_suffix = f"-{proposal.target_level.lower()}"
            raw_target_key = f"{proposal.concept_key}{target_suffix}"
            target_key = (
                raw_target_key
                if len(raw_target_key) <= 128
                else f"{proposal.concept_key[: 128 - len(target_suffix)]}{target_suffix}"
            )
            candidate = OntologyConceptEntity(
                id=new_uuid7_str(),
                concept_key=target_key,
                canonical_term=proposal.canonical_term,
                level=proposal.target_level,
                scope_id=proposal.target_scope_id,
                definition_text=proposal.definition_text
                or (src.definition_text if src else proposal.canonical_term),
                parent_concept_id=src.id if src else None,
                synonyms=src.synonyms if src else (),
                banned_terms=src.banned_terms if src else (),
                profile_translations=src.profile_translations if src else {},
                expected_schema=src.expected_schema if src else {},
                snapshot_branch_status="ACTIVE",
            )
            promoted_concept = await _upsert_concept_on_conn(conn, candidate)

        next_status: PromotionStatus = "APPROVED" if decision == "APPROVE" else "REJECTED"
        await conn.execute(
            SQL_UPDATE_PROPOSAL_DECISION,
            {
                "status": next_status,
                "reviewer": reviewer.email or reviewer.id,
                "comment": review_comment,
                "id": proposal.id,
            },
        )
        updated = (
            await conn.execute(
                sa.text(f"{PROPOSAL_SELECT_SQL} WHERE p.id = CAST(:id AS uuid)"),
                {"id": proposal.id},
            )
        ).one()
        return row_to_proposal(updated), promoted_concept
