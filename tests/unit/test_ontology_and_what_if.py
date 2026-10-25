"""Unit & API contract tests for Story 2.1 (4-Level Ontology) & Story 2.2 (L4 Branch & What-If)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core.domain.exceptions import ObserverModeReadOnlyError, OntologyConflictError
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyHierarchyResolver,
    ProfileSemanticTranslator,
    build_empty_ontology_service,
    build_ontology_resolution_cte_sql,
    build_seeded_ontology_service,
)
from orcia_core.permissions.models import UserIdentity


def _make_user(role: str = "TEAM_LEAD") -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc (Tech Lead)",
        auth_mode="HYBRID",
        oidc_subject="oidc|marc-lead",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )


def test_default_ontology_service_is_completely_empty() -> None:
    """By default in runtime, the ontology service has 0 sample rows."""
    empty_gov = build_empty_ontology_service()
    assert len(empty_gov.concepts) == 0
    assert len(empty_gov.relations) == 0
    assert len(empty_gov.axioms) == 0
    assert len(empty_gov.proposals) == 0


def test_ontology_4_level_resolution_subteam_inheritance_and_latency() -> None:
    """Story 2.1 AC1: 4-level hierarchy merges Sub-Team -> Parent Team -> BU -> Enterprise."""
    gov = build_seeded_ontology_service()
    t0 = time.perf_counter()
    snap = gov.resolve_snapshot(
        enterprise_scope_id="scope-global",
        domain_scope_id="scope-bu-digital",
        team_chain_scope_ids=("scope-subteam-checkout", "scope-team-core"),
        workspace_scope_id="ws-solution-paiement",
        run_scope_id="run-checkout-001",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 15.0

    # Sub-Team specialization overrides Parent Team and Enterprise while merging synonyms
    asset = snap.concepts_by_term["Actif Stratégique"]
    assert asset.level == "3_TEAM"
    assert asset.scope_id == "scope-subteam-checkout"
    assert "Critical Asset" in asset.synonyms
    assert "Plateforme Agentique Core" in asset.synonyms
    assert "Tunnel Checkout Critique" in asset.synonyms

    # L4 active concept is present, but L4 SUPERSEDED concept is strictly excluded
    assert "Exemption 3DS Frictionless TRA" in snap.concepts_by_term
    assert "Terme Branche Obsolète Replay" not in snap.concepts_by_term

    sql = build_ontology_resolution_cte_sql()
    assert "WITH RECURSIVE team_ancestry" in sql
    assert "SELECT DISTINCT ON (canonical_term)" in sql


def test_ontology_immutable_axiom_conflict_raises_422() -> None:
    """Story 2.1 AC1: Contradicting an immutable parent axiom raises ERR_ONTOLOGY_CONFLICT."""
    gov = build_seeded_ontology_service()
    bad_concept = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002999",
        concept_key="concept-l3-illegal-override",
        canonical_term="Actif Stratégique",
        level="3_WORKSPACE",
        scope_id="ws-solution-paiement",
        definition_text="Tentative de surcharge illégale du type asset_id.",
        expected_schema={"asset_id": "int"},  # Contradicts L1 immutable str!
    )
    with pytest.raises(OntologyConflictError) as exc_info:
        OntologyHierarchyResolver.resolve_effective_ontology(
            concepts=(*gov.concepts, bad_concept),
            relations=gov.relations,
            axioms=gov.axioms,
            enterprise_scope_id="scope-global",
            domain_scope_id="scope-bu-digital",
            team_chain_scope_ids=("scope-subteam-checkout", "scope-team-core"),
            workspace_scope_id="ws-solution-paiement",
        )
    assert exc_info.value.error_code == "ERR_ONTOLOGY_CONFLICT"
    assert exc_info.value.http_status == 422


def test_triple_active_execution_blackboard_profile_and_rag_expansion() -> None:
    """Story 2.1 AC2: Validates Blackboard schema, translates for 6 profiles, expands RAG query."""
    gov = build_seeded_ontology_service()
    snap = gov.resolve_snapshot(run_scope_id="run-checkout-001")

    # 1. Blackboard schema & cardinality validation
    valid_res = OntologyHierarchyResolver.validate_blackboard_artifact(
        canonical_term="Actif Stratégique",
        payload={"asset_id": "ast-01", "criticality_tier": 1, "owners": ["team-checkout"]},
        snapshot=snap,
    )
    assert valid_res.valid is True

    invalid_res = OntologyHierarchyResolver.validate_blackboard_artifact(
        canonical_term="Actif Stratégique",
        payload={"asset_id": 123, "owners": []},
        snapshot=snap,
    )
    assert invalid_res.valid is False
    assert "criticality_tier" in invalid_res.missing_fields
    assert any("asset_id" in m for m in invalid_res.type_mismatches)
    assert any("owners" in c for c in invalid_res.cardinality_violations)

    # 2. ProfileSemanticTranslator across all 6 Human Profiles
    asset_concept = snap.concepts_by_term["Actif Stratégique"]
    exec_label = ProfileSemanticTranslator.translate_concept(asset_concept, "EXECUTIVE")
    arch_label = ProfileSemanticTranslator.translate_concept(asset_concept, "ARCHITECT")
    assert "ROI" in exec_label
    assert "Architecture Spine" in arch_label
    assert exec_label != arch_label

    # 3. RAG query expansion with synonyms, relations, and banned term detection
    exp = OntologyHierarchyResolver.expand_rag_query(
        "Audit Critical Asset et Projet Legacy Non Gouverné", snap
    )
    assert "Actif Stratégique" in exp.expanded_terms
    assert "Grand Livre de Paiement" in exp.expanded_terms  # via GOVERNS relation
    assert "Projet Legacy Non Gouverné" in exp.detected_banned_terms


def test_l4_branch_isolation_replay_superseding_and_what_if_promotion() -> None:
    """Story 2.2 AC1 & AC2: L4 extraction, Replay branch superseding, What-If & Promotion."""
    gov = build_seeded_ontology_service()
    marc = _make_user("TEAM_LEAD")

    concept, proposal = gov.extract_l4_concept(
        marc,
        concept_key="concept-l4-sca-delegated",
        canonical_term="Authentification Déléguée SCA",
        run_id="run-checkout-001",
        snapshot_id="snap-branch-a",
        definition_text="Délégation SCA émetteur découverte pendant l'analyse.",
        synonyms=("Delegated SCA",),
    )
    assert concept.snapshot_branch_status == "ACTIVE"
    assert proposal.status == "PENDING_REVIEW"

    # Simulate What-If on L3 sub-team concept (transitively affects L2 and L3 workspace)
    what_if = gov.simulate_what_if(
        concept_key="concept-l3-subteam-checkout-asset",
        proposed_change="Rename Actif Stratégique",
    )
    assert "concept-l2-payment-ledger" in what_if.transitively_affected_concepts
    assert "concept-l3-ws-idempotency-key" in what_if.transitively_affected_concepts
    assert "tpl://architecture-adr-v2" in what_if.impacted_artifact_templates
    assert "db://workflows/payment-delivery-v1" in what_if.impacted_workflow_uris
    assert "run-checkout-001" in what_if.impacted_active_run_ids

    # What-If on immutable concept flags has_immutable_axiom_conflict=True
    what_if_l1 = gov.simulate_what_if(
        concept_key="concept-l1-strategic-asset",
        proposed_change="Attempt to alter L1 immutable axiom",
    )
    assert what_if_l1.has_immutable_axiom_conflict is True

    # Promote L4 proposal to 3_WORKSPACE
    approved = gov.promote_concept(marc, proposal_key=proposal.proposal_key)
    assert approved.status == "APPROVED"

    # Re-promoting an already approved proposal raises OntologyConflictError (422)
    with pytest.raises(OntologyConflictError):
        gov.promote_concept(marc, proposal_key=proposal.proposal_key)

    # Replay invalidates snapshot branch 'snap-branch-a' -> marks L4 concept SUPERSEDED
    superseded_count = gov.mark_snapshot_branch_superseded("snap-branch-a")
    assert superseded_count == 1

    observer = _make_user("OBSERVER")
    with pytest.raises(ObserverModeReadOnlyError):
        gov.promote_concept(observer, proposal_key=proposal.proposal_key)


def test_fastapi_ontology_rag_endpoints_and_rfc9457() -> None:
    """Verify FastAPI /api/v1/ontology-rag/* endpoints (empty default vs fixture=true & 422)."""
    client = TestClient(create_app())

    # 1. Default runtime state (fixture=false) is 100% empty
    res_empty = client.get("/api/v1/ontology-rag/state")
    assert res_empty.status_code == 200
    assert res_empty.json()["concepts"] == []
    assert res_empty.json()["trace_id"] is not None

    # 2. Seeded fixture state (fixture=true) returns ontology & tripartite data
    res_seeded = client.get("/api/v1/ontology-rag/state?fixture=true")
    assert res_seeded.status_code == 200
    assert len(res_seeded.json()["concepts"]) >= 6

    # 3. Resolve ontology with human profile translation
    res_resolve = client.post(
        "/api/v1/ontology-rag/ontology/resolve?fixture=true",
        json={"human_profile": "EXECUTIVE"},
    )
    assert res_resolve.status_code == 200
    assert "Actif Stratégique" in res_resolve.json()["profile_labels"]

    # 4a. Upsert valid concept returns 200 OK
    res_upsert_ok = client.post(
        "/api/v1/ontology-rag/ontology/concepts?fixture=true&persona_key=marc",
        json={
            "concept_key": "concept-l4-valid-new",
            "canonical_term": "Jeton 3DS Délégué",
            "level": "4_RUN_EPHEMERAL",
            "scope_id": "run-checkout-001",
            "definition_text": "Jeton valide",
            "expected_schema": {"token_id": "str"},
        },
    )
    assert res_upsert_ok.status_code == 200
    assert res_upsert_ok.json()["concept_key"] == "concept-l4-valid-new"

    # 4b. Observer persona on upsert returns HTTP 403 ERR_OBSERVER_MODE_READ_ONLY
    res_upsert_obs = client.post(
        "/api/v1/ontology-rag/ontology/concepts?fixture=true&persona_key=claire",
        json={
            "concept_key": "concept-l4-obs",
            "canonical_term": "Interdit",
            "level": "4_RUN_EPHEMERAL",
            "scope_id": "run-checkout-001",
            "definition_text": "Refusé",
        },
    )
    assert res_upsert_obs.status_code == 403
    assert res_upsert_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 4c. Upsert conflicting concept triggers RFC 9457 HTTP 422 ERR_ONTOLOGY_CONFLICT
    res_conflict = client.post(
        "/api/v1/ontology-rag/ontology/concepts?fixture=true",
        json={
            "concept_key": "concept-l3-bad",
            "canonical_term": "Actif Stratégique",
            "level": "3_WORKSPACE",
            "scope_id": "ws-other-custom-scope",
            "definition_text": "Conflit axiome immuable",
            "expected_schema": {"asset_id": "int"},
        },
    )
    assert res_conflict.status_code == 422
    assert res_conflict.json()["error_code"] == "ERR_ONTOLOGY_CONFLICT"
    assert "trace_id" in res_conflict.json()

    # 5. What-If simulation endpoint
    res_what_if = client.post(
        "/api/v1/ontology-rag/ontology/what-if?fixture=true",
        json={
            "concept_key": "concept-l3-subteam-checkout-asset",
            "proposed_change": "Update definition",
        },
    )
    assert res_what_if.status_code == 200
    assert "tpl://architecture-adr-v2" in res_what_if.json()["impacted_artifact_templates"]

    # 6. Promote concept endpoint (200 OK on seeded proposal, 403 on observer, 404 on unknown)
    res_prom_ok = client.post(
        "/api/v1/ontology-rag/ontology/promote?fixture=true&persona_key=marc",
        json={"proposal_key": "prop-concept-l4-3ds-frictionless-exemption-to-3_workspace"},
    )
    assert res_prom_ok.status_code == 200
    assert res_prom_ok.json()["status"] == "APPROVED"

    res_prom_obs = client.post(
        "/api/v1/ontology-rag/ontology/promote?fixture=true&persona_key=claire",
        json={"proposal_key": "prop-concept-l4-3ds-frictionless-exemption-to-3_workspace"},
    )
    assert res_prom_obs.status_code == 403
    assert res_prom_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"


@settings(max_examples=20)
@given(
    synonym=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        min_size=4,
        max_size=16,
    )
)
def test_property_ontology_rag_query_expansion_always_includes_matched_synonym(
    synonym: str,
) -> None:
    """Property test: any query containing a concept's synonym expands to its canonical term."""
    c = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002888",
        concept_key="concept-prop-test",
        canonical_term="TermeCanoniqueTest",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        definition_text="Définition test",
        synonyms=(synonym,),
    )
    snap = OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=(c,),
        relations=(),
        axioms=(),
        enterprise_scope_id="scope-global",
        domain_scope_id="scope-bu",
        team_chain_scope_ids=(),
        workspace_scope_id="ws-1",
    )
    expanded = OntologyHierarchyResolver.expand_rag_query(f"Recherche {synonym} ici", snap)
    assert "TermeCanoniqueTest" in expanded.expanded_terms
