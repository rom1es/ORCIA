"""Story 25.3 — Vertical PG18 + Redis Integration Tests (`HTTP -> PG18`, `AD-17`).

Verifies on real `create_app()` without `dependency_overrides` or `app.state.*` injection:
1. Fresh PG18 starts with `0` runs (`GET /api/v1/orchestration/state` returns `runs == []`).
2. Real run + human anchor / arbitration persisted in PG18 -> `GET /runs/{run_id}/blackboard`
   exposes real `human_anchors` & `pending_arbitrations` (surviving cold restart `app2`).
3. Resolution persists in PG18 (`SELECT` verification) and `pending_arbitrations` clears (`[]`).
4. SQL deletion of `workflow_runs` purges stale RAM entries on `GET /api/v1/orchestration/state`.
5. Security gate: `READ_ONLY_OBSERVER` receives `403 ERR_OBSERVER_MODE_READ_ONLY` on anchor sign
   and arbitration resolution.
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
DB_NAME = "orcia_story_25_3_pg18"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_25_3_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PostgreSQL 18 + pgvector and Redis 7.4 containers at Alembic head."""
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4-alpine") as redis_box,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_host = redis_box.get_container_host_ip()
        redis_port = int(redis_box.get_exposed_port(6379))
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url, redis_url


@pytest.mark.asyncio
async def test_story_25_3_zero_demo_run_blackboard_governance_and_observer_security_pg18(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Day-0 zero-run state, real PG18 anchor/arbitration lifecycle, cold restart & 403."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-25-3-pg18-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-25-3-pg18-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    engine = create_async_engine(pg_url)
    try:
        app1 = create_app()
        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as client1,
        ):
            r_first = await client1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.253@orcia.ia",
                    "display_name": "Admin 25.3",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}
            observer_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER",
            }

            # 1. Fresh PG18 after first-admin creation must have 0 runs
            r_state0 = await client1.get("/api/v1/orchestration/state", headers=auth_headers)
            assert r_state0.status_code == 200, r_state0.text
            assert r_state0.json()["runs"] == []

            # 2. Create real workspace & instantiate run
            r_ws = await client1.post(
                "/api/v1/workspaces",
                headers=auth_headers,
                json={
                    "name": "Espace 25.3 PG18",
                    "slug": "espace-25-3-pg18",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]
            UUID(ws_id)

            r_inst = await client1.post(
                "/api/v1/orchestration/runs/instantiate",
                headers=auth_headers,
                json={
                    "workflow_uri": "orcia://workflows/claims-engineering-delivery",
                    "workspace_id": ws_id,
                },
            )
            assert r_inst.status_code == 200, r_inst.text
            run_id = r_inst.json()["run"]["id"]
            UUID(run_id)

            r_bb0 = await client1.get(
                f"/api/v1/orchestration/runs/{run_id}/blackboard",
                headers=auth_headers,
            )
            assert r_bb0.status_code == 200, r_bb0.text
            assert r_bb0.json()["pending_arbitrations"] == []
            assert r_bb0.json()["human_anchors"] == []

            # 3. Observer mode rejected on anchor sign (403 ERR_OBSERVER_MODE_READ_ONLY)
            r_obs_anchor = await client1.post(
                "/api/v1/orchestration/runs/anchors/sign",
                headers=observer_headers,
                json={
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "section_key": "human_architecture_intent",
                    "content_text": "Tentative observateur devant être rejetée avec HTTP 403.",
                    "signature_text": "Observer",
                    "author_type": "HUMAN",
                },
            )
            assert r_obs_anchor.status_code == 403, r_obs_anchor.text
            assert r_obs_anchor.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # 4. Real anchor sign -> persisted in PG18 & exposed in GET /blackboard
            anchor_text = (
                "Architecture modulaire unidirectionnelle validée sur PostgreSQL 18 sans fallback."
            )
            r_anchor = await client1.post(
                "/api/v1/orchestration/runs/anchors/sign",
                headers=auth_headers,
                json={
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "section_key": "human_architecture_intent",
                    "content_text": anchor_text,
                    "signature_text": "Admin 25.3",
                    "author_type": "HUMAN",
                },
            )
            assert r_anchor.status_code == 200, r_anchor.text

            # 5. Request real arbitration -> persisted in PG18 & exposed in GET /blackboard
            r_arb = await client1.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration",
                headers=auth_headers,
                json={
                    "question_title": "Stratégie d'indexation pgvector",
                    "context_summary": "Arbitrage requis entre HNSW et IVFFlat.",
                    "tie_break_policy": "PAUSE_AND_ESCALATE",
                    "options_matrix": [
                        {
                            "option_key": "OPT_HNSW_PG18",
                            "title": "Index HNSW Cosine PG18",
                            "pros": ["Rappel > 98%"],
                            "cons": ["RAM modérée"],
                            "si_impact": "PostgreSQL 18",
                            "finops_impact": "0 $/mois",
                            "recommended": True,
                        },
                        {
                            "option_key": "OPT_IVFFLAT_PG18",
                            "title": "Index IVFFlat PG18",
                            "pros": ["Build rapide"],
                            "cons": ["Rappel moindre"],
                            "si_impact": "PostgreSQL 18",
                            "finops_impact": "0 $/mois",
                            "recommended": False,
                        },
                    ],
                },
            )
            assert r_arb.status_code == 200, r_arb.text
            arb_id = r_arb.json()["arbitration"]["id"]

            # 6. Observer mode rejected on arbitration resolve (403 ERR_OBSERVER_MODE_READ_ONLY)
            r_obs_arb = await client1.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration/resolve",
                headers=observer_headers,
                json={
                    "arbitration_id": arb_id,
                    "selected_option_key": "OPT_HNSW_PG18",
                    "human_justification": "Tentative observateur.",
                },
            )
            assert r_obs_arb.status_code == 403, r_obs_arb.text
            assert r_obs_arb.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 7. Cold restart app2 -> verify PG18 rehydrates human_anchors & pending_arbitrations
        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            r_login = await client2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin.253@orcia.ia",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                },
            )
            assert r_login.status_code == 200, r_login.text
            cold_headers = {"Authorization": f"Bearer {r_login.json()['access_token']}"}

            r_bb_cold = await client2.get(
                f"/api/v1/orchestration/runs/{run_id}/blackboard",
                headers=cold_headers,
            )
            assert r_bb_cold.status_code == 200, r_bb_cold.text
            bb_cold = r_bb_cold.json()
            assert len(bb_cold["human_anchors"]) == 1
            assert bb_cold["human_anchors"][0]["section_key"] == "human_architecture_intent"
            assert len(bb_cold["pending_arbitrations"]) == 1
            assert bb_cold["pending_arbitrations"][0]["id"] == arb_id
            assert [
                o["option_key"] for o in bb_cold["pending_arbitrations"][0]["options_matrix"]
            ] == [
                "OPT_HNSW_PG18",
                "OPT_IVFFLAT_PG18",
            ]

            # 8. Resolve arbitration -> PG18 SELECT confirms resolution & clears pending
            r_resolve = await client2.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration/resolve",
                headers=cold_headers,
                json={
                    "arbitration_id": arb_id,
                    "selected_option_key": "OPT_HNSW_PG18",
                    "human_justification": "Précision pgvector prioritaire.",
                },
            )
            assert r_resolve.status_code == 200, r_resolve.text

            r_bb_after = await client2.get(
                f"/api/v1/orchestration/runs/{run_id}/blackboard",
                headers=cold_headers,
            )
            assert r_bb_after.status_code == 200, r_bb_after.text
            assert r_bb_after.json()["pending_arbitrations"] == []

            async with engine.connect() as conn:
                anchor_rows = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT section_key, content_text FROM human_anchor_signatures "
                                "WHERE run_id = CAST(:rid AS uuid)"
                            ),
                            {"rid": run_id},
                        )
                    )
                    .mappings()
                    .all()
                )
                assert len(anchor_rows) == 1
                assert anchor_rows[0]["content_text"] == anchor_text

                arb_rows = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT status, selected_option_key "
                                "FROM human_arbitration_requests "
                                "WHERE id = CAST(:aid AS uuid)"
                            ),
                            {"aid": arb_id},
                        )
                    )
                    .mappings()
                    .all()
                )
                assert len(arb_rows) == 1
                assert arb_rows[0]["status"] == "RESOLVED_BY_HUMAN"
                assert arb_rows[0]["selected_option_key"] == "OPT_HNSW_PG18"

            # 9. Instantiate a 2nd run, delete it from PG18, and verify GET /state purges RAM
            r_inst2 = await client2.post(
                "/api/v1/orchestration/runs/instantiate",
                headers=cold_headers,
                json={
                    "workflow_uri": "orcia://workflows/claims-engineering-delivery",
                    "workspace_id": ws_id,
                },
            )
            assert r_inst2.status_code == 200, r_inst2.text
            run_id_2 = r_inst2.json()["run"]["id"]

            r_state_before = await client2.get(
                "/api/v1/orchestration/state",
                headers=cold_headers,
            )
            assert r_state_before.status_code == 200
            assert run_id_2 in {r["id"] for r in r_state_before.json()["runs"]}

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("DELETE FROM step_executions WHERE run_id = CAST(:rid AS uuid)"),
                    {"rid": run_id_2},
                )
                await conn.execute(
                    sa.text("DELETE FROM run_lock_manifests WHERE run_id = CAST(:rid AS uuid)"),
                    {"rid": run_id_2},
                )
                await conn.execute(
                    sa.text("DELETE FROM workflow_runs WHERE id = CAST(:rid AS uuid)"),
                    {"rid": run_id_2},
                )

            r_state_after_purge = await client2.get(
                "/api/v1/orchestration/state",
                headers=cold_headers,
            )
            assert r_state_after_purge.status_code == 200, r_state_after_purge.text
            assert run_id_2 not in {r["id"] for r in r_state_after_purge.json()["runs"]}
            assert run_id in {r["id"] for r in r_state_after_purge.json()["runs"]}
    finally:
        await engine.dispose()
