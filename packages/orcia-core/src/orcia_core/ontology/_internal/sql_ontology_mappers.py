"""SQL row mappers and org/workspace context loader for Ontology PG18 repository."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.ontology.models import (
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyLevel,
    OntologyPromotionProposal,
    OntologyRelationEntity,
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
        pack_bundle_id=str(row[13]) if len(row) > 13 and row[13] is not None else None,
        pack_slug=str(row[14]) if len(row) > 14 and row[14] is not None else None,
        bundle_kind=str(row[15]) if len(row) > 15 and row[15] is not None else None,
    )


def row_to_relation(row: Any) -> OntologyRelationEntity:
    return OntologyRelationEntity(
        id=str(row[0]),
        relation_key=str(row[1]),
        source_concept_key=str(row[2]),
        target_concept_key=str(row[3]),
        relation_type=str(row[4]),
        cardinality=str(row[5] or "1..N"),
        pack_bundle_id=str(row[6]) if len(row) > 6 and row[6] is not None else None,
        pack_slug=str(row[7]) if len(row) > 7 and row[7] is not None else None,
    )


def row_to_axiom(row: Any) -> OntologyAxiomEntity:
    return OntologyAxiomEntity(
        id=str(row[0]),
        axiom_key=str(row[1]),
        concept_key=str(row[2]),
        level=cast(OntologyLevel, str(row[3])),
        scope_id=str(row[4]),
        rule_expression=str(row[5]),
        immutable=bool(row[6]),
        pack_bundle_id=str(row[7]) if len(row) > 7 and row[7] is not None else None,
        pack_slug=str(row[8]) if len(row) > 8 and row[8] is not None else None,
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


_TOPOLOGY_TABLES_READY_ENGINES: set[int] = set()


async def load_org_and_workspaces_context(
    engine: AsyncEngine,
) -> tuple[tuple[OrgUnitNode, ...], tuple[WorkspaceEntity, ...]]:
    """Load `org_units` and `workspaces` from PG18 concurrently across two connections."""
    eng_key = id(engine)
    if eng_key not in _TOPOLOGY_TABLES_READY_ENGINES:
        async with engine.connect() as conn:
            res = await conn.execute(
                sa.text("SELECT to_regclass('public.org_units'), to_regclass('public.workspaces')")
            )
            row = res.first()
            if row is not None:
                if row[0] is None or row[1] is None:
                    return (), ()
            elif res.scalar() is None:
                return (), ()
            if isinstance(engine, AsyncEngine):
                _TOPOLOGY_TABLES_READY_ENGINES.add(eng_key)

    async def _fetch_org_units() -> tuple[OrgUnitNode, ...]:
        async with engine.connect() as conn:
            org_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT id, slug, name, unit_type, parent_id, billing_enabled, "
                        "lead_user_id, member_user_ids_jsonb, "
                        "lead_user_ids_jsonb, ontology_lead_user_ids_jsonb FROM org_units"
                    )
                )
            ).fetchall()
        return tuple(
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

    async def _fetch_workspaces() -> tuple[WorkspaceEntity, ...]:
        async with engine.connect() as conn:
            ws_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT id, slug, name, owner_org_unit_id, "
                        "visibility_mode, finops_cost_usd, settings_jsonb FROM workspaces"
                    )
                )
            ).fetchall()
        out: list[WorkspaceEntity] = []
        for r in ws_rows:
            st = parse_json_dict(r[6]) if len(r) > 6 else {}
            ui_vis = str(st["ui_visibility_mode"]).strip() if st.get("ui_visibility_mode") else None
            personal_owner = (
                str(st["personal_owner_user_id"]).strip()
                if st.get("personal_owner_user_id")
                else None
            )
            out.append(
                WorkspaceEntity(
                    id=str(r[0]),
                    slug=str(r[1]),
                    name=str(r[2]),
                    owner_org_unit_id=str(r[3]),
                    visibility_mode=cast(WorkspaceVisibilityMode, str(r[4])),
                    finops_cost_usd=float(r[5] or 0.0),
                    personal_owner_user_id=personal_owner,
                    ui_visibility_mode=ui_vis,
                )
            )
        return tuple(out)

    units, workspaces = await asyncio.gather(_fetch_org_units(), _fetch_workspaces())
    return units, workspaces
