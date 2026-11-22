"""Focused unit coverage for Epic 25 refactored guards and helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from starlette.requests import Request

from orcia_api.routers._ai_models_helpers import (
    execute_model_connection_test,
    execute_models_discovery,
    require_ai_models_platform_admin,
    resolve_mapping_decrypted_key,
)
from orcia_api.routers._finops_auth_guards import (
    enforce_audit_read_access,
    enforce_scope_level_mutation,
    resolve_workspace_canonical_scope_path,
)
from orcia_api.routers._finops_scope_guards import (
    resolve_workflow_def_workspace_server_side,
    sync_evaluator_topology_from_pg,
    user_governs_org_unit,
    validate_uuid,
)
from orcia_core.bootstrap._internal._sql_workspace_datasources_sync import (
    has_active_global_embedding_model_on_conn,
    trigger_workspace_datasource_sync_on_postgres18,
)
from orcia_core.orchestration import AiModelsHubService
from orcia_core.permissions import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    build_default_auth_and_org_service,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.rag.errors import RagReindexInProgressError
from orcia_kernel.errors import ValidationDomainError


def _make_request(
    *,
    path: str = "/api/v1/test",
    headers: dict[str, str] | None = None,
    auth_svc: Any = None,
    db_engine: Any = None,
    http_client: Any = None,
) -> Request:
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()
    ]
    app = MagicMock()
    app.state.auth_service = auth_svc or build_default_auth_and_org_service()
    app.state.db_engine = db_engine
    app.state.http_client = http_client
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
        "app": app,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_ai_models_helpers_env_var_observer_and_ephemeral_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_svc = build_default_auth_and_org_service()
    obs_user = UserIdentity(
        id="0195f000-0000-7000-8000-000000009001",
        email="obs.role@orcia.io",
        display_name="Observer Role",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000001",
        roles=("OBSERVER",),
    )
    auth_svc.register_user(obs_user)
    tok = auth_svc.jwt_manager.issue_token_pair(
        user_id=obs_user.id,
        email=obs_user.email,
        role="OBSERVER",
        org_unit_id=obs_user.primary_org_unit_id,
        archetype="OBSERVER",
        auth_mode="LOCAL",
    )
    req_obs = _make_request(
        headers={"Authorization": f"Bearer {tok.access_token}"},
        auth_svc=auth_svc,
    )
    with pytest.raises(ObserverModeReadOnlyError):
        require_ai_models_platform_admin(req_obs)

    cipher = PassthroughVaultCipher(master_key=b"0" * 32)
    hub_svc = AiModelsHubService(vault_cipher=cipher)
    mapping = hub_svc.create_mapping(
        scope_level="GLOBAL",
        scope_id="0192c4e0-0000-7000-8000-000000000001",
        display_name="EnvVar Model",
        inference_tier="medium",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="gpt-4o-mini",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="env_var",
        env_var_name="ORCIA_TEST_ENV_API_KEY",
        protocol_mode="openai_compatible",
    )
    monkeypatch.setenv("ORCIA_TEST_ENV_API_KEY", "sk-env-secret-123456")

    req_mem = _make_request(auth_svc=auth_svc, db_engine=None, http_client=None)
    rec_mem, key_mem = await resolve_mapping_decrypted_key(req_mem, mapping.id, auth_svc, hub_svc)
    assert rec_mem.id == mapping.id
    assert key_mem == "sk-env-secret-123456"

    monkeypatch.setattr(
        "orcia_api.routers._ai_models_helpers.get_ai_model_mapping_pg18",
        AsyncMock(return_value=mapping),
    )

    @asynccontextmanager
    async def _begin():
        yield MagicMock()

    fake_engine = MagicMock()
    fake_engine.begin = _begin
    req_pg = _make_request(auth_svc=auth_svc, db_engine=fake_engine, http_client=None)
    rec_pg, key_pg = await resolve_mapping_decrypted_key(req_pg, mapping.id, auth_svc, hub_svc)
    assert rec_pg.id == mapping.id
    assert key_pg == "sk-env-secret-123456"

    monkeypatch.setattr(
        "orcia_api.routers._ai_models_helpers.test_ai_model_endpoint_connection",
        AsyncMock(
            return_value=MagicMock(
                latency_ms=12,
                message_fr="OK FR",
                message_en="OK EN",
            )
        ),
    )
    health, resp = await execute_model_connection_test(mapping, None, req_mem)
    assert health == "OPERATIONAL"
    assert resp.latency_ms == 12

    monkeypatch.setattr(
        "orcia_api.routers._ai_models_helpers.discover_models_from_provider",
        AsyncMock(
            return_value=[
                MagicMock(
                    id="gpt-4o",
                    display_name="GPT-4o",
                    description=None,
                    usage_hint="chat",
                    owned_by="openai",
                )
            ]
        ),
    )
    disc = await execute_models_discovery(
        req_mem,
        endpoint_uri="https://api.openai.com/v1",
        protocol_mode="openai_compatible",
        provider_slug="openai",
        api_key=None,
    )
    assert disc.total_count == 1
    assert isinstance(httpx.AsyncClient(), httpx.AsyncClient)


@pytest.mark.asyncio
async def test_workspace_datasources_sync_guards_and_reindex_pending() -> None:
    conn_no_tbl = MagicMock()
    no_tbl_res = MagicMock()
    no_tbl_res.scalar.return_value = None
    conn_no_tbl.execute = AsyncMock(return_value=no_tbl_res)
    assert await has_active_global_embedding_model_on_conn(conn_no_tbl) is False

    fake_engine = MagicMock()
    with pytest.raises(ResourceNotFoundError):
        await trigger_workspace_datasource_sync_on_postgres18(
            fake_engine,
            workspace_id="not-a-uuid",
            datasource_id="not-a-uuid",
        )

    ws_id = "0195f000-0000-7000-8000-000000000101"
    ds_id = "0195f000-0000-7000-8000-000000000102"
    job_id = "0195f000-0000-7000-8000-000000000103"

    @asynccontextmanager
    async def _begin_missing():
        conn = MagicMock()
        res_empty = MagicMock()
        res_empty.fetchone.return_value = None
        conn.execute = AsyncMock(return_value=res_empty)
        yield conn

    eng_missing = MagicMock()
    eng_missing.begin = _begin_missing
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "orcia_core.bootstrap._internal._sql_workspace_datasources_sync."
            "ensure_workspace_datasources_schema",
            AsyncMock(),
        )
        mp.setattr(
            "orcia_core.bootstrap._internal._sql_workspace_datasources_sync."
            "ensure_iam_accounts_schema",
            AsyncMock(),
        )
        with pytest.raises(ResourceNotFoundError):
            await trigger_workspace_datasource_sync_on_postgres18(
                eng_missing,
                workspace_id=ws_id,
                datasource_id=ds_id,
            )

    current_row = (
        ds_id,
        ws_id,
        "docs",
        "confluence",
        "https://conf.local",
        None,
        "SERVICE_ACCOUNT",
        None,
        None,
        "ACTIVE",
        "DOCUMENT_KB",
        "POLLING_24H",
        None,
        None,
        None,
        None,
        None,
        "FRESH",
        False,
        "SERVICE_ACCOUNT",
        None,
        "DISABLED",
        None,
        None,
        None,
        None,
    )

    @asynccontextmanager
    async def _begin_reindexing():
        conn = MagicMock()

        async def _exec(stmt: Any, params: dict[str, Any] | None = None) -> MagicMock:
            sql = str(stmt)
            res = MagicMock()
            if "FROM workspace_datasources" in sql and "FOR UPDATE" in sql:
                res.fetchone.return_value = current_row
            elif "to_regclass('rag_reindexing_jobs')" in sql:
                res.scalar.return_value = "rag_reindexing_jobs"
            elif "FROM rag_reindexing_jobs" in sql:
                res.fetchone.return_value = (job_id, 55)
            return res

        conn.execute = AsyncMock(side_effect=_exec)
        yield conn

    eng_reindexing = MagicMock()
    eng_reindexing.begin = _begin_reindexing
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "orcia_core.bootstrap._internal._sql_workspace_datasources_sync."
            "ensure_workspace_datasources_schema",
            AsyncMock(),
        )
        mp.setattr(
            "orcia_core.bootstrap._internal._sql_workspace_datasources_sync."
            "ensure_iam_accounts_schema",
            AsyncMock(),
        )
        mp.setattr(
            "orcia_core.bootstrap._internal._sql_workspace_datasources_sync."
            "has_active_global_embedding_model_on_conn",
            AsyncMock(return_value=True),
        )
        with pytest.raises(RagReindexInProgressError) as exc_reindex:
            await trigger_workspace_datasource_sync_on_postgres18(
                eng_reindexing,
                workspace_id=ws_id,
                datasource_id=ds_id,
            )
        assert exc_reindex.value.progress_percentage == 55


@pytest.mark.asyncio
async def test_finops_auth_and_scope_guards_edge_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationDomainError):
        validate_uuid("invalid-uuid", "scope_id")

    monkeypatch.setattr(
        "orcia_api.routers._finops_topology_sync.get_configured_db_engine",
        lambda _r: None,
    )
    auth_svc = build_default_auth_and_org_service()
    root_ou_id = "0192c4e0-0000-7000-8000-000000000001"
    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(
            id=root_ou_id,
            slug="orcia-root",
            name="ORCIA Root",
            unit_type="ENTERPRISE",
            parent_id=None,
        )
    )
    bu_id = "0195f000-0000-7000-8000-00000000a101"
    team_id = "0195f000-0000-7000-8000-00000000a102"
    ws_priv_id = "0195f000-0000-7000-8000-00000000a103"
    ws_std_id = "0195f000-0000-7000-8000-00000000a104"
    missing_id = "0195f000-0000-7000-8000-00000000a999"

    admin = auth_svc.resolve_user(persona_key="karim")
    contrib = auth_svc.resolve_user(persona_key="nadia")
    bu_lead = UserIdentity(
        id="0195f000-0000-7000-8000-00000000b101",
        email="bu.lead@orcia.io",
        display_name="BU Lead",
        auth_mode="LOCAL",
        human_profile_archetype="BU_DIRECTOR",
        platform_role="BU_LEAD",
        primary_org_unit_id=bu_id,
        roles=("BU_LEAD",),
    )
    auth_svc.register_user(bu_lead)

    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(id=bu_id, slug="bu-fin", name="BU Fin", unit_type="BU", parent_id=root_ou_id)
    )
    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(
            id=team_id,
            slug="team-fin",
            name="Team Fin",
            unit_type="TEAM",
            parent_id=bu_id,
            lead_user_ids=(contrib.id,),
        )
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_priv_id,
            slug="priv-ws",
            name="Private WS",
            owner_org_unit_id=team_id,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            personal_owner_user_id=contrib.id,
            ui_visibility_mode="PRIVATE_USER",
        )
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_std_id,
            slug="std-ws",
            name="Standard WS",
            owner_org_unit_id=team_id,
            visibility_mode="STANDARD",
        )
    )

    req = _make_request(auth_svc=auth_svc)

    with pytest.raises(ValidationDomainError):
        await enforce_scope_level_mutation(req, admin, scope_type="WORKSPACE", scope_id=None)
    with pytest.raises(ResourceNotFoundError):
        await enforce_scope_level_mutation(req, admin, scope_type="WORKSPACE", scope_id=missing_id)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_scope_level_mutation(req, admin, scope_type="WORKSPACE", scope_id=ws_priv_id)
    with pytest.raises(ValidationDomainError):
        await enforce_scope_level_mutation(req, admin, scope_type="BU", scope_id=None)
    with pytest.raises(ResourceNotFoundError):
        await enforce_scope_level_mutation(req, admin, scope_type="BU", scope_id=missing_id)

    # PLATFORM_ADMIN passes BU mutation
    await enforce_scope_level_mutation(req, admin, scope_type="BU", scope_id=bu_id)

    # CONTRIBUTOR denied on BU and TEAM
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_scope_level_mutation(req, contrib, scope_type="BU", scope_id=bu_id)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_scope_level_mutation(req, contrib, scope_type="TEAM", scope_id=team_id)

    # BU_LEAD denied on root_ou (does not govern ancestor)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_scope_level_mutation(req, bu_lead, scope_type="BU", scope_id=root_ou_id)

    # Canonical scope paths
    assert resolve_workspace_canonical_scope_path(auth_svc, missing_id) == (
        f"org/workspace/{missing_id}"
    )
    assert resolve_workspace_canonical_scope_path(auth_svc, ws_std_id).endswith(
        "/bu-fin/team-fin/std-ws"
    )

    # user_governs_org_unit branches
    assert user_governs_org_unit(auth_svc, admin, team_id) is True
    assert user_governs_org_unit(auth_svc, bu_lead, bu_id) is True
    assert user_governs_org_unit(auth_svc, bu_lead, team_id) is True
    assert user_governs_org_unit(auth_svc, contrib, team_id) is True
    assert user_governs_org_unit(auth_svc, contrib, root_ou_id) is False

    # Audit read access edge branches
    with pytest.raises(ResourceNotFoundError):
        await enforce_audit_read_access(req, admin, requested_workspace_id=missing_id)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_audit_read_access(req, admin, requested_workspace_id=ws_priv_id)
    ok_scope = await enforce_audit_read_access(req, admin, requested_workspace_id=ws_std_id)
    assert ok_scope.allowed_workspace_ids == (ws_std_id,)

    # Run-scoped audit check with mocked PG engine
    run_id = "0195f000-0000-7000-8000-00000000c111"

    @asynccontextmanager
    async def _conn_ctx(run_ws_val: str | None, ledger_ws: list[tuple[str | None]]):
        conn = MagicMock()

        async def _exec(stmt: Any, params: dict[str, Any] | None = None) -> MagicMock:
            sql = str(stmt)
            r = MagicMock()
            if "FROM workflow_runs" in sql:
                r.scalar.return_value = run_ws_val
            else:
                r.all.return_value = ledger_ws
            return r

        conn.execute = AsyncMock(side_effect=_exec)
        yield conn

    eng_priv_run = MagicMock()
    eng_priv_run.connect = lambda: _conn_ctx(ws_priv_id, [])
    req_priv_run = _make_request(auth_svc=auth_svc, db_engine=eng_priv_run)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_audit_read_access(req_priv_run, admin, requested_run_id=run_id)

    eng_null_ledger = MagicMock()
    eng_null_ledger.connect = lambda: _conn_ctx(None, [(None,)])
    req_null_ledger = _make_request(auth_svc=auth_svc, db_engine=eng_null_ledger)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_audit_read_access(req_null_ledger, contrib, requested_run_id=run_id)

    eng_priv_ledger = MagicMock()
    eng_priv_ledger.connect = lambda: _conn_ctx(None, [(ws_priv_id,)])
    req_priv_ledger = _make_request(auth_svc=auth_svc, db_engine=eng_priv_ledger)
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_audit_read_access(req_priv_ledger, admin, requested_run_id=run_id)

    # sync_evaluator_topology_from_pg JSON-string & exception fallback branches
    @asynccontextmanager
    async def _conn_json_str():
        conn = MagicMock()

        async def _exec(stmt: Any, params: dict[str, Any] | None = None) -> MagicMock:
            sql = str(stmt)
            r = MagicMock()
            m = MagicMock()
            if "FROM org_units" in sql:
                m.all.return_value = [
                    {
                        "id": bu_id,
                        "slug": "bu-fin",
                        "name": "BU Fin",
                        "unit_type": "BU",
                        "parent_id": root_ou_id,
                        "lead_user_id": None,
                        "lead_user_ids_jsonb": "[]",
                        "member_user_ids_jsonb": "[]",
                    }
                ]
            elif "FROM workspaces" in sql:
                m.all.return_value = [
                    {
                        "id": ws_priv_id,
                        "slug": "priv-ws",
                        "name": "Private WS",
                        "owner_org_unit_id": team_id,
                        "visibility_mode": "CONFIDENTIAL_RESTRICTED",
                        "settings_jsonb": "{invalid-json",
                    }
                ]
            else:
                m.all.return_value = []
            r.mappings.return_value = m
            return r

        conn.execute = AsyncMock(side_effect=_exec)
        yield conn

    eng_str = MagicMock()
    eng_str.connect = _conn_json_str
    req_str = _make_request(auth_svc=auth_svc, db_engine=eng_str)
    monkeypatch.setattr(
        "orcia_api.routers._finops_topology_sync.get_configured_db_engine",
        lambda _r: eng_str,
    )
    await sync_evaluator_topology_from_pg(req_str, auth_svc)

    def _broken_conn():
        raise RuntimeError("pg down")

    eng_broken = MagicMock()
    eng_broken.connect = _broken_conn
    monkeypatch.setattr(
        "orcia_api.routers._finops_topology_sync.get_configured_db_engine",
        lambda _r: eng_broken,
    )
    await sync_evaluator_topology_from_pg(req_str, auth_svc)

    assert await resolve_workflow_def_workspace_server_side(req, missing_id) is None
