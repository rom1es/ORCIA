"""Story 6.4: Remote connector quotas, multi-metric telemetry and isolated circuit breakers.

Revision ID: 20261116_0604
Revises: 20261116_0602
Create Date: 2026-11-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261116_0604"
down_revision: str | Sequence[str] | None = "20261116_0602"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS finops_connector_quotas (
                id UUID PRIMARY KEY,
                connector_key VARCHAR(128) NOT NULL UNIQUE,
                display_name VARCHAR(160) NOT NULL DEFAULT '',
                service_kind VARCHAR(32) NOT NULL DEFAULT 'MCP_SERVER',
                scope_type VARCHAR(32) NOT NULL DEFAULT 'GLOBAL' CHECK (
                    scope_type IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE')
                ),
                scope_id UUID NULL,
                valuation_mode VARCHAR(32) NOT NULL DEFAULT 'NATIVE_TELEMETRY' CHECK (
                    valuation_mode IN ('NATIVE_TELEMETRY', 'FIXED_SCALE', 'VOLUMETRIC_ONLY')
                ),
                max_reported_cost_per_call_eur NUMERIC(12, 6) NOT NULL DEFAULT 5.000000 CHECK (
                    max_reported_cost_per_call_eur >= 0
                ),
                fixed_cost_per_call_eur NUMERIC(12, 6) NOT NULL DEFAULT 0.000000 CHECK (
                    fixed_cost_per_call_eur >= 0
                ),
                unit_tariff_eur NUMERIC(12, 6) NOT NULL DEFAULT 0.000000 CHECK (
                    unit_tariff_eur >= 0
                ),
                default_unit_name VARCHAR(64) NULL,
                max_daily_calls INTEGER NULL CHECK (
                    max_daily_calls IS NULL OR max_daily_calls >= 0
                ),
                max_monthly_cost_eur NUMERIC(12, 6) NULL CHECK (
                    max_monthly_cost_eur IS NULL OR max_monthly_cost_eur >= 0
                ),
                daily_calls_count INTEGER NOT NULL DEFAULT 0 CHECK (daily_calls_count >= 0),
                daily_calls_window_date DATE NOT NULL DEFAULT CURRENT_DATE,
                monthly_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000 CHECK (
                    monthly_cost_usd >= 0
                ),
                total_remote_tokens BIGINT NOT NULL DEFAULT 0 CHECK (total_remote_tokens >= 0),
                total_business_units NUMERIC(18, 6) NOT NULL DEFAULT 0.000000 CHECK (
                    total_business_units >= 0
                ),
                circuit_state VARCHAR(32) NOT NULL DEFAULT 'CLOSED' CHECK (
                    circuit_state IN ('CLOSED', 'CIRCUIT_OPEN', 'HALF_OPEN')
                ),
                anomaly_count INTEGER NOT NULL DEFAULT 0 CHECK (anomaly_count >= 0),
                consecutive_anomalies INTEGER NOT NULL DEFAULT 0 CHECK (
                    consecutive_anomalies >= 0
                ),
                last_latency_ms INTEGER NOT NULL DEFAULT 0 CHECK (last_latency_ms >= 0),
                last_tripped_reason TEXT NULL,
                last_tripped_at TIMESTAMPTZ NULL,
                last_invoked_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_finops_connector_quotas_scope
                ON finops_connector_quotas (scope_type, scope_id);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_finops_connector_quotas_circuit
                ON finops_connector_quotas (circuit_state);
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_finops_connector_quotas_circuit;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_finops_connector_quotas_scope;"))
    op.execute(sa.text("DROP TABLE IF EXISTS finops_connector_quotas;"))
