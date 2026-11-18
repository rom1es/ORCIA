"""Pydantic v2 contracts for Story 20.2: Ontology Concepts Permissions & Step-by-Step Promotions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.ontology_and_rag import (
    OntologyConceptSchemaItem,
    OntologyPromotionProposalSchemaItem,
)
from orcia_core.ontology.models import OntologyLevel, PromotionStatus


class OntologyConceptWithPermissionsItem(OntologyConceptSchemaItem):
    """Ontology concept enriched with caller write & step-up promotion capabilities."""

    can_edit: bool = False
    can_propose_promotion: bool = False
    next_promotion_level: OntologyLevel | None = None
    next_promotion_scope_id: str | None = None


class WritableScopeOptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: OntologyLevel
    scope_id: str
    label: str


class OntologyConceptsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[OntologyConceptWithPermissionsItem]
    writable_levels: list[OntologyLevel]
    writable_scopes: list[WritableScopeOptionItem]
    trace_id: str | None = None


class OntologyPromotionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_key: str = Field(..., min_length=1, max_length=128)
    target_level: OntologyLevel | None = None
    target_scope_id: str | None = Field(default=None, max_length=128)
    proposed_change: str = Field(default="", max_length=500)


class OntologyPromotionDecideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["APPROVE", "REJECT"]
    review_comment: str | None = Field(default=None, max_length=1000)


class OntologyPromotionProposalDetailItem(OntologyPromotionProposalSchemaItem):
    """Promotion proposal enriched with collision metadata, reviewer details, and `can_decide`."""

    source_concept_id: str | None = None
    source_scope_id: str | None = None
    definition_text: str = ""
    reviewed_by_user_id: str | None = None
    review_comment: str | None = None
    created_at: str | None = None
    reviewed_at: str | None = None
    collision_detected: bool = False
    colliding_definition: str | None = None
    can_decide: bool = False


class OntologyPromotionsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[OntologyPromotionProposalDetailItem]
    pending_count: int
    trace_id: str | None = None


class OntologyPromotionDecideResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal: OntologyPromotionProposalDetailItem
    promoted_concept: OntologyConceptSchemaItem | None = None
    status: PromotionStatus
    trace_id: str | None = None
