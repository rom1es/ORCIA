"""Unit & HTTP Contract Tests for Story 9.2 — Progressive Day-0 Accostage (1/6),
Anti-First-User Takeover (`LOCK TABLE users IN EXCLUSIVE MODE` + `ORCIA_BOOTSTRAP_TOKEN`)
& Progressive LLM Tier (`1 Modèle -> >= 2 Familles AD-10`).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)
from orcia_core.bootstrap.models import LlmModelEndpoint
from orcia_core.bootstrap.progressive_accostage import (
    ACCOSTAGE_SIX_MILESTONES,
    ProgressiveDay0AccostageService,
)

DUMMY_HASH = "argon2id$test_hash"  # pragma: allowlist secret
DUMMY_PW = "TestPassword!123"  # pragma: allowlist secret


def test_story_9_2_first_user_takeover_guard_bootstrap_token_and_exclusivity() -> None:
    """Verify `ORCIA_BOOTSTRAP_TOKEN` requirement when `ORCIA_ENV != 'local'`."""
    svc_staging = ProgressiveDay0AccostageService(
        orcia_env="staging",
        expected_bootstrap_token="boot-tok-secret-999",
    )

    # Missing or wrong token on non-local env raises HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN
    with pytest.raises(InvalidBootstrapTokenError) as exc_info:
        svc_staging.create_first_platform_admin(
            email="attacker@evil.test",
            display_name="Attacker",
            password_hash=DUMMY_HASH,
            bootstrap_token="wrong-token",
        )
    assert exc_info.value.error_code == "ERR_INVALID_BOOTSTRAP_TOKEN"
    assert exc_info.value.http_status == 403

    # Valid token creates the single first PLATFORM_ADMIN
    created = svc_staging.create_first_platform_admin(
        email="karim@orcia.io",
        display_name="Karim Admin",
        password_hash=DUMMY_HASH,
        bootstrap_token="boot-tok-secret-999",
    )
    assert created.email == "karim@orcia.io"
    assert created.platform_role == "PLATFORM_ADMIN"
    assert created.sql_lock_statement == "LOCK TABLE users IN EXCLUSIVE MODE"

    # Any subsequent attempt when COUNT(*) FROM users > 0 is rejected (409)
    with pytest.raises(FirstUserAlreadyInitializedError) as dup_exc:
        svc_staging.create_first_platform_admin(
            email="second@orcia.io",
            display_name="Second",
            password_hash=DUMMY_HASH,
            bootstrap_token="boot-tok-secret-999",
        )
    assert dup_exc.value.error_code == "ERR_FIRST_USER_ALREADY_INITIALIZED"
    assert dup_exc.value.http_status == 409

    # In local env (`ORCIA_ENV == 'local'`), bootstrap_token is not required if users == 0
    svc_local = ProgressiveDay0AccostageService(orcia_env="local", expected_bootstrap_token=None)
    local_admin = svc_local.create_first_platform_admin(
        email="marc@orcia.local",
        display_name="Marc Local",
        password_hash=DUMMY_HASH,
        bootstrap_token=None,
    )
    assert local_admin.platform_role == "PLATFORM_ADMIN"


@pytest.mark.asyncio
async def test_story_9_2_concurrent_first_admin_creation_serialized_by_exclusive_lock() -> None:
    """Verify concurrent calls to `create_first_platform_admin_async` allow exactly 1 winner."""
    svc = ProgressiveDay0AccostageService(
        orcia_env="production",
        expected_bootstrap_token="prod-boot-token-123",
    )

    results = await asyncio.gather(
        svc.create_first_platform_admin_async(
            email="admin1@orcia.io",
            display_name="Admin 1",
            password_hash=DUMMY_HASH,
            bootstrap_token="prod-boot-token-123",
        ),
        svc.create_first_platform_admin_async(
            email="admin2@orcia.io",
            display_name="Admin 2",
            password_hash=DUMMY_HASH,
            bootstrap_token="prod-boot-token-123",
        ),
        svc.create_first_platform_admin_async(
            email="admin3@orcia.io",
            display_name="Admin 3",
            password_hash=DUMMY_HASH,
            bootstrap_token="prod-boot-token-123",
        ),
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, BaseException)]
    conflicts = [r for r in results if isinstance(r, FirstUserAlreadyInitializedError)]
    assert len(successes) == 1
    assert len(conflicts) == 2


def test_story_9_2_progressive_llm_tier_and_accostage_1_to_6_progression() -> None:
    """Verify 0/6 at Day 0, 1/6 after admin, 1 model -> Quick Trial, >= 2 families -> AD-10."""
    assert len(ACCOSTAGE_SIX_MILESTONES) == 6
    assert [m.title_fr for m in ACCOSTAGE_SIX_MILESTONES] == [
        "1. Compte Admin",
        "2. Modèles IA",
        "3. Organisation",
        "4. Premier Espace d'équipe",
        "5. Première Source",
        "6. Premier Processus",
    ]
    svc = ProgressiveDay0AccostageService(orcia_env="local")

    # Initial state: 0 users, 0 models -> Accostage 0/6
    status0 = svc.get_accostage_status()
    assert status0.completed_count == 0
    assert status0.completed_milestone_keys == ()
    assert status0.total_count == 6
    assert status0.badge_label == "Accostage 0/6"
    assert status0.llm_tier_mode == "UNCONFIGURED"
    assert status0.assistant_trial_enabled is False
    assert status0.agentic_gates_ad10_enabled is False

    # Create first admin -> Accostage 1/6
    svc.create_first_platform_admin(
        email="admin@orcia.local",
        display_name="Admin Local",
        password_hash=DUMMY_HASH,
    )
    status_admin = svc.get_accostage_status()
    assert status_admin.completed_count == 1
    assert status_admin.completed_milestone_keys == ("first-admin",)
    assert status_admin.badge_label == "Accostage 1/6"

    # Configure 1 single LLM family (e.g. Ollama local) at step 2 -> Quick Trial Mode unlocked!
    ep1 = LlmModelEndpoint(
        id="ep-ollama-1",
        endpoint_key="ollama-qwen",
        provider_slug="ollama",
        model_family="qwen-2.5",
        model_name="qwen2.5-coder:14b",
        endpoint_uri="http://localhost:11434",
    )
    status1 = svc.register_progressive_llm_endpoint(ep1)
    assert status1.llm_tier_mode == "QUICK_TRIAL_SINGLE_FAMILY"
    assert status1.assistant_trial_enabled is True
    assert status1.agentic_gates_ad10_enabled is False
    assert "⚠️ 1 seule famille de modèles configurée" in (status1.amber_warning_badge or "")
    assert "AD-10" in (status1.amber_warning_badge or "")
    assert status1.completed_count == 2
    assert status1.badge_label == "Accostage 2/6"

    # Configure a 2nd distinct LLM family (e.g. Anthropic Claude) -> Agentic Gates AD-10 unlocked!
    ep2 = LlmModelEndpoint(
        id="ep-claude-2",
        endpoint_key="claude-sonnet",
        provider_slug="anthropic",
        model_family="anthropic-claude",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com",
    )
    status2 = svc.register_progressive_llm_endpoint(ep2)
    assert status2.llm_tier_mode == "FULL_ORTHOGONAL_AD10"
    assert status2.assistant_trial_enabled is True
    assert status2.agentic_gates_ad10_enabled is True
    assert status2.amber_warning_badge is None
    assert status2.distinct_families == ("anthropic-claude", "qwen-2.5")

    assert svc.orcia_env == "local"
    assert svc.expected_bootstrap_token == "orcia-day0-bootstrap-token"
    admin_rec = svc.first_admin
    assert admin_rec is not None
    svc.set_first_platform_admin_record(None)
    assert svc.first_admin is None
    assert svc.get_accostage_status().completed_milestone_keys == ("first-llm-model",)
    svc.set_first_platform_admin_record(admin_rec)
    assert svc.first_admin == admin_rec
    assert "first-admin" in svc.get_accostage_status().completed_milestone_keys
    svc.set_first_platform_admin_record(None)
    status_ws = svc.mark_milestone_completed("first-space")
    assert status_ws.completed_count == 2
    status_noop = svc.mark_milestone_completed("unknown-milestone")
    assert status_noop.completed_count == 2

    # Pure PG18 count sync covers incremental 0/6 -> 1/6 -> ... -> 6/6 progression
    svc_pg = ProgressiveDay0AccostageService(orcia_env="local")
    s0 = svc_pg.sync_from_pg18_counts(
        users_count=0,
        org_units_count=0,
        workspaces_count=0,
        models_count=0,
        sources_count=0,
        workflows_count=0,
        runs_count=0,
    )
    assert (s0.completed_count, s0.total_count, s0.badge_label) == (0, 6, "Accostage 0/6")
    assert s0.completed_milestone_keys == ()

    s1 = svc_pg.sync_from_pg18_counts(
        users_count=1, org_units_count=0, workspaces_count=0, models_count=0, sources_count=0
    )
    assert (s1.completed_count, s1.badge_label) == (1, "Accostage 1/6")

    s2 = svc_pg.sync_from_pg18_counts(
        users_count=1, org_units_count=0, workspaces_count=0, models_count=1, sources_count=0
    )
    assert (s2.completed_count, s2.badge_label) == (2, "Accostage 2/6")

    s3 = svc_pg.sync_from_pg18_counts(
        users_count=1, org_units_count=1, workspaces_count=0, models_count=1, sources_count=0
    )
    assert (s3.completed_count, s3.badge_label) == (3, "Accostage 3/6")

    s4 = svc_pg.sync_from_pg18_counts(
        users_count=1, org_units_count=1, workspaces_count=1, models_count=1, sources_count=0
    )
    assert (s4.completed_count, s4.badge_label) == (4, "Accostage 4/6")

    s5 = svc_pg.sync_from_pg18_counts(
        users_count=1, org_units_count=1, workspaces_count=1, models_count=1, sources_count=1
    )
    assert (s5.completed_count, s5.badge_label) == (5, "Accostage 5/6")

    synced = svc_pg.sync_from_pg18_counts(
        users_count=1,
        org_units_count=2,
        workspaces_count=1,
        models_count=1,
        sources_count=1,
        workflows_count=0,
        runs_count=1,
    )
    assert synced.completed_count == 6
    assert synced.badge_label == "Accostage 6/6"
    assert len(synced.completed_milestone_keys) == 6


def test_story_9_2_api_endpoints_welcome_setup_and_accostage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify FastAPI endpoints for `/api/v1/bootstrap/welcome-setup/*` and `/accostage-status`."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)

    # 1. GET /api/v1/bootstrap/accostage-status -> first_admin_initialized is False, 0/6 initially
    resp0 = client.get("/api/v1/bootstrap/accostage-status")
    assert resp0.status_code == 200
    body0 = resp0.json()
    assert body0["completed_count"] == 0
    assert body0["completed_milestone_keys"] == []
    assert body0["badge_label"] == "Accostage 0/6"
    assert body0["first_admin_initialized"] is False
    assert body0["first_admin_email"] is None

    # 2. POST /api/v1/bootstrap/welcome-setup/first-admin with wrong token when env != local -> 403
    resp_denied = client.post(
        "/api/v1/bootstrap/welcome-setup/first-admin",
        json={
            "email": "intruder@orcia.io",
            "display_name": "Intruder",
            "password": DUMMY_PW,
            "orcia_env": "production",
            "bootstrap_token": "invalid-token",
        },
    )
    assert resp_denied.status_code == 403
    assert resp_denied.json()["error_code"] == "ERR_INVALID_BOOTSTRAP_TOKEN"

    # 2b. POST /api/v1/bootstrap/welcome-setup/first-admin in local env -> 200 and marks initialized
    resp_admin = client.post(
        "/api/v1/bootstrap/welcome-setup/first-admin",
        json={
            "email": "romain.admin@orcia.fr",
            "display_name": "Romain Admin",
            "password": DUMMY_PW,
            "orcia_env": "local",
        },
    )
    assert resp_admin.status_code == 200
    admin_body = resp_admin.json()
    assert admin_body["email"] == "romain.admin@orcia.fr"
    assert admin_body["display_name"] == "Romain Admin"
    assert admin_body["platform_role"] == "PLATFORM_ADMIN"

    # 2c. Subsequent GET /api/v1/bootstrap/accostage-status reflects first_admin_initialized=True
    resp_after = client.get("/api/v1/bootstrap/accostage-status")
    assert resp_after.status_code == 200
    after_body = resp_after.json()
    assert after_body["first_admin_initialized"] is True
    assert after_body["first_admin_email"] == "romain.admin@orcia.fr"
    assert after_body["first_admin_display_name"] == "Romain Admin"

    # 3. POST /api/v1/bootstrap/welcome-setup/progressive-llm with 1 model -> Quick Trial Mode
    resp_llm1 = client.post(
        "/api/v1/bootstrap/welcome-setup/progressive-llm",
        json={
            "endpoint_key": "local-ollama",
            "provider_slug": "ollama",
            "model_family": "llama-3.3",
            "model_name": "llama3.3:70b",
            "endpoint_uri": "http://localhost:11434",
        },
    )
    assert resp_llm1.status_code == 200
    data1 = resp_llm1.json()
    assert data1["llm_tier_mode"] == "QUICK_TRIAL_SINGLE_FAMILY"
    assert data1["assistant_trial_enabled"] is True
    assert data1["agentic_gates_ad10_enabled"] is False
    assert "⚠️ 1 seule famille de modèles configurée" in data1["amber_warning_badge"]

    # 4. Add 2nd family -> FULL_ORTHOGONAL_AD10
    resp_llm2 = client.post(
        "/api/v1/bootstrap/welcome-setup/progressive-llm",
        json={
            "endpoint_key": "mistral-eu",
            "provider_slug": "mistral",
            "model_family": "mistral-large",
            "model_name": "mistral-large-latest",
            "endpoint_uri": "https://api.mistral.ai",
        },
    )
    assert resp_llm2.status_code == 200
    data2 = resp_llm2.json()
    assert data2["llm_tier_mode"] == "FULL_ORTHOGONAL_AD10"
    assert data2["agentic_gates_ad10_enabled"] is True
    assert data2["amber_warning_badge"] is None

    # 5. PUT & GET /api/v1/bootstrap/platform-setup-state persists 11 collections & syncs Accostage
    put_resp = client.put(
        "/api/v1/bootstrap/platform-setup-state",
        json={
            "org_units": [
                {"id": "org-1", "name": "BU Finance", "slug": "bu-finance", "level": "BU"}
            ],
            "rbac_grants": [{"id": "grant-1", "subjectId": "Chef1", "verb": "read"}],
            "llm_tiers": [
                {
                    "tier": "standard",
                    "tierKey": "standard",
                    "primaryModel": "claude-3-7-sonnet",
                    "modelFamily": "anthropic",
                    "provider": "anthropic",
                    "model": "claude-3-7-sonnet",
                },
                {
                    "tier": "reasoning",
                    "tierKey": "reasoning",
                    "primaryModel": "gpt-4o",
                    "modelFamily": "openai",
                    "provider": "openai",
                    "model": "gpt-4o",
                },
            ],
            "workspaces": [
                {
                    "workspaceId": "ws-1",
                    "name": "Espace Paiements",
                    "slug": "espace-paiements",
                    "visibilityMode": "STANDARD",
                    "lifecyclePhase": "BUILD",
                }
            ],
            "datasources": [
                {"id": "ds-1", "alias": "git-core", "scheme": "git", "uri": "git://core"}
            ],
            "packs": [{"packKey": "orcia-pack-sdlc", "version": "1.0.0", "status": "PUBLISHED"}],
            "workflows": [{"workflowKey": "wf-1", "title": "Audit Code", "version": "1.0.0"}],
            "runs": [{"runId": "run-1", "title": "Run Pilote", "status": "RUNNING"}],
            "catalog_items": [{"resourceId": "wf-wf-1", "title": "Audit Code"}],
            "ontology_concepts": [{"conceptKey": "c-1", "canonicalTerm": "RunLock"}],
            "audit_events": [{"id": "evt-1", "eventType": "WorkspaceCreated", "summary": "ok"}],
        },
    )
    assert put_resp.status_code == 200
    put_data = put_resp.json()
    assert put_data["first_admin_initialized"] is True
    assert len(put_data["workspaces"]) == 1
    assert put_data["workspaces"][0]["name"] == "Espace Paiements"
    assert len(put_data["llm_tiers"]) == 2

    get_resp = client.get("/api/v1/bootstrap/platform-setup-state")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert len(get_data["org_units"]) == 1
    assert len(get_data["workspaces"]) == 1
    assert len(get_data["datasources"]) == 1
    assert len(get_data["workflows"]) == 1

    # Accostage status now reflects all 6 milestones completed!
    resp_acc6 = client.get("/api/v1/bootstrap/accostage-status")
    assert resp_acc6.status_code == 200
    acc6 = resp_acc6.json()
    assert acc6["completed_count"] == 6
    assert acc6["badge_label"] == "Accostage 6/6"
    assert acc6["llm_tier_mode"] == "FULL_ORTHOGONAL_AD10"


@pytest.mark.asyncio
async def test_sql_platform_setup_relational_sync_and_reconciliation_unit() -> None:
    """Unit test `sync_relational_tables_on_postgres18` and `_reconcile_*_on_load`."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
        ROOT_ORG_UNIT_ID,
        deterministic_setup_uuid,
        normalize_setup_slug,
        sync_relational_tables_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_platform_setup_store import (
        _reconcile_org_units_on_load,
        _reconcile_workspaces_on_load,
    )

    assert normalize_setup_slug("  Équipe RTS #1 ", "fallback") == "quipe-rts-1"
    u1 = deterministic_setup_uuid("org:org-1")
    assert deterministic_setup_uuid(str(u1)) == u1

    stale_org_id = uuid4()
    stale_ws_id = uuid4()

    async def _fake_execute(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        sql = str(stmt)
        res = MagicMock()
        if "INSERT INTO org_units" in sql and "'orcia-root'" in sql:
            res.first.return_value = (ROOT_ORG_UNIT_ID,)
        elif "INSERT INTO org_units" in sql:
            res.first.return_value = (params["id"] if params else uuid4(),)
        elif "SELECT id FROM org_units" in sql:
            res.fetchall.return_value = [(stale_org_id,)]
        elif "INSERT INTO workspaces" in sql:
            res.first.return_value = (params["id"] if params else uuid4(),)
        elif "SELECT id FROM workspaces" in sql:
            res.fetchall.return_value = [(stale_ws_id,)]
        elif "SELECT count(*) FROM blackboard_snapshots" in sql:
            res.scalar_one.return_value = 0
        elif "SELECT id, slug, name, unit_type, parent_id" in sql:
            bu_uuid = uuid4()
            team_uuid = uuid4()
            res.fetchall.return_value = [
                (bu_uuid, "123", "123", "BU", ROOT_ORG_UNIT_ID),
                (team_uuid, "moncompte", "MonCompte", "TEAM", bu_uuid),
            ]
        elif "FROM workspaces w" in sql:
            res.fetchall.return_value = [
                (
                    uuid4(),
                    "rts",
                    "RTS",
                    "STANDARD",
                    '{"lifecycle_phase": "MIGRATION", "ui_workspace_id": "ws-1"}',
                    0.0,
                    "moncompte",
                    "MonCompte",
                    "TEAM",
                )
            ]
        return res

    conn = AsyncMock()
    conn.execute.side_effect = _fake_execute

    await sync_relational_tables_on_postgres18(
        conn,
        org_units=[
            {
                "id": "org-1",
                "name": "123",
                "slug": "123",
                "level": "BU",
                "parentId": "scope-global",
            },
            {
                "id": "org-2",
                "name": "MonCompte",
                "slug": "moncompte",
                "level": "TEAM",
                "parentId": "org-1",
            },
        ],
        workspaces=[
            {
                "workspaceId": "ws-1",
                "name": "RTS",
                "slug": "rts",
                "visibilityMode": "STANDARD",
                "lifecyclePhase": "MIGRATION",
                "ownerOrgUnitId": "org-2",
            }
        ],
        llm_tiers=[{"tier": "medium", "primaryModel": "openai/gpt-4o", "modelFamily": "openai"}],
    )

    reconciled_orgs = await _reconcile_org_units_on_load(conn, [])
    assert len(reconciled_orgs) == 2
    assert reconciled_orgs[0] == {
        "id": "org-1",
        "name": "123",
        "slug": "123",
        "level": "BU",
        "parentId": "scope-global",
    }
    assert reconciled_orgs[1] == {
        "id": "org-2",
        "name": "MonCompte",
        "slug": "moncompte",
        "level": "TEAM",
        "parentId": "org-1",
    }

    reconciled_ws = await _reconcile_workspaces_on_load(conn, [], reconciled_orgs)
    assert len(reconciled_ws) == 1
    assert reconciled_ws[0]["name"] == "RTS"
    assert reconciled_ws[0]["ownerOrgUnitId"] == "org-2"
    assert reconciled_ws[0]["ownerOrgUnitName"] == "MonCompte"

    # Also exercise non-empty pass-through & ownerOrgUnitName enrichment
    passthrough_orgs = await _reconcile_org_units_on_load(conn, reconciled_orgs)
    assert passthrough_orgs == reconciled_orgs
    enriched_ws = await _reconcile_workspaces_on_load(
        conn,
        [{"workspaceId": "ws-1", "name": "RTS", "ownerOrgUnitId": "org-2"}],
        reconciled_orgs,
    )
    assert enriched_ws[0]["ownerOrgUnitName"] == "MonCompte"


@pytest.mark.asyncio
async def test_sql_platform_setup_store_hydrates_llm_tiers_from_mappings_unit() -> None:
    """Verify `load_platform_setup_state_from_postgres18` hydrates `llm_tiers` from PG18."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    from orcia_core.bootstrap._internal import sql_platform_setup_store as store

    async def _fake_execute(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        _ = params
        sql = str(stmt)
        res = MagicMock()
        if "FROM platform_settings" in sql:
            res.first.return_value = None
        elif "FROM workspace_llm_tier_mappings" in sql:
            res.fetchall.return_value = [
                (
                    "complex",
                    "deep",
                    "anthropic",
                    "anthropic-claude",
                    "claude-3-7-sonnet",
                    "claude-3-5-haiku",
                    "https://api.anthropic.com",
                    "api_key",
                    True,
                )
            ]
        elif (
            "FROM llm_model_endpoints" in sql or "FROM org_units" in sql or "FROM workspaces" in sql
        ):
            res.fetchall.return_value = []
        return res

    conn = AsyncMock()
    conn.execute.side_effect = _fake_execute

    @asynccontextmanager
    async def _fake_connect():
        yield conn

    fake_engine = MagicMock()
    fake_engine.connect = _fake_connect

    original_get_admin = store.get_first_platform_admin_from_postgres18
    store.get_first_platform_admin_from_postgres18 = AsyncMock(return_value=None)
    try:
        snapshot = await store.load_platform_setup_state_from_postgres18(
            fake_engine, orcia_env="local"
        )
    finally:
        store.get_first_platform_admin_from_postgres18 = original_get_admin

    assert len(snapshot.llm_tiers) == 1
    assert snapshot.llm_tiers[0] == {
        "tier": "complex",
        "defaultEffort": "deep",
        "provider": "anthropic",
        "modelFamily": "anthropic-claude",
        "primaryModel": "claude-3-7-sonnet",
        "secondaryModel": "claude-3-5-haiku",
        "endpointUrl": "https://api.anthropic.com",
        "authMode": "api_key",
        "apiKeyConfigured": True,
    }

    # Verify fallback to `llm_model_endpoints` when mappings are empty, and JSON-string settings
    async def _fake_execute_ep(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        _ = params
        sql = str(stmt)
        res = MagicMock()
        if "FROM platform_settings" in sql:
            res.first.return_value = ('{"workspaces": [{"workspaceId": "ws-1"}]}',)
        elif "FROM workspace_llm_tier_mappings" in sql:
            res.fetchall.return_value = []
        elif "FROM llm_model_endpoints" in sql:
            res.fetchall.return_value = [("ep-1", "gpt-4o", "openai")]
        elif "INSERT INTO org_units" in sql or "INSERT INTO workspaces" in sql:
            res.first.return_value = (store.ROOT_ORG_UNIT_ID,)
        elif "SELECT count(*) FROM blackboard_snapshots" in sql:
            res.scalar_one.return_value = 0
        elif "FROM org_units" in sql or "FROM workspaces" in sql:
            res.fetchall.return_value = []
        return res

    conn.execute.side_effect = _fake_execute_ep

    @asynccontextmanager
    async def _fake_begin():
        yield conn

    fake_engine.begin = _fake_begin
    store.get_first_platform_admin_from_postgres18 = AsyncMock(return_value=None)
    try:
        ep_snap = await store.load_platform_setup_state_from_postgres18(
            fake_engine, orcia_env="local"
        )
        assert len(ep_snap.llm_tiers) == 1
        assert ep_snap.llm_tiers[0]["primaryModel"] == "gpt-4o"
        assert ep_snap.llm_tiers[0]["modelFamily"] == "openai"

        saved_snap = await store.save_platform_setup_state_to_postgres18(
            fake_engine, ep_snap, orcia_env="local"
        )
        assert saved_snap.first_admin_initialized is False
        assert saved_snap.llm_tiers == ep_snap.llm_tiers

        await store.persist_progressive_llm_endpoint_to_postgres18(
            fake_engine,
            LlmModelEndpoint(
                id="ep-1",
                endpoint_key="ep-1",
                provider_slug="openai",
                model_family="openai",
                model_name="gpt-4o",
                endpoint_uri="https://api.openai.com/v1",
            ),
        )
    finally:
        store.get_first_platform_admin_from_postgres18 = original_get_admin

    from orcia_core.bootstrap._internal.sql_accostage_counts import get_accostage_pg18_counts

    async def _fake_counts_none(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        _ = (stmt, params)
        res = MagicMock()
        res.first.return_value = None
        return res

    conn.execute.side_effect = _fake_counts_none
    empty_counts = await get_accostage_pg18_counts(fake_engine)
    assert empty_counts.users_count == 0
    assert empty_counts.admin_created is False
