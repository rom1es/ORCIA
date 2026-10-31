"""Story 10.2: Expand `domain_events_outbox_event_type_check` with `SettingsChanged` & RBAC events.

Revision ID: 0024_story_10_2
Revises: 0023_story_9_5
Create Date: 2026-10-31 17:30:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_story_10_2"
down_revision: str | None = "0023_story_9_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Expand `domain_events_outbox_event_type_check` with `SettingsChanged` and RBAC events."""
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN (
                    'StepCompleted',
                    'ArtifactProduced',
                    'GateEvaluated',
                    'RunTerminated',
                    'HumanArbitrationRequested',
                    'PermissionGranted',
                    'PermissionRevoked',
                    'AccessRequested',
                    'SettingsChanged'
                ));
            """
        )
    )


def downgrade() -> None:
    """Restore initial 5-event `domain_events_outbox_event_type_check` constraint."""
    op.execute(
        sa.text(
            """
            DELETE FROM domain_events_outbox
            WHERE event_type NOT IN (
                'StepCompleted',
                'ArtifactProduced',
                'GateEvaluated',
                'RunTerminated',
                'HumanArbitrationRequested'
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN (
                    'StepCompleted',
                    'ArtifactProduced',
                    'GateEvaluated',
                    'RunTerminated',
                    'HumanArbitrationRequested'
                ));
            """
        )
    )
