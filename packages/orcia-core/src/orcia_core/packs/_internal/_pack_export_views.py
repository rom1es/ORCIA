"""Helper converting non-draft `RawExportEntities` rows into closure member views."""

from __future__ import annotations

from typing import Any

from orcia_core.packs.composer_models import PackDraftMemberView
from orcia_core.packs.models import PackDraftEntityType


def views_from_non_draft_entities(bundle_id: str, entities: Any) -> list[PackDraftMemberView]:
    """Convert all 8 non-draft bundle entity tables into `PackDraftMemberView` rows."""
    views: list[PackDraftMemberView] = []
    for row in entities.catalog_items:
        itype = str(row.get("item_type") or "").upper()
        etype = (
            PackDraftEntityType.AGENT
            if itype == "USER_AGENT"
            else PackDraftEntityType.SKILL
            if itype == "USER_SKILL"
            else PackDraftEntityType.HELP_ARTICLE
            if itype == "HELP_ARTICLE"
            else PackDraftEntityType.INSTRUCTION
        )
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=etype,
                entity_id=str(row["resource_id"]),
                entity_slug=str(row["resource_id"]).rsplit(":", 1)[-1],
                catalog_item_id=str(row["id"]),
            )
        )
    for row in entities.workflows_v2:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.WORKFLOW_V2,
                entity_id=str(row["workflow_id"]),
                entity_slug=str(row["slug"]),
                workflow_v2_id=str(row["id"]),
            )
        )
    for row in entities.vsms_v2:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.VSM_V2,
                entity_id=str(row["vsm_id"]),
                entity_slug=str(row["slug"]),
                vsm_v2_id=str(row["id"]),
            )
        )
    for row in entities.concepts:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.ONTOLOGY_CONCEPT,
                entity_id=str(row["concept_key"]),
                entity_slug=str(row["concept_key"]).rsplit(":", 1)[-1],
                ontology_concept_id=str(row["id"]),
            )
        )
    for row in entities.relations:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.ONTOLOGY_RELATION,
                entity_id=str(row["relation_key"]),
                entity_slug=str(row["relation_key"]).rsplit(":", 1)[-1],
                ontology_relation_id=str(row["id"]),
            )
        )
    for row in entities.axioms:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.ONTOLOGY_AXIOM,
                entity_id=str(row["axiom_key"]),
                entity_slug=str(row["axiom_key"]).rsplit(":", 1)[-1],
                ontology_axiom_id=str(row["id"]),
            )
        )
    for row in entities.dna_mechanisms:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.DNA_MECHANISM,
                entity_id=str(row["mechanism_slug"]),
                entity_slug=str(row["mechanism_slug"]),
                dna_mechanism_id=str(row["id"]),
            )
        )
    for row in entities.policies:
        views.append(
            PackDraftMemberView(
                id=str(row["id"]),
                draft_bundle_id=bundle_id,
                entity_type=PackDraftEntityType.POLICY,
                entity_id=str(row["policy_key"]),
                entity_slug=str(row["policy_key"]).rsplit(":", 1)[-1],
                policy_id=str(row["id"]),
            )
        )
    return views


__all__ = ["views_from_non_draft_entities"]
