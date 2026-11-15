"""Story 19.3 — Integration Tests for AI Models Connection Test on PostgreSQL 18 (`AD-24.3`).

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Real non-blocking chat connection test (`POST /mappings/{id}/test`):
   - Success -> HTTP 200 with OPERATIONAL status and measured latency
   - Verification by SELECT on PostgreSQL 18 of persisted health_status and last_latency_ms
2. Real chat error handling:
   - 401 Unauthorized -> HTTP 401 RFC 9457 with ERR_MODEL_CONNECTION_AUTH_FAILED
   - Verification by SELECT on PostgreSQL 18 that health_status was updated to 'ERROR'
3. Real embedding connection test:
   - 1024-dim success -> HTTP 200 OPERATIONAL and SELECT verification
   - Dimension mismatch -> HTTP 422 RFC 9457 ERR_EMBEDDING_DIMENSION_MISMATCH & SELECT 'ERROR'
4. 0 $ cost in CI (HTTPX MockTransport).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

import httpx
import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_19_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_19_3_pw"  # pragma: allowlist secret


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
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-19-3-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-19-3-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client(mock_http_handler=None) -> tuple[AsyncClient, Any]:  # type: ignore[no-untyped-def]
        app = create_app()
        initialize_app_services(app)
        if mock_http_handler is not None:
            app.state.http_client = httpx.AsyncClient(
                transport=httpx.MockTransport(mock_http_handler)
            )
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test"), app

    return _build_client


@pytest.mark.asyncio
async def test_vertical_chat_and_embedding_connection_tests_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers_admin = {"X-Orcia-Persona": "marc"}
    engine = create_async_engine(database_url)
    user_admin_id = UUID(new_uuid7_str())

    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM workspace_llm_tier_mappings"))
        await conn.execute(sa.text("DELETE FROM iam_accounts"))
        await conn.execute(sa.text("DELETE FROM users"))

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

    # 1. Test Chat Success: MockTransport returns 200 OK
    def chat_mock_success(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/chat/completions" in url_str:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "pong"}}]},
            )
        return httpx.Response(404, text="Not Found")

    client, app = app_client_factory(mock_http_handler=chat_mock_success)

    # Create chat mapping
    create_chat_res = await client.post(
        "/api/v1/settings/ai-models/mappings",
        headers=headers_admin,
        json={
            "scope_level": "GLOBAL",
            "display_name": "Mistral Large (Chat Test)",
            "inference_tier": "complex",
            "effort": "balanced",
            "provider_slug": "mistral",
            "model_family": "Mistral",
            "model_name": "mistral-large-latest",
            "endpoint_uri": "https://api.mistral.ai/v1",
            "auth_mode": "api_key",
            "protocol_mode": "openai_compatible",
            "usage": "chat",
            "secret_input": {"action": "set", "plaintext_value": "sk-mistral-valid-test"},
        },
    )
    assert create_chat_res.status_code == 201
    chat_mapping_id = create_chat_res.json()["id"]

    # Execute test connection -> HTTP 200 OPERATIONAL
    test_chat_res = await client.post(
        f"/api/v1/settings/ai-models/mappings/{chat_mapping_id}/test",
        headers=headers_admin,
    )
    assert test_chat_res.status_code == 200
    test_chat_data = test_chat_res.json()
    assert test_chat_data["health_status"] == "OPERATIONAL"
    assert test_chat_data["latency_ms"] >= 0

    # Vertical PG18 SELECT verification
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT health_status, last_latency_ms "
                        "FROM workspace_llm_tier_mappings WHERE id = :id"
                    ),
                    {"id": UUID(chat_mapping_id)},
                )
            )
            .mappings()
            .one()
        )
        assert row["health_status"] == "OPERATIONAL"
        assert row["last_latency_ms"] is not None

    # 2. Test Chat Auth Failure: MockTransport returns 401
    def chat_mock_auth_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API Key"}})

    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(chat_mock_auth_fail))

    test_auth_fail_res = await client.post(
        f"/api/v1/settings/ai-models/mappings/{chat_mapping_id}/test",
        headers=headers_admin,
    )
    assert test_auth_fail_res.status_code == 401
    fail_json = test_auth_fail_res.json()
    assert fail_json["error_code"] == "ERR_MODEL_CONNECTION_AUTH_FAILED"

    # Vertical PG18 SELECT verification: status must be updated to ERROR
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT health_status, last_latency_ms "
                        "FROM workspace_llm_tier_mappings WHERE id = :id"
                    ),
                    {"id": UUID(chat_mapping_id)},
                )
            )
            .mappings()
            .one()
        )
        assert row["health_status"] == "ERROR"

    # 3. Test Embedding Dimension 1024 Success
    def embedding_mock_1024(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.001] * 1024}]},
        )

    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(embedding_mock_1024))

    create_emb_res = await client.post(
        "/api/v1/settings/ai-models/mappings",
        headers=headers_admin,
        json={
            "scope_level": "GLOBAL",
            "display_name": "OpenAI Embedding 1024",
            "inference_tier": "auto",
            "effort": "default",
            "provider_slug": "openai",
            "model_family": "OpenAI",
            "model_name": "text-embedding-3-large",
            "endpoint_uri": "https://api.openai.com/v1",
            "auth_mode": "api_key",
            "protocol_mode": "openai_compatible",
            "usage": "embedding",
            "secret_input": {"action": "set", "plaintext_value": "sk-openai-embedding"},
        },
    )
    assert create_emb_res.status_code == 201
    emb_mapping_id = create_emb_res.json()["id"]

    test_emb_res = await client.post(
        f"/api/v1/settings/ai-models/mappings/{emb_mapping_id}/test",
        headers=headers_admin,
    )
    assert test_emb_res.status_code == 200
    emb_test_data = test_emb_res.json()
    assert emb_test_data["health_status"] == "OPERATIONAL"

    # Vertical PG18 SELECT
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT health_status, last_latency_ms "
                        "FROM workspace_llm_tier_mappings WHERE id = :id"
                    ),
                    {"id": UUID(emb_mapping_id)},
                )
            )
            .mappings()
            .one()
        )
        assert row["health_status"] == "OPERATIONAL"

    # 4. Test Embedding Dimension Mismatch (e.g. 768 dimensions returned)
    def embedding_mock_768(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.002] * 768}]},
        )

    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(embedding_mock_768))

    test_mismatch_res = await client.post(
        f"/api/v1/settings/ai-models/mappings/{emb_mapping_id}/test",
        headers=headers_admin,
    )
    assert test_mismatch_res.status_code == 422
    mismatch_json = test_mismatch_res.json()
    assert mismatch_json["error_code"] == "ERR_EMBEDDING_DIMENSION_MISMATCH"

    # Vertical PG18 SELECT: status updated to ERROR
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text("SELECT health_status FROM workspace_llm_tier_mappings WHERE id = :id"),
                    {"id": UUID(emb_mapping_id)},
                )
            )
            .mappings()
            .one()
        )
        assert row["health_status"] == "ERROR"
