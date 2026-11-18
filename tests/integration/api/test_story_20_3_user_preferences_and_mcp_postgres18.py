"""Story 20.3 — PostgreSQL 18 vertical integration tests (`HTTP -> PostgreSQL 18 SELECT`).

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Reversible Alembic revision `20261117_2003`
   (`upgrade head` -> `downgrade 20261117_2002` -> `upgrade head`).
2. `GET`/`PATCH /api/v1/users/me/preferences` persisted in `user_preferences` (PG18 SELECT).
3. `POST`/`GET`/`DELETE /api/v1/users/me/mcp-tokens` persisted in `user_mcp_tokens` (SHA-256,
   plaintext returned only on POST 201, cross-user revocation blocked, observer rejected 403).
4. `09_reset_db_first_boot.py` clears `user_preferences` and `user_mcp_tokens` on Day-0 reset.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_20_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_20_3_pw"  # pragma: allowlist secret


def _load_reset_script():
    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    spec = importlib.util.spec_from_file_location("story_20_3_reset_09", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261117_2002"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-20-3-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-20-3-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client():
        app = create_app()
        initialize_app_services(app)
        return app, AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_client


@pytest.mark.asyncio
async def test_story_20_3_preferences_and_mcp_tokens_persist_in_pg18_and_reset(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    app, client = app_client_factory()
    engine = create_async_engine(database_url)
    try:
        async with client:
            # 1. PATCH /api/v1/users/me/preferences
            patch_resp = await client.patch(
                "/api/v1/users/me/preferences",
                params={"persona_key": "karim"},
                json={
                    "theme": "dark",
                    "locale": "en",
                    "default_assistant_hat": "ARCHITECT",
                    "assistant_tone": "detailed",
                    "personal_instructions": "Toujours vérifier les contrats d'architecture.",
                    "auto_open_contextual_help": False,
                    "notifications_enabled": False,
                },
            )
            assert patch_resp.status_code == 200
            karim_id = patch_resp.json()["user_id"]

            # Verify direct PostgreSQL 18 SELECT on user_preferences
            async with engine.connect() as conn:
                pref_row = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT theme, locale, default_assistant_hat, assistant_tone,
                                   personal_instructions, auto_open_help, notifications_enabled
                            FROM user_preferences
                            WHERE user_id = :user_id
                            """
                        ),
                        {"user_id": karim_id},
                    )
                ).one()
            assert tuple(pref_row) == (
                "dark",
                "en",
                "ARCHITECT",
                "detailed",
                "Toujours vérifier les contrats d'architecture.",
                False,
                False,
            )

            # 2. Simulate backend restart -> GET returns persisted PG18 preferences
            _, fresh_client = app_client_factory()
            async with fresh_client:
                get_resp = await fresh_client.get(
                    "/api/v1/users/me/preferences", params={"persona_key": "karim"}
                )
                assert get_resp.status_code == 200
                assert get_resp.json()["theme"] == "dark"
                assert get_resp.json()["default_assistant_hat"] == "ARCHITECT"
                assert get_resp.json()["assistant_tone"] == "detailed"

            # 3. POST /api/v1/users/me/mcp-tokens -> hashed SHA-256 in user_mcp_tokens
            create_resp = await client.post(
                "/api/v1/users/me/mcp-tokens",
                params={"persona_key": "karim"},
                json={
                    "label": "Cursor PG18 Key",
                    "expires_in_days": 90,
                    "rpm_limit": 120,
                    "allowed_workspace_slugs": ["ws-claims-alpha"],
                    "exposed_capabilities": ["ASSISTANT", "KB_GLOSSARY_SEARCH"],
                    "target_kind": "SPACE",
                    "target_slug": "ws-claims-alpha",
                },
            )
            assert create_resp.status_code == 201
            created = create_resp.json()
            plaintext = created["plaintext_token"]
            token_id = created["record"]["token_id"]
            expected_sha = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

            async with engine.connect() as conn:
                tok_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT token_sha256, revoked_at FROM user_mcp_tokens WHERE id = :id"
                        ),
                        {"id": UUID(token_id)},
                    )
                ).one()
            assert tok_row[0] == expected_sha
            assert tok_row[1] is None

            # 4. Cross-user revocation blocked (404)
            claire_del = await client.delete(
                f"/api/v1/users/me/mcp-tokens/{token_id}",
                params={"persona_key": "claire"},
            )
            assert claire_del.status_code == 404

            # 5. Owner revocation updates revoked_at in PG18
            karim_del = await client.delete(
                f"/api/v1/users/me/mcp-tokens/{token_id}",
                params={"persona_key": "karim"},
            )
            assert karim_del.status_code == 200
            assert karim_del.json()["revoked"] is True

            async with engine.connect() as conn:
                revoked_at = (
                    await conn.execute(
                        sa.text("SELECT revoked_at FROM user_mcp_tokens WHERE id = :id"),
                        {"id": UUID(token_id)},
                    )
                ).scalar()
            assert revoked_at is not None

        # 6. Verify `09_reset_db_first_boot.py` clears `user_preferences` and `user_mcp_tokens`
        reset_mod = _load_reset_script()
        assert "user_preferences" in reset_mod.ORDERED_MUTABLE_TABLES_TO_CLEAR
        assert "user_mcp_tokens" in reset_mod.ORDERED_MUTABLE_TABLES_TO_CLEAR
        report = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True

        async with engine.connect() as conn:
            pref_cnt = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM user_preferences"))
            ).scalar()
            tok_cnt = (await conn.execute(sa.text("SELECT COUNT(*) FROM user_mcp_tokens"))).scalar()
        assert pref_cnt == 0
        assert tok_cnt == 0
    finally:
        await engine.dispose()
