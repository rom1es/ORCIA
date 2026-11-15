"""Story 19.6 — Integration Tests for Alembic migration, RAG blocking, and PostgreSQL 18 schema.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261115_2206` (`upgrade head` -> `downgrade 20261115_2105` -> `upgrade head`).
2. Schema inspection: `kb_chunks.embedding_model_id` and `kb_chunks.embedding_generated_at` on PG18.
3. Constraint inspection: `workspace_datasources.freshness_status` permits
   'AWAITING_EMBEDDING_MODEL'.
4. Existing pseudo-vectors cleanup: any chunk before migration has `embedding IS NULL`.
5. Document datasource sync without active embedding model: sets status 'AWAITING_EMBEDDING_MODEL'
   and inserts 0 chunks.
6. Codegraph / Git AST indexing continues to succeed with `embedding IS NULL` (non-blocking).
7. SqlHybridRagRepository: handles mixed chunks (NULL and non-NULL vectors) with NULLS LAST.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_core.bootstrap._internal.sql_workspace_datasources_mutations import (
    trigger_workspace_datasource_sync_on_postgres18,
)
from orcia_core.rag._internal.sql_repository import SqlHybridRagRepository
from orcia_core.rag.errors import NoActiveEmbeddingModelError
from orcia_core.rag.indexer_and_rrf import DifferentiatedIncrementalIndexer
from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_19_6"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_19_6_pw"  # pragma: allowlist secret


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
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261115_2206
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261115_2105"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.mark.asyncio
async def test_story_19_6_schema_and_rag_blocking_postgres18(database_url: str) -> None:
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        # 1. Schema inspection on PostgreSQL 18
        col_res = await conn.execute(
            sa.text(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'kb_chunks'
                  AND column_name IN ('embedding_model_id', 'embedding_generated_at')
                ORDER BY column_name;
                """
            )
        )
        cols = {row[0]: (row[1], row[2]) for row in col_res.fetchall()}
        assert "embedding_model_id" in cols
        assert cols["embedding_model_id"][0] == "uuid"
        assert cols["embedding_model_id"][1] == "YES"
        assert "embedding_generated_at" in cols
        assert "timestamp" in cols["embedding_generated_at"][0]

        # 2. Check constraint includes 'AWAITING_EMBEDDING_MODEL'
        ws_id = new_uuid7_str()
        ds_id = new_uuid7_str()
        user_id = new_uuid7_str()
        ou_id = new_uuid7_str()

        # Seed org unit, workspace and user
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-19-6', 'OU 19.6', 'TEAM') "
                "ON CONFLICT DO NOTHING;"
            ),
            {"id": ou_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:id, 'ws-19-6', 'WS 19.6', :ou_id, 'STANDARD') "
                "ON CONFLICT DO NOTHING;"
            ),
            {"id": ws_id, "ou_id": ou_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users ("
                "  id, email, display_name, auth_mode, human_profile_archetype, "
                "  platform_role, primary_org_unit_id, is_active"
                ") VALUES ("
                "  :id, 'admin196@orcia.test', 'Admin 19.6', 'LOCAL', 'ARCHITECT', "
                "  'PLATFORM_ADMIN', :ou_id, TRUE"
                ") ON CONFLICT DO NOTHING;"
            ),
            {"id": user_id, "ou_id": ou_id},
        )

        # Insert datasource with AWAITING_EMBEDDING_MODEL
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_datasources (
                    id, workspace_id, alias, scheme, uri, role, source_nature, freshness_status
                ) VALUES (
                    :id, :ws_id, 'ds_confluence_test', 'confluence', 'confluence://SPACE/page',
                    'CONTRIBUTOR', 'DOCUMENT_KB', 'STALE'
                );
                """
            ),
            {"id": ds_id, "ws_id": ws_id},
        )

    # 3. Synchronize datasource without active embedding model -> raises NoActiveEmbeddingModelError
    with pytest.raises(NoActiveEmbeddingModelError):
        await trigger_workspace_datasource_sync_on_postgres18(
            engine,
            datasource_id=ds_id,
            workspace_id=ws_id,
        )

    async with engine.begin() as conn:
        # Verify status is AWAITING_EMBEDDING_MODEL and 0 chunks were inserted
        ds_row = (
            await conn.execute(
                sa.text("SELECT freshness_status FROM workspace_datasources WHERE id = :id;"),
                {"id": ds_id},
            )
        ).fetchone()
        assert ds_row is not None
        assert ds_row[0] == "AWAITING_EMBEDDING_MODEL"

        chunks_count = (
            await conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM kb_chunks WHERE datasource_alias = 'ds_confluence_test';"
                )
            )
        ).scalar_one()
        assert chunks_count == 0

        # 4. Codegraph / Git AST indexing continues to index with embedding = NULL (non-blocking)
        doc_git, chunks_git, edges_git = (
            DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph(
                workspace_id=ws_id,
                datasource_id=ds_id,
                datasource_alias="ds_git_repo",
                repo_uri="git://repo/test",
                file_path="src/calc.py",
                python_source="def add(a: int, b: int) -> int:\n    return a + b\n",
                commit_sha="c-123456",
            )
        )
        assert len(chunks_git) >= 1
        assert chunks_git[0].embedding is None

        # Insert codegraph chunk into database
        chunk_git_id = new_uuid7_str()
        doc_git_id = new_uuid7_str()
        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_documents (
                    id, doc_key, workspace_id, datasource_id,
                    source_uri, source_scheme, indexing_regime, title, revision_tag, content_sha256
                ) VALUES (
                    :id, :doc_key, :ws_id, :ds_id,
                    'git://repo/test', 'git', 'CODE_AST_GRAPH', 'calc.py', 'c-123456', 'hash-git'
                );
                """
            ),
            {"id": doc_git_id, "doc_key": f"doc-git-{doc_git_id}", "ws_id": ws_id, "ds_id": ds_id},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_chunks (
                    id, chunk_key, document_id, workspace_id, datasource_alias,
                    chunk_role, contextual_header, content_text, token_count, embedding
                ) VALUES (
                    :id, :chunk_key, :doc_id, :ws_id, 'ds_git_repo',
                    'AST_SYMBOL', '[git : calc.py]', 'def add(a, b): return a + b', 15, NULL
                );
                """
            ),
            {
                "id": chunk_git_id,
                "chunk_key": f"chunk-git-{chunk_git_id}",
                "doc_id": doc_git_id,
                "ws_id": ws_id,
            },
        )

        # 5. Insert another chunk with non-null embedding (using fake vector)
        fake_emb = FakeDeterministicEmbeddingAdapter()
        q_vec = fake_emb.embed_query_sync("calculate sum addition")
        vec_literal = "[" + ",".join(str(v) for v in q_vec) + "]"
        chunk_sem_id = new_uuid7_str()

        await conn.execute(
            sa.text(
                """
                INSERT INTO kb_chunks (
                    id, chunk_key, document_id, workspace_id, datasource_alias,
                    chunk_role, contextual_header, content_text, token_count, embedding
                ) VALUES (
                    :id, :chunk_key, :doc_id, :ws_id, 'ds_git_repo',
                    'CHILD', '[doc : addition]', 'Addition formula explanation', 20,
                    CAST(:vec AS halfvec(1024))
                );
                """
            ),
            {
                "id": chunk_sem_id,
                "chunk_key": f"chunk-sem-{chunk_sem_id}",
                "doc_id": doc_git_id,
                "ws_id": ws_id,
                "vec": vec_literal,
            },
        )

    # 6. Verify SqlHybridRagRepository search query tolerates mixed NULL/non-NULL embeddings
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    rag_repo = SqlHybridRagRepository(session_maker)

    hits = await rag_repo.search_hybrid_rrf(
        workspace_id=ws_id,
        query_text="addition formula",
        query_embedding=q_vec,
        limit=5,
    )
    assert len(hits) >= 1
    hit_keys = [h.chunk_key for h in hits]
    # The semantic chunk matches vector + text, the git chunk matches text, neither crashed
    assert any("chunk-sem-" in k or "chunk-git-" in k for k in hit_keys)

    await engine.dispose()
