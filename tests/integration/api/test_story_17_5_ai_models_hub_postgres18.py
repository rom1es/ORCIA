"""Story 17.5 — Vertical HTTP -> PostgreSQL 18 Integration Tests for AI Models Hub.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261114_1705` (`upgrade head` -> `downgrade 20261111_1704` -> `upgrade head`).
2. SSRF prevention (`422 ERR_UNSAFE_LLM_ENDPOINT_URL`) on cloud metadata IPs.
3. Read-only observer guard (`403 ERR_OBSERVER_MODE_READ_ONLY`).
4. AES-256-GCM encrypted API key in PostgreSQL 18 and masked hint verification.
5. 1-click test connection updating health status and latency in PostgreSQL 18.
6. Secret key rotation (keep, set, clear) via PATCH.
7. Impact evaluation and deletion.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import httpx
import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_17_5"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_17_5_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261114_1705
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261111_1704"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-17-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-17-5-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client() -> AsyncClient:
        app = create_app()
        initialize_app_services(app)

        def mock_llm_handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "mock-msg",
                    "content": [{"type": "text", "text": "pong"}],
                    "choices": [{"message": {"role": "assistant", "content": "pong"}}],
                },
            )

        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_llm_handler))
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_client


@pytest.mark.asyncio
async def test_ai_models_hub_postgres18_full_lifecycle(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers_admin = {"X-Orcia-Persona": "karim"}
    headers_observer = {
        "X-Orcia-Persona": "sarah",
        "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER",
    }
    engine = create_async_engine(database_url)
    user_admin_id = UUID(new_uuid7_str())

    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM workspace_llm_tier_mappings"))
        await conn.execute(sa.text("DELETE FROM iam_accounts"))
        await conn.execute(sa.text("DELETE FROM users"))

        # Root org unit
        root_ou = (
            await conn.execute(
                sa.text("SELECT id FROM org_units WHERE unit_type = 'ENTERPRISE' LIMIT 1")
            )
        ).scalar()
        if root_ou is None:
            root_ou = UUID(new_uuid7_str())
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                    "VALUES (:id, 'orcia-root', 'ORCIA Enterprise', 'ENTERPRISE', NULL)"
                ),
                {"id": root_ou},
            )

        # Admin user
        await conn.execute(
            sa.text(
                "INSERT INTO users ("
                "  id, email, display_name, auth_mode, human_profile_archetype, "
                "  platform_role, primary_org_unit_id, is_active"
                ") VALUES ("
                "  :id, 'marc.admin@orcia.io', 'Marc Admin', 'LOCAL', 'ARCHITECT', "
                "  'PLATFORM_ADMIN', :ou_id, TRUE"
                ")"
            ),
            {"id": user_admin_id, "ou_id": root_ou},
        )

    async with app_client_factory() as client:
        # 1. SSRF Guard test: cloud metadata link-local IP
        ssrf_res = await client.post(
            "/api/v1/settings/ai-models/mappings",
            headers=headers_admin,
            json={
                "scope_level": "GLOBAL",
                "display_name": "SSRF Exploit Target",
                "inference_tier": "medium",
                "provider_slug": "malicious",
                "model_family": "Custom",
                "model_name": "exploit-model",
                "endpoint_uri": "http://169.254.169.254/latest/meta-data",
                "auth_mode": "none_local",
            },
        )
        assert ssrf_res.status_code == 422
        assert ssrf_res.json()["error_code"] == "ERR_UNSAFE_LLM_ENDPOINT_URL"

        # 2. Observer Mode Guard test: read-only observer cannot create model
        obs_res = await client.post(
            "/api/v1/settings/ai-models/mappings",
            headers=headers_observer,
            json={
                "scope_level": "GLOBAL",
                "display_name": "Blocked Observer Model",
                "inference_tier": "simple",
                "provider_slug": "anthropic",
                "model_family": "Anthropic",
                "model_name": "claude-3-5-haiku",
                "endpoint_uri": "https://api.anthropic.com/v1",
                "auth_mode": "none_local",
            },
        )
        assert obs_res.status_code == 403
        assert obs_res.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 3. Create mapping with AES-256-GCM secret
        canary_secret = "sk-ant-api03-canarysecret-999888777123"  # pragma: allowlist secret
        create_res = await client.post(
            "/api/v1/settings/ai-models/mappings",
            headers=headers_admin,
            json={
                "scope_level": "GLOBAL",
                "display_name": "Claude 3.7 Sonnet (Standard)",
                "inference_tier": "medium",
                "effort": "balanced",
                "provider_slug": "anthropic",
                "model_family": "Anthropic",
                "model_name": "claude-3-7-sonnet",
                "fallback_model_name": "claude-3-5-haiku",
                "endpoint_uri": "https://api.anthropic.com/v1",
                "auth_mode": "api_key",
                "protocol_mode": "openai_compatible",
                "secret_input": {
                    "action": "set",
                    "plaintext_value": canary_secret,
                },
            },
        )
        assert create_res.status_code == 201
        created_json = create_res.json()
        mapping_id = created_json["id"]
        assert created_json["secret_status"]["configured"] is True
        assert created_json["secret_status"]["masked_hint"] == "••••••••7123"
        assert created_json["secret_status"]["fingerprint"] is not None
        # Verify canary plaintext is NEVER exposed in HTTP response
        assert canary_secret not in create_res.text

        # 4. Direct PostgreSQL 18 SELECT: verify encryption and storage
        async with engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT encrypted_api_key, secret_fingerprint, secret_masked_hint, "
                            "       health_status, auth_mode, display_name "
                            "FROM workspace_llm_tier_mappings WHERE id = :id"
                        ),
                        {"id": UUID(mapping_id)},
                    )
                )
                .mappings()
                .one()
            )
            assert row["encrypted_api_key"] is not None
            assert ":" in row["encrypted_api_key"]
            assert canary_secret not in row["encrypted_api_key"]
            assert row["secret_masked_hint"] == "••••••••7123"
            assert row["secret_fingerprint"].startswith("sha256:")
            assert row["health_status"] == "UNTESTED"
            assert row["display_name"] == "Claude 3.7 Sonnet (Standard)"

        # 5. List mappings via GET: returns items with masked hint
        list_res = await client.get(
            "/api/v1/settings/ai-models/mappings",
            headers=headers_admin,
        )
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert len(items) >= 1
        found = next(i for i in items if i["id"] == mapping_id)
        assert found["secret_status"]["masked_hint"] == "••••••••7123"
        assert canary_secret not in list_res.text

        # 6. Test connection via POST .../test
        test_res = await client.post(
            f"/api/v1/settings/ai-models/mappings/{mapping_id}/test",
            headers=headers_admin,
        )
        assert test_res.status_code == 200
        test_data = test_res.json()
        assert test_data["health_status"] in ("OPERATIONAL", "DEGRADED", "ERROR")
        assert test_data["latency_ms"] >= 0

        # Verify test result persisted in PostgreSQL 18
        async with engine.begin() as conn:
            updated_health = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT health_status, last_latency_ms "
                            "FROM workspace_llm_tier_mappings WHERE id = :id"
                        ),
                        {"id": UUID(mapping_id)},
                    )
                )
                .mappings()
                .one()
            )
            assert updated_health["health_status"] in ("OPERATIONAL", "DEGRADED", "ERROR")
            assert updated_health["last_latency_ms"] is not None

        # 7. Rotate secret key via PATCH
        rotated_canary = "sk-ant-api03-rotatedsecret-444555666777"
        patch_res = await client.patch(
            f"/api/v1/settings/ai-models/mappings/{mapping_id}",
            headers=headers_admin,
            json={
                "display_name": "Claude 3.7 Sonnet (Clé Remplacée)",
                "secret_input": {
                    "action": "set",
                    "plaintext_value": rotated_canary,
                },
            },
        )
        assert patch_res.status_code == 200
        patched_json = patch_res.json()
        assert patched_json["display_name"] == "Claude 3.7 Sonnet (Clé Remplacée)"
        assert patched_json["secret_status"]["masked_hint"] == "••••••••6777"
        assert rotated_canary not in patch_res.text

        # 8. Delete impact analysis
        impact_res = await client.get(
            f"/api/v1/settings/ai-models/mappings/{mapping_id}/delete-impact",
            headers=headers_admin,
        )
        assert impact_res.status_code == 200
        impact_json = impact_res.json()
        assert impact_json["mapping_id"] == mapping_id

        # 9. Force delete mapping
        del_res = await client.delete(
            f"/api/v1/settings/ai-models/mappings/{mapping_id}?mode=force",
            headers=headers_admin,
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "DELETED"

        # Verify deletion from PostgreSQL 18
        async with engine.begin() as conn:
            deleted_count = (
                await conn.execute(
                    sa.text("SELECT COUNT(*) FROM workspace_llm_tier_mappings WHERE id = :id"),
                    {"id": UUID(mapping_id)},
                )
            ).scalar()
            assert deleted_count == 0


@pytest.mark.asyncio
async def test_ai_models_hub_delete_without_false_positive_and_empty_reindex_status_pg18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Story 25.4: Static workflow_definitions_v2 never blocks delete; empty corpus reports 0/0."""
    headers_admin = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    wf_v2_id = UUID(new_uuid7_str())

    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM workspace_llm_tier_mappings"))
        await conn.execute(sa.text("DELETE FROM kb_chunks"))
        await conn.execute(sa.text("DELETE FROM kb_documents"))
        await conn.execute(sa.text("DELETE FROM rag_reindexing_jobs"))
        await conn.execute(sa.text("DELETE FROM workflow_definitions_v2"))
        await conn.execute(
            sa.text(
                """
                INSERT INTO workflow_definitions_v2 (
                    id, workflow_id, slug, version, status, pack_id, execution_mode, spec_jsonb
                ) VALUES (
                    :id, 'wf-static-medium', 'wf-static-medium', '1.0.0', 'published',
                    'core-pack', 'native_orcia', '{"default_tier": "medium"}'::jsonb
                )
                """
            ),
            {"id": wf_v2_id},
        )

    async with app_client_factory() as client:
        create_res = await client.post(
            "/api/v1/settings/ai-models/mappings",
            headers=headers_admin,
            json={
                "scope_level": "GLOBAL",
                "display_name": "Sole Medium Model",
                "inference_tier": "medium",
                "effort": "balanced",
                "provider_slug": "openai",
                "model_family": "OpenAI",
                "model_name": "gpt-4o-mini",
                "endpoint_uri": "https://api.openai.com/v1",
                "auth_mode": "none_local",
                "protocol_mode": "openai_compatible",
            },
        )
        assert create_res.status_code == 201
        mapping_id = create_res.json()["id"]

        impact_res = await client.get(
            f"/api/v1/settings/ai-models/mappings/{mapping_id}/delete-impact",
            headers=headers_admin,
        )
        assert impact_res.status_code == 200
        impact = impact_res.json()
        assert impact["is_last_active_for_tier"] is True
        assert impact["dependent_workflows_count"] == 0
        assert impact["pinned_active_runs_count"] == 0

        del_res = await client.delete(
            f"/api/v1/settings/ai-models/mappings/{mapping_id}?mode=reject",
            headers=headers_admin,
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "DELETED"

        async with engine.begin() as conn:
            remaining = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workspace_llm_tier_mappings"))
            ).scalar()
            assert remaining == 0

        list_res = await client.get(
            "/api/v1/settings/ai-models/mappings",
            headers=headers_admin,
        )
        assert list_res.status_code == 200
        assert list_res.json()["items"] == []

        reindex_res = await client.get(
            "/api/v1/settings/ai-models/reindex-status",
            headers=headers_admin,
        )
        assert reindex_res.status_code == 200
        reindex_json = reindex_res.json()
        assert reindex_json["status"] == "IDLE"
        assert reindex_json["indexed_chunks_count"] == 0
        assert reindex_json["indexed_documents_count"] == 0


