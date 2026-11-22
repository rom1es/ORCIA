"""Shared PG18 + Redis testcontainers & seed helpers for Story 26.5 (`create_app()`)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer
try:
    from testcontainers.community.redis import RedisContainer
except ImportError:
    from testcontainers.redis import RedisContainer

from orcia_api.main import create_app
from orcia_core.testing.cassette_llm import DeterministicCassetteEmbedding
from orcia_kernel.ids import new_uuid7_str

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_26_5"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_26_5_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg_and_redis_urls() -> Iterator[tuple[str, str]]:
    """Spin up ephemeral `pgvector/pgvector:pg18` upgraded to head + `redis:7.4.2-alpine`."""
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4.2-alpine") as redis_c,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{redis_c.get_exposed_port(6379)}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        res = subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Alembic upgrade head failed:\n{res.stdout}\n{res.stderr}")
        yield pg_url, redis_url


@pytest_asyncio.fixture
async def real_lifespan_client_factory(
    pg_and_redis_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, str]:
    """Configure real PG18 + Redis env vars and return a clean `create_app()` opener."""
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-26-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-26-5-vault-key-0001")

    def _open_client() -> Any:
        @asynccontextmanager
        async def _ctx() -> AsyncIterator[AsyncClient]:
            app = create_app()
            assert app.dependency_overrides == {}
            async with (
                app.router.lifespan_context(app),
                AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
            ):
                yield client

        return _ctx()

    return _open_client, pg_url


async def seed_pg18_ontology_rag_and_blackboard(
    engine: AsyncEngine,
    *,
    ws_a: str,
    ws_b: str,
    admin_user_id: str,
) -> None:
    """Seed PG18 ontology concepts/axioms, KB docs/chunks, and isolated blackboard snapshots."""
    emb = DeterministicCassetteEmbedding()
    vec_ledger = "[" + ",".join(f"{v:.6f}" for v in await emb.embed_query("Payment Ledger")) + "]"
    c1_id, c2_id = new_uuid7_str(), new_uuid7_str()
    ax1_id, ax2_id = new_uuid7_str(), new_uuid7_str()
    ds_jira, ds_conf, ds_sec, ds_b = (
        new_uuid7_str(),
        new_uuid7_str(),
        new_uuid7_str(),
        new_uuid7_str(),
    )
    doc_jira, doc_stale, doc_sec, doc_b = (
        new_uuid7_str(),
        new_uuid7_str(),
        new_uuid7_str(),
        new_uuid7_str(),
    )
    run_a, step_a, snap_a = new_uuid7_str(), new_uuid7_str(), new_uuid7_str()
    run_b, step_b, snap_b = new_uuid7_str(), new_uuid7_str(), new_uuid7_str()

    async with engine.begin() as conn:
        # 1. Ontology L3 Workspace concepts & axioms (1 relevant, 1 unrelated)
        await conn.execute(
            sa.text(
                """
                INSERT INTO ontology_concepts (
                    id, concept_key, canonical_term, level, scope_id, definition_text,
                    synonyms_jsonb, banned_terms_jsonb, profile_translations_jsonb,
                    expected_schema_jsonb, snapshot_branch_status
                ) VALUES
                (
                    CAST(:c1 AS uuid), 'concept-l3-payment-ledger', 'Payment Ledger',
                    '3_WORKSPACE', :ws_a, 'Append-only settlement capture ledger.',
                    CAST('["Settlement Journal"]' AS jsonb), CAST('[]' AS jsonb),
                    CAST('{"ARCHITECT": "Event-Sourced Payment Ledger (PG18)"}' AS jsonb),
                    CAST('{}' AS jsonb), 'ACTIVE'
                ),
                (
                    CAST(:c2 AS uuid), 'concept-l3-office-badge', 'Onboarding Badge',
                    '3_WORKSPACE', :ws_a, 'Physical building entry card.',
                    CAST('[]' AS jsonb), CAST('[]' AS jsonb),
                    CAST('{}' AS jsonb), CAST('{}' AS jsonb), 'ACTIVE'
                );
                """
            ),
            {"c1": c1_id, "c2": c2_id, "ws_a": ws_a},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO ontology_axioms (
                    id, axiom_key, concept_id, level, scope_id, rule_expression, immutable
                ) VALUES
                (
                    CAST(:ax1 AS uuid), 'ax-ledger-append-only', CAST(:c1 AS uuid),
                    '3_WORKSPACE', :ws_a, 'Ledger rows MUST NOT be mutated or deleted.', TRUE
                ),
                (
                    CAST(:ax2 AS uuid), 'ax-badge-expiry', CAST(:c2 AS uuid),
                    '3_WORKSPACE', :ws_a, 'Badge expires after 365 days.', FALSE
                );
                """
            ),
            {"ax1": ax1_id, "ax2": ax2_id, "c1": c1_id, "c2": c2_id, "ws_a": ws_a},
        )

        # 2. Datasources, KB Documents & Chunks across ws_a and ws_b
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_datasources (id, workspace_id, alias, scheme, uri, role)
                VALUES
                (CAST(:ds_jira AS uuid), CAST(:ws_a AS uuid), 'jira-pay',
                 'jira', 'jira://PAY', 'REFERENCE'),
                (CAST(:ds_conf AS uuid), CAST(:ws_a AS uuid), 'conf-pay',
                 'confluence', 'confluence://SPEC-PAY', 'ACTIVE'),
                (CAST(:ds_sec AS uuid), CAST(:ws_a AS uuid), 'conf-sec',
                 'confluence', 'confluence://SECRET', 'ACTIVE'),
                (CAST(:ds_b AS uuid), CAST(:ws_b AS uuid), 'jira-other',
                 'jira', 'jira://OTHER', 'REFERENCE');
                """
            ),
            {
                "ds_jira": ds_jira,
                "ds_conf": ds_conf,
                "ds_sec": ds_sec,
                "ds_b": ds_b,
                "ws_a": ws_a,
                "ws_b": ws_b,
            },
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_documents (
                    id, doc_key, workspace_id, datasource_id, source_uri,
                    source_scheme, indexing_regime, title, revision_tag,
                    content_sha256, freshness_ttl_days, is_stale
                ) VALUES
                (CAST(:dj AS uuid), 'doc-jira-pay42', CAST(:ws_a AS uuid), CAST(:dsj AS uuid),
                 'jira://PAY-42', 'jira', 'DOC_PARENT_CHILD',
                 'PAY-42 Settlement Rule', 'v3', 'sha-j', 30, FALSE),
                (CAST(:dc AS uuid), 'doc-conf-old', CAST(:ws_a AS uuid), CAST(:dsc AS uuid),
                 'confluence://SPEC-PAY/old-spec', 'confluence', 'DOC_PARENT_CHILD',
                 'Legacy Settlement Spec', 'v1', 'sha-c', 7, TRUE),
                (CAST(:dsec AS uuid), 'doc-conf-secret', CAST(:ws_a AS uuid), CAST(:dssec AS uuid),
                 'confluence://SECRET/payroll', 'confluence', 'DOC_PARENT_CHILD',
                 'Payroll Ledger Secret', 'v1', 'sha-s', 30, FALSE),
                (CAST(:db AS uuid), 'doc-wsb-leak', CAST(:ws_b AS uuid), CAST(:dsb AS uuid),
                 'jira://OTHER-99', 'jira', 'DOC_PARENT_CHILD',
                 'Workspace B Settlement Secret', 'v1', 'sha-b', 30, FALSE);
                """
            ),
            {
                "dj": doc_jira,
                "dc": doc_stale,
                "dsec": doc_sec,
                "db": doc_b,
                "ws_a": ws_a,
                "ws_b": ws_b,
                "dsj": ds_jira,
                "dsc": ds_conf,
                "dssec": ds_sec,
                "dsb": ds_b,
            },
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_chunks (
                    id, chunk_key, document_id, workspace_id, datasource_alias,
                    chunk_role, contextual_header, content_text, token_count, embedding
                ) VALUES
                (CAST(:c1 AS uuid), 'chk-jira-pay42', CAST(:dj AS uuid),
                 CAST(:ws_a AS uuid), 'jira-pay', 'CHILD', '[jira | PAY-42]',
                 'Authoritative payment ledger settlement rule: 7500 EUR threshold.',
                 14, CAST(:vec AS halfvec(1024))),
                (CAST(:c2 AS uuid), 'chk-conf-old', CAST(:dc AS uuid),
                 CAST(:ws_a AS uuid), 'conf-pay', 'CHILD', '[confluence | Old]',
                 'Deprecated payment ledger settlement note from 2024.',
                 12, CAST(:vec AS halfvec(1024))),
                (CAST(:c3 AS uuid), 'chk-conf-secret', CAST(:dsec AS uuid),
                 CAST(:ws_a AS uuid), 'conf-sec', 'CHILD', '[confluence | Secret]',
                 'RESTRICTED_PAYROLL_LEAK settlement salary 999999.',
                 10, CAST(:vec AS halfvec(1024))),
                (CAST(:c4 AS uuid), 'chk-wsb-leak', CAST(:db AS uuid),
                 CAST(:ws_b AS uuid), 'jira-other', 'CHILD', '[jira | OTHER-99]',
                 'WORKSPACE_B_LEAK payment ledger threshold.',
                 10, CAST(:vec AS halfvec(1024)));
                """
            ),
            {
                "c1": new_uuid7_str(),
                "c2": new_uuid7_str(),
                "c3": new_uuid7_str(),
                "c4": new_uuid7_str(),
                "dj": doc_jira,
                "dc": doc_stale,
                "dsec": doc_sec,
                "db": doc_b,
                "ws_a": ws_a,
                "ws_b": ws_b,
                "vec": vec_ledger,
            },
        )

        # 3. Active Blackboard snapshots in ws_a vs ws_b
        wf_def_id = new_uuid7_str()
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions (id, uri, version, sha256) "
                "VALUES (CAST(:id AS uuid), 'orcia://wf/story-26-5@v1', '1.0.0', 'sha-265') "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": wf_def_id},
        )
        wf_def_id = str(
            (
                await conn.execute(
                    sa.text(
                        "SELECT id::text FROM workflow_definitions "
                        "WHERE uri = 'orcia://wf/story-26-5@v1' LIMIT 1"
                    )
                )
            ).scalar_one()
        )
        for rid, sid, snap_id, rkey, skey, ws_id, payload in (
            (
                run_a,
                step_a,
                snap_a,
                "run-265-a",
                "snap-265-a",
                ws_a,
                {"threshold_eur": 7500, "ws": "A"},
            ),
            (
                run_b,
                step_b,
                snap_b,
                "run-265-b",
                "snap-265-b",
                ws_b,
                {"isolated_ws_b_marker": "MUST_NOT_LEAK"},
            ),
        ):
            await conn.execute(
                sa.text(
                    "INSERT INTO workflow_runs (id, run_key, workspace_id, workflow_def_id, "
                    "root_run_id, status, initiated_by_user_id) "
                    "VALUES (CAST(:rid AS uuid), :rkey, CAST(:ws AS uuid), CAST(:wf AS uuid), "
                    "CAST(:rid AS uuid), 'RUNNING', CAST(:uid AS uuid))"
                ),
                {"rid": rid, "rkey": rkey, "ws": ws_id, "wf": wf_def_id, "uid": admin_user_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO step_executions "
                    "(id, step_execution_key, run_id, step_key, step_index, status) "
                    "VALUES (CAST(:sid AS uuid), :skey, CAST(:rid AS uuid), "
                    "'analyze_ledger', 0, 'COMMITTED')"
                ),
                {"sid": sid, "skey": f"step-{skey}", "rid": rid},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO blackboard_snapshots (id, snapshot_key, run_id, "
                    "step_execution_id, step_key, branch_status, artifact_payload_jsonb, "
                    "artifact_cas_key, artifact_sha256) "
                    "VALUES (CAST(:id AS uuid), :skey, CAST(:rid AS uuid), "
                    "CAST(:sid AS uuid), 'analyze_ledger', 'ACTIVE', "
                    "CAST(:pl AS jsonb), :cas, :sha)"
                ),
                {
                    "id": snap_id,
                    "skey": skey,
                    "rid": rid,
                    "sid": sid,
                    "pl": json.dumps(payload),
                    "cas": f"cas/{skey}",
                    "sha": f"sha256_{skey}",
                },
            )
