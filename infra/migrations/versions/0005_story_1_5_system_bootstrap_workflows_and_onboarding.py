"""Story 1.5 Governed Day-0 System Bootstrap Workflows & Autonomous Team/Workspace Onboarding.

Revision ID: 0005_story_1_5
Revises: 0004_story_1_4
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005_story_1_5"
down_revision: str | None = "0004_story_1_4"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE llm_model_endpoints (
        id UUID PRIMARY KEY,
        endpoint_key VARCHAR(128) NOT NULL UNIQUE,
        provider_slug VARCHAR(64) NOT NULL,
        model_family VARCHAR(64) NOT NULL,
        model_name VARCHAR(128) NOT NULL,
        endpoint_uri TEXT NOT NULL,
        connectivity_verified BOOLEAN NOT NULL DEFAULT FALSE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_llm_model_endpoints_family "
        "ON llm_model_endpoints(model_family);"
    ),
    """
    CREATE TABLE system_bootstrap_runs (
        id UUID PRIMARY KEY,
        run_key VARCHAR(128) NOT NULL UNIQUE,
        workflow_uri VARCHAR(128) NOT NULL CHECK (
            workflow_uri LIKE 'orcia://system/bootstrap/%'
        ),
        scope_level VARCHAR(32) NOT NULL CHECK (
            scope_level IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE')
        ),
        target_org_unit_id UUID NULL REFERENCES org_units(id) ON DELETE SET NULL,
        target_workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE SET NULL,
        triggered_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status VARCHAR(32) NOT NULL CHECK (
            status IN ('COMPLETED', 'BLOCKED_BY_GATE', 'FAILED')
        ),
        gate_passed BOOLEAN NOT NULL DEFAULT FALSE,
        gate_report_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        execution_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_system_bootstrap_runs_workflow_uri "
        "ON system_bootstrap_runs(workflow_uri);"
    ),
    """
    CREATE TABLE user_onboarding_states (
        id UUID PRIMARY KEY,
        user_email VARCHAR(255) NOT NULL UNIQUE,
        user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        invited_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE CASCADE,
        human_profile_archetype VARCHAR(64) NOT NULL,
        assigned_role VARCHAR(64) NOT NULL,
        workspace_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
        init_user_completed BOOLEAN NOT NULL DEFAULT FALSE,
        linked_connectors_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_user_onboarding_states_org_unit "
        "ON user_onboarding_states(org_unit_id);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS user_onboarding_states;",
    "DROP TABLE IF EXISTS system_bootstrap_runs;",
    "DROP TABLE IF EXISTS llm_model_endpoints;",
)


def upgrade() -> None:
    """Create Story 1.5 LLM model endpoints, bootstrap runs, and user onboarding state tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 1.5 LLM model endpoints, bootstrap runs, and user onboarding state tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
