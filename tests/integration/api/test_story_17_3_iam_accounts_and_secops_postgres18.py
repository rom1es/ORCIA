"""Story 17.3 — Vertical HTTP -> PostgreSQL 18 Integration Tests for IAM Accounts & SecOps Grants.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261111_1703` (`upgrade head` -> `downgrade 20261111_1702` -> `upgrade head`).
2. Day-0 initial admin auto-synchronization (`users` -> `iam_accounts`) with
   `roles = ["PLATFORM_ADMIN", "SECOPS"]`, verified via direct SQL `SELECT`.
3. Closed 6-role matrix (`GET /api/v1/settings/iam/role-matrix`, `BU_LEAD`,
   `WRITE_ONLY_NEVER_READABLE`), `422 ERR_IAM_INVALID_ROLE`, `409 ERR_IAM_DUPLICATE_PRINCIPAL`,
   and `org_units.member_user_ids_jsonb` sync on `HUMAN` & `SERVICE_PRINCIPAL` accounts.
4. Separation of `SECOPS` to a dedicated RSSI account + deterministic anti-lockout
   (`422 ERR_ADMIN_LOCKOUT_PREVENTED` on demote, disable, or delete of last `ACTIVE` admin).
5. `READ_ONLY_OBSERVER` guard (`403 ERR_OBSERVER_MODE_READ_ONLY`) and granular SecOps grants
   (`resource_kind`, `effect="INHERITANCE_BLOCK"`) persisted in `role_permission_grants`.
"""

from __future__ import annotations

