"""Story 24.3 — Persist governed MCP exposures, PAT hashes, and audit contract.

Revision ID: 20261120_2403
Revises: 20261120_2402
Create Date: 2026-11-20

Pure raw SQL Expand migration (`op.execute(sa.text(...))`), zero ORM imports, UUIDv7 PKs,
zero plaintext PAT secrets, and fully reversible `downgrade()`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_2403"
down_revision: str | Sequence[str] | None = "20261120_2402"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BASE_OUTBOX_EVENT_TYPES: tuple[str, ...] = (
    "StepCompleted",
    "ArtifactProduced",
    "GateEvaluated",
    "RunTerminated",
    "HumanArbitrationRequested",
    "PermissionGranted",
    "PermissionRevoked",
    "AccessRequested",
    "SettingsChanged",
    "DatasourceSyncRequested",
    "DatasourceFreshnessEvaluated",
    "EmbeddingReindexStarted",
    "EmbeddingReindexCompleted",
    "EmbeddingReindexFailed",
    "AdminConnectionTested",
    "BudgetCircuitTripped",
    "BudgetOverrideApproved",
    "RemoteUsageAnomalyCapped",
    "ConnectorCircuitTripped",
    "AutonomousContractSigned",
    "AutonomousContractRevoked",
    "AutonomousEscalated",
    "TriggerFired",
    "SelfTriggerBlocked",
    "TriggerCircuitOpened",
    "WorkflowPublished",
    "PostHocSampleSelected",
    "KillSwitchActivated",
    "AutonomousArtifactRolledBack",
)


def _format_in_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{val}'" for val in values)


def upgrade() -> None:
    """Create `mcp_exposed_agents`, `mcp_governed_pat_tokens`, and allow `ADMIN_CONNECTION_TEST`."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS mcp_exposed_agents (
                id UUID PRIMARY KEY,
                workspace_slug VARCHAR(128) NOT NULL,
                agent_slug VARCHAR(128) NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                mcp_exposed BOOLEAN NOT NULL DEFAULT TRUE,
                regime VARCHAR(64) NOT NULL DEFAULT 'CONSULTATION_ANALYSIS'
                    CHECK (regime IN ('CONSULTATION_ANALYSIS', 'GOVERNED_STAGED_COPILOT')),
                system_prompt_layers_1_to_4 TEXT NOT NULL DEFAULT '',
                secret_refs_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                human_authored_required BOOLEAN NOT NULL DEFAULT FALSE,
                updated_by VARCHAR(128) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_mcp_exposed_agents_ws_agent UNIQUE (workspace_slug, agent_slug)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_mcp_exposed_agents_ws_updated
                ON mcp_exposed_agents (workspace_slug, updated_at DESC, id DESC);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS mcp_governed_pat_tokens (
                id UUID PRIMARY KEY,
                token_sha256 VARCHAR(64) NOT NULL UNIQUE,
                allowed_workspace_slugs_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                revoked_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE domain_events_outbox "
            "DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;"
        )
    )
    expanded_list = _format_in_list((*_BASE_OUTBOX_EVENT_TYPES, "ADMIN_CONNECTION_TEST"))
    op.execute(
        sa.text(
            f"""
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN ({expanded_list}));
            """
        )
    )


def downgrade() -> None:
    """Drop Story 24.3 MCP exposure tables and restore previous outbox CHECK constraint."""
    op.execute(
        sa.text("DELETE FROM domain_events_outbox WHERE event_type = 'ADMIN_CONNECTION_TEST';")
    )
    op.execute(
        sa.text(
            "ALTER TABLE domain_events_outbox "
            "DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;"
        )
    )
    base_list = _format_in_list(_BASE_OUTBOX_EVENT_TYPES)
    op.execute(
        sa.text(
            f"""
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN ({base_list}));
            """
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS mcp_governed_pat_tokens;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mcp_exposed_agents_ws_updated;"))
    op.execute(sa.text("DROP TABLE IF EXISTS mcp_exposed_agents;"))
