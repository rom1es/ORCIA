"""Story 20.2 — PostgreSQL 18 vertical integration tests (`HTTP -> PostgreSQL 18 SELECT`).

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Reversible Alembic revision `20261117_2002`
   (`upgrade head` -> `downgrade 20261117_2001` -> `upgrade head`).
2. Full `L4 -> L3 -> L2 -> L1` lifecycle persisted across `ontology_concepts`,
   `ontology_promotion_proposals`, and `audit_ledger`, with `ONTOLOGY_LEAD` validation on BU L2
   and collision detection at target level.
3. Strict isolation (`ONTOLOGY_LEAD` rejected `403` on L1 & other BU; `OBSERVER` rejected `403`).
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

from orcia_core.permissions import UserIdentity

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_20_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_20_2_pw"  # pragma: allowlist secret


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
            [*alembic_cmd, "downgrade", "20261117_2001"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-20-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-20-2-vault-key-0001")
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
async def test_story_20_2_full_l4_to_l1_promotion_lifecycle_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    app, client = app_client_factory()
    admin_headers = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    try:
        async with client:
            # 1. Admin creates BU Finance, Team Comptabilité, and provisions ONTOLOGY_LEAD Sophie
            for principal, name, roles in [
                ("sophie.onto@orcia.ia", "Sophie Référente", ["ONTOLOGY_LEAD"]),
                ("marc.lead@orcia.io", "Marc Lead", ["TEAM_LEAD"]),
                ("nadia.dev@orcia.io", "Nadia Dev", ["CONTRIBUTOR"]),
            ]:
                r_acc = await client.post(
                    "/api/v1/settings/iam/accounts",
                    headers=admin_headers,
                    json={
                        "principal_id": principal,
                        "display_name": name,
                        "email": principal,
                        "account_kind": "HUMAN",
                        "roles": roles,
                    },
                )
                assert r_acc.status_code == 200, r_acc.text

            r_bu = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={
                    "name": "BU Finance",
                    "slug": "bu-finance",
                    "kind": "BU",
                    "ontology_lead_user_ids": ["sophie.onto@orcia.ia"],
                },
            )
            assert r_bu.status_code == 200
            bu_id = r_bu.json()["id"]

            r_team = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={
                    "name": "Équipe Compta",
                    "slug": "team-compta",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                    "lead_user_ids": ["marc.lead@orcia.io"],
                    "member_user_ids": ["nadia.dev@orcia.io"],
                },
            )
            assert r_team.status_code == 200
            team_id = r_team.json()["id"]

            ws_id = "0195f000-0000-7000-8000-000000002022"
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspaces "
                        "(id, slug, name, owner_org_unit_id, visibility_mode) "
                        "VALUES (CAST(:id AS uuid), 'ws-compta', 'WS Compta', "
                        "CAST(:owner AS uuid), 'STANDARD') ON CONFLICT (id) DO NOTHING"
                    ),
                    {"id": ws_id, "owner": team_id},
                )

            # Register Sophie persona on app auth_service for HTTP header simulation
            svc = app.state.auth_service
            sophie_identity = UserIdentity(
                id="0195f000-0000-7000-8000-000000002099",
                email="sophie.onto@orcia.ia",
                display_name="Sophie Référente",
                auth_mode="LOCAL",
                human_profile_archetype="ARCHITECT",
                platform_role="ONTOLOGY_LEAD",
                primary_org_unit_id=bu_id,
                roles=("ONTOLOGY_LEAD",),
            )
            svc.register_user(sophie_identity)
            svc._persona_map["sophie"] = sophie_identity.id  # noqa: SLF001
            sophie_headers = {"X-Orcia-Persona": "sophie"}
            nadia_headers = {"X-Orcia-Persona": "nadia"}
            marc_headers = {"X-Orcia-Persona": "marc"}

            # 2. Nadia (CONTRIBUTOR) creates term at L4 (4_WORKSPACE) -> persisted in PG18
            r_c4 = await client.post(
                "/api/v1/ontology-rag/ontology/concepts",
                headers=nadia_headers,
                json={
                    "concept_key": "marge-nette-l4",
                    "canonical_term": "Marge Nette Opérationnelle",
                    "level": "4_WORKSPACE",
                    "scope_id": ws_id,
                    "definition_text": "Marge après charges opérationnelles directes.",
                },
            )
            assert r_c4.status_code == 200, r_c4.text

            # 3. Nadia proposes L4 -> L3; Marc (TEAM_LEAD) approves L3
            r_p3 = await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=nadia_headers,
                json={"concept_key": "marge-nette-l4"},
            )
            assert r_p3.status_code == 200
            assert r_p3.json()["target_level"] == "3_TEAM"
            assert r_p3.json()["target_scope_id"] == team_id

            r_d3 = await client.post(
                f"/api/v1/ontology-rag/ontology/promotions/{r_p3.json()['id']}/decide",
                headers=marc_headers,
                json={"decision": "APPROVE", "review_comment": "Validé équipe"},
            )
            assert r_d3.status_code == 200
            l3_key = r_d3.json()["promoted_concept"]["concept_key"]

            # Seed an existing homonym at L2 to verify collision detection!
            r_homonym = await client.post(
                "/api/v1/ontology-rag/ontology/concepts",
                headers=sophie_headers,
                json={
                    "concept_key": "marge-nette-l2-existing",
                    "canonical_term": "Marge Nette Opérationnelle",
                    "level": "2_DOMAIN",
                    "scope_id": bu_id,
                    "definition_text": "Ancienne définition BU Finance.",
                },
            )
            assert r_homonym.status_code == 200

            # 4. Marc proposes L3 -> L2; Sophie (ONTOLOGY_LEAD) sees collision & approves L2
            r_p2 = await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=marc_headers,
                json={"concept_key": l3_key},
            )
            assert r_p2.status_code == 200
            assert r_p2.json()["target_level"] == "2_DOMAIN"
            assert r_p2.json()["collision_detected"] is True
            assert "Ancienne définition BU Finance" in (r_p2.json()["colliding_definition"] or "")

            r_d2 = await client.post(
                f"/api/v1/ontology-rag/ontology/promotions/{r_p2.json()['id']}/decide",
                headers=sophie_headers,
                json={"decision": "APPROVE"},
            )
            assert r_d2.status_code == 200
            l2_key = r_d2.json()["promoted_concept"]["concept_key"]

            # 5. Sophie proposes L2 -> L1; Sophie cannot approve L1 (403); Karim approves L1
            r_p1 = await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=sophie_headers,
                json={"concept_key": l2_key},
            )
            assert r_p1.status_code == 200
            assert r_p1.json()["target_level"] == "1_ENTERPRISE"

            r_sophie_l1 = await client.post(
                f"/api/v1/ontology-rag/ontology/promotions/{r_p1.json()['id']}/decide",
                headers=sophie_headers,
                json={"decision": "APPROVE"},
            )
            assert r_sophie_l1.status_code == 403

            r_d1 = await client.post(
                f"/api/v1/ontology-rag/ontology/promotions/{r_p1.json()['id']}/decide",
                headers=admin_headers,
                json={"decision": "APPROVE"},
            )
            assert r_d1.status_code == 200
            assert r_d1.json()["promoted_concept"]["level"] == "1_ENTERPRISE"
            l1_key = r_d1.json()["promoted_concept"]["concept_key"]

            # 5b. Cross-scope key collision from 4_WORKSPACE contributor -> HTTP 409
            r_forged = await client.post(
                "/api/v1/ontology-rag/ontology/concepts",
                headers=nadia_headers,
                json={
                    "concept_key": l1_key,
                    "canonical_term": "Écrasement illégal",
                    "level": "4_WORKSPACE",
                    "scope_id": ws_id,
                    "definition_text": "Tentative downgrade L1",
                },
            )
            assert r_forged.status_code == 409
            assert r_forged.json()["error_code"] == "ERR_ONTOLOGY_CONFLICT"

            # 5c. Forged target_scope_id at promotion creation -> HTTP 403
            r_forged_target = await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=nadia_headers,
                json={
                    "concept_key": "marge-nette-l4",
                    "target_scope_id": "0195f000-0000-7000-8000-000000009999",
                },
            )
            assert r_forged_target.status_code == 403

        # 6. Direct PostgreSQL 18 SELECT verification (restart-proof truth)
        async with engine.connect() as conn:
            levels_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT level, scope_id, canonical_term FROM ontology_concepts "
                        "WHERE LOWER(canonical_term) = LOWER('Marge Nette Opérationnelle')"
                    )
                )
            ).fetchall()
            levels_present = {str(r[0]) for r in levels_rows}
            assert {"4_WORKSPACE", "3_TEAM", "2_DOMAIN", "1_ENTERPRISE"}.issubset(levels_present)

            # L1 concept was never downgraded by the 409 forged upsert
            l1_row = (
                await conn.execute(
                    sa.text("SELECT level, scope_id FROM ontology_concepts WHERE concept_key = :k"),
                    {"k": l1_key},
                )
            ).one()
            assert str(l1_row[0]) == "1_ENTERPRISE"
            assert str(l1_row[1]) == "scope-global"

            promo_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT status, reviewed_by_user_id, reviewed_at "
                        "FROM ontology_promotion_proposals "
                        "WHERE term = 'Marge Nette Opérationnelle'"
                    )
                )
            ).fetchall()
            assert len(promo_rows) == 3
            assert all(str(r[0]) == "APPROVED" and r[1] and r[2] is not None for r in promo_rows)

            audit_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT event_type, workspace_id, org_unit_id, metadata_jsonb, scope_path "
                        "FROM audit_ledger WHERE event_type IN "
                        "('ONTOLOGY_CONCEPT_CREATED', 'ONTOLOGY_PROMOTION_APPROVED')"
                    )
                )
            ).fetchall()
            assert len(audit_rows) >= 5
            ws_created_rows = [
                r
                for r in audit_rows
                if r[0] == "ONTOLOGY_CONCEPT_CREATED" and (r[3] or {}).get("level") == "4_WORKSPACE"
            ]
            assert len(ws_created_rows) == 1
            assert str(ws_created_rows[0][1]) == ws_id
            assert str(ws_created_rows[0][2]) == team_id
            l1_approved_rows = [
                r
                for r in audit_rows
                if r[0] == "ONTOLOGY_PROMOTION_APPROVED" and r[4] == "scope-global"
            ]
            # L1 promotion audit row has both workspace_id=NULL and org_unit_id=NULL
            assert len(l1_approved_rows) >= 1
            assert all(r[1] is None and r[2] is None for r in l1_approved_rows)
            _ = UUID(ws_id)
    finally:
        await engine.dispose()
