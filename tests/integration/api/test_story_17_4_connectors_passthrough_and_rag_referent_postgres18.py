"""Story 17.4 — Vertical HTTP -> PostgreSQL 18 Integration Tests for Connectors & RAG.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261111_1704` (`upgrade head` -> `downgrade 20261111_1703` -> `upgrade head`).
2. Zero workspace pollution when managing enterprise connectors.
3. SSRF prevention (`422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL`) on cloud metadata IPs.
4. Read-only observer guard (`403 ERR_OBSERVER_MODE_READ_ONLY`).
5. AES-256-GCM cipher in PostgreSQL 18 with canary secret absence in JSON payloads.
6. User passthrough tokens (`PUT`, `GET`, `DELETE`) and FinOps profile.
7. RAG Referent dynamic health cycle (`ACTIVE` -> `PAUSED_REFERENT_RENEWAL_REQUIRED` -> `ACTIVE`).
"""

from __future__ import annotations

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

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_17_4"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_17_4_pw"  # pragma: allowlist secret


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
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261111_1704
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261111_1703"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-17-4-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-17-4-vault-key-0001")
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
async def test_connectors_passthrough_and_rag_referent_postgres18(
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
    ws_id = UUID(new_uuid7_str())

    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM workspace_datasources"))
        await conn.execute(sa.text("DELETE FROM user_connector_passthrough_tokens"))
        await conn.execute(sa.text("DELETE FROM enterprise_connectors"))
        await conn.execute(sa.text("DELETE FROM workspaces"))
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
                "  :id, 'karim.admin@orcia.io', 'Karim Admin', 'LOCAL', 'SECOPS', "
                "  'PLATFORM_ADMIN', :ou_id, TRUE"
                ")"
            ),
            {"id": user_admin_id, "ou_id": root_ou},
        )

        # Workspace
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id) "
                "VALUES (:id, 'test-rag-ws', 'Test RAG WS', :ou_id)"
            ),
            {"id": ws_id, "ou_id": root_ou},
        )

    async with app_client_factory() as client:
        # 1. SSRF Guard test (422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL on cloud metadata)
        ssrf_res = await client.post(
            "/api/v1/settings/connectors",
            headers=headers_admin,
            json={
                "name": "Cloud Metadata Exploit",
                "connector_kind": "JIRA",
                "base_url": "http://169.254.169.254/latest/meta-data",
                "auth_mode": "OAUTH2_PASSTHROUGH",
            },
        )
        assert ssrf_res.status_code == 422
        assert ssrf_res.json()["error_code"] == "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL"

        # 2. Observer Mode Guard test (403 ERR_OBSERVER_MODE_READ_ONLY)
        obs_res = await client.post(
            "/api/v1/settings/connectors",
            headers=headers_observer,
            json={
                "name": "Jira Corp Internal",
                "connector_kind": "JIRA",
                "base_url": "https://jira.corp.internal/rest/api",
                "auth_mode": "PERSONAL_ACCESS_TOKEN",
            },
        )
        assert obs_res.status_code == 403
        assert obs_res.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 3. Create Connector with canary secret & verify 0 workspace pollution
        async with engine.connect() as conn:
            ws_count_before = (
                await conn.execute(sa.text("SELECT count(*) FROM workspaces"))
            ).scalar()

        canary_secret = "CANARY_SECRET_SUPER_CONFIDENTIAL_12345"  # pragma: allowlist secret
        create_res = await client.post(
            "/api/v1/settings/connectors",
            headers=headers_admin,
            json={
                "name": "Jira Corp Internal",
                "connector_kind": "JIRA",
                "base_url": "https://jira.corp.internal/rest/api",
                "auth_mode": "PERSONAL_ACCESS_TOKEN",
                "admin_secret_value": canary_secret,
                "enabled": True,
            },
        )
        assert create_res.status_code == 201, create_res.text
        conn_data = create_res.json()
        connector_id = conn_data["id"]

        # Secret is NEVER leaked in JSON response
        assert canary_secret not in create_res.text
        assert conn_data["admin_secret_status"]["configured"] is True
        assert conn_data["admin_secret_status"]["fingerprint"].startswith("sha256:")

        # Verify zero workspace pollution
        async with engine.connect() as conn:
            ws_count_after = (
                await conn.execute(sa.text("SELECT count(*) FROM workspaces"))
            ).scalar()
            assert ws_count_after == ws_count_before

            # Verify PostgreSQL 18 AES-256-GCM ciphertext
            db_conn = (
                await conn.execute(
                    sa.text(
                        "SELECT encrypted_admin_secret, admin_secret_fingerprint "
                        "FROM enterprise_connectors WHERE id = :id"
                    ),
                    {"id": UUID(connector_id)},
                )
            ).one()
            assert ":" in db_conn[0]
            assert canary_secret not in db_conn[0]
            assert db_conn[1] == conn_data["admin_secret_status"]["fingerprint"]

        # 4. User account profile & Passthrough token lifecycle
        prof_res = await client.get("/api/v1/users/me/account-profile", headers=headers_admin)
        assert prof_res.status_code == 200, prof_res.text
        profile = prof_res.json()
        assert profile["email"] == "karim.admin@orcia.io"
        assert "roles" in profile
        assert "teams" in profile

        # Observer cannot store token
        obs_token_res = await client.put(
            f"/api/v1/users/me/passthrough-tokens/{connector_id}",
            headers=headers_observer,
            json={"secret_value": "OBSERVER_TOKEN"},  # pragma: allowlist secret
        )
        assert obs_token_res.status_code == 403

        # Upsert personal passthrough token
        canary_user_token = "CANARY_USER_TOKEN_PAT_9876543210"  # pragma: allowlist secret
        put_token_res = await client.put(
            f"/api/v1/users/me/passthrough-tokens/{connector_id}",
            headers=headers_admin,
            json={
                "secret_value": canary_user_token,
                "external_author_login": "karim_jira",
            },
        )
        assert put_token_res.status_code == 200, put_token_res.text
        token_data = put_token_res.json()
        assert canary_user_token not in put_token_res.text
        assert token_data["connected"] is True
        assert token_data["external_author_login"] == "karim_jira"
        assert token_data["secret_status"]["configured"] is True

        # Verify token in DB
        async with engine.connect() as conn:
            db_tok = (
                await conn.execute(
                    sa.text(
                        "SELECT encrypted_token, external_author_login, status "
                        "FROM user_connector_passthrough_tokens "
                        "WHERE connector_id = :cid AND user_id = :uid"
                    ),
                    {"cid": UUID(connector_id), "uid": "karim.admin@orcia.io"},
                )
            ).one()
            assert ":" in db_tok[0]
            assert canary_user_token not in db_tok[0]
            assert db_tok[1] == "karim_jira"
            assert db_tok[2] == "ACTIVE"

        # List tokens
        tokens_list_res = await client.get(
            "/api/v1/users/me/passthrough-tokens", headers=headers_admin
        )
        assert tokens_list_res.status_code == 200
        active_tokens = tokens_list_res.json()["items"]
        assert len(active_tokens) == 1
        assert active_tokens[0]["connected"] is True
        assert active_tokens[0]["external_author_login"] == "karim_jira"

        # 5. Workspace Datasources & Dynamic RAG Health Cycle
        # 5a. Service Account Mode -> ACTIVE
        ds_sa_res = await client.post(
            f"/api/v1/workspaces/{ws_id}/datasources",
            headers=headers_admin,
            json={
                "alias": "jira-crawler-sa",
                "scheme": "jira",
                "uri": "https://jira.corp.internal/crawler",
                "connector_id": connector_id,
                "sync_identity_mode": "SERVICE_ACCOUNT",
                "service_account_id": "sa-jira-crawler",
            },
        )
        assert ds_sa_res.status_code == 201, ds_sa_res.text
        ds_sa = ds_sa_res.json()
        assert ds_sa["sync_status"] == "ACTIVE"
        assert ds_sa["service_account_id"] == "sa-jira-crawler"

        # 5b. Referent User Mode with active token -> ACTIVE
        ds_ref_res = await client.post(
            f"/api/v1/workspaces/{ws_id}/datasources",
            headers=headers_admin,
            json={
                "alias": "jira-team-ref",
                "scheme": "jira",
                "uri": "https://jira.corp.internal/team-ref",
                "connector_id": connector_id,
                "sync_identity_mode": "TEAM_REFERENT_USER",
                "referent_user_id": "karim.admin@orcia.io",
            },
        )
        assert ds_ref_res.status_code == 201, ds_ref_res.text
        ds_ref = ds_ref_res.json()
        assert ds_ref["sync_status"] == "ACTIVE"
        assert ds_ref["referent_user_id"] == "karim.admin@orcia.io"

        # 5c. Revoke passthrough token -> Referent Datasource drops to PAUSED
        del_tok_res = await client.delete(
            f"/api/v1/users/me/passthrough-tokens/{connector_id}", headers=headers_admin
        )
        assert del_tok_res.status_code == 200
        assert del_tok_res.json()["revoked"] is True

        # Re-check datasources health dynamically
        list_ds_res = await client.get(
            f"/api/v1/workspaces/{ws_id}/datasources", headers=headers_admin
        )
        assert list_ds_res.status_code == 200
        ds_items = {d["id"]: d for d in list_ds_res.json()["items"]}

        # Service Account remains ACTIVE
        assert ds_items[ds_sa["id"]]["sync_status"] == "ACTIVE"

        # Referent datasource is now PAUSED
        paused_item = ds_items[ds_ref["id"]]
        assert paused_item["sync_status"] == "PAUSED_REFERENT_RENEWAL_REQUIRED"
        assert paused_item["sync_status_reason"] == "REFERENT_TOKEN_MISSING"

        # 5d. Renew Referent inline via PATCH (or reinstate token)
        # Re-upsert token
        await client.put(
            f"/api/v1/users/me/passthrough-tokens/{connector_id}",
            headers=headers_admin,
            json={"secret_value": "NEW_CANARY_TOKEN"},  # pragma: allowlist secret
        )

        # Datasource auto-recovers to ACTIVE
        list_ds_recheck = await client.get(
            f"/api/v1/workspaces/{ws_id}/datasources", headers=headers_admin
        )
        assert list_ds_recheck.status_code == 200
        recheck_items = {d["id"]: d for d in list_ds_recheck.json()["items"]}
        assert recheck_items[ds_ref["id"]]["sync_status"] == "ACTIVE"
