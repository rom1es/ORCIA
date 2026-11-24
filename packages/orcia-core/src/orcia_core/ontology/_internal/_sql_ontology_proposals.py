"""PostgreSQL 18 proposal decision persistence helper for ontology promotions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.ontology._internal.sql_ontology_mappers import (
    PROPOSAL_SELECT_SQL,
    row_to_concept,
    row_to_proposal,
)
from orcia_core.ontology._internal.sql_ontology_queries import (
    SQL_SELECT_CONCEPT_BY_ID,
    SQL_UPDATE_PROPOSAL_DECISION,
)
from orcia_core.ontology.errors import OntologyConflictError, ResourceNotFoundError
from orcia_core.ontology.models import (
    OntologyConceptEntity,
    OntologyPromotionProposal,
    PromotionStatus,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str


async def decide_proposal_pg(
    engine: AsyncEngine,
    *,
    proposal_id_or_key: str,
    decision: Literal["APPROVE", "REJECT"],
    reviewer: UserIdentity,
    review_comment: str | None = None,
    upsert_concept_fn: object | None = None,
) -> tuple[OntologyPromotionProposal, OntologyConceptEntity | None]:
    """Approve or reject a proposal atomically in PG18, upserting target concept on APPROVE."""
    from orcia_core.ontology._internal.sql_ontology_repository import _upsert_concept_on_conn

    upsert_cb = upsert_concept_fn if callable(upsert_concept_fn) else _upsert_concept_on_conn
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
                detail_code="ERR_ONTOLOGY_PROPOSAL_NOT_FOUND",
                detail_params={"proposal_id": proposal_id_or_key},
            )
        proposal = row_to_proposal(row)
        if proposal.status != "PENDING_REVIEW":
            raise OntologyConflictError(
                detail_code="ERR_ONTOLOGY_PROPOSAL_STATUS",
                detail_params={"proposal_key": proposal.proposal_key, "status": proposal.status},
            )
        promoted_concept: OntologyConceptEntity | None = None
        if decision == "APPROVE":
            promoted_concept = await _approve_target_concept(conn, row, proposal, upsert_cb)

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


async def _approve_target_concept(
    conn: AsyncConnection,
    row: object,
    proposal: OntologyPromotionProposal,
    upsert_cb: Callable[[AsyncConnection, OntologyConceptEntity], Awaitable[OntologyConceptEntity]],
) -> OntologyConceptEntity:
    src_id = proposal.source_concept_id or str(row.__getitem__(2))  # type: ignore[index]
    src_row = (await conn.execute(SQL_SELECT_CONCEPT_BY_ID, {"src_id": src_id})).first()
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
    return await upsert_cb(conn, candidate)


__all__ = ["decide_proposal_pg"]
