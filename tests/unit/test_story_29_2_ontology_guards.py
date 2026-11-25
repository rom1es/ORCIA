"""Story 29.2 (Layer 1a) — Unit tests for P1-A, P1-B.1, P1-B.2 & P2-2 ontology/CC guards."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_api.dependencies import (
    get_embedding_port,
    get_ontology_and_rag_services,
    require_rag_available,
)
from orcia_api.main import create_app
from orcia_core.ontology.models import OntologyConceptEntity, OntologyRelationEntity
from orcia_core.permissions.models import UserIdentity, WorkspaceEntity, WorkspaceMembershipEntity


def _make_isolated_app(monkeypatch: pytest.MonkeyPatch) -> Any:
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
    return app


@pytest.mark.asyncio
async def test_p1a_create_promotion_syncs_topology_and_blocks_revoked_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-A: POST /ontology/promotions calls sync_evaluator_topology_from_pg before read check."""
    app = _make_isolated_app(monkeypatch)
    ws_conf_id = "0192c4e0-0000-7000-8000-000000000203"
    nadia = app.state.auth_service.resolve_user(persona_key="nadia")
    req = Request({"type": "http", "app": app, "headers": []})
    gov, _, _ = get_ontology_and_rag_services(req, fixture=False)
    gov._concepts["conf_promo_concept"] = OntologyConceptEntity(
        id="0195f292-0000-7000-8000-000000001901",
        concept_key="conf_promo_concept",
        canonical_term="Secret Promo Term",
        level="3_WORKSPACE",
        scope_id=ws_conf_id,
        definition_text="Confidential term",
    )
    # Seed stale in-memory membership for nadia that PG sync will revoke
    app.state.auth_service.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="stale-nadia-conf",
            workspace_id=ws_conf_id,
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id=nadia.id,
        )
    )
    sync_calls = 0

    async def _fake_sync(_request: Any, auth_svc: Any, **_kw: Any) -> None:
        nonlocal sync_calls
        sync_calls += 1
        auth_svc.evaluator.replace_memberships(())

    monkeypatch.setattr(
        "orcia_api.routers._ontology_promotions_helpers.sync_evaluator_topology_from_pg",
        _fake_sync,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/ontology-rag/ontology/promotions",
            params={"persona_key": "nadia"},
            json={"concept_key": "conf_promo_concept", "target_level": "3_TEAM"},
        )
        assert r.status_code == 403
        assert r.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
        assert sync_calls >= 1


