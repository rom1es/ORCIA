"""Story 19.5 — Integration Tests for AI Models usage & single active embedding on PostgreSQL 18.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261115_2105` (`upgrade head` -> `downgrade 20261115_1901` -> `upgrade head`).
2. Schema inspection: `usage` column and partial unique index on PostgreSQL 18.
3. HTTP POST /mappings with `usage='chat'` and `usage='embedding'`.
4. Verification by SELECT on PostgreSQL 18 of persisted usage and active flags.
5. Strict single active global embedding: creating second global embedding deactivates the first.
6. Raw SQL enforcement: inserting 2 active global embedding rows triggers UniqueViolationError.
7. Rejection of Anthropic for embedding usage (`422 ERR_EMBEDDING_PROVIDER_UNSUPPORTED`).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

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
DB_NAME = "orcia_story_19_5"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_19_5_pw"  # pragma: allowlist secret


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
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261115_2105
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261115_1901"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-19-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-19-5-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client() -> AsyncClient:
        app = create_app()
        initialize_app_services(app)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_client


@pytest.mark.asyncio
async def test_ai_models_usage_and_uniqueness_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers_admin = {"X-Orcia-Persona": "marc"}
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM workspace_llm_tier_mappings"))
        await conn.execute(sa.text("DELETE FROM iam_accounts"))
        await conn.execute(sa.text("DELETE FROM users"))

        # Verify Alembic migration added column usage and unique index
        col_res = await conn.execute(
            sa.text(
                """
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'workspace_llm_tier_mappings' AND column_name = 'usage';
                """
            )
        )
        col_row = col_res.fetchone()
        assert col_row is not None
        assert col_row[0] == "usage"

        idx_res = await conn.execute(
            sa.text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'workspace_llm_tier_mappings'
                  AND indexname = 'idx_llm_tier_mappings_single_active_global_embedding';
                """
            )
        )
        assert idx_res.fetchone() is not None

    async with app_client_factory() as client:
        # 1. Connect a Chat model (default usage = 'chat')
        chat_payload = {
            "scope_level": "GLOBAL",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "display_name": "Mistral Large Production",
            "inference_tier": "complex",
            "effort": "deep",
            "provider_slug": "mistral",
            "model_family": "Mistral",
            "model_name": "mistral-large-latest",
            "endpoint_uri": "https://api.mistral.ai",
            "protocol_mode": "openai_compatible",
            "usage": "chat",
        }
        res_chat = await client.post(
            "/api/v1/settings/ai-models/mappings", json=chat_payload, headers=headers_admin
        )
        assert res_chat.status_code == 201
        assert res_chat.json()["id"]
        assert res_chat.json()["usage"] == "chat"

        # 2. Connect first Global Embedding Model
        embed1_payload = {
            "scope_level": "GLOBAL",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "display_name": "OpenAI text-embedding-3-large",
            "inference_tier": "auto",
            "effort": "default",
            "provider_slug": "openai",
            "model_family": "OpenAI",
            "model_name": "text-embedding-3-large",
            "endpoint_uri": "https://api.openai.com/v1",
            "protocol_mode": "openai_compatible",
            "usage": "embedding",
        }
        res_embed1 = await client.post(
            "/api/v1/settings/ai-models/mappings", json=embed1_payload, headers=headers_admin
        )
        assert res_embed1.status_code == 201
        embed1_id = res_embed1.json()["id"]
        assert res_embed1.json()["usage"] == "embedding"
        assert res_embed1.json()["is_active"] is True

        # Verify in PostgreSQL 18 via direct SELECT
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT usage, is_active FROM workspace_llm_tier_mappings WHERE id = :id"
                    ),
                    {"id": embed1_id},
                )
            ).fetchone()
            assert row is not None
            assert row[0] == "embedding"
            assert row[1] is True

        # 3. Connect second Global Embedding Model -> embed1 must be switched to is_active = FALSE
        embed2_payload = {
            "scope_level": "GLOBAL",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "display_name": "Gemini text-embedding-004",
            "inference_tier": "auto",
            "effort": "default",
            "provider_slug": "google",
            "model_family": "Google",
            "model_name": "text-embedding-004",
            "endpoint_uri": "https://generativelanguage.googleapis.com",
            "protocol_mode": "gemini_native",
            "usage": "embedding",
        }
        res_embed2 = await client.post(
            "/api/v1/settings/ai-models/mappings", json=embed2_payload, headers=headers_admin
        )
        assert res_embed2.status_code == 201
        embed2_id = res_embed2.json()["id"]
        assert res_embed2.json()["is_active"] is True

        # Verify in PostgreSQL 18: embed1 is now inactive, embed2 is active
        async with engine.begin() as conn:
            active_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT id, usage, is_active
                        FROM workspace_llm_tier_mappings
                        WHERE usage = 'embedding' AND scope_level = 'GLOBAL' AND is_active = TRUE
                        """
                    )
                )
            ).fetchall()
            assert len(active_rows) == 1
            assert str(active_rows[0][0]) == embed2_id

            # Verify embed1 is active = False
            row1 = (
                await conn.execute(
                    sa.text("SELECT is_active FROM workspace_llm_tier_mappings WHERE id = :id"),
                    {"id": embed1_id},
                )
            ).fetchone()
            assert row1 is not None and row1[0] is False

        # 4. Strict Database constraint: attempting direct SQL insertion of a second active row
        # must be rejected by PostgreSQL 18 partial unique index!
        async with engine.begin() as conn:
            with pytest.raises(Exception) as exc_info:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspace_llm_tier_mappings (
                            id, scope_level, scope_id, inference_tier, effort,
                            fallback_order, provider_slug, model_family, model_name,
                            endpoint_uri, is_active, usage
                        ) VALUES (
                            :id, 'GLOBAL', :scope_id, 'auto', 'default', 99, 'test',
                            'Test', 'test-model', 'https://api.openai.com', TRUE, 'embedding'
                        )
                        """
                    ),
                    {"id": new_uuid7_str(), "scope_id": "0195f000-0000-7000-8000-000000000301"},
                )
            # Either asyncpg UniqueViolationError or SQLAlchemy IntegrityError
            assert "idx_llm_tier_mappings_single_active_global_embedding" in str(exc_info.value)

        # 5. Anthropic rejection for usage='embedding'
        anthropic_payload = {
            "scope_level": "GLOBAL",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "display_name": "Claude Embedding",
            "inference_tier": "auto",
            "effort": "default",
            "provider_slug": "anthropic",
            "model_family": "Anthropic",
            "model_name": "claude-3-5-sonnet",
            "endpoint_uri": "https://api.anthropic.com/v1",
            "protocol_mode": "anthropic_messages",
            "usage": "embedding",
        }
        res_anthropic = await client.post(
            "/api/v1/settings/ai-models/mappings", json=anthropic_payload, headers=headers_admin
        )
        assert res_anthropic.status_code == 422
        assert res_anthropic.json()["error_code"] == "ERR_EMBEDDING_PROVIDER_UNSUPPORTED"
