"""Layer 2 integration tests for Story 24.2 on real PG18 + Redis via `create_app()`."""

from __future__ import annotations

import importlib.util
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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from orcia_core.rag.models import (
    CodeGraphEdgeEntity,
    KbChunkEntity,
    KbDocumentEntity,
    KbStaleAlertEntity,
    TripartiteTraceEdgeEntity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_story_24_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_24_2_pw"  # pragma: allowlist secret


def _run_alembic(pg_url: str, *args: str) -> None:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PostgreSQL 18 + pgvector and Redis 7.4 containers."""
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
        yield pg_url, redis_url


@pytest.mark.asyncio
async def test_alembic_24_2_upgrade_downgrade_roundtrip(infra_urls: tuple[str, str]) -> None:
    """Verify `20261120_2402` upgrade -> downgrade (`20261120_2401`) -> upgrade `head`."""
    pg_url, _ = infra_urls
    _run_alembic(pg_url, "upgrade", "20261120_2402")

    engine = create_async_engine(pg_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            dna_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.workspace_dna_mechanisms')"))
            ).scalar_one()
            dna_idx = (
                await conn.execute(
                    sa.text(
                        "SELECT 1 FROM pg_indexes WHERE tablename = 'workspace_dna_mechanisms' "
                        "AND indexname = 'ix_workspace_dna_mechanisms_ws_updated'"
                    )
                )
            ).scalar_one_or_none()
        assert dna_tbl == "workspace_dna_mechanisms"
        assert dna_idx == 1

        _run_alembic(pg_url, "downgrade", "20261120_2401")
        async with engine.connect() as conn:
            dna_after_down = (
                await conn.execute(sa.text("SELECT to_regclass('public.workspace_dna_mechanisms')"))
            ).scalar_one()
        assert dna_after_down is None

        _run_alembic(pg_url, "upgrade", "head")
        async with engine.connect() as conn:
            dna_head = (
                await conn.execute(sa.text("SELECT to_regclass('public.workspace_dna_mechanisms')"))
            ).scalar_one()
        assert dna_head == "workspace_dna_mechanisms"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_real_composition_root_triggers_dna_waivers_cold_pg18_and_reset(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify triggers UUIDv7, 409 duplicate key, Starlark DNA, waivers, cold PG18 & Day-0 reset."""
    pg_url, redis_url = infra_urls
    _run_alembic(pg_url, "upgrade", "head")

    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-24-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-24-2-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    engine = create_async_engine(pg_url, poolclass=NullPool)
    try:
        app1 = create_app()
        assert app1.dependency_overrides == {}

        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as client1,
        ):
            r_first = await client1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.242@orcia.ia",
                    "display_name": "Admin Story 24.2",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}

            r_ws = await client1.post(
                "/api/v1/workspaces",
                headers=auth_headers,
                json={
                    "name": "Espace Story 24.2",
                    "slug": "espace-story-24-2",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]
            UUID(ws_id)

            # 1. Service Principal + Autonomy Contract -> Sequential LOG_SINK_ALERT triggers
            r_sp = await client1.post(
                "/api/v1/settings/iam/accounts",
                headers=auth_headers,
                json={
                    "principal_id": "sp-242-logsink",
                    "display_name": "Robot 24.2",
                    "account_kind": "SERVICE_PRINCIPAL",
                    "roles": ["TEAM_LEAD"],
                    "team_ids": [ws_id],
                },
            )
            assert r_sp.status_code in (200, 201), r_sp.text
            sp_id = r_sp.json()["id"]

            r_contract = await client1.post(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/autonomy-contract",
                headers=auth_headers,
                json={
                    "workflow_version": "1.0.0",
                    "criticality": "STANDARD",
                    "service_principal_id": sp_id,
                },
            )
            assert r_contract.status_code == 201, r_contract.text

            generated_keys: list[str] = []
            for idx in range(5):
                r_trig = await client1.post(
                    f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
                    headers=auth_headers,
                    json={
                        "trigger_type": "LOG_SINK_ALERT",
                        "log_sink_service": f"orcia-svc-{idx}",
                        "log_sink_query_text": "level:ERROR",
                    },
                )
                assert r_trig.status_code == 201, r_trig.text
                generated_keys.append(r_trig.json()["trigger_key"])

            assert len(set(generated_keys)) == 5
            assert all(k.startswith("trg-log_sink_alert-") for k in generated_keys)

            # Explicit trigger_key works once, then returns 409 RFC 9457 ERR_TRIGGER_DUPLICATE_KEY
            r_custom = await client1.post(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
                headers=auth_headers,
                json={
                    "trigger_type": "LOG_SINK_ALERT",
                    "trigger_key": "custom-alert-24-2",
                    "log_sink_service": "orcia-api",
                },
            )
            assert r_custom.status_code == 201, r_custom.text
            assert r_custom.json()["trigger_key"] == "custom-alert-24-2"

            r_dup = await client1.post(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
                headers=auth_headers,
                json={
                    "trigger_type": "LOG_SINK_ALERT",
                    "trigger_key": "custom-alert-24-2",
                    "log_sink_service": "orcia-api",
                },
            )
            assert r_dup.status_code == 409, r_dup.text
            assert r_dup.json()["error_code"] == "ERR_TRIGGER_DUPLICATE_KEY"

            # 1b. Platform alert ingress deduplicates via `trigger_webhook_deliveries` in PG18
            alert_secret = "orcia-24-2-alert-secret"  # pragma: allowlist secret
            r_alert_trg = await client1.post(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
                headers=auth_headers,
                json={
                    "trigger_type": "LOG_SINK_ALERT",
                    "trigger_key": "alert-delivery-pg18-24-2",
                    "log_sink_service": "orcia-worker",
                    "log_sink_query_text": "level:ERROR",
                    "cooldown_window_seconds": 0,
                    "webhook_secret": {"action": "set", "plaintext_value": alert_secret},
                },
            )
            assert r_alert_trg.status_code == 201, r_alert_trg.text
            alert_trg_id = r_alert_trg.json()["id"]
            alert_body = {
                "trigger_id": alert_trg_id,
                "service": "orcia-worker",
                "exception_type": "TimeoutError",
                "message": "Gateway timeout 504",
                "traceback": "File worker.py, line 10, in run\nTimeoutError",
            }
            r_alert_1 = await client1.post(
                "/api/v1/triggers/alerts",
                headers={"x-orcia-alert-secret": alert_secret},
                json=alert_body,
            )
            assert r_alert_1.status_code == 200, r_alert_1.text
            assert r_alert_1.json()["outcome"] == "DISPATCHED"

            r_alert_2 = await client1.post(
                "/api/v1/triggers/alerts",
                headers={"x-orcia-alert-secret": alert_secret},
                json=alert_body,
            )
            assert r_alert_2.status_code == 200, r_alert_2.text
            assert r_alert_2.json()["outcome"] == "DUPLICATE_SUPPRESSED"

            # 2. Starlark DNA compile -> activate -> list -> evaluate
            r_compile = await client1.post(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms/compile",
                headers=auth_headers,
                json={
                    "rule_id": "RULE_24_2_REF",
                    "directive_title": "Orientation Qualité 24.2",
                    "norm_title": "Règle Référence 24.2",
                    "natural_language_rule_fr": "Le champ reference_code doit être renseigné.",
                    "required_field": "reference_code",
                    "simulate_initial_bad_regex": True,
                },
            )
            assert r_compile.status_code == 200, r_compile.text
            mech_id = r_compile.json()["mechanism_id"]
            assert r_compile.json()["self_corrected"] is True

            r_activate = await client1.post(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms/{mech_id}/activate",
                headers=auth_headers,
                json={},
            )
            assert r_activate.status_code == 200, r_activate.text
            assert r_activate.json()["signed_and_active"] is True

            r_list_mechs = await client1.get(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms",
                headers=auth_headers,
            )
            assert r_list_mechs.status_code == 200, r_list_mechs.text
            assert any(m["mechanism_id"] == mech_id for m in r_list_mechs.json())

            r_eval = await client1.post(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms/{mech_id}/evaluate",
                headers=auth_headers,
                json={"payload": {"reference_code": "ORCIA_24_2"}},
            )
            assert r_eval.status_code == 200, r_eval.text
            assert r_eval.json()["passed"] is True
            assert r_eval.json()["llm_tokens_consumed"] == 0

            # 3. Exception waivers + five-tabs dynamic slug resolution
            r_waiver = await client1.post(
                f"/api/v1/workspaces/{ws_id}/exception-waivers",
                headers=auth_headers,
                json={
                    "source_uri": "orcia://workspaces/espace-story-24-2/artifacts",
                    "source_sha256": "sha256:workspace-source-baseline-2402",
                    "conflict_rule_id": "RULE_FRESHNESS_DRIFT",
                    "norm_level": "3_WORKSPACE",
                    "dna_chain": [],
                    "reason": "Dérogation Story 24.2 persistée PG18",
                    "ttl_days": 30,
                },
            )
            assert r_waiver.status_code == 200, r_waiver.text
            waiver_id = r_waiver.json()["waiver_id"]

            r_tabs = await client1.get(
                f"/api/v1/workspaces/{ws_id}/five-tabs",
                headers=auth_headers,
            )
            assert r_tabs.status_code == 200, r_tabs.text
            assert r_tabs.json()["workspace_slug"] == "espace-story-24-2"
            assert any(w["waiver_id"] == waiver_id for w in r_tabs.json()["active_waivers"])

            # 4. Source sync (`AD-24.7` NULL vecs) + RAG index-db-ddl & tripartite audit -> PG18
            r_ds1 = await client1.post(
                f"/api/v1/workspaces/{ws_id}/datasources",
                headers=auth_headers,
                json={
                    "alias": "pg-schema-242",
                    "scheme": "git",
                    "uri": "https://git.local/app.git",
                    "service_account_id": sp_id,
                    "source_nature": "SOURCE_CODE",
                    "sync_mode": "POLLING_24H",
                    "target_scope": "main",
                    "target_ref": "refs/heads/main",
                },
            )
            assert r_ds1.status_code == 201, r_ds1.text
            ds1_id = r_ds1.json()["id"]

            r_sync1 = await client1.post(
                f"/api/v1/workspaces/{ws_id}/datasources/{ds1_id}/sync",
                headers=auth_headers,
            )
            assert r_sync1.status_code == 200, r_sync1.text

            r_emb = await client1.post(
                "/api/v1/settings/ai-models/mappings",
                headers=auth_headers,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": "0192c4e0-0000-7000-8000-000000000001",
                    "display_name": "Ollama BGE-M3",
                    "inference_tier": "simple",
                    "provider_slug": "ollama",
                    "model_family": "BGE",
                    "model_name": "bge-m3:latest",
                    "endpoint_uri": "http://127.0.0.1:11434/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "embedding",
                },
            )
            assert r_emb.status_code == 201, r_emb.text

            r_ddl = await client1.post(
                "/api/v1/ontology-rag/rag/index-db-ddl",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "datasource_id": ds1_id,
                    "datasource_alias": "pg-schema-242",
                    "db_uri": "postgresql://db.local/app",
                    "ddl_sql": "CREATE TABLE claims (id UUID PRIMARY KEY, amount NUMERIC);",
                    "schema_version": "v1",
                    "ontology_concepts": ["Sinistre"],
                },
            )
            assert r_ddl.status_code == 200, r_ddl.text
            ddl_doc_key = r_ddl.json()["doc_key"]

            r_audit_trip = await client1.post(
                "/api/v1/ontology-rag/tripartite/audit-doc-vs-code",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "confluence_uri": "confluence://SPACE/CLAIMS-SPEC",
                    "git_repo_uri": "https://git.local/claims.git",
                    "git_symbol": "main",
                    "doc_rule_summary": "Seuil validation sinistre PAY-242",
                    "code_rule_summary": "Validation PAY-242",
                    "newer_done_jira_key": "PAY-242",
                },
            )
            assert r_audit_trip.status_code == 200, r_audit_trip.text

            # 5. Evict in-memory caches and verify direct SELECT in PG18
            r_evict = await client1.post("/api/v1/_e2e/evict-memory-caches", headers=auth_headers)
            assert r_evict.status_code == 200, r_evict.text

            async with engine.connect() as conn:
                trig_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM workflow_triggers "
                            "WHERE workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"ws": ws_id},
                    )
                ).scalar_one()
                assert trig_count == 7

                alert_deliv_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM trigger_webhook_deliveries "
                            "WHERE trigger_id = CAST(:tid AS uuid)"
                        ),
                        {"tid": alert_trg_id},
                    )
                ).scalar_one()
                assert alert_deliv_count == 1

                sync_doc_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, indexing_regime FROM kb_documents "
                            "WHERE workspace_id = CAST(:ws AS uuid) AND id = CAST(:dsid AS uuid)"
                        ),
                        {"ws": ws_id, "dsid": ds1_id},
                    )
                ).one()
                assert sync_doc_row[1] == "CODE_AST_GRAPH"

                # AD-24.7: datasource sync without embedding writes NULL embedding vectors
                sync_chunk_null = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*), COUNT(embedding), COUNT(embedding_model_id) "
                            "FROM kb_chunks WHERE document_id = CAST(:did AS uuid)"
                        ),
                        {"did": sync_doc_row[0]},
                    )
                ).one()
                assert sync_chunk_null[0] >= 1
                assert sync_chunk_null[1] == 0
                assert sync_chunk_null[2] == 0

                ddl_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, indexing_regime FROM kb_documents "
                            "WHERE workspace_id = CAST(:ws AS uuid) AND doc_key = :dk"
                        ),
                        {"ws": ws_id, "dk": ddl_doc_key},
                    )
                ).one()
                assert ddl_row[1] == "DB_DDL_ONLY"

                ddl_chunk_cnt = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM kb_chunks WHERE document_id = CAST(:did AS uuid)"
                        ),
                        {"did": ddl_row[0]},
                    )
                ).scalar_one()
                assert ddl_chunk_cnt >= 1

                trip_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM tripartite_trace_edges "
                            "WHERE workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"ws": ws_id},
                    )
                ).scalar_one()
                assert trip_count >= 1

                dna_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT rule_id, signed_and_active FROM workspace_dna_mechanisms "
                            "WHERE id = CAST(:mid AS uuid) AND workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"mid": mech_id, "ws": ws_id},
                    )
                ).one()
                assert dna_row[0] == "RULE_24_2_REF"
                assert dna_row[1] is True

                waiver_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT conflict_rule_id, status FROM workspace_exception_waivers "
                            "WHERE waiver_id = CAST(:wid AS uuid) "
                            "AND workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"wid": waiver_id, "ws": ws_id},
                    )
                ).one()
                assert waiver_row[0] == "RULE_FRESHNESS_DRIFT"
                assert waiver_row[1] == "ACTIVE"

        # 5. Second cold Composition Root reads everything from PG18
        app2 = create_app()
        assert app2.dependency_overrides == {}
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            # Evaluate FIRST on cold app2 -> exercises `repo.get_mechanism()` against PG18
            r_eval_cold = await client2.post(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms/{mech_id}/evaluate",
                headers=auth_headers,
                json={"payload": {"reference_code": "COLD_OK"}},
            )
            assert r_eval_cold.status_code == 200, r_eval_cold.text
            assert r_eval_cold.json()["passed"] is True

            r_mechs_cold = await client2.get(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms",
                headers=auth_headers,
            )
            assert r_mechs_cold.status_code == 200, r_mechs_cold.text
            assert any(
                m["mechanism_id"] == mech_id and m["signed_and_active"] is True
                for m in r_mechs_cold.json()
            )

            r_activate_missing = await client2.post(
                f"/api/v1/workspaces/{ws_id}/dna-mechanisms/0195f000-0000-7000-8000-999999999999/activate",
                headers=auth_headers,
                json={},
            )
            assert r_activate_missing.status_code == 404

            r_waivers_cold = await client2.get(
                f"/api/v1/workspaces/{ws_id}/exception-waivers",
                headers=auth_headers,
                params={"active_only": "true"},
            )
            assert r_waivers_cold.status_code == 200, r_waivers_cold.text
            assert any(w["waiver_id"] == waiver_id for w in r_waivers_cold.json())

            r_trigs_cold = await client2.get(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
                headers=auth_headers,
            )
            assert r_trigs_cold.status_code == 200, r_trigs_cold.text
            assert len(r_trigs_cold.json()["items"]) == 7

            # Verify direct SQL writes (`sql_rag_writes` & `sql_tripartite_writes`) + `/state` PG18
            from orcia_core.rag._internal.sql_rag_writes import upsert_kb_document_bundle_pg
            from orcia_core.rag._internal.sql_tripartite_writes import (
                upsert_kb_stale_alert_pg,
                upsert_tripartite_edges_pg,
            )

            sm = async_sessionmaker(engine, expire_on_commit=False)
            assert (
                await upsert_kb_document_bundle_pg(
                    sm,
                    document=KbDocumentEntity(
                        id="0195f242-0000-7000-8000-000000000499",
                        doc_key="doc-missing-ws",
                        workspace_id="0195f242-0000-7000-8000-999999999998",
                        datasource_id="0195f242-0000-7000-8000-999999999997",
                        datasource_alias="missing",
                        source_uri="confluence://missing",
                        source_scheme="confluence",
                        indexing_regime="DOC_PARENT_CHILD",
                        title="Missing WS",
                        revision_tag="v1",
                        content_sha256="b" * 64,
                        freshness_ttl_days=30,
                        is_stale=False,
                    ),
                )
                is None
            )

            saved_bundle = await upsert_kb_document_bundle_pg(
                sm,
                document=KbDocumentEntity(
                    id="0195f242-0000-7000-8000-000000000402",
                    doc_key="doc-24-2",
                    workspace_id=ws_id,
                    datasource_id="",
                    datasource_alias="auto-source-242",
                    source_uri="confluence://SPACE/SPEC-24-2",
                    source_scheme="confluence",
                    indexing_regime="DOC_PARENT_CHILD",
                    title="Spec 24.2",
                    revision_tag="v1",
                    content_sha256="a" * 64,
                    freshness_ttl_days=30,
                    is_stale=True,
                ),
                chunks=(
                    KbChunkEntity(
                        id="0195f242-0000-7000-8000-000000000412",
                        chunk_key="chunk-24-2-parent",
                        document_id="0195f242-0000-7000-8000-000000000402",
                        workspace_id=ws_id,
                        datasource_alias="auto-source-242",
                        parent_chunk_id=None,
                        chunk_role="PARENT",
                        contextual_header="[Spec 24.2]",
                        content_text="Contenu parent",
                        token_count=12,
                        embedding=None,
                    ),
                ),
                code_edges=(
                    CodeGraphEdgeEntity(
                        id="0195f242-0000-7000-8000-000000000422",
                        edge_key="cg-edge-24-2",
                        workspace_id=ws_id,
                        source_repo_uri="https://git.local/repo.git",
                        source_symbol="fn_a",
                        target_repo_uri="https://git.local/repo.git",
                        target_symbol="fn_b",
                        edge_type="CALLS",
                    ),
                ),
            )
            assert saved_bundle is not None

            await upsert_tripartite_edges_pg(
                sm,
                edges=(
                    TripartiteTraceEdgeEntity(
                        id="0195f242-0000-7000-8000-000000000403",
                        edge_key="edge-24-2",
                        workspace_id=ws_id,
                        source_uri="git://claims/core-engine#fn",
                        source_node_type="GIT_SYMBOL",
                        target_uri="jira://issues/ORCIA-242",
                        target_node_type="JIRA_ISSUE",
                        relation_type="IMPLEMENTS_ISSUE",
                        jira_issue_key="ORCIA-242",
                    ),
                ),
            )
            await upsert_kb_stale_alert_pg(
                sm,
                alert=KbStaleAlertEntity(
                    id="0195f242-0000-7000-8000-000000000404",
                    alert_key="alert-24-2",
                    workspace_id=ws_id,
                    document_key="doc-24-2",
                    source_uri="confluence://SPACE/SPEC-24-2",
                    alert_reason="NEWER_JIRA_CONTRADICTION",
                    diagnostic_marker="[STALE_WARNING]",
                    justifying_jira_key="ORCIA-242",
                    impacted_run_ids=("run-242",),
                    resolved=False,
                ),
            )

            r_rag_state = await client2.get(
                "/api/v1/ontology-rag/state",
                headers=auth_headers,
                params={"fixture": "false", "workspace_id": ws_id},
            )
            assert r_rag_state.status_code == 200, r_rag_state.text
            rag_payload = r_rag_state.json()
            assert any(d["doc_key"] == "doc-24-2" for d in rag_payload["documents"])
            assert any(d["doc_key"] == ddl_doc_key for d in rag_payload["documents"])
            assert any(e["edge_key"] == "edge-24-2" for e in rag_payload["tripartite_edges"])
            assert any(a["alert_key"] == "alert-24-2" for a in rag_payload["stale_alerts"])

        # 6. Day-0 reset script purges workspace_dna_mechanisms, waivers & workflow_triggers
        reset_script = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
        spec = importlib.util.spec_from_file_location("orcia_test_09_reset_24_2", reset_script)
        assert spec is not None and spec.loader is not None
        reset_mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reset_mod
        spec.loader.exec_module(reset_mod)
        report = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True
        assert report.remaining_users_count == 0

        async with engine.connect() as conn:
            dna_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workspace_dna_mechanisms"))
            ).scalar_one()
            waivers_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workspace_exception_waivers"))
            ).scalar_one()
            triggers_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_triggers"))
            ).scalar_one()
        assert dna_after == 0
        assert waivers_after == 0
        assert triggers_after == 0
    finally:
        await engine.dispose()