@pytest.mark.asyncio
async def test_p1b1_resolve_and_what_if_isolate_confidential_and_private_concepts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-B.1: /ontology/resolve & /ontology/what-if (fixture=False) deny non-members & filter."""
    app = _make_isolated_app(monkeypatch)
    ws_conf_id = "0192c4e0-0000-7000-8000-000000000203"
    ws_priv_id = "0195f292-0000-7000-8000-000000001999"
    marc = app.state.auth_service.resolve_user(persona_key="marc")
    app.state.auth_service.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_priv_id,
            slug="priv-marc-onto",
            name="Private Marc",
            owner_org_unit_id=marc.primary_org_unit_id,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            personal_owner_user_id=marc.id,
            ui_visibility_mode="PRIVATE_USER",
        )
    )
    req = Request({"type": "http", "app": app, "headers": []})
    gov, _, _ = get_ontology_and_rag_services(req, fixture=False)
    gov._concepts["l1_pub"] = OntologyConceptEntity(
        id="0195f292-0000-7000-8000-000000001910",
        concept_key="l1_pub",
        canonical_term="Global Public Term",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        definition_text="Public",
    )
    gov._concepts["conf_c"] = OntologyConceptEntity(
        id="0195f292-0000-7000-8000-000000001911",
        concept_key="conf_c",
        canonical_term="Confidential Secret",
        level="3_WORKSPACE",
        scope_id=ws_conf_id,
        definition_text="Secret",
    )
    gov._concepts["priv_c"] = OntologyConceptEntity(
        id="0195f292-0000-7000-8000-000000001912",
        concept_key="priv_c",
        canonical_term="Private Secret",
        level="4_WORKSPACE",
        scope_id=ws_priv_id,
        definition_text="Private",
    )
    gov._relations.append(
        OntologyRelationEntity(
            id="0195f292-0000-7000-8000-000000001913",
            relation_key="rel-pub-conf",
            source_concept_key="l1_pub",
            target_concept_key="conf_c",
            relation_type="GOVERNS",
        )
    )
    gov._template_bindings["tpl://ws-conf-secret/doc"] = ("conf_c",)
    gov._active_run_bindings["0195f000-0000-7000-8000-000000000703"] = ("l1_pub", "conf_c")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for intruder in ("karim", "nadia", "claire"):
            for ws_id in (ws_conf_id, ws_priv_id):
                r_res = await client.post(
                    "/api/v1/ontology-rag/ontology/resolve",
                    params={"persona_key": intruder},
                    json={"workspace_scope_id": ws_id, "human_profile": "TECH_LEAD"},
                )
                assert r_res.status_code == 403
                assert r_res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            # Without concrete workspace_scope_id: confidential/private layers & relations hidden
            r_global = await client.post(
                "/api/v1/ontology-rag/ontology/resolve",
                params={"persona_key": intruder},
                json={"workspace_scope_id": "scope-global", "human_profile": "TECH_LEAD"},
            )
            assert r_global.status_code == 200
            keys = {c["concept_key"] for c in r_global.json()["concepts"]}
            assert "l1_pub" in keys
            assert "conf_c" not in keys
            assert "priv_c" not in keys
            assert r_global.json()["relations"] == []

            for ckey in ("conf_c", "priv_c"):
                r_wi = await client.post(
                    "/api/v1/ontology-rag/ontology/what-if",
                    params={"persona_key": intruder},
                    json={"concept_key": ckey, "proposed_change": "probe"},
                )
                assert r_wi.status_code == 403
                assert r_wi.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            r_wi_pub = await client.post(
                "/api/v1/ontology-rag/ontology/what-if",
                params={"persona_key": intruder},
                json={"concept_key": "l1_pub", "proposed_change": "rename"},
            )
            assert r_wi_pub.status_code == 200
            wi_body = r_wi_pub.json()
            assert "conf_c" not in wi_body["transitively_affected_concepts"]
            assert "tpl://ws-conf-secret/doc" not in wi_body["impacted_artifact_templates"]
            assert "0195f000-0000-7000-8000-000000000703" not in wi_body["impacted_active_run_ids"]

        # Explicit member (marc) retains access
        r_marc_res = await client.post(
            "/api/v1/ontology-rag/ontology/resolve",
            params={"persona_key": "marc"},
            json={"workspace_scope_id": ws_conf_id, "human_profile": "TECH_LEAD"},
        )
        assert r_marc_res.status_code == 200
        assert any(c["concept_key"] == "conf_c" for c in r_marc_res.json()["concepts"])
        assert (
            await client.post(
                "/api/v1/ontology-rag/ontology/what-if",
                params={"persona_key": "marc"},
                json={"concept_key": "conf_c", "proposed_change": "update"},
            )
        ).status_code == 200


@pytest.mark.asyncio
async def test_p1b2_global_write_fails_closed_when_zero_writable_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-B.2: POST /rag/index-db-ddl & /tripartite/audit-doc-vs-code fail closed on GLOBAL/''."""
    app = _make_isolated_app(monkeypatch)
    for key in ("nows", "obsws"):
        u = UserIdentity(
            id=f"0195f292-0000-7000-8000-00000000195{1 if key == 'nows' else 2}",
            email=f"{key}@orcia.test",
            display_name=key,
            auth_mode="LOCAL",
            human_profile_archetype="DEVELOPER",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="0195f292-0000-7000-8000-000000009999",
        )
        app.state.auth_service.register_user(u)
        app.state.auth_service._persona_map[key] = u.id
        if key == "obsws":
            app.state.auth_service.evaluator.upsert_membership(
                WorkspaceMembershipEntity(
                    id="obs-only-mem",
                    workspace_id="0192c4e0-0000-7000-8000-000000000201",
                    role="CONTRIBUTOR",
                    access_mode="READ_ONLY_OBSERVER",
                    user_id=u.id,
                )
            )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for p_key, exp_code in (
            ("nows", "ERR_SCOPE_ACCESS_DENIED"),
            ("obsws", "ERR_OBSERVER_MODE_READ_ONLY"),
        ):
            for ws_val in ("GLOBAL", ""):
                r_ddl = await client.post(
                    "/api/v1/ontology-rag/rag/index-db-ddl",
                    params={"persona_key": p_key},
                    json={
                        "workspace_id": ws_val,
                        "datasource_id": "ds-1",
                        "datasource_alias": "db",
                        "db_uri": "db://x",
                        "ddl_sql": "CREATE TABLE t (id INT);",
                        "schema_version": "v1",
                    },
                )
                assert r_ddl.status_code == 403
                assert r_ddl.json()["error_code"] == exp_code

                r_trip = await client.post(
                    "/api/v1/ontology-rag/tripartite/audit-doc-vs-code",
                    params={"persona_key": p_key},
                    json={
                        "workspace_id": ws_val,
                        "confluence_uri": "confluence://X/1",
                        "git_repo_uri": "git://x/r",
                        "git_symbol": "fn",
                        "doc_rule_summary": "A",
                        "code_rule_summary": "B",
                    },
                )
                assert r_trip.status_code == 403
                assert r_trip.json()["error_code"] == exp_code


@pytest.mark.asyncio
async def test_p22_control_center_syncs_topology_on_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P2-2: Control Center routes invoke sync_evaluator_topology_from_pg before service calls."""
    app = _make_isolated_app(monkeypatch)
    sync_calls = 0

    async def _fake_sync(_request: Any, _auth_svc: Any, **_kw: Any) -> None:
        nonlocal sync_calls
        sync_calls += 1

    monkeypatch.setattr(
        "orcia_api.routers.control_center.sync_evaluator_topology_from_pg", _fake_sync
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (
            await client.get("/api/v1/control-center/overview", params={"persona_key": "marc"})
        ).status_code == 200
        assert (
            await client.get(
                "/api/v1/control-center/command-palette", params={"persona_key": "marc"}
            )
        ).status_code == 200
        assert sync_calls == 2
