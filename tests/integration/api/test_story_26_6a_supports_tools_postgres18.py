"""Story 26.6a — Vertical PG18 + Redis Integration Tests for `supports_tools` & Alembic 266a."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_5_helpers import (
    pg_and_redis_urls,
    real_lifespan_client_factory,
)

__all__ = ["pg_and_redis_urls", "real_lifespan_client_factory"]

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.asyncio
async def test_story_26_6a_alembic_roundtrip_and_supports_tools_pg18_vertical(
    real_lifespan_client_factory: Any,
    pg_and_redis_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic 20261122_266a roundtrip, PG18 persistence, override, and 422 guard."""
    pg_url, _redis_url = pg_and_redis_urls
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "downgrade", "20261122_265"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "false")
    open_client, _ = real_lifespan_client_factory
    engine = create_async_engine(pg_url)
    try:
        async with open_client() as client:
            boot = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin266a@orcia.io",
                    "display_name": "Admin 26.6a",
                    "password": "Admin266a!StrongPassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code == 200, boot.text
            hdrs = {"Authorization": f"Bearer {boot.json()['access_token']}"}

            bu = await client.post(
                "/api/v1/org-units",
                headers=hdrs,
                json={"name": "BU 26.6a", "slug": "bu-266a", "kind": "BU"},
            )
            assert bu.status_code == 200, bu.text
            ws = await client.post(
                "/api/v1/workspaces",
                headers=hdrs,
                json={
                    "name": "WS 26.6a",
                    "slug": "ws-266a",
                    "owner_org_unit_id": bu.json()["id"],
                    "visibility_mode": "STANDARD",
                },
            )
            assert ws.status_code in (200, 201), ws.text
            ws_id = ws.json()["id"]

            # 1. Create Gemini Native mapping -> defaults to supports_tools=false in PG18
            r_gem = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Gemini Native 26.6a",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "google",
                    "model_family": "Gemini",
                    "model_name": "gemini-2.5-flash",
                    "endpoint_uri": "https://generativelanguage.googleapis.com/v1beta",
                    "auth_mode": "none_local",
                    "protocol_mode": "gemini_native",
                    "usage": "chat",
                },
            )
            assert r_gem.status_code in (200, 201), r_gem.text
            gem_data = r_gem.json()
            gem_id = gem_data["id"]
            assert gem_data["supports_tools"] is False
            assert gem_data["supports_tools_override"] is None

            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        sa.text(
                            "SELECT supports_tools, supports_tools_override "
                            "FROM workspace_llm_tier_mappings WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": gem_id},
                    )
                ).one()
                assert row[0] is False and row[1] is None

            # 2. Requesting Speed 2 on supports_tools=false fails pre-stream with 422
            r_s2 = await client.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "user_prompt": "Investigate with tools",
                    "requested_speed": "SPEED_2_AGENT_TOOLS",
                },
            )
            assert r_s2.status_code == 422, r_s2.text
            assert r_s2.json()["error_code"] == "ERR_MODEL_TOOLS_UNSUPPORTED"

            # Speed 1 still succeeds with 0 embeddings (AD-24.6 invariant)
            r_s1 = await client.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "user_prompt": "Quick question",
                    "requested_speed": "SPEED_1_FAST",
                },
            )
            assert r_s1.status_code == 202, r_s1.text

            # 3. PLATFORM_ADMIN manual override supports_tools_override=true -> persisted in PG18
            r_patch_true = await client.patch(
                f"/api/v1/settings/ai-models/mappings/{gem_id}",
                headers=hdrs,
                json={"supports_tools_override": True},
            )
            assert r_patch_true.status_code == 200, r_patch_true.text
            assert r_patch_true.json()["supports_tools"] is True
            assert r_patch_true.json()["supports_tools_override"] is True

            # Clear override back to NULL -> reverts to detected false
            r_patch_null = await client.patch(
                f"/api/v1/settings/ai-models/mappings/{gem_id}",
                headers=hdrs,
                json={"supports_tools_override": None},
            )
            assert r_patch_null.status_code == 200, r_patch_null.text
            assert r_patch_null.json()["supports_tools"] is False
            assert r_patch_null.json()["supports_tools_override"] is None

            async with engine.connect() as conn:
                row2 = (
                    await conn.execute(
                        sa.text(
                            "SELECT supports_tools, supports_tools_override "
                            "FROM workspace_llm_tier_mappings WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": gem_id},
                    )
                ).one()
                assert row2[0] is False and row2[1] is None
    finally:
        await engine.dispose()
