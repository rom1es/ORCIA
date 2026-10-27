"""ImpactSimulatorService (What-If) & L4 Branch-Isolated Ontology Governance (Story 2.2, AD-7).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from orcia_core.ontology.errors import (
    ObserverModeReadOnlyError,
    OntologyConflictError,
    ResourceNotFoundError,
)
from orcia_core.ontology.models import (
    ONTOLOGY_LEVEL_PRIORITY,
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyLevel,
    OntologyPromotionProposal,
    OntologyRelationEntity,
    ResolvedOntologySnapshot,
    WhatIfImpactReport,
)
from orcia_core.ontology.resolver import OntologyHierarchyResolver
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str


class ImpactSimulatorService:
    """Graph traversal What-If impact simulator over relations, templates, workflows, and runs."""

    @staticmethod
    def simulate_what_if(
        *,
        concept_key: str,
        proposed_change: str,
        concepts: tuple[OntologyConceptEntity, ...],
        relations: tuple[OntologyRelationEntity, ...],
        axioms: tuple[OntologyAxiomEntity, ...],
        template_bindings: dict[str, tuple[str, ...]],
        workflow_bindings: dict[str, tuple[str, ...]],
        active_run_bindings: dict[str, tuple[str, ...]],
        violates_immutable_axiom: bool = False,
    ) -> WhatIfImpactReport:
        concept = next((c for c in concepts if c.concept_key == concept_key), None)
        if concept is None:
            raise ResourceNotFoundError(detail_override=f"Concept '{concept_key}' not found.")

        # Graph BFS traversal over ontology_relations
        visited: list[str] = [concept_key]
        frontier: list[str] = [concept_key]
        while frontier:
            curr = frontier.pop(0)
            for rel in relations:
                if rel.source_concept_key == curr and rel.target_concept_key not in visited:
                    visited.append(rel.target_concept_key)
                    frontier.append(rel.target_concept_key)

        transitively_affected = tuple(k for k in visited if k != concept_key)
        affected_set = set(visited)

        impacted_templates = tuple(
            tpl
            for tpl, bound_keys in sorted(template_bindings.items())
            if affected_set.intersection(bound_keys)
        )
        impacted_workflows = tuple(
            wf
            for wf, bound_keys in sorted(workflow_bindings.items())
            if affected_set.intersection(bound_keys)
        )
        impacted_runs = tuple(
            run_id
            for run_id, bound_keys in sorted(active_run_bindings.items())
            if affected_set.intersection(bound_keys)
        )

        concept_by_id = {c.id: c for c in concepts}
        concept_by_key = {c.concept_key: c for c in concepts}
        ancestor_keys: set[str] = {concept_key}
        cursor_id = concept.parent_concept_id
        while cursor_id and cursor_id in concept_by_id:
            parent_c = concept_by_id[cursor_id]
            if parent_c.concept_key in ancestor_keys:
                break
            ancestor_keys.add(parent_c.concept_key)
            cursor_id = parent_c.parent_concept_id

        for other_c in concepts:
            if other_c.canonical_term == concept.canonical_term and (
                ONTOLOGY_LEVEL_PRIORITY[other_c.level] <= ONTOLOGY_LEVEL_PRIORITY[concept.level]
            ):
                ancestor_keys.add(other_c.concept_key)

        has_immutable = violates_immutable_axiom or any(
            ax.immutable and ax.concept_key in ancestor_keys and ax.concept_key in concept_by_key
            for ax in axioms
        )
        return WhatIfImpactReport(
            concept_key=concept_key,
            canonical_term=concept.canonical_term,
            proposed_change=proposed_change,
            transitively_affected_concepts=transitively_affected,
            impacted_artifact_templates=impacted_templates,
            impacted_workflow_uris=impacted_workflows,
            impacted_active_run_ids=impacted_runs,
            has_immutable_axiom_conflict=has_immutable,
        )


def _assert_mutable_actor(user: UserIdentity, instance: str) -> None:
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
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
        self._concepts[concept.concept_key] = concept
        return concept

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
    ) -> OntologyPromotionProposal:
        _assert_mutable_actor(user, "/api/v1/ontology-rag/ontology/promote")

        proposal = self._proposals.get(proposal_key)
        if proposal is None:
            raise ResourceNotFoundError(detail_override=f"Proposal '{proposal_key}' not found.")
        if proposal.status != "PENDING_REVIEW":
            raise OntologyConflictError(
                detail_override=(
                    f"Proposal '{proposal_key}' has status '{proposal.status}' "
                    "and cannot be promoted."
                )
            )

        source_concept = self._concepts.get(proposal.concept_key)
        if source_concept is None:
            raise ResourceNotFoundError(
                detail_override=f"Concept '{proposal.concept_key}' not found."
            )
        if source_concept.snapshot_branch_status != "ACTIVE":
            raise OntologyConflictError(
                detail_override=(
                    f"Concept '{source_concept.concept_key}' belongs to a SUPERSEDED branch "
                    "and cannot be promoted."
                )
            )
        if proposal.impact_report.has_immutable_axiom_conflict:
            raise OntologyConflictError(
                detail_override=(
                    f"Proposal '{proposal_key}' conflicts with an immutable parent axiom."
                )
            )
        if proposal.target_level in ("1_ENTERPRISE", "2_DOMAIN") and user.platform_role not in (
            "SYSTEM_ADMIN",
            "ONTOLOGY_STEWARD_L1_L2",
        ):
            raise OntologyConflictError(
                detail_override=(
                    f"Promotion to {proposal.target_level} requires SYSTEM_ADMIN or "
                    "ONTOLOGY_STEWARD_L1_L2."
                )
            )

        if (
            ONTOLOGY_LEVEL_PRIORITY[proposal.target_level]
            >= ONTOLOGY_LEVEL_PRIORITY[proposal.source_level]
        ):
            raise OntologyConflictError(
                detail_override=(
                    f"Promotion target {proposal.target_level} must be a higher governance "
                    f"level than {proposal.source_level}."
                )
            )

        promoted_key = f"{proposal.concept_key}-{proposal.target_level.lower()}"
        self._concepts[promoted_key] = OntologyConceptEntity(
            id=new_uuid7_str(),
            concept_key=promoted_key,
            canonical_term=source_concept.canonical_term,
            level=proposal.target_level,
            scope_id=proposal.target_scope_id,
            definition_text=source_concept.definition_text,
            parent_concept_id=source_concept.id,
            synonyms=source_concept.synonyms,
            banned_terms=source_concept.banned_terms,
            profile_translations=source_concept.profile_translations,
            expected_schema=source_concept.expected_schema,
            snapshot_branch_status="ACTIVE",
        )
        approved = OntologyPromotionProposal(
            id=proposal.id,
            proposal_key=proposal.proposal_key,
            concept_key=proposal.concept_key,
            canonical_term=proposal.canonical_term,
            source_level=proposal.source_level,
            target_level=proposal.target_level,
            target_scope_id=proposal.target_scope_id,
            proposed_by_user_id=proposal.proposed_by_user_id,
            status="APPROVED",
            impact_report=proposal.impact_report,
            badge_color_token=proposal.badge_color_token,
        )
        self._proposals[proposal_key] = approved
        return approved
