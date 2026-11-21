"""Story 25.5 Layer 2 Vertical HTTP -> PostgreSQL 18 Integration Tests (`AD-24`).

Uses the real Composition Root (`create_app()` + `app.router.lifespan_context(app)`)
with zero `dependency_overrides` and zero manual `app.state.*` injection against
ephemeral `pgvector/pgvector:pg18` + `redis:7.4.2-alpine` containers.

Verifies:
1. With `1` active `chat` model and `0` `embedding` model in PG18:
   - `POST /api/v1/assistant/three-speed/turn` returns `200`,
   - `POST /api/v1/assistant/chat/stream` returns `200`,
   - `GET /api/v1/search` returns `200` (`speed2_executed=False`, Speed-1 lexical),
   - `POST /api/v1/ontology-rag/rag/search` returns `422 ERR_NO_ACTIVE_EMBEDDING_MODEL`.
2. `POST /api/v1/workspaces/{ws}/datasources`:
   - `source_nature='DOCUMENT_KB'` returns `422 ERR_NO_ACTIVE_EMBEDDING_MODEL` and
     `SELECT COUNT(*) FROM workspace_datasources` stays `0`,
   - `source_nature='SOURCE_CODE'` returns `201` and persists in PG18 (`SELECT` confirmed).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer
try:
    from testcontainers.community.redis import RedisContainer
except ImportError:
    from testcontainers.redis import RedisContainer

from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_25_5"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_25_5_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg_and_redis_urls() -> Iterator[tuple[str, str]]:
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4.2-alpine") as redis_c,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{redis_c.get_exposed_port(6379)}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        res = subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Alembic upgrade head failed:\n{res.stdout}\n{res.stderr}")
        yield pg_url, redis_url


@pytest_asyncio.fixture
async def real_lifespan_client_factory(
    pg_and_redis_urls: tuple[str, str], monkeypatch: pytest.MonkeyPatch
):  # type: ignore[no-untyped-def]
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-25-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-25-5-vault-key-0001")

    def _open_client():  # type: ignore[no-untyped-def]
        @asynccontextmanager
        async def _ctx() -> AsyncIterator[AsyncClient]:
            app = create_app()
            assert app.dependency_overrides == {}
            async with (
                app.router.lifespan_context(app),
                AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
            ):
                yield client

        return _ctx()

    return _open_client, pg_url


@pytest.mark.asyncio
async def test_story_25_5_chat_only_assistant_and_rag_datasource_guard_postgres18(
    real_lifespan_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    open_client, pg_url = real_lifespan_client_factory
    engine = create_async_engine(pg_url)
    try:
        async with open_client() as client:
            # 1. Bootstrap Day-0 admin -> real JWT Bearer
            r_admin = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.255@orcia.ia",
                    "display_name": "Admin 25.5",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_admin.status_code == 200, r_admin.text
            admin_token = r_admin.json()["access_token"]
            auth = {"Authorization": f"Bearer {admin_token}"}

            # 2. Create OrgUnit + Workspace in PG18
            r_bu = await client.post(
                "/api/v1/org-units",
                headers=auth,
                json={"name": "BU 25.5", "slug": "bu-255", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=auth,
                json={
                    "name": "Espace 25.5",
                    "slug": "espace-255",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                    "owner_org_unit_id": bu_id,
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]

            # 3. Configure 1 active chat model and 0 embedding models in PG18
            r_chat_model = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=auth,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Chat GPT-4o Mini",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "gpt-4o-mini",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                },
            )
            assert r_chat_model.status_code in (200, 201), r_chat_model.text

            async with engine.connect() as conn:
                emb_cnt = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM workspace_llm_tier_mappings "
                            "WHERE usage = 'embedding' AND is_active = TRUE"
                        )
                    )
                ).scalar_one()
                assert emb_cnt == 0

            # 4. Assistant endpoints & GET /search return 200 with 0 embedding model
            r_turn = await client.post(
                "/api/v1/assistant/three-speed/turn",
                headers=auth,
                json={
                    "workspace_id": ws_id,
                    "user_prompt": "Explique les règles du workspace",
                    "requested_speed": "SPEED_1_FAST",
                },
            )
            assert r_turn.status_code == 200, r_turn.text
            assert r_turn.json()["response_text"]

            r_stream = await client.post(
                "/api/v1/assistant/chat/stream",
                headers=auth,
                json={
                    "workspace_id": ws_id,
                    "user_prompt": "Synthèse rapide",
                },
            )
            assert r_stream.status_code == 200, r_stream.text
            assert "text/event-stream" in r_stream.headers["content-type"]

            r_search = await client.get(
                "/api/v1/search",
                headers=auth,
                params={"q": "Espace 25.5", "workspace_id": ws_id},
            )
            assert r_search.status_code == 200, r_search.text
            assert r_search.json()["speed2_executed"] is False

            # Pure RAG search still rejects 422 ERR_NO_ACTIVE_EMBEDDING_MODEL
            r_pure_rag = await client.post(
                "/api/v1/ontology-rag/rag/search",
                headers=auth,
                json={"workspace_id": ws_id, "query_text": "test rag", "top_k": 3},
            )
            assert r_pure_rag.status_code == 422, r_pure_rag.text
            assert r_pure_rag.json()["error_code"] == "ERR_NO_ACTIVE_EMBEDDING_MODEL"

            # 5. Datasource guard: DOCUMENT_KB rejected 422 before INSERT (COUNT remains 0)
            r_ds_doc = await client.post(
                f"/api/v1/workspaces/{ws_id}/datasources",
                headers=auth,
                json={
                    "alias": "Confluence Interdite Sans Embedding",
                    "scheme": "confluence",
                    "uri": "https://confluence.corp.local/spaces/ARCH",
                    "source_nature": "DOCUMENT_KB",
                },
            )
            assert r_ds_doc.status_code == 422, r_ds_doc.text
            assert r_ds_doc.json()["error_code"] == "ERR_NO_ACTIVE_EMBEDDING_MODEL"
            assert r_ds_doc.headers["content-type"].startswith("application/problem+json")

            async with engine.connect() as conn:
                ds_count_after_doc = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM workspace_datasources WHERE workspace_id = :wid"
                        ),
                        {"wid": UUID(ws_id)},
                    )
                ).scalar_one()
                assert ds_count_after_doc == 0

            # 6. Datasource guard: SOURCE_CODE returns 201 and persists in PG18
            r_ds_code = await client.post(
                f"/api/v1/workspaces/{ws_id}/datasources",
                headers=auth,
                json={
                    "alias": "Repo Core Codegraph",
                    "scheme": "git",
                    "uri": "https://gitlab.corp.local/core/api.git",
                    "source_nature": "SOURCE_CODE",
                    "codegraph_enabled": True,
                },
            )
            assert r_ds_code.status_code == 201, r_ds_code.text
            created_code = r_ds_code.json()
            assert created_code["source_nature"] == "SOURCE_CODE"
            ds_code_id = created_code["id"]

            # 6b. PATCH /datasources switching SOURCE_CODE -> DOCUMENT_KB without embedding -> 422
            r_ds_patch = await client.patch(
                f"/api/v1/workspaces/{ws_id}/datasources/{ds_code_id}",
                headers=auth,
                json={"source_nature": "DOCUMENT_KB"},
            )
            assert r_ds_patch.status_code == 422, r_ds_patch.text
            assert r_ds_patch.json()["error_code"] == "ERR_NO_ACTIVE_EMBEDDING_MODEL"
            assert r_ds_patch.headers["content-type"].startswith("application/problem+json")

            async with engine.connect() as conn:
                ds_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT alias, source_nature FROM workspace_datasources "
                            "WHERE workspace_id = :wid"
                        ),
                        {"wid": UUID(ws_id)},
                    )
                ).fetchone()
                assert ds_row is not None
                assert ds_row[0] == "Repo Core Codegraph"
                assert ds_row[1] == "SOURCE_CODE"

        # 7. Cold reload on a fresh create_app() instance confirms PG18 persistence
        async with open_client() as cold_client:
            r_list = await cold_client.get(
                f"/api/v1/workspaces/{ws_id}/datasources",
                headers=auth,
            )
            assert r_list.status_code == 200, r_list.text
            items = r_list.json()["items"]
            assert len(items) == 1
            assert items[0]["alias"] == "Repo Core Codegraph"
            assert items[0]["source_nature"] == "SOURCE_CODE"
    finally:
        await engine.dispose()
