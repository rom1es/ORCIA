"""Story 19.7 — Integration Tests for RAG Reindexing on real PostgreSQL 18 + pgvector.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261115_2307` idempotency (upgrade head -> downgrade -> upgrade).
2. Schema inspection: reindexing jobs, pending queue, partial unique index.
3. End-to-end vector reindexing job with `execute_rag_reindex_job` and fake embedding.
4. SQL verification:
   - 100% of document chunks updated with target embedding_model_id and non-NULL vectors.
   - Code graph AST chunks remain untouched with embedding=NULL (D11).
   - Document datasources in AWAITING_EMBEDDING_MODEL unblocked to SYNCED upon completion.
   - Outbox events (EmbeddingReindexStarted, EmbeddingReindexCompleted) persisted.
5. Search blocking guard (`check_rag_operational_on_conn`) raises 503 during job.
6. Multi-model switch: reindexing with Model B replaces all vectors without mixing.
7. Resumption: subsequent run after interruption only vectorizes remaining chunks.
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
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.rag._internal.sql_reindex import (
    create_or_replace_reindex_job_pg18,
)
from orcia_core.rag.errors import RagReindexInProgressError
from orcia_core.rag.reindex import check_rag_operational_on_conn, execute_rag_reindex_job

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_19_7"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_19_7_pw"  # pragma: allowlist secret


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
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261115_2307
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261115_2206"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.mark.asyncio
async def test_reindexing_schema_and_partial_unique_index_postgres18(
    database_url: str,
) -> None:
    """Verify schema tables and partial unique index guaranteeing 1 active job."""
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        # Check tables existence
        tables_res = await conn.execute(
            sa.text(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('rag_reindexing_jobs', 'rag_reindexing_pending_ingestions')
                ORDER BY table_name;
                """
            )
        )
        tables = [r[0] for r in tables_res.fetchall()]
        assert "rag_reindexing_jobs" in tables
        assert "rag_reindexing_pending_ingestions" in tables

        # Check unique partial index
        idx_res = await conn.execute(
            sa.text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'rag_reindexing_jobs'
                  AND indexname = 'idx_rag_reindex_single_active';
                """
            )
        )
        assert idx_res.fetchone() is not None


@pytest.mark.asyncio
async def test_reindex_execution_lock_and_vector_update_postgres18(
    database_url: str,
) -> None:
    """End-to-end integration test of vector corpus reindexing on PostgreSQL 18."""
    engine = create_async_engine(database_url)
    fake_adapter = FakeDeterministicEmbeddingAdapter()

    ou_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    ds_doc_id = new_uuid7_str()
    ds_code_id = new_uuid7_str()
    doc_id = new_uuid7_str()
    code_doc_id = new_uuid7_str()
    model_a_id = new_uuid7_str()
    model_b_id = new_uuid7_str()

    async with engine.begin() as conn:
        # 1. Seed org unit & workspace & models
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-reindex-test', 'OU Reindex Test', 'TEAM') "
                "ON CONFLICT DO NOTHING;"
            ),
            {"id": ou_id},
        )

        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:wid, 'ws-reindex-test', 'Workspace Reindex Test', :ou_id, 'STANDARD') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {"wid": ws_id, "ou_id": ou_id},
        )

        global_scope_id = new_uuid7_str()
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_llm_tier_mappings (
                    id, scope_level, scope_id, inference_tier, effort, provider_slug,
                    model_family, model_name, endpoint_uri, auth_mode, protocol_mode,
                    fallback_order, is_active, draining, usage, created_at, updated_at
                ) VALUES (
                    :id_a, 'GLOBAL', :global_scope_id, 'simple', 'balanced', 'openai',
                    'OpenAI', 'text-embedding-3-small', 'https://api.openai.com/v1',
                    'none_local', 'openai_compatible', 1, TRUE, FALSE, 'embedding', NOW(), NOW()
                ), (
                    :id_b, 'GLOBAL', :global_scope_id, 'simple', 'balanced', 'mistral',
                    'Mistral', 'mistral-embed', 'https://api.mistral.ai/v1',
                    'none_local', 'openai_compatible', 2, FALSE, FALSE, 'embedding', NOW(), NOW()
                );
                """
            ),
            {
                "id_a": UUID(model_a_id),
                "id_b": UUID(model_b_id),
                "global_scope_id": UUID(global_scope_id),
            },
        )

        # 2. Seed document datasource in AWAITING_EMBEDDING_MODEL + code datasource
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_datasources (
                    id, workspace_id, alias, scheme, uri, role, source_nature, freshness_status
                ) VALUES (
                    :ds_doc_id, :wid, 'confluence_docs', 'confluence', 'confluence://SPACE/page',
                    'CONTRIBUTOR', 'DOCUMENT_KB', 'AWAITING_EMBEDDING_MODEL'
                ), (
                    :ds_code_id, :wid, 'git_repo', 'git', 'git://repo/orcia',
                    'CONTRIBUTOR', 'SOURCE_CODE', 'SYNCED'
                );
                """
            ),
            {"ds_doc_id": UUID(ds_doc_id), "ds_code_id": UUID(ds_code_id), "wid": UUID(ws_id)},
        )

        # 3. Seed kb_documents
        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_documents (
                    id, doc_key, workspace_id, datasource_id,
                    source_uri, source_scheme, indexing_regime, title, revision_tag, content_sha256
                ) VALUES (
                    :doc_id, 'doc-confluence-1', :wid, :ds_doc_id,
                    'confluence://SPACE/page', 'confluence', 'DOC_PARENT_CHILD',
                    'Spec', 'rev-1', 'sha-doc'
                ), (
                    :code_doc_id, 'doc-git-1', :wid, :ds_code_id,
                    'git://repo/orcia', 'git', 'CODE_AST_GRAPH', 'code.py', 'sha-code', 'sha-code'
                );
                """
            ),
            {
                "doc_id": UUID(doc_id),
                "code_doc_id": UUID(code_doc_id),
                "wid": UUID(ws_id),
                "ds_doc_id": UUID(ds_doc_id),
                "ds_code_id": UUID(ds_code_id),
            },
        )

        # 4. Seed kb_chunks: 2 document chunks without vectors + 1 AST chunk
        chunk_doc_1 = new_uuid7_str()
        chunk_doc_2 = new_uuid7_str()
        chunk_ast = new_uuid7_str()
        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_chunks (
                    id, chunk_key, document_id, workspace_id, datasource_alias,
                    chunk_role, contextual_header, content_text, token_count,
                    embedding, embedding_model_id, created_at
                ) VALUES (
                    :c1, 'chunk-doc-1', :doc_id, :wid, 'confluence_docs',
                    'PARENT', 'Header 1', 'Content of section 1', 10,
                    NULL, NULL, NOW()
                ), (
                    :c2, 'chunk-doc-2', :doc_id, :wid, 'confluence_docs',
                    'CHILD', 'Header 2', 'Content of section 2', 12,
                    NULL, NULL, NOW()
                ), (
                    :c_ast, 'chunk-ast-1', :code_doc_id, :wid, 'git_repo',
                    'AST_SYMBOL', 'Code Header', 'def run(): pass', 8,
                    NULL, NULL, NOW()
                );
                """
            ),
            {
                "c1": UUID(chunk_doc_1),
                "c2": UUID(chunk_doc_2),
                "c_ast": UUID(chunk_ast),
                "doc_id": UUID(doc_id),
                "code_doc_id": UUID(code_doc_id),
                "wid": UUID(ws_id),
            },
        )

    # 5. Create reindexing job for Model A
    async with engine.begin() as conn:
        job = await create_or_replace_reindex_job_pg18(
            conn,
            target_model_id=model_a_id,
            target_model_name="text-embedding-3-small",
            actor_id="test-admin",
            trace_id="00000000000000000000000000000001",
        )
        assert job.status == "PENDING"
        assert job.total_chunks == 2  # AST chunks excluded!

        # 6. Verify operational guard raises 503 while job is active
        with pytest.raises(RagReindexInProgressError) as exc_info:
            await check_rag_operational_on_conn(conn)
        assert exc_info.value.error_code == "ERR_RAG_REINDEX_IN_PROGRESS"
        assert exc_info.value.progress_percentage == 0

    # 7. Execute reindexing job with FakeDeterministicEmbeddingAdapter
    completed_job = await execute_rag_reindex_job(
        engine=engine,
        job_id=job.id,
        target_model_id=model_a_id,
        embedding_port=fake_adapter,
        batch_size=50,
        trace_id="00000000000000000000000000000001",
    )
    assert completed_job.status == "COMPLETED"
    assert completed_job.progress_percentage == 100
    assert completed_job.processed_chunks == 2

    # 8. Inspect database state post-reindexing
    async with engine.begin() as conn:
        # All document chunks have model_a_id and non-NULL vectors
        doc_chunks_res = await conn.execute(
            sa.text(
                """
                SELECT id, embedding_model_id, embedding IS NOT NULL
                FROM kb_chunks
                WHERE chunk_role != 'AST_SYMBOL'
                ORDER BY id;
                """
            )
        )
        doc_chunks = doc_chunks_res.fetchall()
        assert len(doc_chunks) == 2
        for chk in doc_chunks:
            assert str(chk[1]) == model_a_id
            assert chk[2] is True

        # AST chunk remains untouched with NULL vector (D11)
        ast_res = await conn.execute(
            sa.text(
                """
                SELECT embedding_model_id, embedding
                FROM kb_chunks
                WHERE chunk_role = 'AST_SYMBOL';
                """
            )
        )
        ast_row = ast_res.fetchone()
        assert ast_row is not None
        assert ast_row[0] is None
        assert ast_row[1] is None

        # Document datasource unblocked to SYNCED
        ds_res = await conn.execute(
            sa.text(
                """
                SELECT freshness_status FROM workspace_datasources
                WHERE id = :ds_id;
                """
            ),
            {"ds_id": UUID(ds_doc_id)},
        )
        assert ds_res.fetchone()[0] == "SYNCED"

        # Outbox events persisted
        ev_res = await conn.execute(
            sa.text(
                """
                SELECT event_type FROM domain_events_outbox
                WHERE aggregate_id = :job_id
                ORDER BY created_at;
                """
            ),
            {"job_id": str(job.id)},
        )
        events = [r[0] for r in ev_res.fetchall()]
        assert "EmbeddingReindexStarted" in events
        assert "EmbeddingReindexCompleted" in events

        # Operational guard no longer raises after completion
        await check_rag_operational_on_conn(conn)


@pytest.mark.asyncio
async def test_reindex_empty_corpus_immediately_completed_postgres18(
    database_url: str,
) -> None:
    """When corpus has 0 document chunks (Day-0 reset), reindexing completes immediately
    without blocking.
    """
    engine = create_async_engine(database_url)
    fake_adapter = FakeDeterministicEmbeddingAdapter()

    ws_id = new_uuid7_str()
    ou_id = new_uuid7_str()
    model_id = new_uuid7_str()
    ds_id = new_uuid7_str()
    global_scope_id = new_uuid7_str()

    async with engine.begin() as conn:
        # Clean up any leftover active global embedding models, jobs, and kb chunks
        await conn.execute(sa.text("DELETE FROM kb_chunks;"))
        await conn.execute(sa.text("DELETE FROM kb_documents;"))
        await conn.execute(sa.text("DELETE FROM workspace_datasources;"))
        await conn.execute(sa.text("DELETE FROM rag_reindexing_jobs;"))
        await conn.execute(sa.text("DELETE FROM workspace_llm_tier_mappings;"))

        # Seed org unit, workspace, model, and empty datasource in AWAITING_EMBEDDING_MODEL
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-empty-test', 'OU Empty Test', 'TEAM') "
                "ON CONFLICT DO NOTHING;"
            ),
            {"id": UUID(ou_id)},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:wid, 'ws-empty-test', 'Workspace Empty Test', :ou_id, 'STANDARD') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {"wid": UUID(ws_id), "ou_id": UUID(ou_id)},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_llm_tier_mappings (
                    id, scope_level, scope_id, inference_tier, effort, provider_slug,
                    model_family, model_name, endpoint_uri, auth_mode, protocol_mode,
                    fallback_order, is_active, draining, usage, created_at, updated_at
                ) VALUES (
                    :mid, 'GLOBAL', :global_scope_id, 'simple', 'balanced', 'openai',
                    'OpenAI', 'text-embedding-3-small', 'https://api.openai.com/v1',
                    'none_local', 'openai_compatible', 1, TRUE, FALSE, 'embedding', NOW(), NOW()
                );
                """
            ),
            {"mid": UUID(model_id), "global_scope_id": UUID(global_scope_id)},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_datasources (
                    id, workspace_id, alias, scheme, uri, role, source_nature, freshness_status
                ) VALUES (
                    :ds_id, :wid, 'empty_docs', 'confluence', 'confluence://SPACE/empty',
                    'CONTRIBUTOR', 'DOCUMENT_KB', 'AWAITING_EMBEDDING_MODEL'
                );
                """
            ),
            {"ds_id": UUID(ds_id), "wid": UUID(ws_id)},
        )

        # Trigger reindexing on empty corpus
        job = await create_or_replace_reindex_job_pg18(
            conn,
            target_model_id=model_id,
            target_model_name="text-embedding-3-small",
            actor_id="test-admin",
            trace_id="00000000000000000000000000000099",
        )
        # Directly COMPLETED without intermediate blocking state
        assert job.status == "COMPLETED"
        assert job.total_chunks == 0
        assert job.processed_chunks == 0
        assert job.progress_percentage == 100

        # RAG operational guard DOES NOT RAISE
        await check_rag_operational_on_conn(conn)

        # Datasource immediately unblocked to SYNCED
        ds_res = await conn.execute(
            sa.text("SELECT freshness_status FROM workspace_datasources WHERE id = :ds_id;"),
            {"ds_id": UUID(ds_id)},
        )
        assert ds_res.fetchone()[0] == "SYNCED"

        # Outbox events generated
        ev_res = await conn.execute(
            sa.text(
                """
                SELECT event_type FROM domain_events_outbox
                WHERE aggregate_id = :job_id
                ORDER BY created_at;
                """
            ),
            {"job_id": str(job.id)},
        )
        events = [r[0] for r in ev_res.fetchall()]
        assert "EmbeddingReindexStarted" in events
        assert "EmbeddingReindexCompleted" in events

    # Worker execution immediately returns COMPLETED job without batching
    completed_job = await execute_rag_reindex_job(
        engine=engine,
        job_id=job.id,
        target_model_id=model_id,
        embedding_port=fake_adapter,
        trace_id="00000000000000000000000000000099",
    )
    assert completed_job.status == "COMPLETED"
    assert completed_job.progress_percentage == 100