import json
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
DB_NAME = "orcia_story_17_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_17_3_pw"  # pragma: allowlist secret


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
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261111_1703
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261111_1702"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-17-3-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-17-3-vault-key-0001")
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
async def test_iam_accounts_day0_sync_anti_lockout_and_secops_grants_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("DELETE FROM role_permission_grants"))
            await conn.execute(sa.text("DELETE FROM iam_accounts"))
            await conn.execute(sa.text("DELETE FROM workspaces"))
            await conn.execute(sa.text("DELETE FROM org_units WHERE unit_type <> 'ENTERPRISE'"))
            await conn.execute(sa.text("DELETE FROM users"))
            # Seed a Day-0 initial admin in `users` to verify automatic directory sync
            root_ou = (
                await conn.execute(
                    sa.text("SELECT id FROM org_units WHERE unit_type = 'ENTERPRISE' LIMIT 1")
                )
            ).scalar()
            if root_ou is None:
                root_ou = UUID(new_uuid7_str())
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                        VALUES (:id, 'orcia-root', 'ORCIA Enterprise', 'ENTERPRISE', NULL)
                        """
                    ),
                    {"id": root_ou},
                )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO users (
                        id, email, display_name, auth_mode, human_profile_archetype,
                        platform_role, primary_org_unit_id, is_active
                    )
                    VALUES (
                        :id, 'romain.admin@orcia.fr', 'Romain Admin Jour 0', 'LOCAL',
                        'SECOPS', 'PLATFORM_ADMIN', :ou_id, TRUE
                    )
                    """
                ),
                {"id": UUID(new_uuid7_str()), "ou_id": root_ou},
            )

        async with app_client_factory() as client:
            # 1. Native 6-role matrix check
            r_matrix = await client.get("/api/v1/settings/iam/role-matrix", headers=headers)
            assert r_matrix.status_code == 200, r_matrix.text
            matrix_body = r_matrix.json()
            assert matrix_body["secret_visibility_policy"] == "WRITE_ONLY_NEVER_READABLE"
            assert [r["role"] for r in matrix_body["roles"]] == [
                "PLATFORM_ADMIN",
                "SECOPS",
                "BU_LEAD",
                "TEAM_LEAD",
                "CONTRIBUTOR",
                "OBSERVER",
            ]

            # 2. Day-0 admin auto-sync on GET /api/v1/settings/iam/accounts
            r_list = await client.get("/api/v1/settings/iam/accounts", headers=headers)
            assert r_list.status_code == 200, r_list.text
            accounts = r_list.json()["accounts"]
            assert len(accounts) == 1
            day0_acc = accounts[0]
            assert day0_acc["principal_id"] == "romain.admin@orcia.fr"
            assert day0_acc["roles"] == ["PLATFORM_ADMIN", "SECOPS"]

            async with engine.connect() as conn:
                db_day0 = (
                    await conn.execute(
                        sa.text(
                            "SELECT principal_id, roles_jsonb, status "
                            "FROM iam_accounts WHERE id = :id"
                        ),
                        {"id": UUID(day0_acc["id"])},
                    )
                ).one()
            assert db_day0[0] == "romain.admin@orcia.fr"
            db_roles = json.loads(db_day0[1]) if isinstance(db_day0[1], str) else db_day0[1]
            assert db_roles == ["PLATFORM_ADMIN", "SECOPS"]
            assert db_day0[2] == "ACTIVE"

            # 3. Create a TEAM org unit, then create RSSI human + SERVICE_PRINCIPAL accounts
            r_team = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={"name": "Équipe SecOps Cyber", "kind": "TEAM"},
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]

            r_bad_role = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=headers,
                json={
                    "principal_id": "invalid@orcia.fr",
                    "display_name": "Invalid Role",
                    "roles": ["GHOST_ROLE"],
                },
            )
            assert r_bad_role.status_code == 422
            assert r_bad_role.json()["error_code"] == "ERR_IAM_INVALID_ROLE"

            r_rssi = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=headers,
                json={
                    "principal_id": "claire.rssi@orcia.fr",
                    "display_name": "Claire RSSI",
                    "email": "claire.rssi@orcia.fr",
                    "account_kind": "HUMAN",
                    "auth_source": "OIDC_FEDERATED",
                    "roles": ["SECOPS"],
                    "team_ids": [team_id],
                    "status": "ACTIVE",
                },
            )
            assert r_rssi.status_code == 200, r_rssi.text

            r_dup = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=headers,
                json={
                    "principal_id": "claire.rssi@orcia.fr",
                    "display_name": "Duplicate RSSI",
                    "roles": ["OBSERVER"],
                },
            )
            assert r_dup.status_code == 409
            assert r_dup.json()["error_code"] == "ERR_IAM_DUPLICATE_PRINCIPAL"

            r_sp = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=headers,
                json={
                    "principal_id": "sp-worker-sync",
                    "display_name": "Connecteur Sync Worker",
                    "account_kind": "SERVICE_PRINCIPAL",
                    "auth_source": "SERVICE_TOKEN",
                    "roles": ["CONTRIBUTOR"],
                    "status": "ACTIVE",
                },
            )
            assert r_sp.status_code == 200, r_sp.text
            assert r_sp.json()["account_kind"] == "SERVICE_PRINCIPAL"

            # Verify team membership sync directly in PostgreSQL 18 `org_units`
            async with engine.connect() as conn:
                raw_members = (
                    await conn.execute(
                        sa.text("SELECT member_user_ids_jsonb FROM org_units WHERE id = :id"),
                        {"id": UUID(team_id)},
                    )
                ).scalar_one()
            members_list = json.loads(raw_members) if isinstance(raw_members, str) else raw_members
            assert "claire.rssi@orcia.fr" in members_list

            # 4. Separate SECOPS from Day-0 admin -> ok; demote/disable/delete sole admin -> 422
            r_sep = await client.patch(
                f"/api/v1/settings/iam/accounts/{day0_acc['id']}",
                headers=headers,
                json={"roles": ["PLATFORM_ADMIN"]},
            )
            assert r_sep.status_code == 200, r_sep.text
            assert r_sep.json()["roles"] == ["PLATFORM_ADMIN"]

            for bad_patch in ({"roles": ["SECOPS"]}, {"status": "DISABLED"}):
                r_lock = await client.patch(
                    f"/api/v1/settings/iam/accounts/{day0_acc['id']}",
                    headers=headers,
                    json=bad_patch,
                )
                assert r_lock.status_code == 422
                assert r_lock.json()["error_code"] == "ERR_ADMIN_LOCKOUT_PREVENTED"

            r_del_lock = await client.delete(
                f"/api/v1/settings/iam/accounts/{day0_acc['id']}", headers=headers
            )
            assert r_del_lock.status_code == 422
            assert r_del_lock.json()["error_code"] == "ERR_ADMIN_LOCKOUT_PREVENTED"

            # Promote a second ACTIVE PLATFORM_ADMIN, then delete the first one
            r_backup = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=headers,
                json={
                    "principal_id": "backup.admin@orcia.fr",
                    "display_name": "Backup Admin",
                    "email": "backup.admin@orcia.fr",
                    "roles": ["PLATFORM_ADMIN"],
                    "status": "ACTIVE",
                },
            )
            assert r_backup.status_code == 200
            r_del_ok = await client.delete(
                f"/api/v1/settings/iam/accounts/{day0_acc['id']}", headers=headers
            )
            assert r_del_ok.status_code == 200

            # 5. Observer guard (403) + Granular SecOps grant persisted in PostgreSQL 18
            r_obs = await client.post(
                "/api/v1/settings/iam/grants",
                headers={**headers, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                json={
                    "actor_persona": "karim",
                    "subject_type": "ROLE",
                    "subject_id": "TEAM_LEAD",
                    "scope_path": "bu-cyber/ws-c3",
                    "verbs": ["read"],
                },
            )
            assert r_obs.status_code == 403
            assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            r_grant = await client.post(
                "/api/v1/settings/iam/grants",
                headers=headers,
                json={
                    "actor_persona": "karim",
                    "subject_type": "ROLE",
                    "subject_id": "BU_LEAD",
                    "scope_path": "bu-cyber/ws-c3",
                    "verbs": ["read"],
                    "effect": "INHERITANCE_BLOCK",
                    "resource_kind": "DATASOURCE",
                },
            )
            assert r_grant.status_code == 200, r_grant.text
            grant_id = r_grant.json()[0]["id"]

            async with engine.connect() as conn:
                db_grant = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT resource_kind, effect, inheritance_block
                            FROM role_permission_grants
                            WHERE id = :id
                            """
                        ),
                        {"id": UUID(grant_id)},
                    )
                ).one()
            assert db_grant[0] == "DATASOURCE"
            assert db_grant[1] == "INHERITANCE_BLOCK"
            assert db_grant[2] is True

            r_grants_get = await client.get("/api/v1/settings/iam/grants", headers=headers)
            assert r_grants_get.status_code == 200
            assert any(g["id"] == grant_id for g in r_grants_get.json())

            r_grant_del = await client.delete(
                f"/api/v1/settings/iam/grants/{grant_id}", headers=headers
            )
            assert r_grant_del.status_code == 200
            async with engine.connect() as conn:
                rem_cnt = (
                    await conn.execute(
                        sa.text("SELECT COUNT(*) FROM role_permission_grants WHERE id = :id"),
                        {"id": UUID(grant_id)},
                    )
                ).scalar_one()
            assert rem_cnt == 0

            # 6. Team unassignment + 404 / validation edge cases on PostgreSQL 18
            rssi_id = r_rssi.json()["id"]
            r_unassign = await client.patch(
                f"/api/v1/settings/iam/accounts/{rssi_id}",
                headers=headers,
                json={"display_name": "Claire RSSI Lead", "team_ids": []},
            )
            assert r_unassign.status_code == 200
            assert r_unassign.json()["display_name"] == "Claire RSSI Lead"
            assert r_unassign.json()["team_ids"] == []

            for bad_url in (
                "/api/v1/settings/iam/accounts/not-a-uuid",
                f"/api/v1/settings/iam/accounts/{new_uuid7_str()}",
            ):
                assert (
                    await client.patch(bad_url, headers=headers, json={"display_name": "X"})
                ).status_code == 404
                assert (await client.delete(bad_url, headers=headers)).status_code == 404
            assert (
                await client.delete("/api/v1/settings/iam/grants/not-a-uuid", headers=headers)
            ).status_code == 404
            assert (
                await client.delete(
                    f"/api/v1/settings/iam/grants/{new_uuid7_str()}", headers=headers
                )
            ).status_code == 404

            # 7. Schema auto-recreation + Day-0 placeholder & platform_settings fallback
            async with engine.begin() as conn:
                await conn.execute(sa.text("DROP TABLE iam_accounts"))
                await conn.execute(sa.text("DROP TABLE role_permission_grants"))
                await conn.execute(sa.text("DELETE FROM users"))
                await conn.execute(sa.text("DELETE FROM platform_settings"))
            r_placeholder = await client.get("/api/v1/settings/iam/accounts", headers=headers)
            assert r_placeholder.status_code == 200
            assert r_placeholder.json()["accounts"][0]["principal_id"] == "admin@orcia.local"
            assert (await client.get("/api/v1/settings/iam/grants", headers=headers)).json() == []
    finally:
        await engine.dispose()
