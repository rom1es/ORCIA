"""PostgreSQL 18 real-time entity counts for Day-0 Accostage (`REM-21`)."""

from __future__ import annotations

from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True, slots=True)
class AccostagePg18Counts:
    """Authoritative Day-0 accostage entity counts read from PostgreSQL 18."""

    users_count: int
    org_units_count: int
    workspaces_count: int
    models_count: int
    sources_count: int
    workflows_count: int = 0

    @property
    def admin_created(self) -> bool:
        """Return True when at least one active user exists in PostgreSQL 18."""
        return self.users_count > 0


async def get_accostage_pg18_counts(engine: AsyncEngine) -> AccostagePg18Counts:
    """Query PostgreSQL 18 for real Accostage entity counts across all 6 milestones."""
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT
                        (SELECT COUNT(*)::int FROM users WHERE is_active = TRUE) AS users_count,
                        (
                            SELECT COUNT(*)::int
                            FROM org_units
                            WHERE unit_type <> 'ENTERPRISE'
                        ) AS org_units_count,
                        (SELECT COUNT(*)::int FROM workspaces) AS workspaces_count,
                        GREATEST(
                            (
                                SELECT COUNT(*)::int
                                FROM llm_model_endpoints
                                WHERE is_active = TRUE
                            ),
                            (
                                SELECT COUNT(*)::int
                                FROM workspace_llm_tier_mappings
                                WHERE is_active = TRUE
                            )
                        ) AS models_count,
                        (SELECT COUNT(*)::int FROM workspace_datasources) AS sources_count,
                        GREATEST(
                            (SELECT COUNT(*)::int FROM workflow_definitions_v2),
                            (SELECT COUNT(*)::int FROM workflow_runs)
                        ) AS workflows_count
                    """
                )
            )
        ).first()
        if row is None:
            return AccostagePg18Counts(0, 0, 0, 0, 0, 0)
        return AccostagePg18Counts(
            users_count=int(row[0] or 0),
            org_units_count=int(row[1] or 0),
            workspaces_count=int(row[2] or 0),
            models_count=int(row[3] or 0),
            sources_count=int(row[4] or 0),
            workflows_count=int(row[5] or 0) if len(row) > 5 else 0,
        )
