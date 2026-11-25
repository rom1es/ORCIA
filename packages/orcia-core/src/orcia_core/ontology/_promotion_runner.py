"""In-memory ontology promotion validation & approval helper."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from orcia_core.ontology.errors import (
    OntologyConflictError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.ontology.models import (
    ONTOLOGY_LEVEL_PRIORITY,
    OntologyConceptEntity,
    OntologyPromotionProposal,
)
from orcia_core.ontology.permissions import (
    assert_can_review_promotion,
    can_write_ontology_level,
    user_effective_roles,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_kernel.ids import new_uuid7_str


def execute_promote_concept(
    concepts: dict[str, OntologyConceptEntity],
    proposals: dict[str, OntologyPromotionProposal],
    user: UserIdentity,
    *,
    proposal_key: str,
    org_units: Sequence[OrgUnitNode] = (),
    workspaces: Sequence[WorkspaceEntity] = (),
    memberships: Sequence[WorkspaceMembershipEntity] = (),
    allow_fixture_fallback: bool = False,
) -> OntologyPromotionProposal:
    """Validate actor authority, enforce axiom/hierarchy rules, and approve promotion."""
    proposal = proposals.get(proposal_key)
    if proposal is None:
        raise ResourceNotFoundError(detail_override=f"Proposal '{proposal_key}' not found.")
    if proposal.status != "PENDING_REVIEW":
        raise OntologyConflictError(
            detail_override=f"Proposal '{proposal_key}' has status '{proposal.status}'."
        )
    source_concept = concepts.get(proposal.concept_key)
    if source_concept is None:
        raise ResourceNotFoundError(detail_override=f"Concept '{proposal.concept_key}' not found.")
    if source_concept.snapshot_branch_status != "ACTIVE":
        raise OntologyConflictError(
            detail_override=(
                f"Concept '{source_concept.concept_key}' belongs to a SUPERSEDED branch."
            )
        )
    if proposal.impact_report.has_immutable_axiom_conflict:
        raise OntologyConflictError(
            detail_override=(f"Proposal '{proposal_key}' conflicts with an immutable parent axiom.")
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
                    allow_fixture_fallback and proposal.target_scope_id == "ws-solution-paiement"
                ),
            )
            if not allowed_ws:
                raise ScopeAccessDeniedError(
                    detail_code="ERR_ONTOLOGY_VALIDATION_DENIED",
                    detail_params={
                        "target_level": proposal.target_level,
                        "target_scope_id": proposal.target_scope_id,
                    },
                )
        else:
            assert_can_review_promotion(
                user,
                proposal.target_level,
                proposal.target_scope_id,
                org_units,
                workspaces,
                memberships,
                source_scope_id=proposal.source_scope_id,
                instance="/api/v1/ontology-rag/ontology/promote",
            )
    else:
        _check_fallback_roles(user, roles, proposal)

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
    concepts[promoted_key] = OntologyConceptEntity(
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
    proposals[proposal_key] = approved
    return approved


def _check_fallback_roles(
    user: UserIdentity,
    roles: frozenset[str],
    proposal: OntologyPromotionProposal,
) -> None:
    if proposal.target_level == "2_DOMAIN":
        if not (roles & {"PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR", "ONTOLOGY_LEAD"}):
            raise ScopeAccessDeniedError(
                detail_override=(
                    "Promotion to 2_DOMAIN requires PLATFORM_ADMIN, BU_LEAD, or ONTOLOGY_LEAD."
                )
            )
        if (
            "PLATFORM_ADMIN" not in roles
            and user.primary_org_unit_id
            and proposal.target_scope_id != user.primary_org_unit_id
        ):
            raise ScopeAccessDeniedError(
                detail_code="ERR_ONTOLOGY_VALIDATION_DENIED",
                detail_params={
                    "target_level": "2_DOMAIN",
                    "target_scope_id": proposal.target_scope_id,
                },
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
                detail_code="ERR_ONTOLOGY_VALIDATION_DENIED",
                detail_params={
                    "target_level": "3_TEAM",
                    "target_scope_id": proposal.target_scope_id,
                },
            )


__all__ = ["execute_promote_concept"]
