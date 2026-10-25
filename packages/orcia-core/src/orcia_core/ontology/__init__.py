"""4-Level Dynamic Ontology, CTE Inheritance, Active Triple Execution & What-If Simulation."""

from __future__ import annotations

from orcia_core.ontology.impact_and_promotion import (
    ImpactSimulatorService,
    OntologyGovernanceService,
)
from orcia_core.ontology.models import (
    ONTOLOGY_LEVEL_PRIORITY,
    BlackboardSchemaValidationResult,
    ExpandedRagQuery,
    HumanProfileArchetype,
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyLevel,
    OntologyPromotionProposal,
    OntologyRelationEntity,
    PromotionStatus,
    ResolvedOntologySnapshot,
    SnapshotBranchStatus,
    WhatIfImpactReport,
)
from orcia_core.ontology.resolver import (
    OntologyHierarchyResolver,
    ProfileSemanticTranslator,
    build_ontology_resolution_cte_sql,
)

DOMAIN_NAME: str = "ontology"


def build_empty_ontology_service() -> OntologyGovernanceService:
    """Build an empty OntologyGovernanceService (default Day-0 runtime with 0 sample rows)."""
    return OntologyGovernanceService()


def build_seeded_ontology_service() -> OntologyGovernanceService:
    """Build a test-seeded OntologyGovernanceService for automated unit/contract tests."""
    c_l1 = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002001",
        concept_key="concept-l1-strategic-asset",
        canonical_term="Actif Stratégique",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        definition_text="Actif critique du SI Groupe soumis aux exigences d'audit PCI-DSS/DORA.",
        synonyms=("Critical Asset", "Brique Critique Groupe"),
        banned_terms=("Projet Legacy Non Gouverné",),
        profile_translations={
            "EXECUTIVE": "Actif Stratégique (ROI & Risque Réglementaire DORA/PCI-DSS)",
            "PM_BUSINESS": "Produit Cœur Métier à SLA Critique (99.99%)",
            "ARCHITECT": "Composant Tier-1 sous contrat Architecture Spine immuable",
            "TECH_LEAD": "Service Tier-1 (Couverture >= 90%, 0-diff OpenAPI)",
            "DEVELOPER": "Module critique sous garde-fous CI/CD stricts",
            "SECOPS": "Périmètre régulé PCI-DSS / Audit Ledger Append-Only",
        },
        expected_schema={"asset_id": "str", "criticality_tier": "int", "owners": "non_empty_list"},
    )
    c_l2 = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002002",
        concept_key="concept-l2-payment-ledger",
        canonical_term="Grand Livre de Paiement",
        level="2_DOMAIN",
        scope_id="scope-bu-digital",
        parent_concept_id=c_l1.id,
        definition_text="Journal comptable immuable des transactions de la BU Digital & Paiements.",
        synonyms=("Payment Ledger", "Journal Transactionnel"),
        profile_translations={
            "EXECUTIVE": "Grand Livre Financier Consolidé BU",
            "ARCHITECT": "Event-Sourced Ledger Append-Only (PostgreSQL 18)",
        },
        expected_schema={"ledger_id": "str", "currency": "str"},
    )
    c_l3_parent_team = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002003",
        concept_key="concept-l3-team-parent-asset",
        canonical_term="Actif Stratégique",
        level="3_TEAM",
        scope_id="scope-team-core",
        parent_concept_id=c_l1.id,
        definition_text="Actif Stratégique décliné par l'Équipe Parente Architecture.",
        synonyms=("Plateforme Agentique Core",),
        expected_schema={"asset_id": "str", "criticality_tier": "int", "owners": "non_empty_list"},
    )
    c_l3_sub_team = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002004",
        concept_key="concept-l3-subteam-checkout-asset",
        canonical_term="Actif Stratégique",
        level="3_TEAM",
        scope_id="scope-subteam-checkout",
        parent_concept_id=c_l3_parent_team.id,
        definition_text="Actif Stratégique spécialisé par la Sous-Équipe Checkout.",
        synonyms=("Microservice Tier-1", "Tunnel Checkout Critique"),
        expected_schema={"asset_id": "str", "criticality_tier": "int", "owners": "non_empty_list"},
    )
    c_l3_workspace = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002005",
        concept_key="concept-l3-ws-idempotency-key",
        canonical_term="Clé d'Idempotence Paiement",
        level="3_WORKSPACE",
        scope_id="ws-solution-paiement",
        parent_concept_id=c_l2.id,
        definition_text="Jeton UUIDv7 garantissant l'exécution unique d'une capture PSP.",
        synonyms=("Idempotency-Key", "Capture Dedup Token"),
        expected_schema={"idempotency_key": "str", "ttl_seconds": "int"},
    )
    c_l4_active = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002006",
        concept_key="concept-l4-3ds-frictionless-exemption",
        canonical_term="Exemption 3DS Frictionless TRA",
        level="4_RUN_EPHEMERAL",
        scope_id="run-checkout-001",
        definition_text="Règle d'exemption Transaction Risk Analysis découverte durant le Run.",
        synonyms=("TRA Exemption DSP2",),
        introduced_in_snapshot_id="snap-active-001",
        snapshot_branch_status="ACTIVE",
    )
    c_l4_superseded = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002007",
        concept_key="concept-l4-obsolete-branch-term",
        canonical_term="Terme Branche Obsolète Replay",
        level="4_RUN_EPHEMERAL",
        scope_id="run-checkout-001",
        definition_text="Concept issu d'un snapshot annulé après Replay (ne doit jamais fuiter).",
        introduced_in_snapshot_id="snap-superseded-000",
        snapshot_branch_status="SUPERSEDED",
    )

    rel_1 = OntologyRelationEntity(
        id="0192c4e0-0000-7000-8000-000000002101",
        relation_key="rel-asset-governs-ledger",
        source_concept_key=c_l3_sub_team.concept_key,
        target_concept_key=c_l2.concept_key,
        relation_type="GOVERNS",
        cardinality="1..N",
    )
    rel_2 = OntologyRelationEntity(
        id="0192c4e0-0000-7000-8000-000000002102",
        relation_key="rel-ledger-requires-idempotency",
        source_concept_key=c_l2.concept_key,
        target_concept_key=c_l3_workspace.concept_key,
        relation_type="REQUIRES",
        cardinality="1..1",
    )

    ax_immutable = OntologyAxiomEntity(
        id="0192c4e0-0000-7000-8000-000000002201",
        axiom_key="axiom-l1-strategic-asset-immutable-schema",
        concept_key=c_l1.concept_key,
        level="1_ENTERPRISE",
        scope_id="scope-global",
        rule_expression=(
            "IMMUTABLE_SCHEMA(asset_id:str, criticality_tier:int, owners:non_empty_list)"
        ),
        immutable=True,
    )

    prop_l4 = OntologyPromotionProposal(
        id="0192c4e0-0000-7000-8000-000000002301",
        proposal_key="prop-concept-l4-3ds-frictionless-exemption-to-3_workspace",
        concept_key=c_l4_active.concept_key,
        canonical_term=c_l4_active.canonical_term,
        source_level="4_RUN_EPHEMERAL",
        target_level="3_WORKSPACE",
        target_scope_id="ws-solution-paiement",
        proposed_by_user_id="0192c4e0-0000-7000-8000-000000000102",
        status="PENDING_REVIEW",
        impact_report=WhatIfImpactReport(
            concept_key=c_l4_active.concept_key,
            canonical_term=c_l4_active.canonical_term,
            proposed_change="Promote Exemption 3DS Frictionless TRA to 3_WORKSPACE",
            transitively_affected_concepts=(),
            impacted_artifact_templates=("tpl://payment-api-contract",),
            impacted_workflow_uris=("db://workflows/payment-delivery-v1",),
            impacted_active_run_ids=("run-checkout-001",),
            has_immutable_axiom_conflict=False,
        ),
        badge_color_token="ontology-cyan",
    )

    return OntologyGovernanceService(
        concepts=(
            c_l1,
            c_l2,
            c_l3_parent_team,
            c_l3_sub_team,
            c_l3_workspace,
            c_l4_active,
            c_l4_superseded,
        ),
        relations=(rel_1, rel_2),
        axioms=(ax_immutable,),
        proposals=(prop_l4,),
        template_bindings={
            "tpl://architecture-adr-v2": (
                c_l1.concept_key,
                c_l3_sub_team.concept_key,
                c_l2.concept_key,
            ),
            "tpl://payment-api-contract": (c_l3_workspace.concept_key, c_l4_active.concept_key),
        },
        workflow_bindings={
            "db://workflows/payment-delivery-v1": (
                c_l2.concept_key,
                c_l3_workspace.concept_key,
                c_l4_active.concept_key,
            ),
        },
        active_run_bindings={
            "run-checkout-001": (c_l3_workspace.concept_key, c_l4_active.concept_key),
        },
    )


__all__ = [
    "ONTOLOGY_LEVEL_PRIORITY",
    "BlackboardSchemaValidationResult",
    "ExpandedRagQuery",
    "HumanProfileArchetype",
    "ImpactSimulatorService",
    "OntologyAxiomEntity",
    "OntologyConceptEntity",
    "OntologyGovernanceService",
    "OntologyHierarchyResolver",
    "OntologyLevel",
    "OntologyPromotionProposal",
    "OntologyRelationEntity",
    "ProfileSemanticTranslator",
    "PromotionStatus",
    "ResolvedOntologySnapshot",
    "SnapshotBranchStatus",
    "WhatIfImpactReport",
    "build_empty_ontology_service",
    "build_ontology_resolution_cte_sql",
    "build_seeded_ontology_service",
]
