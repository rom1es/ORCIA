"""Unit tests for Story 31.5 delete RBAC guardrails."""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from orcia_api.main import create_app
from orcia_api.routers._entity_delete_rbac import (
    build_catalog_target_authorizer,
    build_dna_target_authorizer,
    build_ontology_target_authorizer,
    build_policy_target_authorizer,
    build_wf_vsm_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import (
    OrgUnitNode,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

pytestmark = pytest.mark.story("31.5")


def _setup_rbac_app(monkeypatch: pytest.MonkeyPatch) -> tuple[FastAPI, str, str, str, str]:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    org_root = "0192c4e0-0000-7000-8000-000000000001"
    org_bu = "0192c4e0-0000-7000-8000-000000000099"
    ws_a = "0195f000-0000-7000-8000-000000000391"
    ws_priv = "0195f000-0000-7000-8000-000000000392"
    auth_svc = app.state.auth_service
    marc = auth_svc.resolve_user(persona_key="marc")
    ev = auth_svc.evaluator
    ev.upsert_org_unit(OrgUnitNode(id=org_root, slug="root", name="R", unit_type="ENTERPRISE"))
    ev.upsert_org_unit(
        OrgUnitNode(
            id=org_bu,
            slug="bu",
            name="BU",
            unit_type="BU",
            parent_id=org_root,
            lead_user_id=marc.id,
        )
    )
    ev.upsert_workspace(
        WorkspaceEntity(id=ws_a, slug="ws-a", name="WS A", owner_org_unit_id=org_bu)
    )
    ev.upsert_workspace(
        WorkspaceEntity(
            id=ws_priv,
            slug="ws-p",
            name="Priv",
            owner_org_unit_id=org_root,
            ui_visibility_mode="PRIVATE_USER",
            personal_owner_user_id="other-user",
        )
    )
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-m-a",
            workspace_id=ws_a,
            user_id=marc.id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-m-priv",
            workspace_id=ws_priv,
            user_id=marc.id,
            role="TEAM_LEAD",
            access_mode="READ_ONLY_OBSERVER",
        )
    )
    return app, org_root, org_bu, ws_a, ws_priv


@pytest.mark.asyncio
async def test_entity_delete_rbac_all_authorizers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover every target & draft authorization branch in `_entity_delete_rbac.py`."""
    from starlette.requests import Request as StarletteRequest

    app, org_root, org_bu, ws_a, ws_priv = _setup_rbac_app(monkeypatch)
    req_marc = StarletteRequest(
        {
            "type": "http",
            "app": app,
            "method": "DELETE",
            "path": "/api/v1/test",
            "query_string": b"persona_key=marc",
            "headers": [],
        }
    )
    user, auth_svc, _tid, auth_draft = await prepare_entity_delete_guards(
        req_marc, persona_key="marc"
    )
    # Draft authorizer across WORKSPACE / BU / GLOBAL
    auth_draft("b1", "WORKSPACE", ws_a)
    auth_draft("b2", "BU", org_bu)
    with pytest.raises(ScopeAccessDeniedError):
        auth_draft("b3", "GLOBAL", "global")
    with pytest.raises(ScopeAccessDeniedError):
        auth_draft("b4", "BU", org_root)
    with pytest.raises(ScopeAccessDeniedError):
        auth_draft("b5", "WORKSPACE", ws_priv)

    cat_auth = build_catalog_target_authorizer(auth_svc, user, instance="/x")
    cat_auth(ws_a, "TEAM")
    with pytest.raises(ScopeAccessDeniedError):
        cat_auth("", "TEAM")

    wf_auth = build_wf_vsm_target_authorizer(auth_svc, user, instance="/x")
    wf_auth({"spec_jsonb": {"owner_workspace_id": ws_a}})
    wf_auth({"pack_id": f"workspace:{ws_a}", "spec_jsonb": {}})
    wf_auth({"pack_id": "workspace", "spec_jsonb": {"scope_type": "BU", "scope_id": org_bu}})
    wf_auth({"pack_id": "workspace", "spec_jsonb": {}})
    with pytest.raises(ScopeAccessDeniedError):
        wf_auth({"spec_jsonb": {"owner_workspace_id": "unknown-ws"}})

    onto_c = build_ontology_target_authorizer(
        auth_svc, user, entity_type="ONTOLOGY_CONCEPT", instance="/x"
    )
    onto_c({"level": "2_DOMAIN", "scope_id": org_bu})
    onto_c({"level": "3_WORKSPACE", "scope_id": ws_a})
    with pytest.raises(ScopeAccessDeniedError):
        onto_c({"level": "1_ENTERPRISE", "scope_id": "enterprise"})
    with pytest.raises(ScopeAccessDeniedError):
        onto_c({"level": "2_DOMAIN", "scope_id": org_root})

    onto_r = build_ontology_target_authorizer(
        auth_svc, user, entity_type="ONTOLOGY_RELATION", instance="/x"
    )
    onto_r(
        {
            "src_level": "3_WORKSPACE",
            "src_scope_id": ws_a,
            "tgt_level": "2_DOMAIN",
            "tgt_scope_id": org_bu,
        }
    )
    with pytest.raises(ScopeAccessDeniedError):
        onto_r({})

    pol_auth = build_policy_target_authorizer(auth_svc, user, instance="/x")
    pol_auth({"policy_key": f"ws:{ws_a}:git"})
    with pytest.raises(ScopeAccessDeniedError):
        pol_auth({"policy_key": "global-pol"})

    dna_auth = build_dna_target_authorizer(auth_svc, user, instance="/x")
    dna_auth({"bid": "b1", "scope_type": "WORKSPACE", "scope_id": ws_a})
    with pytest.raises(ScopeAccessDeniedError):
        dna_auth({"bid": None})

    # Observer-mode workspace membership raises ObserverModeReadOnlyError on write
    ws_obs = "0195f000-0000-7000-8000-000000000393"
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(id=ws_obs, slug="obs", name="Obs", owner_org_unit_id=org_root)
    )
    auth_svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-m-obs",
            workspace_id=ws_obs,
            user_id=user.id,
            role="TEAM_LEAD",
            access_mode="READ_ONLY_OBSERVER",
        )
    )
    with pytest.raises(ObserverModeReadOnlyError):
        cat_auth(ws_obs, "TEAM")
