"""Story 1.3 Federated Multi-Source Catalog, CAS SHA-256, 4-Layer Overrides & BMAD Adapter.

Revision ID: 0003_story_1_3
Revises: 0002_story_1_2
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0003_story_1_3"
down_revision: str | None = "0002_story_1_2"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE catalog_items (
        id UUID PRIMARY KEY,
        resource_id VARCHAR(128) NOT NULL UNIQUE,
        uri TEXT NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        resource_type VARCHAR(32) NOT NULL CHECK (
            resource_type IN ('workflow', 'agent', 'skill', 'template', 'datasource')
        ),
        source_format VARCHAR(32) NOT NULL DEFAULT 'ORCIA' CHECK (
            source_format IN ('ORCIA', 'BMAD_PACK')
        ),
        version VARCHAR(64) NOT NULL,
        sha256 VARCHAR(64) NOT NULL,
        cas_key VARCHAR(128) NOT NULL,
        visibility_scope VARCHAR(32) NOT NULL CHECK (
            visibility_scope IN (
                'DRAFT',
                'SHARED_WORKSPACE',
                'SHARED_TEAM',
                'SHARED_BU',
                'PENDING_APPROVAL',
                'PUBLISHED_ORG'
            )
        ),
        owner_org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE RESTRICT,
        owner_workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_uri ON catalog_items(uri);",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_sha256 ON catalog_items(sha256);",
    (
        "CREATE INDEX IF NOT EXISTS idx_catalog_items_owner_org_unit_id "
        "ON catalog_items(owner_org_unit_id);"
    ),
    """
    CREATE TABLE workflow_definitions (
        id UUID PRIMARY KEY,
        workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        uri TEXT NOT NULL UNIQUE,
        version VARCHAR(64) NOT NULL,
        source_format VARCHAR(32) NOT NULL DEFAULT 'ORCIA' CHECK (
            source_format IN ('ORCIA', 'BMAD_PACK')
        ),
        steps_schema_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        adaptive_gate_policy VARCHAR(32) NOT NULL DEFAULT 'STANDARD' CHECK (
            adaptive_gate_policy IN ('STRICT', 'STANDARD', 'FAST_TRACK')
        ),
        sha256 VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_workflow_definitions_workspace_id "
        "ON workflow_definitions(workspace_id);"
    ),
    ("CREATE INDEX IF NOT EXISTS idx_workflow_definitions_sha256 ON workflow_definitions(sha256);"),
    """
    CREATE TABLE workspace_customization_overrides (
        id UUID PRIMARY KEY,
        override_key VARCHAR(128) NOT NULL UNIQUE,
        org_unit_id UUID NULL REFERENCES org_units(id) ON DELETE CASCADE,
        workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
        target_uri TEXT NOT NULL,
        override_layer VARCHAR(32) NOT NULL CHECK (
            override_layer IN ('TEAM', 'WORKSPACE', 'USER')
        ),
        override_manifest_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        sha256 VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_workspace_customization_overrides_target_uri "
        "ON workspace_customization_overrides(target_uri);"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_workspace_customization_overrides_workspace_id "
        "ON workspace_customization_overrides(workspace_id);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS workspace_customization_overrides;",
    "DROP TABLE IF EXISTS workflow_definitions;",
    "DROP TABLE IF EXISTS catalog_items;",
)


def upgrade() -> None:
    """Create Story 1.3 federated catalog, workflow definitions, and 4-layer overrides tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 1.3 federated catalog, workflow definitions, and 4-layer overrides tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
