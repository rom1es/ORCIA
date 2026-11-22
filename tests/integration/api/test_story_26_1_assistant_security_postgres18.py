"""Story 26.1 — Layer 2 PG18 Vertical Integration Tests on Real Composition Root.

Verifies without dependency_overrides:
1. Cross-workspace IDOR rejection on PG18-persisted workspaces (UUID and slug) & pre-stream 403.
2. Real workspace `scope_id` resolution in `assistant_llm_resolver` (with GLOBAL fallback).
3. `GET /api/v1/bootstrap/platform-setup-state` unauthenticated `{is_initialized, step}` vs
   `PLATFORM_ADMIN` full view with zero credentials leaked.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app
from orcia_core.orchestration._internal.sql_ai_model_mappings import (
    create_ai_model_mapping_pg18,
)
from orcia_core.permissions import SecretInputSpec
from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_26_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_26_1_pw"  # pragma: allowlist secret


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
            "PATH": "/usr/bin:/bin",
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "alembic"), "-c", "infra/migrations/alembic.ini"]
            + ["upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield url


@pytest.mark.asyncio
async def test_pg18_vertical_assistant_scope_guard_resolver_and_setup_state(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify real PG18 workspace guard (UUID & slug), real scope_id LLM resolution & setup."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "false")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-26-1-jwt-secret-00000001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-26-1-vault-key-00000001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    engine = create_async_engine(database_url)
    try:
        app = create_app()
        assert app.dependency_overrides == {}
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            # 1. Day-0 unauthenticated setup-state projection returns ONLY {is_initialized, step}
            day0_state = await client.get("/api/v1/bootstrap/platform-setup-state")
            assert day0_state.status_code == 200
            assert day0_state.json()["is_initialized"] is False
            assert set(day0_state.json().keys()) == {"is_initialized", "step"}

            # 2. Bootstrap first admin -> access_token
            admin_res = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.26.1@orcia.test",
                    "display_name": "Admin 26.1",
                    "password": "StrongPassword!261",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert admin_res.status_code == 200, admin_res.text
            admin_token = admin_res.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Unauthenticated setup-state still exposes zero admin emails or configs
            post_init_unauth = await client.get("/api/v1/bootstrap/platform-setup-state")
            assert post_init_unauth.status_code == 200
            assert set(post_init_unauth.json().keys()) == {"is_initialized", "step"}
            assert post_init_unauth.json()["is_initialized"] is True

            # Admin setup-state returns full view
            admin_setup = await client.get(
                "/api/v1/bootstrap/platform-setup-state", headers=admin_headers
            )
            assert admin_setup.status_code == 200
            assert admin_setup.json()["first_admin_email"] == "admin.26.1@orcia.test"

            # 3. Create OrgUnit + 2 Workspaces (ws_alpha standard, ws_beta confidential)
            bu_res = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={"name": "BU 26.1", "slug": "bu-26-1", "kind": "BU"},
            )
            assert bu_res.status_code in (200, 201), bu_res.text
            bu_id = bu_res.json()["id"]

            ws_a_res = await client.post(
                "/api/v1/workspaces",
                headers=admin_headers,
                json={
                    "name": "Workspace Alpha 26.1",
                    "slug": "ws-alpha-26-1",
                    "owner_org_unit_id": bu_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert ws_a_res.status_code in (200, 201), ws_a_res.text
            ws_a_id = ws_a_res.json()["id"]

            # Create confidential workspace owned by a separate user in PG18
            ws_b_id = new_uuid7_str()
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode)
                        VALUES (CAST(:id AS uuid), 'ws-conf-26-1', 'Confidential 26.1',
                                CAST(:ou AS uuid), 'CONFIDENTIAL_RESTRICTED')
                        """
                    ),
                    {"id": ws_b_id, "ou": bu_id},
                )
                # Register a workspace-scoped chat model mapping for ws_a_id
                await create_ai_model_mapping_pg18(
                    conn,
                    cipher=app.state.auth_service.vault_cipher,
                    scope_level="WORKSPACE",
                    scope_id=ws_a_id,
                    display_name="Workspace Alpha Chat Model",
                    inference_tier="medium",
                    effort="balanced",
                    provider_slug="openai",
                    model_family="OpenAI",
                    model_name="openai-ws-alpha-custom",
                    endpoint_uri="https://api.openai.com/v1",
                    auth_mode="api_key",
                    protocol_mode="openai_compatible",
                    usage="chat",
                    secret_input=SecretInputSpec(
                        action="set", plaintext_value="sk-ws-alpha-secret-9999"
                    ),
                )

            # 4. Cross-workspace IDOR on confidential workspace (both UUID and slug) -> 403
            for conf_ref in (ws_b_id, "ws-conf-26-1"):
                idor_res = await client.post(
                    "/api/v1/assistant/three-speed/stream",
                    headers=admin_headers,
                    json={"workspace_id": conf_ref, "user_prompt": "Read confidential"},
                )
                assert idor_res.status_code == 403
                assert idor_res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            # 5. Real workspace scope_id resolves workspace model (never shadowed by snapshot)
            put_snap = await client.put(
                "/api/v1/bootstrap/platform-setup-state",
                headers=admin_headers,
                json={
                    "org_units": [
                        {
                            "id": "org-bu-26-1",
                            "slug": "bu-26-1",
                            "name": "BU 26.1",
                            "level": "BU",
                        }
                    ],
                    "llm_tiers": [
                        {
                            "tier": "medium",
                            "primaryModel": "global-stripped-fallback",
                            "modelFamily": "openai",
                            "endpointUrl": "https://api.openai.com/v1",
                            "apiKey": "sk-stripped-not-returned",  # pragma: allowlist secret
                        }
                    ],
                },
            )
            assert put_snap.status_code == 200

            # [P2-2] Unauthenticated setup-state reflects PG18 milestone progress (not FIRST_ADMIN)
            progressed = await client.get("/api/v1/bootstrap/platform-setup-state")
            assert progressed.status_code == 200
            assert progressed.json()["is_initialized"] is True
            assert progressed.json()["step"] != "FIRST_ADMIN"

            from starlette.requests import Request as StarletteRequest

            from orcia_api.routers.assistant_llm_resolver import resolve_configured_llm_endpoint

            scope = {
                "type": "http",
                "app": app,
                "headers": [],
                "path": "/api/v1/assistant/three-speed/turn",
            }
            fake_req = StarletteRequest(scope)
            ep_a = await resolve_configured_llm_endpoint(
                fake_req, requested_tier="medium", workspace_id=ws_a_id
            )
            assert ep_a is not None
            assert ep_a.model_name == "openai-ws-alpha-custom"
            assert ep_a.api_key == "sk-ws-alpha-secret-9999"  # pragma: allowlist secret

            # Slug resolution works identically
            ep_slug = await resolve_configured_llm_endpoint(
                fake_req, requested_tier="medium", workspace_id="ws-alpha-26-1"
            )
            assert ep_slug is not None
            assert ep_slug.model_name == "openai-ws-alpha-custom"
            assert ep_slug.api_key == "sk-ws-alpha-secret-9999"  # pragma: allowlist secret
    finally:
        await engine.dispose()
