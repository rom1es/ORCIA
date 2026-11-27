"""Unit tests for Story 31.5 guarded entity DELETE routers & 403/404 paths (`<= 260 L`)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_api.main import create_app
from orcia_core.permissions.models import (
    OrgUnitNode,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


def _make_app(monkeypatch: pytest.MonkeyPatch, *, with_engine: bool = True) -> FastAPI:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    ws_id = "0195f000-0000-7000-8000-000000000301"
    org_id = "0192c4e0-0000-7000-8000-000000000001"
    auth_svc = app.state.auth_service
    default_user = auth_svc.resolve_user()
    ev = auth_svc.evaluator
    ev.upsert_org_unit(OrgUnitNode(id=org_id, slug="root", name="R", unit_type="ENTERPRISE"))
    ev.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug="ws-315-del",
            name="WS 315 Del",
            owner_org_unit_id=org_id,
            visibility_mode="STANDARD",
        )
    )
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-315-del",
            workspace_id=ws_id,
            user_id=default_user.id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    if with_engine:
        uid = str(uuid7())
        draft_id = str(uuid7())

        def handler(sql: str, _params: dict[str, Any]) -> FakeSqlResult:
            if "SELECT (to_regclass('public.pack_draft_memberships')" in sql:
                return FakeSqlResult(scalar_val=True, has_scalar=True)
            if "SELECT to_regclass('public.audit_ledger')" in sql:
                return FakeSqlResult(scalar_val="audit_ledger", has_scalar=True)
            if "FROM pack_draft_memberships m" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "bundle_id": draft_id,
                            "pack_slug": "linked-draft",
                            "version": "0.1.0",
                            "title": "Linked",
                            "scope_type": "WORKSPACE",
                            "scope_id": ws_id,
                        }
                    ]
                )
            if "DELETE FROM pack_draft_memberships" in sql:
                return FakeSqlResult(mappings=[{"id": str(uuid7()), "draft_bundle_id": draft_id}])
            if "FROM workflow_definitions_v2" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": "wf-1",
                            "label_val": "WF 1",
                            "bid": None,
                            "pack_id": f"workspace:{ws_id}",
                            "spec_jsonb": {},
                        }
                    ]
                )
            if "FROM vsm_definitions_v2" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": "vsm-1",
                            "label_val": "VSM 1",
                            "bid": None,
                            "pack_id": f"workspace:{ws_id}",
                            "spec_jsonb": {},
                        }
                    ]
                )
            if "FROM ontology_concepts" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": "c-1",
                            "label_val": "C 1",
                            "bid": None,
                            "level": "3_WORKSPACE",
                            "scope_id": ws_id,
                        }
                    ]
                )
            if "FROM ontology_relations" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": "r-1",
                            "label_val": "r-1",
                            "bid": None,
                            "src_level": "3_WORKSPACE",
                            "src_scope_id": ws_id,
                            "tgt_level": "3_WORKSPACE",
                            "tgt_scope_id": ws_id,
                        }
                    ]
                )
            if "FROM ontology_axioms" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": "a-1",
                            "label_val": "a-1",
                            "bid": None,
                            "level": "3_WORKSPACE",
                            "scope_id": ws_id,
                        }
                    ]
                )
            if "FROM pack_dna_mechanisms" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": "m-1",
                            "label_val": "M 1",
                            "bid": draft_id,
                            "bundle_kind": "CUSTOM",
                            "bundle_status": "DRAFT",
                            "scope_type": "WORKSPACE",
                            "scope_id": ws_id,
                        }
                    ]
                )
            if "FROM permission_broker_policies" in sql:
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": uid,
                            "key_val": f"ws:{ws_id}:p-1",
                            "label_val": "p-1",
                            "bid": None,
                            "policy_key": f"ws:{ws_id}:p-1",
                        }
                    ]
                )
            if "FROM catalog_items" in sql:
                return FakeSqlResult(
                    mappings=[{"uid": uid, "ws_id": ws_id, "bid": None, "visibility_scope": "TEAM"}]
                )
            return FakeSqlResult()

        app.state.db_engine = FakeSqlEngine(handler)
    else:
        app.state.db_engine = None
    return app


@pytest.mark.asyncio
async def test_guarded_delete_routers_409_unlink_and_observer_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify all guarded DELETE routes enforce 409 anti-hostage, unlink=true & 403."""
    app = _make_app(monkeypatch, with_engine=True)
    routes = [
        "/api/v1/workflows/v2/wf-1",
        "/api/v1/vsm/vsm-1",
        "/api/v1/ontology-rag/ontology/concepts/c-1",
        "/api/v1/ontology-rag/ontology/relations/r-1",
        "/api/v1/ontology-rag/ontology/axioms/a-1",
        "/api/v1/permissions/broker/policies/p-1",
        "/api/v1/packs/composer/dna-mechanisms/m-1",
        "/api/v1/catalog/instructions/inst-1",
        "/api/v1/help/art-1",
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in routes:
            r409 = await client.delete(path)
            assert r409.status_code == 409, path
            assert r409.json()["error_code"] == "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
            r_ok = await client.delete(f"{path}?unlink_from_draft_packs=true")
            assert r_ok.status_code == 200, path
            assert len(r_ok.json()["unlinked_draft_packs"]) == 1
            r_obs = await client.delete(path, headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"})
            assert r_obs.status_code == 403

        # Agents and skills delete routes also propagate ?unlink_from_draft_packs=true
        saved_engine = app.state.db_engine
        app.state.db_engine = None
        r_sk = await client.post(
            "/api/v1/agents-and-skills/skills",
            json={
                "skill_id": "sk-315-del",
                "name": "Skill 315",
                "objective": "Obj",
                "instructions": "Do work.",
            },
        )
        assert r_sk.status_code == 200
        r_ag = await client.post(
            "/api/v1/agents-and-skills/agents",
            json={
                "agent_id": "ag-315-del",
                "name": "Agent 315",
                "role_mission": "Mission",
                "instructions": "Assist.",
            },
        )
        assert r_ag.status_code == 200
        app.state.db_engine = saved_engine

        async def _noop_sync(*_a: Any, **_kw: Any) -> dict[str, int]:
            return {}

        monkeypatch.setattr(
            "orcia_api.routers._agents_and_skills_skills_routes.sync_from_postgres18_if_enabled",
            _noop_sync,
        )
        monkeypatch.setattr(
            "orcia_api.routers.agents_and_skills._sync_from_postgres18_if_enabled",
            _noop_sync,
        )
        r_sk_409 = await client.delete("/api/v1/agents-and-skills/skills/sk-315-del")
        assert r_sk_409.status_code == 409
        r_sk_del = await client.delete(
            "/api/v1/agents-and-skills/skills/sk-315-del?unlink_from_draft_packs=true"
        )
        assert r_sk_del.status_code == 200
        assert len(r_sk_del.json()["unlinked_draft_packs"]) == 1
        r_ag_409 = await client.delete("/api/v1/agents-and-skills/agents/ag-315-del")
        assert r_ag_409.status_code == 409
        r_ag_del = await client.delete(
            "/api/v1/agents-and-skills/agents/ag-315-del?unlink_from_draft_packs=true"
        )
        assert r_ag_del.status_code == 200
        assert len(r_ag_del.json()["unlinked_draft_packs"]) == 1

    app_no_eng = _make_app(monkeypatch, with_engine=False)
    async with AsyncClient(
        transport=ASGITransport(app=app_no_eng), base_url="http://test"
    ) as client_no_eng:
        assert (await client_no_eng.delete("/api/v1/workflows/v2/wf-1")).status_code == 404
        assert (await client_no_eng.delete("/api/v1/vsm/vsm-1")).status_code == 404
        assert (
            await client_no_eng.delete("/api/v1/ontology-rag/ontology/concepts/c-1")
        ).status_code == 404
        assert (
            await client_no_eng.delete("/api/v1/permissions/broker/policies/p-1")
        ).status_code == 404
        assert (
            await client_no_eng.delete("/api/v1/packs/composer/dna-mechanisms/m-1")
        ).status_code == 403
