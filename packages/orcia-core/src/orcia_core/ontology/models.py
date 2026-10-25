"""Pure domain models for the 4-level Dynamic Ontology & What-If Impact Simulation (Story 2.1, 2.2).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

OntologyLevel = Literal[
    "1_ENTERPRISE",
    "2_DOMAIN",
    "3_TEAM",
    "3_WORKSPACE",
    "4_RUN_EPHEMERAL",
]

SnapshotBranchStatus = Literal["ACTIVE", "SUPERSEDED"]

PromotionStatus = Literal["PENDING_REVIEW", "APPROVED", "REJECTED"]

HumanProfileArchetype = Literal[
    "PM_BUSINESS",
    "ARCHITECT",
    "TECH_LEAD",
    "DEVELOPER",
    "SECOPS",
    "EXECUTIVE",
]

ONTOLOGY_LEVEL_PRIORITY: dict[OntologyLevel, int] = {
    "1_ENTERPRISE": 1,
    "2_DOMAIN": 2,
    "3_TEAM": 3,
    "3_WORKSPACE": 4,
    "4_RUN_EPHEMERAL": 5,
}


@dataclass(frozen=True, slots=True)
class OntologyConceptEntity:
    """Concept node in the 4-level Ontology hierarchy (`1_ENTERPRISE` .. `4_RUN_EPHEMERAL`)."""

    id: str
    concept_key: str
    canonical_term: str
    level: OntologyLevel
    scope_id: str
    definition_text: str
    parent_concept_id: str | None = None
    synonyms: tuple[str, ...] = ()
    banned_terms: tuple[str, ...] = ()
    profile_translations: dict[str, str] = field(default_factory=dict)
    expected_schema: dict[str, str] = field(default_factory=dict)
    introduced_in_snapshot_id: str | None = None
    snapshot_branch_status: SnapshotBranchStatus = "ACTIVE"


@dataclass(frozen=True, slots=True)
class OntologyRelationEntity:
    """Directed semantic relation between two ontology concepts with cardinality."""

    id: str
    relation_key: str
    source_concept_key: str
    target_concept_key: str
    relation_type: str
    cardinality: str = "1..N"


@dataclass(frozen=True, slots=True)
class OntologyAxiomEntity:
    """Formal domain rule or constraint attached to an ontology concept."""

    id: str
    axiom_key: str
    concept_key: str
    level: OntologyLevel
    scope_id: str
    rule_expression: str
    immutable: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedOntologySnapshot:
    """Merged ontology view for a Workspace or Workflow Run resolved in < 15 ms."""

    workspace_id: str
    run_id: str | None
    concepts_by_term: dict[str, OntologyConceptEntity]
    relations: tuple[OntologyRelationEntity, ...]
    axioms: tuple[OntologyAxiomEntity, ...]
    resolution_chain_scopes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BlackboardSchemaValidationResult:
    """Result of Plan 1 Active Ontology execution (Blackboard/Template schema & cardinality)."""

    valid: bool
    checked_concept_key: str
    missing_fields: tuple[str, ...] = ()
    type_mismatches: tuple[str, ...] = ()
    cardinality_violations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExpandedRagQuery:
    """Result of Plan 3 Active Ontology execution (RAG synonym/relation expansion & guard)."""

    original_query: str
    expanded_terms: tuple[str, ...]
    matched_concept_keys: tuple[str, ...]
    detected_banned_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WhatIfImpactReport:
    """Graph traversal What-If impact report prior to promoting or mutating a concept (FR-9)."""

    concept_key: str
    canonical_term: str
    proposed_change: str
    transitively_affected_concepts: tuple[str, ...]
    impacted_artifact_templates: tuple[str, ...]
    impacted_workflow_uris: tuple[str, ...]
    impacted_active_run_ids: tuple[str, ...]
    has_immutable_axiom_conflict: bool = False


@dataclass(frozen=True, slots=True)
class OntologyPromotionProposal:
    """Governed promotion proposal from L4/L3 to higher ontology levels (Story 2.2)."""

    id: str
    proposal_key: str
    concept_key: str
    canonical_term: str
    source_level: OntologyLevel
    target_level: OntologyLevel
    target_scope_id: str
    proposed_by_user_id: str
    status: PromotionStatus
    impact_report: WhatIfImpactReport
    badge_color_token: str = "ontology-cyan"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "proposal_key": self.proposal_key,
            "concept_key": self.concept_key,
            "canonical_term": self.canonical_term,
            "source_level": self.source_level,
            "target_level": self.target_level,
            "target_scope_id": self.target_scope_id,
            "proposed_by_user_id": self.proposed_by_user_id,
            "status": self.status,
            "badge_color_token": self.badge_color_token,
        }
