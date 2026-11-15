"""Vertical HTTP -> PostgreSQL 18 Integration Tests for multi-lead units and BU invariants.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261115_1902` idempotency:
   `upgrade head` -> `downgrade 20261115_1901` -> `upgrade head`.
2. PostgreSQL 18 table constraints:
   - `chk_org_units_bu_no_members`: BU rejection if `member_user_ids_jsonb <> '[]'`.
   - `chk_org_units_lead_user_ids_is_array`: rejection if not JSONB array.
   - `iam_accounts` CHECK constraint supporting `LOCAL_PASSWORD`.
3. B1 Strict bidirectional sync over HTTP:
   - 422 `ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN` on BU creation/update with members.
   - Multi-lead assignment on BU gives `BU_LEAD` to all co-leads.
   - Lead removal revokes `BU_LEAD` automatically when no other BU is led.
   - IAM account update with `led_bu_ids` synchronizes `org_units.lead_user_ids_jsonb`.
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_kernel.ids import new_uuid7

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_multi_lead_int"
DB_USER = "orcia"
DB_PASSWORD = "orcia_multi_lead_pw"  # pragma: allowlist secret


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
            "PYTHONPATH": (
                f"{REPO_ROOT}/packages/orcia-kernel/src:"
                f"{REPO_ROOT}/packages/orcia-core/src:"
                f"{REPO_ROOT}/packages/orcia-connectors/src:"
                f"{REPO_ROOT}/apps/api/src:"
                f"{REPO_ROOT}/apps/worker/src:"
                f"{REPO_ROOT}"
            ),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]

        def _run_alembic(args: list[str]) -> None:
            res = subprocess.run(args, cwd=REPO_ROOT, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Alembic failed ({res.returncode}):\n"
                    f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}"
                )

        # 1. Upgrade to head
        _run_alembic([*alembic_cmd, "upgrade", "head"])
        # 2. Downgrade to 20261115_1901
        _run_alembic([*alembic_cmd, "downgrade", "20261115_1901"])
        # 3. Upgrade back to head (verifies 20261115_1902 reversibility)
        _run_alembic([*alembic_cmd, "upgrade", "head"])
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-multi-lead-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-multi-lead-vault-key-0001")
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
async def test_database_level_constraints_and_local_password_postgres18(
    database_url: str,
) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        root_id = new_uuid7()
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                "VALUES (:id, 'root-enterprise', 'Enterprise Root', 'ENTERPRISE', NULL) "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": root_id},
        )
        actual_root = (
            await conn.execute(sa.text("SELECT id FROM org_units WHERE slug = 'root-enterprise'"))
        ).scalar()

        # Invariant 1: BU with non-empty member_user_ids_jsonb violates chk_org_units_bu_no_members
        with pytest.raises(IntegrityError):
            async with conn.begin_nested():
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (
                            id, slug, name, unit_type, parent_id, member_user_ids_jsonb
                        ) VALUES (
                            :id, 'bu-forbidden', 'BU Rejet', 'BU', :pid,
                            '["alice@orcia.local"]'::jsonb
                        )
                        """
                    ),
                    {"id": new_uuid7(), "pid": actual_root},
                )

        # Invariant 2: lead_user_ids_jsonb must be a JSON array
        with pytest.raises(IntegrityError):
            async with conn.begin_nested():
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (
                            id, slug, name, unit_type, parent_id, lead_user_ids_jsonb
                        ) VALUES (
                            :id, 'bu-bad-leads', 'BU Bad Leads', 'BU', :pid,
                            '{"not": "array"}'::jsonb
                        )
                        """
                    ),
                    {"id": new_uuid7(), "pid": actual_root},
                )

        # Invariant 3: iam_accounts accepts LOCAL_PASSWORD
        user_id = new_uuid7()
        await conn.execute(
            sa.text(
                """
                INSERT INTO iam_accounts (
                    id, principal_id, display_name, email,
                    account_kind, auth_source, roles_jsonb
                ) VALUES (
                    :id, 'local_user@orcia.local', 'Local User', 'local_user@orcia.local',
                    'HUMAN', 'LOCAL_PASSWORD', '["CONTRIBUTOR"]'::jsonb
                )
                """
            ),
            {"id": user_id},
        )
        saved_auth = (
            await conn.execute(
                sa.text("SELECT auth_source FROM iam_accounts WHERE id = :id"),
                {"id": user_id},
            )
        ).scalar()
        assert saved_auth == "LOCAL_PASSWORD"

    await engine.dispose()


@pytest.mark.asyncio
async def test_vertical_http_multi_lead_b1_strict_sync_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        for tbl in ("role_permission_grants", "iam_accounts", "workspaces", "users"):
            await conn.execute(sa.text(f"DELETE FROM {tbl}"))
        await conn.execute(sa.text("DELETE FROM org_units WHERE unit_type <> 'ENTERPRISE'"))

        root_id = (
            await conn.execute(
                sa.text("SELECT id FROM org_units WHERE unit_type = 'ENTERPRISE' LIMIT 1")
            )
        ).scalar()
        if root_id is None:
            root_id = new_uuid7()
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                    "VALUES (:id, 'orcia-ent', 'ORCIA Root', 'ENTERPRISE', NULL)"
                ),
                {"id": root_id},
            )

        # Seed admin and candidate leads in users and iam_accounts
        admin_id = new_uuid7()
        lead1_id = new_uuid7()
        lead2_id = new_uuid7()
        for uid, email, name, role in (
            (admin_id, "admin@orcia.local", "Admin", "PLATFORM_ADMIN"),
            (lead1_id, "lead1@orcia.local", "Alice Lead", "CONTRIBUTOR"),
            (lead2_id, "lead2@orcia.local", "Bob Lead", "CONTRIBUTOR"),
        ):
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO users (
                        id, email, display_name, auth_mode,
                        human_profile_archetype, platform_role, primary_org_unit_id
                    ) VALUES (
                        :id, :email, :name, 'LOCAL', 'CONTRIBUTOR', :role, :p_ou
                    )
                    """
                ),
                {"id": uid, "email": email, "name": name, "role": role, "p_ou": root_id},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO iam_accounts (
                        id, principal_id, display_name, email,
                        account_kind, auth_source, roles_jsonb
                    ) VALUES (
                        :id, :email, :name, :email, 'HUMAN', 'LOCAL_PASSWORD', :roles
                    )
                    """
                ),
                {"id": uid, "email": email, "name": name, "roles": f'["{role}"]'},
            )

    headers = {
        "X-Orcia-Persona": "karim",
        "X-User-Id": str(admin_id),
        "X-User-Email": "admin@orcia.local",
        "X-User-Roles": "PLATFORM_ADMIN",
    }

    client = app_client_factory()

    # 1. Reject BU creation with non-empty members (422 ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN)
    resp_rej = await client.post(
        "/api/v1/org-units",
        headers=headers,
        json={
            "name": "Direction RH",
            "slug": "direction-rh",
            "kind": "BU",
            "member_user_ids": ["lead1@orcia.local"],
        },
    )
    assert resp_rej.status_code == 422
    assert "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN" in resp_rej.text

    # 2. Create BU with co-leads lead1 and lead2
    resp_bu = await client.post(
        "/api/v1/org-units",
        headers=headers,
        json={
            "name": "Direction Ventes",
            "slug": "direction-ventes",
            "kind": "BU",
            "lead_user_ids": ["lead1@orcia.local", "lead2@orcia.local"],
        },
    )
    assert resp_bu.status_code == 200, resp_bu.text
    bu_data = resp_bu.json()
    assert bu_data["lead_user_ids"] == ["lead1@orcia.local", "lead2@orcia.local"]
    assert bu_data["lead_user_id"] == "lead1@orcia.local"
    bu_id = bu_data["id"]

    # Verify B1 sync: both lead1 and lead2 now have BU_LEAD role in iam_accounts
    async with engine.begin() as conn:
        r1 = (
            await conn.execute(
                sa.text("SELECT roles_jsonb FROM iam_accounts WHERE email = 'lead1@orcia.local'")
            )
        ).scalar()
        r2 = (
            await conn.execute(
                sa.text("SELECT roles_jsonb FROM iam_accounts WHERE email = 'lead2@orcia.local'")
            )
        ).scalar()
        assert "BU_LEAD" in r1
        assert "BU_LEAD" in r2

    # 3. Create a TEAM under BU with lead2 as lead and lead1 as member
    resp_team = await client.post(
        "/api/v1/org-units",
        headers=headers,
        json={
            "name": "Équipe Inside Sales",
            "slug": "inside-sales",
            "kind": "TEAM",
            "parent_id": bu_id,
            "lead_user_ids": ["lead2@orcia.local"],
            "member_user_ids": ["lead1@orcia.local"],
        },
    )
    assert resp_team.status_code == 200, resp_team.text
    team_data = resp_team.json()
    assert team_data["member_user_ids"] == ["lead1@orcia.local"]

    # 4. Remove lead1 from BU leads -> B1 Strict revokes BU_LEAD automatically
    resp_patch = await client.patch(
        f"/api/v1/org-units/{bu_id}",
        headers=headers,
        json={"lead_user_ids": ["lead2@orcia.local"]},
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["lead_user_ids"] == ["lead2@orcia.local"]

    async with engine.begin() as conn:
        r1_after = (
            await conn.execute(
                sa.text("SELECT roles_jsonb FROM iam_accounts WHERE email = 'lead1@orcia.local'")
            )
        ).scalar()
        # lead1 no longer leads any BU, BU_LEAD must be removed
        assert "BU_LEAD" not in r1_after
        # lead2 still leads BU and TEAM
        r2_after = (
            await conn.execute(
                sa.text("SELECT roles_jsonb FROM iam_accounts WHERE email = 'lead2@orcia.local'")
            )
        ).scalar()
        assert "BU_LEAD" in r2_after
        assert "TEAM_LEAD" in r2_after

    # 5. Reverse sync: Update IAM account for lead1 with led_bu_ids=[bu_id]
    resp_acc_patch = await client.patch(
        f"/api/v1/settings/iam/accounts/{lead1_id}",
        headers=headers,
        json={"led_bu_ids": [bu_id]},
    )
    assert resp_acc_patch.status_code == 200, resp_acc_patch.text
    acc_data = resp_acc_patch.json()
    assert bu_id in acc_data["led_bu_ids"]

    # BU now has lead1 re-added to lead_user_ids
    async with engine.begin() as conn:
        bu_leads = (
            await conn.execute(
                sa.text("SELECT lead_user_ids_jsonb FROM org_units WHERE id = :id"),
                {"id": UUID(bu_id)},
            )
        ).scalar()
        assert "lead1@orcia.local" in bu_leads
        assert "lead2@orcia.local" in bu_leads

    await client.aclose()
    await engine.dispose()
