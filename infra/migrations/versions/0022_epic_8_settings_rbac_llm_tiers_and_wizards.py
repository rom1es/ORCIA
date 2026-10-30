"""Epic 8: RBAC 6 verbs, LLM cognitive tiers, platform_settings & wizard_sessions (`AD-21`).

Revision ID: 0022_epic_8
Revises: 0021_story_5_1
Create Date: 2026-10-30 14:35:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_epic_8"
down_revision: str | None = "0021_story_5_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `role_permission_grants`, `workspace_llm_tier_mappings`, `inference_attempts`,
    `platform_settings`, and `wizard_sessions` tables (`Stories 8.1..8.6`, `AD-21`).
    """
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS role_permission_grants (
                id UUID PRIMARY KEY,
                subject_type VARCHAR(32) NOT NULL
                    CHECK (subject_type IN ('USER', 'ROLE', 'SERVICE_PRINCIPAL')),
                subject_id VARCHAR(128) NOT NULL,
                scope_path VARCHAR(512) NOT NULL,
                verb VARCHAR(32) NOT NULL
                    CHECK (verb IN ('create', 'read', 'update', 'delete', 'execute', 'grant')),
                effect VARCHAR(16) NOT NULL DEFAULT 'ALLOW'
                    CHECK (effect IN ('ALLOW', 'DENY')),
                inheritance_block BOOLEAN NOT NULL DEFAULT FALSE,
                conditions_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                hidden_when_unauthorized BOOLEAN NOT NULL DEFAULT FALSE,
                granted_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (subject_type, subject_id, scope_path, verb, effect)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_role_permission_grants_lookup
                ON role_permission_grants (subject_type, subject_id, scope_path, verb);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS workspace_llm_tier_mappings (
                id UUID PRIMARY KEY,
                scope_level VARCHAR(32) NOT NULL DEFAULT 'WORKSPACE'
                    CHECK (scope_level IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE')),
                scope_id UUID NOT NULL,
                inference_tier VARCHAR(32) NOT NULL
                    CHECK (inference_tier IN ('simple', 'medium', 'complex', 'auto')),
                effort VARCHAR(32) NOT NULL DEFAULT 'default'
                    CHECK (effort IN ('default', 'fast', 'balanced', 'deep')),
                provider_slug VARCHAR(64) NOT NULL,
                model_family VARCHAR(64) NOT NULL,
                model_name VARCHAR(128) NOT NULL,
                secret_ref UUID NULL,
                inference_params_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                max_tokens_budget INTEGER NOT NULL DEFAULT 8192 CHECK (max_tokens_budget > 0),
                max_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 10.000000 CHECK (max_cost_usd >= 0),
                fallback_order INTEGER NOT NULL DEFAULT 1 CHECK (fallback_order >= 1),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                draining BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (scope_id, inference_tier, effort, fallback_order)
            );
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS inference_attempts (
                id UUID PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_execution_id UUID NOT NULL REFERENCES step_executions(id) ON DELETE CASCADE,
                attempt_index INTEGER NOT NULL CHECK (attempt_index >= 1),
                requested_tier VARCHAR(32) NOT NULL
                    CHECK (requested_tier IN ('simple', 'medium', 'complex', 'auto')),
                resolved_tier VARCHAR(32) NOT NULL
                    CHECK (resolved_tier IN ('simple', 'medium', 'complex')),
                effort VARCHAR(32) NOT NULL DEFAULT 'default'
                    CHECK (effort IN ('default', 'fast', 'balanced', 'deep')),
                model_family VARCHAR(64) NOT NULL,
                model_name VARCHAR(128) NOT NULL,
                deterministic_gate_passed BOOLEAN NOT NULL DEFAULT TRUE,
                failure_reason TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
                idempotency_key VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_inference_attempts_run_step
                ON inference_attempts (run_id, step_execution_id, attempt_index);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS platform_settings (
                id UUID PRIMARY KEY,
                scope_level VARCHAR(32) NOT NULL
                    CHECK (scope_level IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE')),
                scope_id UUID NOT NULL,
                category VARCHAR(64) NOT NULL
                    CHECK (category IN (
                        'iam', 'connectors', 'ai-models', 'packs', 'workflows', 'audit'
                    )),
                key VARCHAR(128) NOT NULL,
                value_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                secret_ref UUID NULL,
                secret_fingerprint VARCHAR(64) NULL,
                version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
                etag VARCHAR(64) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_by VARCHAR(128) NOT NULL DEFAULT 'system',
                UNIQUE (scope_level, scope_id, category, key)
            );
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS wizard_sessions (
                id UUID PRIMARY KEY,
                wizard_type VARCHAR(64) NOT NULL
                    CHECK (wizard_type IN ('sdlc_tech_lead', 'ops_manager', 'secops_admin')),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                scope_id UUID NOT NULL,
                current_step_index INTEGER NOT NULL DEFAULT 1
                    CHECK (current_step_index BETWEEN 1 AND 5),
                state_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                dbos_workflow_id VARCHAR(255) NOT NULL UNIQUE,
                status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS'
                    CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'ABANDONED')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )


def downgrade() -> None:
    """Drop Epic 8 tables in reverse dependency order."""
    op.execute(sa.text("DROP TABLE IF EXISTS wizard_sessions;"))
    op.execute(sa.text("DROP TABLE IF EXISTS platform_settings;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_inference_attempts_run_step;"))
    op.execute(sa.text("DROP TABLE IF EXISTS inference_attempts;"))
    op.execute(sa.text("DROP TABLE IF EXISTS workspace_llm_tier_mappings;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_role_permission_grants_lookup;"))
    op.execute(sa.text("DROP TABLE IF EXISTS role_permission_grants;"))