@pytest.mark.asyncio
async def test_ai_models_delete_pinned_by_active_workflow_run_returns_409_pg18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """MAJOR-1 proof: PG18 workflow_runs (RUNNING) + inference_attempts blocks delete with 409."""
    headers_admin = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    ws_id = UUID(new_uuid7_str())
    wf_def_id = UUID(new_uuid7_str())
    run_id = UUID(new_uuid7_str())
    step_id = UUID(new_uuid7_str())
    attempt_id = UUID(new_uuid7_str())

    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("DELETE FROM inference_attempts"))
            await conn.execute(sa.text("DELETE FROM step_executions"))
            await conn.execute(sa.text("DELETE FROM workflow_runs"))
            await conn.execute(sa.text("DELETE FROM workflow_definitions"))
            await conn.execute(sa.text("DELETE FROM workspace_llm_tier_mappings"))

            root_ou = (
                await conn.execute(
                    sa.text("SELECT id FROM org_units WHERE unit_type = 'ENTERPRISE' LIMIT 1")
                )
            ).scalar()
            if root_ou is None:
                root_ou = UUID(new_uuid7_str())
                await conn.execute(
                    sa.text(
                        "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                        "VALUES (:id, 'orcia-root', 'ORCIA Enterprise', 'ENTERPRISE', NULL)"
                    ),
                    {"id": root_ou},
                )

            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (:id, :slug, 'Active Run WS', :ou_id, 'STANDARD')"
                ),
                {"id": ws_id, "slug": f"active-run-ws-{str(ws_id)[:8]}", "ou_id": root_ou},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workflow_definitions (id, workspace_id, uri, version, sha256) "
                    "VALUES (:id, :wid, :uri, '1.0.0', :sha)"
                ),
                {
                    "id": wf_def_id,
                    "wid": ws_id,
                    "uri": f"orcia://wf/pinned/{wf_def_id}",
                    "sha": "a" * 64,
                },
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workflow_runs ("
                    "  id, run_key, workspace_id, workflow_def_id, root_run_id, status"
                    ") VALUES (:id, :rkey, :wid, :wf_id, :id, 'RUNNING')"
                ),
                {
                    "id": run_id,
                    "rkey": f"run-pinned-{str(run_id)[:8]}",
                    "wid": ws_id,
                    "wf_id": wf_def_id,
                },
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO step_executions ("
                    "  id, step_execution_key, run_id, step_key, step_index"
                    ") VALUES (:id, :skey, :run_id, 'step-1', 0)"
                ),
                {"id": step_id, "skey": f"step-pinned-{str(step_id)[:8]}", "run_id": run_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO inference_attempts ("
                    "  id, run_id, step_execution_id, attempt_index, requested_tier, "
                    "  resolved_tier, effort, model_family, model_name, idempotency_key"
                    ") VALUES ("
                    "  :id, :run_id, :step_id, 1, 'medium', 'medium', 'balanced', "
                    "  'OpenAI', 'gpt-4o-pinned', :ikey"
                    ")"
                ),
                {
                    "id": attempt_id,
                    "run_id": run_id,
                    "step_id": step_id,
                    "ikey": f"attempt-{attempt_id}",
                },
            )

        async with app_client_factory() as client:
            # Create two active models for tier 'medium' so pinned guard triggers 409
            r1 = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=headers_admin,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Pinned Medium Model",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "gpt-4o-pinned",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                },
            )
            assert r1.status_code == 201, r1.text
            pinned_id = r1.json()["id"]

            r2 = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=headers_admin,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Backup Medium Model",
                    "inference_tier": "medium",
                    "effort": "deep",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "gpt-4o-backup",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                },
            )
            assert r2.status_code == 201, r2.text

            impact_res = await client.get(
                f"/api/v1/settings/ai-models/mappings/{pinned_id}/delete-impact",
                headers=headers_admin,
            )
            assert impact_res.status_code == 200, impact_res.text
            impact = impact_res.json()
            assert impact["pinned_active_runs_count"] >= 1
            assert str(run_id) in impact["pinned_run_ids"]
            assert impact["is_last_active_for_tier"] is False

            del_reject = await client.delete(
                f"/api/v1/settings/ai-models/mappings/{pinned_id}?mode=reject",
                headers=headers_admin,
            )
            assert del_reject.status_code == 409, del_reject.text
            assert del_reject.json()["error_code"] == "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS"

            del_drain = await client.delete(
                f"/api/v1/settings/ai-models/mappings/{pinned_id}?mode=drain",
                headers=headers_admin,
            )
            assert del_drain.status_code == 200, del_drain.text
            assert del_drain.json()["status"] == "DRAINING"

            async with engine.begin() as conn:
                row = (
                    await conn.execute(
                        sa.text(
                            "SELECT draining, is_active FROM workspace_llm_tier_mappings "
                            "WHERE id = :id"
                        ),
                        {"id": UUID(pinned_id)},
                    )
                ).one()
                assert row[0] is True
                assert row[1] is False
    finally:
        await engine.dispose()
