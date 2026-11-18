"""Story 20.4 — PostgreSQL 18 vertical integration tests (`HTTP -> PG18 SELECT`).

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. User-confined aggregation in `GET /api/v1/users/me/profile-summary`:
   - `total_tokens`, `peak_daily_tokens`, `longest_streak_days`, `current_streak_days`
   - `led_business_units`, `ontology_business_units`, `led_teams`, `member_teams`
   - `popular_items` Top 5 from User A's workflows/steps/tools with ZERO leakage from User B.
2. End-to-end `POST /api/v1/assistant/three-speed/turn` & `/stream` write
   `ASSISTANT_TURN_COMPLETED` rows into `audit_ledger` in PostgreSQL 18.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.permissions import UserIdentity
from orcia_core.ports.embedding import EMBEDDING_FIXED_DIMENSION, EmbeddingPort

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_20_4"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_20_4_pw"  # pragma: allowlist secret


class _FakeEmbeddingPort(EmbeddingPort):
    @property
    def dimension(self) -> int:
        return EMBEDDING_FIXED_DIMENSION

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.01] * EMBEDDING_FIXED_DIMENSION for _ in texts]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        return [0.01] * EMBEDDING_FIXED_DIMENSION


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
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield url


@pytest.mark.asyncio
async def test_story_20_4_profile_summary_and_assistant_telemetry_postgres18(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-20-4-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-20-4-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    app = create_app()
    initialize_app_services(app)
    engine = create_async_engine(database_url)
    app.state.db_engine = engine
    app.state.embedding_port = _FakeEmbeddingPort()

    user_a_id = "0195f000-0000-7000-8000-00000000a001"
    user_b_id = "0195f000-0000-7000-8000-00000000b002"
    bu_a_id = "0195f000-0000-7000-8000-000000001001"
    bu_b_id = "0195f000-0000-7000-8000-000000001002"
    team_lead_id = "0195f000-0000-7000-8000-000000002001"
    team_mem_id = "0195f000-0000-7000-8000-000000002002"
    ws_id = "0195f000-0000-7000-8000-000000003001"
    wf_def_a_id = "0195f000-0000-7000-8000-000000004001"
    wf_def_b_id = "0195f000-0000-7000-8000-000000004002"
    run_a_id = "0195f000-0000-7000-8000-000000005001"
    run_b_id = "0195f000-0000-7000-8000-000000005002"

    now_utc = datetime.now(UTC)
    today_dt = now_utc.replace(hour=10, minute=0, second=0, microsecond=0)
    yest_dt = today_dt - timedelta(days=1)
    old_days = [today_dt - timedelta(days=d) for d in (12, 11, 10, 9)]

    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type, lead_user_ids_jsonb,
                                           ontology_lead_user_ids_jsonb, member_user_ids_jsonb)
                    VALUES
                      (:bu_a, 'bu-alpha', 'BU Alpha', 'BU', CAST(:bu_a_leads AS jsonb),
                       CAST(:bu_a_onto AS jsonb), '[]'::jsonb),
                      (:bu_b, 'bu-beta', 'BU Beta', 'BU', CAST(:bu_b_leads AS jsonb),
                       '[]'::jsonb, '[]'::jsonb),
                      (:t_lead, 'team-pay', 'Team Pay', 'TEAM', CAST(:t_lead_ids AS jsonb),
                       '[]'::jsonb, '[]'::jsonb),
                      (:t_mem, 'team-ops', 'Team Ops', 'TEAM', '[]'::jsonb,
                       '[]'::jsonb, CAST(:t_mem_ids AS jsonb))
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "bu_a": bu_a_id,
                    "bu_a_leads": json.dumps([user_a_id]),
                    "bu_a_onto": json.dumps([user_a_id]),
                    "bu_b": bu_b_id,
                    "bu_b_leads": json.dumps([user_b_id]),
                    "t_lead": team_lead_id,
                    "t_lead_ids": json.dumps([user_a_id]),
                    "t_mem": team_mem_id,
                    "t_mem_ids": json.dumps([user_a_id]),
                },
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO users (id, email, display_name, auth_mode, human_profile_archetype,
                                       platform_role, primary_org_unit_id)
                    VALUES
                      (:ua, 'claire.a@orcia.ia', 'Claire Alpha', 'LOCAL',
                       'ARCHITECT', 'BU_LEAD', :bu_a),
                      (:ub, 'marc.b@orcia.ia', 'Marc Beta', 'LOCAL',
                       'DEVELOPER', 'TEAM_LEAD', :bu_b)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"ua": user_a_id, "bu_a": bu_a_id, "ub": user_b_id, "bu_b": bu_b_id},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workspaces (id, slug, name, owner_org_unit_id)
                    VALUES (:ws_id, 'ws-alpha', 'Espace Alpha', :bu_a)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"ws_id": ws_id, "bu_a": bu_a_id},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workflow_definitions (id, uri, workspace_id, version, sha256,
                                                      steps_schema_jsonb)
                    VALUES
                      (:wd_a, 'orcia://wf/sinistres', :ws_id, '1.0.0',
                       'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                       '{"title":"Analyse Sinistres"}'::jsonb),
                      (:wd_b, 'orcia://wf/secret-b', :ws_id, '1.0.0',
                       'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                       '{"title":"Secret Beta WF"}'::jsonb)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"wd_a": wf_def_a_id, "wd_b": wf_def_b_id, "ws_id": ws_id},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workflow_runs (id, run_key, workspace_id, workflow_def_id,
                                               root_run_id, initiated_by_user_id, created_at)
                    VALUES
                      (:ra, 'run-a-1', :ws_id, :wd_a, :ra, :ua, :today),
                      (:rb, 'run-b-1', :ws_id, :wd_b, :rb, :ub, :today)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "ra": run_a_id,
                    "rb": run_b_id,
                    "ws_id": ws_id,
                    "wd_a": wf_def_a_id,
                    "wd_b": wf_def_b_id,
                    "ua": user_a_id,
                    "ub": user_b_id,
                    "today": today_dt,
                },
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO step_executions (id, step_execution_key, run_id, step_key,
                                                 step_index, step_type)
                    VALUES
                      ('0195f000-0000-7000-8000-000000006001', 'se-a-1', :ra,
                       'agent-risk', 0, 'AGENT'),
                      ('0195f000-0000-7000-8000-000000006002', 'se-a-2', :ra,
                       'skill-dora', 1, 'SKILL'),
                      ('0195f000-0000-7000-8000-000000006003', 'se-b-1', :rb,
                       'agent-beta-secret', 0, 'AGENT')
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"ra": run_a_id, "rb": run_b_id},
            )

            ledger_rows = [
                (
                    "0195f000-0000-7000-8000-000000007001",
                    user_a_id,
                    "claire.a@orcia.ia",
                    100,
                    50,
                    today_dt,
                    '{"tool_name":"rag-search"}',
                ),
                (
                    "0195f000-0000-7000-8000-000000007002",
                    user_a_id,
                    "claire.a@orcia.ia",
                    300,
                    200,
                    yest_dt,
                    '{"tool_name":"rag-search"}',
                ),
                (
                    "0195f000-0000-7000-8000-000000007003",
                    user_a_id,
                    "claire.a@orcia.ia",
                    40,
                    10,
                    old_days[0],
                    "{}",
                ),
                (
                    "0195f000-0000-7000-8000-000000007004",
                    user_a_id,
                    "claire.a@orcia.ia",
                    40,
                    10,
                    old_days[1],
                    "{}",
                ),
                (
                    "0195f000-0000-7000-8000-000000007005",
                    user_a_id,
                    "claire.a@orcia.ia",
                    40,
                    10,
                    old_days[2],
                    "{}",
                ),
                (
                    "0195f000-0000-7000-8000-000000007006",
                    user_a_id,
                    "claire.a@orcia.ia",
                    40,
                    10,
                    old_days[3],
                    "{}",
                ),
                (
                    "0195f000-0000-7000-8000-000000007999",
                    user_b_id,
                    "marc.b@orcia.ia",
                    99999,
                    99999,
                    today_dt,
                    '{"tool_name":"secret-b-tool"}',
                ),
            ]
            for idx, (rid, aid, aemail, itok, otok, cdt, mjson) in enumerate(ledger_rows, start=1):
                seid = f"0195f000-0000-7000-8000-00000000800{idx}"
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO audit_ledger (
                            id, source_event_id, actor_type, actor_id, actor_email,
                            event_type, summary, model_id, input_tokens, output_tokens,
                            trace_id, metadata_jsonb, created_at
                        )
                        VALUES (
                            :id, :seid, 'HUMAN', :aid, :aemail,
                            'ASSISTANT_TURN_COMPLETED', 'Turn', 'm-test', :itok, :otok,
                            '00000000000000000000000000000001', CAST(:mjson AS jsonb), :cdt
                        )
                        """
                    ),
                    {
                        "id": rid,
                        "seid": seid,
                        "aid": aid,
                        "aemail": aemail,
                        "itok": itok,
                        "otok": otok,
                        "mjson": mjson,
                        "cdt": cdt,
                    },
                )

        auth_svc = app.state.auth_service
        user_a = UserIdentity(
            id=user_a_id,
            email="claire.a@orcia.ia",
            display_name="Claire Alpha",
            auth_mode="LOCAL",
            human_profile_archetype="ARCHITECT",
            platform_role="BU_LEAD",
            primary_org_unit_id=bu_a_id,
            roles=("BU_LEAD", "ONTOLOGY_LEAD"),
        )
        auth_svc.register_user(user_a)
        tokens_a = auth_svc._issue_for_user(user_a, "LOCAL", None)  # noqa: SLF001
        headers_a = {"Authorization": f"Bearer {tokens_a.access_token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/users/me/profile-summary", headers=headers_a)
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["user_id"] == user_a_id
            assert data["display_name"] == "Claire Alpha"
            assert data["handle"] == "claire.a"
            assert data["led_business_units"] == ["BU Alpha"]
            assert data["ontology_business_units"] == ["BU Alpha"]
            assert data["led_teams"] == ["Team Pay"]
            assert data["member_teams"] == ["Team Ops"]
            assert data["total_tokens"] == 150 + 500 + (50 * 4)  # 850 (0 leakage from User B)
            assert data["peak_daily_tokens"] == 500
            assert data["longest_streak_days"] == 4
            assert data["current_streak_days"] == 2
            pop_keys = {p["item_key"] for p in data["popular_items"]}
            assert wf_def_a_id in pop_keys
            assert "agent-risk" in pop_keys
            assert "skill-dora" in pop_keys
            assert "rag-search" in pop_keys
            assert "agent-beta-secret" not in pop_keys
            assert "secret-b-tool" not in pop_keys

            # 2. Verify POST /api/v1/assistant/three-speed/turn persists ledger row in PG18
            turn_res = await client.post(
                "/api/v1/assistant/three-speed/turn",
                headers=headers_a,
                json={"workspace_id": ws_id, "user_prompt": "Résume la conformité DORA."},
            )
            assert turn_res.status_code == 200, turn_res.text
            turn_id = turn_res.json()["turn_id"]

        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT event_type, actor_id, actor_email, input_tokens, output_tokens,
                               metadata_jsonb->>'turn_id'
                        FROM audit_ledger
                        WHERE actor_id = :ua AND metadata_jsonb->>'turn_id' = :tid
                        """
                    ),
                    {"ua": user_a_id, "tid": turn_id},
                )
            ).fetchone()
            assert row is not None
            assert row[0] == "ASSISTANT_TURN_COMPLETED"
            assert row[1] == user_a_id
            assert row[2] == "claire.a@orcia.ia"
            assert int(row[3]) >= 1 and int(row[4]) >= 1
    finally:
        await engine.dispose()
