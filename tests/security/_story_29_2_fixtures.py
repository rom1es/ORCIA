"""Shared isolated app & confidential/PRIVATE_USER fixtures for Story 29.2 security tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Request
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_api.dependencies import (
    get_embedding_port,
    get_ontology_and_rag_services,
    require_rag_available,
)
from orcia_api.main import create_app
from orcia_core.ontology.models import (
    OntologyConceptEntity,
    OntologyPromotionProposal,
    WhatIfImpactReport,
)
from orcia_core.permissions.models import WorkspaceDatasourceEntity, WorkspaceEntity
from orcia_core.rag.models import TripartiteTraceEdgeEntity

WS_CONF_ID = "0192c4e0-0000-7000-8000-000000000203"
WS_PRIV_ID = "0195f292-0000-7000-8000-000000000299"


def build_confidential_isolation_app(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Create isolated app with confidential 3_WORKSPACE, PRIVATE_USER, proposal & edge."""
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")

    app = create_app()
    fake_emb = FakeDeterministicEmbeddingAdapter()
    app.state.embedding_port = fake_emb
    app.dependency_overrides[get_embedding_port] = lambda: fake_emb
    app.dependency_overrides[require_rag_available] = lambda: fake_emb

    dummy_req = Request({"type": "http", "app": app, "headers": []})
    gov, _, trip = get_ontology_and_rag_services(dummy_req, fixture=False)
    gov._concepts["secret_merger_codename"] = OntologyConceptEntity(
        id="0195f292-0000-7000-8000-000000000901",
        concept_key="secret_merger_codename",
        canonical_term="Projet Phoenix Confidentiel",
        level="3_WORKSPACE",
        scope_id=WS_CONF_ID,
        parent_concept_id=None,
        definition_text="Confidentiel strict",
    )
    gov._concepts["private_marc_term"] = OntologyConceptEntity(
        id="0195f292-0000-7000-8000-000000000905",
        concept_key="private_marc_term",
        canonical_term="Terme Personnel Marc",
        level="4_WORKSPACE",
        scope_id=WS_PRIV_ID,
        parent_concept_id=None,
        definition_text="Privé Marc",
    )
    gov._proposals["prop-conf-292"] = OntologyPromotionProposal(
        id="0195f292-0000-7000-8000-000000000902",
        proposal_key="prop-conf-292",
        concept_key="secret_merger_codename",
        canonical_term="Projet Phoenix Confidentiel",
        source_level="3_WORKSPACE",
        source_scope_id=WS_CONF_ID,
        target_level="3_TEAM",
        target_scope_id="0192c4e0-0000-7000-8000-000000000103",
        proposed_by_user_id="0192c4e0-0000-7000-8000-000000000302",
        status="PENDING_REVIEW",
        impact_report=WhatIfImpactReport(
            concept_key="secret_merger_codename",
            canonical_term="Projet Phoenix Confidentiel",
            proposed_change="Promote confidential term",
            transitively_affected_concepts=(),
            impacted_artifact_templates=(),
            impacted_workflow_uris=(),
            impacted_active_run_ids=(),
            has_immutable_axiom_conflict=False,
        ),
        badge_color_token="cyan",
        source_concept_id="0195f292-0000-7000-8000-000000000901",
        definition_text="Confidentiel strict",
    )
    trip._edges.append(
        TripartiteTraceEdgeEntity(
            id="0195f292-0000-7000-8000-000000000903",
            edge_key="unknown-ws-edge-292",
            workspace_id="0195f292-0000-7000-8000-999999999999",
            source_uri="confluence://SECRET/1",
            source_node_type="CONFLUENCE_PAGE",
            target_uri="git://secret/repo#secret_fn",
            target_node_type="GIT_SYMBOL",
            relation_type="IMPLEMENTS",
        )
    )

    auth_svc = app.state.auth_service
    ws_conf = auth_svc.evaluator.get_workspace(WS_CONF_ID)
    assert ws_conf is not None
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_conf.id,
            slug=ws_conf.slug,
            name=ws_conf.name,
            owner_org_unit_id=ws_conf.owner_org_unit_id,
            visibility_mode=ws_conf.visibility_mode,
            finops_cost_usd=ws_conf.finops_cost_usd,
            datasources=(
                WorkspaceDatasourceEntity(
                    id="0195f292-0000-7000-8000-000000000904",
                    workspace_id=ws_conf.id,
                    alias="secret-git-repo",
                    scheme="git",
                    uri="git://secret.internal/merger.git",
                    role="CODE_REPOSITORY",
                    execution_identity="passthrough",
                    freshness_ttl_days=14,
                ),
            ),
        )
    )
    marc = auth_svc.resolve_user(persona_key="marc")
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=WS_PRIV_ID,
            slug=f"personal-{marc.id}",
            name="Espace personnel — Marc",
            owner_org_unit_id=marc.primary_org_unit_id,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            finops_cost_usd=12.0,
            personal_owner_user_id=marc.id,
            ui_visibility_mode="PRIVATE_USER",
        )
    )
    return app
