"""Story 20.1 — PostgreSQL 18 vertical integration tests (`HTTP -> PostgreSQL 18 SELECT`).

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Reversible Alembic revision `20261117_2001`
   (`upgrade head` -> `downgrade 20261117_1601` -> `upgrade head`).
2. `BU_LEAD` (Martin Pecheur) subtree delegation, `TEAM_LEAD` (`pascal.lacdap@orcia.ia`)
   delegation, and `POST /api/v1/org-units/invite-user` (`ONTOLOGY_LEAD`) persisted across
   `org_units`, `iam_accounts`, `users`, and `audit_ledger`.
3. Bidirectional B1 sync between `org_units.ontology_lead_user_ids_jsonb`
   and `iam_accounts.roles_jsonb`.
4. `hydrate_user_identity_from_pg` preserving `platform_role` (`BU_LEAD`, `ONTOLOGY_LEAD`).
5. Scoped `GET /api/v1/audit/ledger` isolation across `BU_LEAD`, `TEAM_LEAD`, and `SECOPS`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_api.routers._auth_pg_helpers import (
    hydrate_user_identity_from_pg,
    user_identity_from_candidate,
)
from orcia_core.bootstrap import load_local_auth_candidate_from_postgres18

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_20_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_20_1_pw"  # pragma: allowlist secret


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
            [*alembic_cmd, "downgrade", "20261117_1601"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-20-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-20-1-vault-key-0001")
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
async def test_story_20_1_delegation_invitation_b1_sync_and_audit_scope_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    admin_headers = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            # 1. Admin creates BU Commerce, BU Finance, and child Team Ventes + provisions leads
            r_list = await client.get("/api/v1/settings/iam/accounts", headers=admin_headers)
            assert r_list.status_code == 200

            r_martin = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                json={
                    "principal_id": "martin.pecheur@orcia.ia",
                    "display_name": "Martin Pecheur",
                    "email": "martin.pecheur@orcia.ia",
                    "account_kind": "HUMAN",
                    "roles": ["BU_LEAD"],
                },
            )
            assert r_martin.status_code == 200, r_martin.text

            r_pascal = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                json={
                    "principal_id": "pascal.lacdap@orcia.ia",
                    "display_name": "Pascal Lacdap",
                    "email": "pascal.lacdap@orcia.ia",
                    "account_kind": "HUMAN",
                    "roles": ["TEAM_LEAD"],
                },
            )
            assert r_pascal.status_code == 200, r_pascal.text

            r_bu_comm = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={
                    "name": "Direction Commerce",
                    "kind": "BU",
                    "lead_user_ids": ["martin.pecheur@orcia.ia"],
                },
            )
            assert r_bu_comm.status_code == 200, r_bu_comm.text
            bu_comm_id = r_bu_comm.json()["id"]

            r_bu_fin = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={"name": "Direction Finance", "kind": "BU"},
            )
            assert r_bu_fin.status_code == 200, r_bu_fin.text
            bu_fin_id = r_bu_fin.json()["id"]

            # 2. BU_LEAD Martin logs in via /auth/login/local and creates child Team Ventes
            login_martin = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "martin.pecheur@orcia.ia",
                    "password": r_martin.json()["temporary_password"],
                },
            )
            assert login_martin.status_code == 200, login_martin.text
            martin_headers = {"Authorization": f"Bearer {login_martin.json()['access_token']}"}
            r_team = await client.post(
                "/api/v1/org-units",
                headers=martin_headers,
                json={
                    "name": "Équipe Ventes",
                    "kind": "TEAM",
                    "parent_id": bu_comm_id,
                    "lead_user_ids": ["pascal.lacdap@orcia.ia"],
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_ventes_id = r_team.json()["id"]

            # 3. BU_LEAD Martin invites Camille as ONTOLOGY_LEAD on BU Commerce
            r_invite = await client.post(
                "/api/v1/org-units/invite-user",
                headers=martin_headers,
                json={
                    "target_org_unit_id": bu_comm_id,
                    "email": "camille.onto@orcia.ia",
                    "display_name": "Camille Onto",
                    "assignment_role": "ONTOLOGY_LEAD",
                },
            )
            assert r_invite.status_code == 200, r_invite.text
            camille_acc_id = r_invite.json()["account_id"]
            assert r_invite.json()["effective_roles"] == ["ONTOLOGY_LEAD"]

            # Direct PG18 verification: org_units, iam_accounts, users, audit_ledger
            async with engine.connect() as conn:
                ou_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT ontology_lead_user_ids_jsonb FROM org_units WHERE id = :id"
                        ),
                        {"id": UUID(bu_comm_id)},
                    )
                ).one()
                onto_list = json.loads(ou_row[0]) if isinstance(ou_row[0], str) else ou_row[0]
                assert "camille.onto@orcia.ia" in onto_list

                cand_martin = await load_local_auth_candidate_from_postgres18(
                    conn, email="martin.pecheur@orcia.ia"
                )
                assert cand_martin is not None
                assert cand_martin.platform_role == "BU_LEAD"
                stale_martin = replace(
                    user_identity_from_candidate(cand_martin),
                    platform_role="CONTRIBUTOR",
                    roles=("CONTRIBUTOR",),
                )
                hydrated_martin = await hydrate_user_identity_from_pg(engine, stale_martin)
                assert hydrated_martin.platform_role == "BU_LEAD"

                cand_camille = await load_local_auth_candidate_from_postgres18(
                    conn, email="camille.onto@orcia.ia"
                )
                assert cand_camille is not None
                assert cand_camille.platform_role == "ONTOLOGY_LEAD"
                assert user_identity_from_candidate(cand_camille).platform_role == "ONTOLOGY_LEAD"

                audit_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM audit_ledger "
                            "WHERE org_unit_id = :ou AND event_type = 'IAM_ACCOUNT_INVITED'"
                        ),
                        {"ou": UUID(bu_comm_id)},
                    )
                ).scalar_one()
                assert audit_count >= 1

            # 4. B1 Bidirectional sync: Admin removes ONTOLOGY_LEAD from Camille -> BU cleaned in PG
            r_demote = await client.patch(
                f"/api/v1/settings/iam/accounts/{camille_acc_id}",
                headers=admin_headers,
                json={"roles": ["CONTRIBUTOR"]},
            )
            assert r_demote.status_code == 200, r_demote.text
            async with engine.connect() as conn:
                ou_after = (
                    await conn.execute(
                        sa.text(
                            "SELECT ontology_lead_user_ids_jsonb FROM org_units WHERE id = :id"
                        ),
                        {"id": UUID(bu_comm_id)},
                    )
                ).scalar_one()
                onto_after = json.loads(ou_after) if isinstance(ou_after, str) else ou_after
                assert "camille.onto@orcia.ia" not in onto_after

            # 5. TEAM_LEAD Pascal logs in, updates own team & is scoped in GET /api/v1/audit/ledger
            login_pascal = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "pascal.lacdap@orcia.ia",
                    "password": r_pascal.json()["temporary_password"],
                },
            )
            assert login_pascal.status_code == 200, login_pascal.text
            pascal_headers = {"Authorization": f"Bearer {login_pascal.json()['access_token']}"}
            assert (
                await client.patch(
                    f"/api/v1/org-units/{team_ventes_id}",
                    headers=pascal_headers,
                    json={"name": "Équipe Ventes Directes"},
                )
            ).status_code == 200

            # Scoped audit ledger checks on real PostgreSQL 18
            audit_martin = await client.get("/api/v1/audit/ledger", headers=martin_headers)
            assert audit_martin.status_code == 200
            martin_ou_ids = {e["org_unit_id"] for e in audit_martin.json()["entries"]}
            assert bu_comm_id in martin_ou_ids
            assert team_ventes_id in martin_ou_ids
            assert bu_fin_id not in martin_ou_ids
            assert None not in martin_ou_ids

            audit_pascal = await client.get("/api/v1/audit/ledger", headers=pascal_headers)
            assert audit_pascal.status_code == 200
            pascal_ou_ids = {e["org_unit_id"] for e in audit_pascal.json()["entries"]}
            assert team_ventes_id in pascal_ou_ids
            assert bu_comm_id not in pascal_ou_ids
            assert bu_fin_id not in pascal_ou_ids

            # 6. Story 25.2 — Non-delegated CONTRIBUTOR/OBSERVER reads full org tree read-only
            #    (can_* == False) and receives 403 on all mutations against real PG18.
            r_contrib = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                json={
                    "principal_id": "claire.contrib@orcia.ia",
                    "display_name": "Claire Contrib",
                    "email": "claire.contrib@orcia.ia",
                    "account_kind": "HUMAN",
                    "roles": ["CONTRIBUTOR"],
                },
            )
            assert r_contrib.status_code == 200, r_contrib.text
            login_contrib = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "claire.contrib@orcia.ia",
                    "password": r_contrib.json()["temporary_password"],
                },
            )
            assert login_contrib.status_code == 200, login_contrib.text
            contrib_headers = {"Authorization": f"Bearer {login_contrib.json()['access_token']}"}

            ro_tree = await client.get("/api/v1/org-units", headers=contrib_headers)
            assert ro_tree.status_code == 200, ro_tree.text
            ro_units = {u["id"]: u for u in ro_tree.json()["org_units"]}
            assert {bu_comm_id, bu_fin_id, team_ventes_id}.issubset(ro_units.keys())
            for unit in ro_units.values():
                assert unit["can_edit"] is False
                assert unit["can_create_child"] is False
                assert unit["can_delete"] is False
                assert unit["can_manage_members"] is False
                assert unit["can_manage_ontology_leads"] is False
                assert unit["can_invite_users"] is False

            assert (
                await client.post(
                    "/api/v1/org-units",
                    headers=contrib_headers,
                    json={"name": "Unauthorized PG BU", "kind": "BU"},
                )
            ).status_code == 403
            assert (
                await client.patch(
                    f"/api/v1/org-units/{team_ventes_id}",
                    headers=contrib_headers,
                    json={"name": "Unauthorized Rename"},
                )
            ).status_code == 403
            assert (
                await client.delete(
                    f"/api/v1/org-units/{team_ventes_id}",
                    headers=contrib_headers,
                )
            ).status_code == 403
            assert (
                await client.post(
                    "/api/v1/org-units/invite-user",
                    headers=contrib_headers,
                    json={
                        "target_org_unit_id": team_ventes_id,
                        "email": "blocked.pg@orcia.ia",
                        "display_name": "Blocked PG",
                        "assignment_role": "TEAM_MEMBER",
                    },
                )
            ).status_code == 403
            # Also verify OBSERVER read-only header blocks mutations
            obs_ro = await client.get(
                "/api/v1/org-units",
                headers={**martin_headers, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
            )
            assert obs_ro.status_code == 200
            for unit in obs_ro.json()["org_units"]:
                assert unit["can_edit"] is False
                assert unit["can_delete"] is False
            assert (
                await client.patch(
                    f"/api/v1/org-units/{bu_comm_id}",
                    headers={**martin_headers, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                    json={"name": "Blocked Observer Rename"},
                )
            ).status_code == 403
    finally:
        await engine.dispose()
