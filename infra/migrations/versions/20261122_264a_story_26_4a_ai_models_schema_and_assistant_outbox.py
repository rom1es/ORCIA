"""Story 26.4a — Migrate runtime AI model DDL to Alembic and add assistant outbox events.

Revision ID: 20261122_264a
Revises: 20261120_2403
Create Date: 2026-11-22

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261122_264a"
down_revision: str | Sequence[str] | None = "20261120_2403"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREVIOUS_OUTBOX_EVENT_TYPES: tuple[str, ...] = (
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
    "ADMIN_CONNECTION_TEST",
)

_ASSISTANT_OUTBOX_EVENT_TYPES: tuple[str, ...] = (
    "AssistantTurnStarted",
    "AssistantTurnCompleted",
    "AssistantTurnStopped",
    "AssistantTurnFailed",
)


def _format_in_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{val}'" for val in values)


def upgrade() -> None:
    """Consolidate `workspace_llm_tier_mappings` indexes/columns and expand outbox event types."""
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                ADD COLUMN IF NOT EXISTS display_name VARCHAR(160) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS fallback_model_name VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS endpoint_uri TEXT NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS auth_mode VARCHAR(32) NOT NULL DEFAULT 'api_key',
                ADD COLUMN IF NOT EXISTS protocol_mode VARCHAR(32)
                    NOT NULL DEFAULT 'openai_compatible',
                ADD COLUMN IF NOT EXISTS env_var_name VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT NULL,
                ADD COLUMN IF NOT EXISTS secret_fingerprint VARCHAR(64) NULL,
                ADD COLUMN IF NOT EXISTS secret_masked_hint VARCHAR(32) NULL,
                ADD COLUMN IF NOT EXISTS secret_updated_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS secret_updated_by VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS health_status VARCHAR(32) NOT NULL DEFAULT 'UNTESTED',
                ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS last_latency_ms INTEGER NULL,
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS usage VARCHAR(32) NOT NULL DEFAULT 'chat';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_llm_tier_mappings_scope_tier_active
                ON workspace_llm_tier_mappings (scope_level, inference_tier, is_active);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_tier_mappings_single_active_global_embedding
                ON workspace_llm_tier_mappings (scope_level, usage)
                WHERE (usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL');
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_llm_tier_mappings_active_chat_lookup
                ON workspace_llm_tier_mappings (
                    scope_level, scope_id, inference_tier, fallback_order, created_at
                )
                WHERE (usage = 'chat' AND is_active = TRUE AND draining = FALSE);
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE domain_events_outbox "
            "DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;"
        )
    )
    expanded_list = _format_in_list((*_PREVIOUS_OUTBOX_EVENT_TYPES, *_ASSISTANT_OUTBOX_EVENT_TYPES))
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
    """Drop Story 26.4a chat lookup index and restore previous outbox CHECK constraint."""
    deleted_list = _format_in_list(_ASSISTANT_OUTBOX_EVENT_TYPES)
    op.execute(sa.text(f"DELETE FROM domain_events_outbox WHERE event_type IN ({deleted_list});"))
    op.execute(
        sa.text(
            "ALTER TABLE domain_events_outbox "
            "DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;"
        )
    )
    prev_list = _format_in_list(_PREVIOUS_OUTBOX_EVENT_TYPES)
    op.execute(
        sa.text(
            f"""
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN ({prev_list}));
            """
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_llm_tier_mappings_active_chat_lookup;"))
