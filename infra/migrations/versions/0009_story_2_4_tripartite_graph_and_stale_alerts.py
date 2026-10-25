"""Story 2.4 Multi-Source Tripartite Graph (`Confluence <-> Jira <-> Git`) & `[STALE_WARNING]`.

Revision ID: 0009_story_2_4
Revises: 0008_story_2_3
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0009_story_2_4"
down_revision: str | None = "0008_story_2_3"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE tripartite_trace_edges (
        id UUID PRIMARY KEY,
        edge_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        source_uri TEXT NOT NULL,
        source_node_type VARCHAR(32) NOT NULL CHECK (
            source_node_type IN (
                'CONFLUENCE_PAGE', 'JIRA_ISSUE', 'GIT_SYMBOL', 'GIT_COMMIT', 'ONTOLOGY_CONCEPT'
            )
        ),
        target_uri TEXT NOT NULL,
        target_node_type VARCHAR(32) NOT NULL CHECK (
            target_node_type IN (
                'CONFLUENCE_PAGE', 'JIRA_ISSUE', 'GIT_SYMBOL', 'GIT_COMMIT', 'ONTOLOGY_CONCEPT'
            )
        ),
        relation_type VARCHAR(32) NOT NULL CHECK (
            relation_type IN (
                'DOCUMENTS', 'SPECIFIES', 'FIXES', 'BLOCKS', 'IMPLEMENTS_ISSUE', 'AFFECTS_CONCEPT'
            )
        ),
        jira_issue_key VARCHAR(64) NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_tripartite_trace_edges_workspace_jira "
        "ON tripartite_trace_edges(workspace_id, jira_issue_key);"
    ),
    """
    CREATE TABLE kb_stale_alerts (
        id UUID PRIMARY KEY,
        alert_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
        alert_reason VARCHAR(64) NOT NULL CHECK (
            alert_reason IN ('TTL_EXPIRED', 'NEWER_JIRA_CONTRADICTION', 'CODE_DRIFT_DETECTED')
        ),
        diagnostic_marker VARCHAR(64) NOT NULL DEFAULT '[STALE_WARNING]',
        justifying_jira_key VARCHAR(64) NULL,
        impacted_run_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
        resolved BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_kb_stale_alerts_workspace_resolved "
        "ON kb_stale_alerts(workspace_id, resolved);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS kb_stale_alerts;",
    "DROP TABLE IF EXISTS tripartite_trace_edges;",
)


def upgrade() -> None:
    """Create Story 2.4 tripartite_trace_edges and kb_stale_alerts tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 2.4 tripartite_trace_edges and kb_stale_alerts tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
