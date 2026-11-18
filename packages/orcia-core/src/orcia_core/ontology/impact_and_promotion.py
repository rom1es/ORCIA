"""ImpactSimulatorService (What-If) & L4 Branch-Isolated Ontology Governance (Story 2.2, AD-7).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from orcia_core.ontology.errors import (
    ObserverModeReadOnlyError,
    OntologyConflictError,
    OntologyScopeConflictError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
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
from orcia_core.ontology.permissions import (
    assert_can_review_promotion,
    can_write_ontology_level,
    user_effective_roles,
)
from orcia_core.ontology.resolver import OntologyHierarchyResolver
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
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
                detail_override=(
                    f"La clé '{concept.concept_key}' appartient déjà au périmètre "
                    f"({existing.level}, '{existing.scope_id}') et ne peut être écrasée "
                    f"depuis ({concept.level}, '{concept.scope_id}')."
                )
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

        proposal = self._proposals.get(proposal_key)
        if proposal is None:
            raise ResourceNotFoundError(detail_override=f"Proposal '{proposal_key}' not found.")
        if proposal.status != "PENDING_REVIEW":
            raise OntologyConflictError(
                detail_override=f"Proposal '{proposal_key}' has status '{proposal.status}'."
            )
        source_concept = self._concepts.get(proposal.concept_key)
        if source_concept is None:
            raise ResourceNotFoundError(
                detail_override=f"Concept '{proposal.concept_key}' not found."
            )
        if source_concept.snapshot_branch_status != "ACTIVE":
            raise OntologyConflictError(
                detail_override=(
                    f"Concept '{source_concept.concept_key}' belongs to a SUPERSEDED branch."
                )
            )
        if proposal.impact_report.has_immutable_axiom_conflict:
            raise OntologyConflictError(
                detail_override=(
                    f"Proposal '{proposal_key}' conflicts with an immutable parent axiom."
                )
            )
        roles = user_effective_roles(user)
        if proposal.target_level == "1_ENTERPRISE" and "PLATFORM_ADMIN" not in roles:
            raise ScopeAccessDeniedError(
                detail_override="Promotion to 1_ENTERPRISE requires PLATFORM_ADMIN."
            )
        if org_units or workspaces:
            if proposal.target_level in ("3_WORKSPACE", "4_WORKSPACE"):
                allowed_ws = can_write_ontology_level(
                    user,
                    proposal.target_level,
                    proposal.target_scope_id,
                    org_units,
                    workspaces,
                    memberships,
                    allow_ephemeral_fallback=(
                        allow_fixture_fallback
                        and proposal.target_scope_id == "ws-solution-paiement"
                    ),
                )
                if not allowed_ws:
                    raise ScopeAccessDeniedError(
                        detail_override=(
                            f"Validation refusée pour le palier {proposal.target_level} "
                            f"({proposal.target_scope_id})."
                        )
                    )
            else:
                assert_can_review_promotion(
                    user,
                    proposal.target_level,
                    proposal.target_scope_id,
                    org_units,
                    workspaces,
                    instance="/api/v1/ontology-rag/ontology/promote",
                )
        else:
            if proposal.target_level == "2_DOMAIN":
                if not (roles & {"PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR", "ONTOLOGY_LEAD"}):
                    raise ScopeAccessDeniedError(
                        detail_override=(
                            "Promotion to 2_DOMAIN requires PLATFORM_ADMIN, "
                            "BU_LEAD, or ONTOLOGY_LEAD."
                        )
                    )
                if (
                    "PLATFORM_ADMIN" not in roles
                    and user.primary_org_unit_id
                    and proposal.target_scope_id != user.primary_org_unit_id
                ):
                    raise ScopeAccessDeniedError(
                        detail_override=(
                            f"Validation refusée pour le palier 2_DOMAIN "
                            f"({proposal.target_scope_id})."
                        )
                    )
            elif proposal.target_level == "3_TEAM":
                team_review_roles = {
                    "PLATFORM_ADMIN",
                    "BU_LEAD",
                    "BU_DIRECTOR",
                    "ONTOLOGY_LEAD",
                    "TEAM_LEAD",
                }
                if not (roles & team_review_roles):
                    raise ScopeAccessDeniedError(
                        detail_override=(
                            "Promotion to 3_TEAM requires TEAM_LEAD, BU_LEAD, or ONTOLOGY_LEAD."
                        )
                    )
                if (
                    "PLATFORM_ADMIN" not in roles
                    and user.primary_org_unit_id
                    and proposal.target_scope_id != user.primary_org_unit_id
                ):
                    raise ScopeAccessDeniedError(
                        detail_override=(
                            f"Validation refusée pour le palier 3_TEAM "
                            f"({proposal.target_scope_id})."
                        )
                    )
        if (
            ONTOLOGY_LEVEL_PRIORITY[proposal.target_level]
            >= ONTOLOGY_LEVEL_PRIORITY[proposal.source_level]
        ):
            raise OntologyConflictError(
                detail_override=(
                    f"Target {proposal.target_level} must outrank {proposal.source_level}."
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
        approved = replace(proposal, status="APPROVED")
        self._proposals[proposal_key] = approved
        return approved
