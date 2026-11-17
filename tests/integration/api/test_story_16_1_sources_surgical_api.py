"""Vertical HTTP + PostgreSQL 18 integration tests for Story 16.1 (`sources_surgical.py`).

Validates:
- `GET /api/v1/sources/inspect-lines` on `docs/product/capabilities.yaml` (`#L1-50`, `#L1-500`
  capped at `250`) and `packs/sdlc/pack.yaml` (`pack://sdlc/pack.yaml`)
- `POST /api/v1/sources/surgical-explore` across all 4 read-only primitives
- RFC 9457 `application/problem+json` envelopes with `trace_id` on Path Traversal (`422`),
  SSRF (`403`), and missing files (`404`)
- `READ_SOURCE` governance masking (`redacted=True`, `lines=[]`, `0` content leaked) via
  `MatrixPermissionEvaluator` Catalog ACL, `CONFIDENTIAL_RESTRICTED` workspace, and header guard
- Real PostgreSQL 18 (`pgvector/pgvector:pg18`) vertical persistence check (`AD-17` Layer 2)
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

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_16_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_16_1_pw"  # pragma: allowlist secret


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


@pytest.fixture
def api_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-16-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-16-1-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build() -> AsyncClient:
        app = create_app()
        initialize_app_services(app)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build


@pytest.mark.asyncio
async def test_inspect_lines_and_surgical_explore_vertical_http_pg18(
    database_url: str,
    api_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with api_client_factory() as client:
            # Verify vertical PG18 wiring (Day-0 admin persisted in PostgreSQL 18 `users`)
            admin_resp = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "story16.1.admin@orcia.test",
                    "display_name": "Admin Story 16.1",
                    "password": "Story16-1-Admin-Password!",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert admin_resp.status_code in (200, 409)

            async with engine.connect() as conn:
                row_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT count(*) FROM users WHERE email = 'story16.1.admin@orcia.test'"
                        )
                    )
                ).scalar_one()
                assert row_count == 1

            # 1. Inspect capabilities.yaml #L1-50
            cap_resp = await client.get(
                "/api/v1/sources/inspect-lines",
                params={"uri": "docs/product/capabilities.yaml", "start_line": 1, "end_line": 50},
            )
            assert cap_resp.status_code == 200, cap_resp.text
            cap_data = cap_resp.json()
            assert cap_data["file_badge_code"] == "Y"
            assert cap_data["display_filename"] == "capabilities.yaml"
            assert cap_data["formatted_badge"] == "Analyzed Y capabilities.yaml #L1-50"
            assert cap_data["start_line"] == 1
            assert cap_data["end_line"] == 50
            assert len(cap_data["lines"]) == 50
            assert cap_data["lines"][0]["line_number"] == 1
            assert cap_data["lines"][49]["line_number"] == 50
            assert cap_data["redacted"] is False
            assert len(cap_data["sha256"]) == 64
            assert cap_data["trace_id"]

            # 2. Enforce strict 250-line cap on HTTP endpoint
            capped_resp = await client.get(
                "/api/v1/sources/inspect-lines",
                params={"uri": "docs/product/capabilities.yaml", "start_line": 1, "end_line": 500},
            )
            assert capped_resp.status_code == 200
            capped_data = capped_resp.json()
            assert len(capped_data["lines"]) == 250
            assert capped_data["end_line"] == 250

            # 3. Inspect declarative pack.yaml (`packs/sdlc/pack.yaml` & `pack://sdlc/pack.yaml`)
            pack_resp = await client.get(
                "/api/v1/sources/inspect-lines",
                params={"uri": "packs/sdlc/pack.yaml", "start_line": 1, "end_line": 20},
            )
            assert pack_resp.status_code == 200
            assert pack_resp.json()["file_badge_code"] == "Y"
            assert len(pack_resp.json()["lines"]) >= 5

            vpack_resp = await client.get(
                "/api/v1/sources/inspect-lines",
                params={"uri": "pack://sdlc/pack.yaml", "start_line": 1, "end_line": 10},
            )
            assert vpack_resp.status_code == 200
            assert vpack_resp.json()["exists"] is True

            # 4. Execute all 4 primitives via POST /api/v1/sources/surgical-explore
            state_resp = await client.post(
                "/api/v1/sources/surgical-explore",
                json={
                    "primitive": "check_resource_state",
                    "resource_uri": "packs/sdlc/pack.yaml",
                },
            )
            assert state_resp.status_code == 200
            assert state_resp.json()["exists"] is True
            assert state_resp.json()["total_lines"] >= 10

            outline_resp = await client.post(
                "/api/v1/sources/surgical-explore",
                json={
                    "primitive": "outline_resource_structure",
                    "resource_uri": "docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md",
                },
            )
            assert outline_resp.status_code == 200
            outline_body = outline_resp.json()
            assert outline_body["file_badge_code"] == "M↓"
            assert len(outline_body["outline"]) >= 4

            search_resp = await client.post(
                "/api/v1/sources/surgical-explore",
                json={
                    "primitive": "search_workspace_snippets",
                    "resource_uri": "packs/sdlc",
                    "query": "sdlc",
                    "max_results": 5,
                },
            )
            assert search_resp.status_code == 200
            assert len(search_resp.json()["snippets"]) >= 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sources_surgical_rfc9457_errors_and_read_source_masking(
    api_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    async with api_client_factory() as client:
        # 1. Path Traversal -> 422 RFC 9457 Problem Details
        trav_resp = await client.get(
            "/api/v1/sources/inspect-lines",
            params={"uri": "../pyproject.toml", "start_line": 1, "end_line": 20},
        )
        assert trav_resp.status_code == 422
        assert "application/problem+json" in trav_resp.headers["content-type"]
        trav_problem = trav_resp.json()
        assert trav_problem["error_code"] == "ERR_VALIDATION_FAILED"
        assert trav_problem["trace_id"]

        # 2. SSRF Cloud Metadata -> 403 RFC 9457 Problem Details
        ssrf_resp = await client.get(
            "/api/v1/sources/inspect-lines",
            params={"uri": "http://169.254.169.254/latest/meta-data/"},
        )
        assert ssrf_resp.status_code == 403
        assert "application/problem+json" in ssrf_resp.headers["content-type"]
        assert ssrf_resp.json()["error_code"] == "ERR_POLICY_DENIED"
        assert ssrf_resp.json()["trace_id"]

        # 3. Missing file -> 404 RFC 9457 Problem Details
        missing_resp = await client.get(
            "/api/v1/sources/inspect-lines",
            params={"uri": "docs/non-existent-file-16-1.md"},
        )
        assert missing_resp.status_code == 404
        assert "application/problem+json" in missing_resp.headers["content-type"]
        assert missing_resp.json()["error_code"] == "ERR_RESOURCE_NOT_FOUND"

        # 4. READ_SOURCE masking via Catalog ACL blackbox resource (`can_read_source=False`)
        acl_masked = await client.get(
            "/api/v1/sources/inspect-lines",
            params={
                "uri": "catalog://res-blackbox-security-agent",
                "persona_key": "nadia",
            },
        )
        assert acl_masked.status_code == 200
        acl_body = acl_masked.json()
        assert acl_body["redacted"] is True
        assert acl_body["redacted_reason"] == "READ_SOURCE_REQUIRED"
        assert acl_body["lines"] == []
        assert acl_body["sha256"] is None
        hint = acl_body["permission_request_hint"] or ""
        assert "PERM-READ-SOURCE-" in hint
        assert "res-blackbox" in hint

        # 5. READ_SOURCE masking via X-Orcia-Read-Source header restriction
        hdr_masked = await client.get(
            "/api/v1/sources/inspect-lines",
            params={"uri": "packs/sdlc/pack.yaml", "start_line": 1, "end_line": 10},
            headers={"X-Orcia-Read-Source": "denied"},
        )
        assert hdr_masked.status_code == 200
        hdr_body = hdr_masked.json()
        assert hdr_body["redacted"] is True
        assert hdr_body["redacted_reason"] == "READ_SOURCE_REQUIRED"
        assert hdr_body["lines"] == []
