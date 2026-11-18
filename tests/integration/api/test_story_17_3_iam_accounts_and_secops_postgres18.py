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
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._story_17_3_fixtures import (
    app_client_factory,
    count_grants_by_id,
    database_url,
    reset_iam_test_db,
    seed_day0_admin_user,
)

from orcia_kernel.ids import new_uuid7_str

__all__ = ["app_client_factory", "database_url"]


@pytest.mark.asyncio
async def test_iam_accounts_day0_sync_anti_lockout_and_secops_grants_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    try:
        await reset_iam_test_db(engine)
        await seed_day0_admin_user(
            engine, email="romain.admin@orcia.fr", display_name="Romain Admin Jour 0"
        )

        async with app_client_factory() as client:
            # 1. Native 7-role matrix check
            r_matrix = await client.get("/api/v1/settings/iam/role-matrix", headers=headers)
            assert r_matrix.status_code == 200, r_matrix.text
            matrix_body = r_matrix.json()
            expected_policy = "WRITE_ONLY_NEVER_READABLE"  # pragma: allowlist secret
            assert matrix_body["secret_visibility_policy"] == expected_policy
            assert [r["role"] for r in matrix_body["roles"]] == [
                "PLATFORM_ADMIN",
                "SECOPS",
                "BU_LEAD",
                "TEAM_LEAD",
                "ONTOLOGY_LEAD",
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
                assert (
                    r_lock.status_code == 422
                    and r_lock.json()["error_code"] == "ERR_ADMIN_LOCKOUT_PREVENTED"
                )

            r_del_lock = await client.delete(
                f"/api/v1/settings/iam/accounts/{day0_acc['id']}", headers=headers
            )
            assert (
                r_del_lock.status_code == 422
                and r_del_lock.json()["error_code"] == "ERR_ADMIN_LOCKOUT_PREVENTED"
            )

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
                            "SELECT resource_kind, effect, inheritance_block "
                            "FROM role_permission_grants WHERE id = :id"
                        ),
                        {"id": UUID(grant_id)},
                    )
                ).one()
            assert (
                db_grant[0] == "DATASOURCE"
                and db_grant[1] == "INHERITANCE_BLOCK"
                and db_grant[2] is True
            )

            r_grants_get = await client.get("/api/v1/settings/iam/grants", headers=headers)
            assert r_grants_get.status_code == 200 and any(
                g["id"] == grant_id for g in r_grants_get.json()
            )

            r_grant_del = await client.delete(
                f"/api/v1/settings/iam/grants/{grant_id}", headers=headers
            )
            assert r_grant_del.status_code == 200
            assert await count_grants_by_id(engine, grant_id) == 0

            # 6. Team unassignment + 404 / validation edge cases on PostgreSQL 18
            rssi_id = r_rssi.json()["id"]
            r_unassign = await client.patch(
                f"/api/v1/settings/iam/accounts/{rssi_id}",
                headers=headers,
                json={"display_name": "Claire RSSI Lead", "team_ids": []},
            )
            assert (
                r_unassign.status_code == 200
                and r_unassign.json()["display_name"] == "Claire RSSI Lead"
                and r_unassign.json()["team_ids"] == []
            )

            for bad_url in (
                "/api/v1/settings/iam/accounts/not-a-uuid",
                f"/api/v1/settings/iam/accounts/{new_uuid7_str()}",
            ):
                assert (
                    await client.patch(bad_url, headers=headers, json={"display_name": "X"})
                ).status_code == 404
                assert (await client.delete(bad_url, headers=headers)).status_code == 404
            for bad_grant in (
                "/api/v1/settings/iam/grants/not-a-uuid",
                f"/api/v1/settings/iam/grants/{new_uuid7_str()}",
            ):
                assert (await client.delete(bad_grant, headers=headers)).status_code == 404

            # 7. Schema auto-recreation + Day-0 placeholder & platform_settings fallback
            async with engine.begin() as conn:
                for stmt in (
                    "DROP TABLE iam_accounts CASCADE",
                    "DROP TABLE role_permission_grants",
                    "DELETE FROM users",
                    "DELETE FROM platform_settings",
                ):
                    await conn.execute(sa.text(stmt))
            r_placeholder = await client.get("/api/v1/settings/iam/accounts", headers=headers)
            assert r_placeholder.status_code == 200
            assert r_placeholder.json()["accounts"][0]["principal_id"] == "admin@orcia.local"
            assert (await client.get("/api/v1/settings/iam/grants", headers=headers)).json() == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_iam_admin_secops_elevation_vertical_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    engine = create_async_engine(database_url)
    try:
        await reset_iam_test_db(engine)
        async with app_client_factory() as client:
            admin_email = "alex.admin@orcia.fr"
            admin_pw = "OrciaAdmin!2026"  # pragma: allowlist secret
            setup_res = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={"email": admin_email, "password": admin_pw, "display_name": "Alex Admin"},
            )
            assert setup_res.status_code == 200, setup_res.text

            login_res = await client.post(
                "/api/v1/auth/login/local",
                json={"email": admin_email, "password": admin_pw},
            )
            assert login_res.status_code == 200, login_res.text
            bearer = login_res.json()["access_token"]
            assert client.cookies.get("orcia_refresh_token") is not None

            # Retrieve IAM accounts and force initial roles strictly to ["PLATFORM_ADMIN"]
            acc_list = (
                await client.get(
                    "/api/v1/settings/iam/accounts",
                    headers={"Authorization": f"Bearer {bearer}"},
                )
            ).json()["accounts"]
            account_id = acc_list[0]["id"]
            p_init = await client.patch(
                f"/api/v1/settings/iam/accounts/{account_id}",
                headers={"Authorization": f"Bearer {bearer}"},
                json={"roles": ["PLATFORM_ADMIN"]},
            )
            assert p_init.status_code == 200 and p_init.json()["roles"] == ["PLATFORM_ADMIN"]

            # GET /api/v1/auth/session sees ["PLATFORM_ADMIN"]
            s1 = (await client.get("/api/v1/auth/session")).json()
            assert s1["authenticated"] is True and s1["session"]["roles"] == ["PLATFORM_ADMIN"]
            tok1 = s1["session"]["access_token"]

            # Elevate with "SECOPS" via PATCH /api/v1/settings/iam/accounts/{id}
            p_elev = await client.patch(
                f"/api/v1/settings/iam/accounts/{account_id}",
                headers={"Authorization": f"Bearer {tok1}"},
                json={"roles": ["PLATFORM_ADMIN", "SECOPS"]},
            )
            assert p_elev.status_code == 200 and "SECOPS" in p_elev.json()["roles"]

            # GET /api/v1/auth/session immediately sees "SECOPS" without server restart
            s2 = (await client.get("/api/v1/auth/session")).json()
            assert s2["authenticated"] is True and "SECOPS" in s2["session"]["roles"]
            elev_auth = {"Authorization": f"Bearer {s2['session']['access_token']}"}

            # Create SecOps grant exception via POST /api/v1/settings/iam/grants
            g_res = await client.post(
                "/api/v1/settings/iam/grants",
                headers=elev_auth,
                json={
                    "subject_type": "ROLE",
                    "subject_id": "TEAM_LEAD",
                    "scope_path": "bu-cyber/ws-vault",
                    "verbs": ["read", "execute"],
                    "effect": "ALLOW",
                    "resource_kind": "DATASOURCE",
                },
            )
            assert g_res.status_code == 200, g_res.text
            grant_id = g_res.json()[0]["id"]
            assert await count_grants_by_id(engine, grant_id) == 1

            del_res = await client.delete(
                f"/api/v1/settings/iam/grants/{grant_id}", headers=elev_auth
            )
            assert del_res.status_code == 200, del_res.text
            assert await count_grants_by_id(engine, grant_id) == 0
    finally:
        await engine.dispose()
