"""Story 6.2: FinOps scope budgets, baselines, overrides and paused status expansion.

Revision ID: 20261116_0602
Revises: 20261116_0601
Create Date: 2026-11-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261116_0602"
down_revision: str | Sequence[str] | None = "20261116_0601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Expand workflow_runs.status CHECK constraint to include PAUSED_MAX_RETRIES
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'workflow_runs'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%status%IN%'
                ) LOOP
                    EXECUTE 'ALTER TABLE workflow_runs DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_runs ADD CONSTRAINT ck_workflow_runs_status CHECK (
                status IN (
                    'INITIALIZED',
                    'RUNNING',
                    'WAITING_FOR_HUMAN_ARBITRATION',
                    'WAITING_FOR_HUMAN_GATE',
                    'PAUSED_CIRCUIT_BREAKER',
                    'PAUSED_BUDGET_EXCEEDED',
                    'PAUSED_MAX_RETRIES',
                    'COMPLETED',
                    'FAILED',
                    'ROLLED_BACK'
                )
            );
            """
        )
    )

    # 2. Expand step_executions.status (PAUSED_BUDGET_EXCEEDED & PAUSED_MAX_RETRIES)
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'step_executions'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%status%IN%'
                ) LOOP
                    EXECUTE 'ALTER TABLE step_executions DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE step_executions ADD CONSTRAINT ck_step_executions_status CHECK (
                status IN (
                    'PENDING',
                    'WAITING_FOR_HUMAN_ANCHOR',
                    'EXECUTING_AGENT',
                    'WAITING_FOR_HUMAN_ARBITRATION',
                    'EVALUATING_GATES',
                    'WAITING_FOR_HUMAN_GATE',
                    'COMMITTED',
                    'CHALLENGED_REWIND',
                    'PAUSED_BUDGET_EXCEEDED',
                    'PAUSED_MAX_RETRIES',
                    'FAILED'
                )
            );
            """
        )
    )

    # 3. Create finops_scope_budgets table
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS finops_scope_budgets (
                id UUID PRIMARY KEY,
                scope_type VARCHAR(32) NOT NULL CHECK (
                    scope_type IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE')
                ),
                scope_id UUID NULL,
                monthly_budget_usd NUMERIC(12, 6) NOT NULL CHECK (monthly_budget_usd >= 0),
                warning_threshold_pct INTEGER NOT NULL DEFAULT 80 CHECK (
                    warning_threshold_pct >= 1 AND warning_threshold_pct <= 100
                ),
                hard_stop_pct INTEGER NOT NULL DEFAULT 100 CHECK (
                    hard_stop_pct >= warning_threshold_pct AND hard_stop_pct <= 200
                ),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_finops_scope_budgets_null_safe
                ON finops_scope_budgets (
                    scope_type,
                    (COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid))
                );
            """
        )
    )

    # 4. Create finops_workflow_baselines table
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS finops_workflow_baselines (
                id UUID PRIMARY KEY,
                workflow_definition_id UUID NOT NULL
                    REFERENCES workflow_definitions(id) ON DELETE CASCADE,
                scope_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                manual_time_minutes INTEGER NOT NULL CHECK (manual_time_minutes >= 0),
                manual_cost_usd NUMERIC(12, 6) NOT NULL CHECK (manual_cost_usd >= 0),
                target_ttm_reduction_pct INTEGER NOT NULL DEFAULT 25 CHECK (
                    target_ttm_reduction_pct >= 0 AND target_ttm_reduction_pct <= 100
                ),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_finops_workflow_baselines_null_safe
                ON finops_workflow_baselines (
                    workflow_definition_id,
                    (COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid))
                );
            """
        )
    )

    # 5. Create finops_budget_overrides table
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS finops_budget_overrides (
                id UUID PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                requested_by UUID NOT NULL REFERENCES users(id),
                approved_by UUID NOT NULL REFERENCES users(id),
                override_amount_usd NUMERIC(12, 6) NOT NULL CHECK (override_amount_usd > 0),
                reason TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_finops_budget_overrides_run_created
                ON finops_budget_overrides (run_id, created_at DESC);
            """
        )
    )


def downgrade() -> None:
    # 1. Drop finops tables in reverse order
    op.execute(sa.text("DROP TABLE IF EXISTS finops_budget_overrides;"))
    op.execute(sa.text("DROP TABLE IF EXISTS finops_workflow_baselines;"))
    op.execute(sa.text("DROP TABLE IF EXISTS finops_scope_budgets;"))

    # 2. Restore step_executions CHECK constraint
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'step_executions'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%status%IN%'
                ) LOOP
                    EXECUTE 'ALTER TABLE step_executions DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE step_executions ADD CONSTRAINT ck_step_executions_status CHECK (
                status IN (
                    'PENDING',
                    'WAITING_FOR_HUMAN_ANCHOR',
                    'EXECUTING_AGENT',
                    'WAITING_FOR_HUMAN_ARBITRATION',
                    'EVALUATING_GATES',
                    'WAITING_FOR_HUMAN_GATE',
                    'COMMITTED',
                    'CHALLENGED_REWIND',
                    'FAILED'
                )
            );
            """
        )
    )

    # 3. Restore workflow_runs CHECK constraint
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'workflow_runs'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%status%IN%'
                ) LOOP
                    EXECUTE 'ALTER TABLE workflow_runs DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_runs ADD CONSTRAINT ck_workflow_runs_status CHECK (
                status IN (
                    'INITIALIZED',
                    'RUNNING',
                    'WAITING_FOR_HUMAN_ARBITRATION',
                    'WAITING_FOR_HUMAN_GATE',
                    'PAUSED_CIRCUIT_BREAKER',
                    'PAUSED_BUDGET_EXCEEDED',
                    'COMPLETED',
                    'FAILED',
                    'ROLLED_BACK'
                )
            );
            """
        )
    )
