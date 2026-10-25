"""Story 2.3 Multi-Source Incremental Indexing (`halfvec(1024)` + BM25) & Code Graph.

Revision ID: 0008_story_2_3
Revises: 0007_story_2_2
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0008_story_2_3"
down_revision: str | None = "0007_story_2_2"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE kb_documents (
        id UUID PRIMARY KEY,
        doc_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        datasource_id UUID NOT NULL REFERENCES workspace_datasources(id) ON DELETE CASCADE,
        source_uri TEXT NOT NULL,
        source_scheme VARCHAR(32) NOT NULL CHECK (
            source_scheme IN ('confluence', 'jira', 'git', 'db')
        ),
        indexing_regime VARCHAR(32) NOT NULL CHECK (
            indexing_regime IN ('DOC_PARENT_CHILD', 'CODE_AST_GRAPH', 'DB_DDL_ONLY')
        ),
        title VARCHAR(255) NOT NULL,
        revision_tag VARCHAR(128) NOT NULL,
        content_sha256 VARCHAR(64) NOT NULL,
        freshness_ttl_days INTEGER NOT NULL DEFAULT 90,
        last_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        is_stale BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_kb_documents_workspace_datasource "
        "ON kb_documents(workspace_id, datasource_id);"
    ),
    """
    CREATE TABLE kb_chunks (
        id UUID PRIMARY KEY,
        chunk_key VARCHAR(128) NOT NULL UNIQUE,
        document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        datasource_alias VARCHAR(128) NOT NULL,
        parent_chunk_id UUID NULL REFERENCES kb_chunks(id) ON DELETE CASCADE,
        chunk_role VARCHAR(32) NOT NULL CHECK (
            chunk_role IN ('PARENT', 'CHILD', 'UNIFIED_JIRA', 'AST_SYMBOL', 'DDL_SCHEMA')
        ),
        contextual_header TEXT NOT NULL,
        content_text TEXT NOT NULL,
        token_count INTEGER NOT NULL CHECK (token_count > 0),
        embedding halfvec(1024) NULL,
        search_tsv TSVECTOR GENERATED ALWAYS AS (
            to_tsvector(
                'simple',
                coalesce(contextual_header, '') || ' ' || coalesce(content_text, '')
            )
        ) STORED,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_hnsw "
        "ON kb_chunks USING hnsw (embedding halfvec_cosine_ops);"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_kb_chunks_search_tsv_gin "
        "ON kb_chunks USING gin (search_tsv);"
    ),
    """
    CREATE TABLE code_graph_edges (
        id UUID PRIMARY KEY,
        edge_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        source_repo_uri TEXT NOT NULL,
        source_symbol VARCHAR(255) NOT NULL,
        target_repo_uri TEXT NOT NULL,
        target_symbol VARCHAR(255) NOT NULL,
        edge_type VARCHAR(32) NOT NULL CHECK (
            edge_type IN ('DEFINES', 'CALLS', 'IMPORTS', 'IMPLEMENTS_CONCEPT', 'TESTED_BY')
        ),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_code_graph_edges_workspace_symbol "
        "ON code_graph_edges(workspace_id, source_symbol);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS code_graph_edges;",
    "DROP TABLE IF EXISTS kb_chunks;",
    "DROP TABLE IF EXISTS kb_documents;",
)


def upgrade() -> None:
    """Create Story 2.3 kb_documents, kb_chunks (halfvec(1024) + BM25), and code_graph_edges."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 2.3 Hybrid RAG & Code Graph tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
