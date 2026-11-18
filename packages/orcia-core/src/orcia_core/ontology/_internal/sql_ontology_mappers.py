"""SQL row mappers and org/workspace context loader for Ontology PG18 repository."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.ontology.models import (
    OntologyConceptEntity,
    OntologyLevel,
    OntologyPromotionProposal,
    PromotionStatus,
    SnapshotBranchStatus,
    WhatIfImpactReport,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    OrgUnitType,
    WorkspaceEntity,
    WorkspaceVisibilityMode,
)

PROPOSAL_SELECT_SQL = """
    SELECT p.id, p.proposal_key, p.concept_id, p.source_level, p.target_level,
           p.target_scope_id, p.proposed_by_user_id, p.status, p.impact_report_jsonb,
           p.created_at, p.source_concept_id, c.concept_key,
           COALESCE(NULLIF(p.term, ''), c.canonical_term),
           COALESCE(NULLIF(p.definition, ''), c.definition_text),
           COALESCE(p.source_scope_id, c.scope_id),
           p.reviewed_by_user_id, p.reviewed_at, p.review_comment
    FROM ontology_promotion_proposals p
    LEFT JOIN ontology_concepts c ON c.id = p.concept_id
"""


def parse_json_list(raw: object) -> tuple[str, ...]:
    if isinstance(raw, list):
        return tuple(str(x) for x in raw if x is not None)
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                return tuple(str(x) for x in decoded if x is not None)
        except ValueError:
            return ()
    return ()


def parse_json_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return dict(decoded)
        except ValueError:
            return {}
    return {}


def maybe_uuid(val: str | None) -> str | None:
    if not val:
        return None
    try:
        return str(UUID(str(val).strip()))
    except (ValueError, TypeError):
        return None


def row_to_concept(row: Any) -> OntologyConceptEntity:
    return OntologyConceptEntity(
        id=str(row[0]),
        concept_key=str(row[1]),
        canonical_term=str(row[2]),
        level=cast(OntologyLevel, str(row[3])),
        scope_id=str(row[4]),
        parent_concept_id=str(row[5]) if row[5] is not None else None,
        definition_text=str(row[6]),
        synonyms=parse_json_list(row[7]),
        banned_terms=parse_json_list(row[8]),
        profile_translations={str(k): str(v) for k, v in parse_json_dict(row[9]).items()},
        expected_schema={str(k): str(v) for k, v in parse_json_dict(row[10]).items()},
        introduced_in_snapshot_id=str(row[11]) if row[11] is not None else None,
        snapshot_branch_status=cast(SnapshotBranchStatus, str(row[12])),
    )


def row_to_proposal(row: Any) -> OntologyPromotionProposal:
    rep = parse_json_dict(row[8])
    impact = WhatIfImpactReport(
        concept_key=str(rep.get("concept_key") or row[11] or ""),
        canonical_term=str(rep.get("canonical_term") or row[12] or ""),
        proposed_change=str(rep.get("proposed_change") or ""),
        transitively_affected_concepts=tuple(
            str(x) for x in rep.get("transitively_affected_concepts", [])
        ),  # noqa: E501
        impacted_artifact_templates=tuple(
            str(x) for x in rep.get("impacted_artifact_templates", [])
        ),  # noqa: E501
        impacted_workflow_uris=tuple(str(x) for x in rep.get("impacted_workflow_uris", [])),
        impacted_active_run_ids=tuple(str(x) for x in rep.get("impacted_active_run_ids", [])),
        has_immutable_axiom_conflict=bool(rep.get("has_immutable_axiom_conflict", False)),
    )
    created_val, reviewed_val = row[9], row[16]
    actor = str(rep.get("proposed_by_actor") or (str(row[6]) if row[6] is not None else "unknown"))
    return OntologyPromotionProposal(
        id=str(row[0]),
        proposal_key=str(row[1]),
        concept_key=str(rep.get("concept_key") or row[11] or str(row[2])),
        canonical_term=str(row[12] or rep.get("canonical_term") or ""),
        source_level=cast(OntologyLevel, str(row[3])),
        target_level=cast(OntologyLevel, str(row[4])),
        target_scope_id=str(row[5]),
        proposed_by_user_id=actor,
        status=cast(PromotionStatus, str(row[7])),
        impact_report=impact,
        badge_color_token=str(rep.get("badge_color_token") or "ontology-cyan"),
        source_concept_id=str(row[10]) if row[10] is not None else str(row[2]),
        source_scope_id=str(row[14]) if row[14] is not None else None,
        definition_text=str(row[13] or ""),
        reviewed_by_user_id=str(row[15]) if row[15] is not None else None,
        review_comment=str(row[17]) if row[17] is not None else None,
        created_at=created_val.isoformat() if hasattr(created_val, "isoformat") else None,
        reviewed_at=reviewed_val.isoformat() if hasattr(reviewed_val, "isoformat") else None,
        collision_detected=bool(rep.get("collision_detected", False)),
        colliding_definition=(
            str(rep["colliding_definition"])
            if rep.get("colliding_definition") is not None
            else None  # noqa: E501
        ),
    )


async def load_org_and_workspaces_context(
    engine: AsyncEngine,
) -> tuple[tuple[OrgUnitNode, ...], tuple[WorkspaceEntity, ...]]:
    """Load `org_units` and `workspaces` from PG18 in two flat queries (zero N+1)."""
    async with engine.connect() as conn:
        org_reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
        ws_reg = (await conn.execute(sa.text("SELECT to_regclass('public.workspaces')"))).scalar()
        if org_reg is None:
            return (), ()
        org_rows = (
            await conn.execute(
                sa.text(
                    "SELECT id, slug, name, unit_type, parent_id, billing_enabled, "
                    "lead_user_id, member_user_ids_jsonb, "
                    "lead_user_ids_jsonb, ontology_lead_user_ids_jsonb FROM org_units"
                )
            )
        ).fetchall()
        units = tuple(
            OrgUnitNode(
                id=str(r[0]),
                slug=str(r[1]),
                name=str(r[2]),
                unit_type=cast(OrgUnitType, str(r[3])),
                parent_id=str(r[4]) if r[4] is not None else None,
                billing_enabled=bool(r[5]),
                lead_user_id=str(r[6]) if r[6] is not None else None,
                member_user_ids=parse_json_list(r[7]),
                lead_user_ids=parse_json_list(r[8]),
                ontology_lead_user_ids=parse_json_list(r[9]),
            )
            for r in org_rows
        )
        if ws_reg is None:
            return units, ()
        ws_rows = (
            await conn.execute(
                sa.text(
                    "SELECT id, slug, name, owner_org_unit_id, visibility_mode, finops_cost_usd "
                    "FROM workspaces"
                )
            )
        ).fetchall()
        workspaces = tuple(
            WorkspaceEntity(
                id=str(r[0]),
                slug=str(r[1]),
                name=str(r[2]),
                owner_org_unit_id=str(r[3]),
                visibility_mode=cast(WorkspaceVisibilityMode, str(r[4])),
                finops_cost_usd=float(r[5] or 0.0),
            )
            for r in ws_rows
        )
        return units, workspaces
