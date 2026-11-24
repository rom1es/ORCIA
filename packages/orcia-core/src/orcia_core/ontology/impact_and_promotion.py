"""ImpactSimulatorService (What-If) & L4 Branch-Isolated Ontology Governance (Story 2.2, AD-7).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Sequence

from orcia_core.ontology._impact_simulator import ImpactSimulatorService
from orcia_core.ontology._promotion_runner import execute_promote_concept
from orcia_core.ontology.errors import ObserverModeReadOnlyError, OntologyScopeConflictError
from orcia_core.ontology.models import (
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyLevel,
    OntologyPromotionProposal,
    OntologyRelationEntity,
    ResolvedOntologySnapshot,
    WhatIfImpactReport,
)
from orcia_core.ontology.resolver import OntologyHierarchyResolver
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_kernel.ids import new_uuid7_str


def _assert_mutable_actor(user: UserIdentity, instance: str) -> None:
    if str(user.platform_role).upper() in ("OBSERVER", "READ_ONLY_OBSERVER"):
        raise ObserverModeReadOnlyError(instance=instance)


class OntologyGovernanceService:
    """In-memory / repository-backed service for 4-level Ontology, L4 extraction & What-If."""

    def __init__(
        self,
        *,
        concepts: tuple[OntologyConceptEntity, ...] = (),
        relations: tuple[OntologyRelationEntity, ...] = (),
        axioms: tuple[OntologyAxiomEntity, ...] = (),
        proposals: tuple[OntologyPromotionProposal, ...] = (),
        template_bindings: dict[str, tuple[str, ...]] | None = None,
        workflow_bindings: dict[str, tuple[str, ...]] | None = None,
        active_run_bindings: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._concepts: dict[str, OntologyConceptEntity] = {c.concept_key: c for c in concepts}
        self._relations: list[OntologyRelationEntity] = list(relations)
        self._axioms: list[OntologyAxiomEntity] = list(axioms)
        self._proposals: dict[str, OntologyPromotionProposal] = {
            p.proposal_key: p for p in proposals
        }
        self._template_bindings = dict(template_bindings or {})
        self._workflow_bindings = dict(workflow_bindings or {})
        self._active_run_bindings = dict(active_run_bindings or {})

    @property
    def concepts(self) -> tuple[OntologyConceptEntity, ...]:
        return tuple(self._concepts.values())

    @property
    def relations(self) -> tuple[OntologyRelationEntity, ...]:
        return tuple(self._relations)

    @property
    def axioms(self) -> tuple[OntologyAxiomEntity, ...]:
        return tuple(self._axioms)

    @property
    def proposals(self) -> tuple[OntologyPromotionProposal, ...]:
        return tuple(self._proposals.values())

    def resolve_snapshot(
        self,
        *,
        enterprise_scope_id: str = "scope-global",
        domain_scope_id: str = "scope-bu-digital",
        team_chain_scope_ids: tuple[str, ...] = ("scope-subteam-checkout", "scope-team-core"),
        workspace_scope_id: str = "ws-solution-paiement",
        run_scope_id: str | None = None,
    ) -> ResolvedOntologySnapshot:
        return OntologyHierarchyResolver.resolve_effective_ontology(
            concepts=self.concepts,
            relations=self.relations,
            axioms=self.axioms,
            enterprise_scope_id=enterprise_scope_id,
            domain_scope_id=domain_scope_id,
            team_chain_scope_ids=team_chain_scope_ids,
            workspace_scope_id=workspace_scope_id,
            run_scope_id=run_scope_id,
        )

    def upsert_concept(
        self, user: UserIdentity, concept: OntologyConceptEntity
    ) -> OntologyConceptEntity:
        _assert_mutable_actor(user, "/api/v1/ontology-rag/ontology/concepts")
        existing = self._concepts.get(concept.concept_key)
        if existing is not None and (existing.level, existing.scope_id or "") != (
            concept.level,
            concept.scope_id or "",
        ):
            raise OntologyScopeConflictError(
                detail_code="ERR_ONTOLOGY_SCOPE_CONFLICT_DETAIL",
                detail_params={
                    "concept_key": concept.concept_key,
                    "existing_level": existing.level,
                    "existing_scope": existing.scope_id or "",
                    "level": concept.level,
                    "target_scope": concept.scope_id or "",
                },
            )
        self._concepts[concept.concept_key] = concept
        return concept

    def save_proposal(self, proposal: OntologyPromotionProposal) -> OntologyPromotionProposal:
        """Store or update an ontology promotion proposal in the service registry."""
        self._proposals[proposal.proposal_key] = proposal
        return proposal

    def extract_l4_concept(
        self,
        user: UserIdentity,
        *,
        concept_key: str,
        canonical_term: str,
        run_id: str,
        snapshot_id: str,
        definition_text: str,
        synonyms: tuple[str, ...] = (),
        target_promotion_level: OntologyLevel = "3_WORKSPACE",
        target_scope_id: str = "ws-solution-paiement",
    ) -> tuple[OntologyConceptEntity, OntologyPromotionProposal]:
        """Extract a new L4 concept bound to `snapshot_id` (`ACTIVE`) and create a proposal."""
        _assert_mutable_actor(user, "/api/v1/ontology-rag/ontology/extract-l4")

        concept = OntologyConceptEntity(
            id=new_uuid7_str(),
            concept_key=concept_key,
            canonical_term=canonical_term,
            level="4_RUN_EPHEMERAL",
            scope_id=run_id,
            definition_text=definition_text,
            synonyms=synonyms,
            introduced_in_snapshot_id=snapshot_id,
            snapshot_branch_status="ACTIVE",
        )
        self._concepts[concept_key] = concept
        impact = self.simulate_what_if(
            concept_key=concept_key,
            proposed_change=(
                f"Promote {canonical_term} from 4_RUN_EPHEMERAL to {target_promotion_level}"
            ),
        )
        proposal_key = f"prop-{concept_key}-to-{target_promotion_level.lower()}"
        proposal = OntologyPromotionProposal(
            id=new_uuid7_str(),
            proposal_key=proposal_key,
            concept_key=concept_key,
            canonical_term=canonical_term,
            source_level="4_RUN_EPHEMERAL",
            target_level=target_promotion_level,
            target_scope_id=target_scope_id,
            proposed_by_user_id=user.id,
            status="PENDING_REVIEW",
            impact_report=impact,
            badge_color_token="ontology-cyan",
        )
        self._proposals[proposal_key] = proposal
        return concept, proposal

    def mark_snapshot_branch_superseded(self, snapshot_id: str) -> int:
        """Mark all L4 concepts introduced in `snapshot_id` as `SUPERSEDED` after a Replay."""
        count = 0
        for key, c in list(self._concepts.items()):
            if c.level == "4_RUN_EPHEMERAL" and c.introduced_in_snapshot_id == snapshot_id:
                self._concepts[key] = OntologyConceptEntity(
                    id=c.id,
                    concept_key=c.concept_key,
                    canonical_term=c.canonical_term,
                    level=c.level,
                    scope_id=c.scope_id,
                    definition_text=c.definition_text,
                    parent_concept_id=c.parent_concept_id,
                    synonyms=c.synonyms,
                    banned_terms=c.banned_terms,
                    profile_translations=c.profile_translations,
                    expected_schema=c.expected_schema,
                    introduced_in_snapshot_id=c.introduced_in_snapshot_id,
                    snapshot_branch_status="SUPERSEDED",
                )
                count += 1
        return count

    def simulate_what_if(self, *, concept_key: str, proposed_change: str) -> WhatIfImpactReport:
        return ImpactSimulatorService.simulate_what_if(
            concept_key=concept_key,
            proposed_change=proposed_change,
            concepts=self.concepts,
            relations=self.relations,
            axioms=self.axioms,
            template_bindings=self._template_bindings,
            workflow_bindings=self._workflow_bindings,
            active_run_bindings=self._active_run_bindings,
        )

    def promote_concept(
        self,
        user: UserIdentity,
        *,
        proposal_key: str,
        org_units: Sequence[OrgUnitNode] = (),
        workspaces: Sequence[WorkspaceEntity] = (),
        memberships: Sequence[WorkspaceMembershipEntity] = (),
        allow_fixture_fallback: bool = False,
    ) -> OntologyPromotionProposal:
        _assert_mutable_actor(user, "/api/v1/ontology-rag/ontology/promote")
        return execute_promote_concept(
            self._concepts,
            self._proposals,
            user,
            proposal_key=proposal_key,
            org_units=org_units,
            workspaces=workspaces,
            memberships=memberships,
            allow_fixture_fallback=allow_fixture_fallback,
        )


__all__ = ["ImpactSimulatorService", "OntologyGovernanceService"]
