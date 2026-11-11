"""PostgreSQL 18 `AsyncSession` store for `workflow_definitions_v2` (`Story 16.3`, `CAP-160`).

Persists edited and drafted `WorkflowDefinitionV2` definitions (including `orchestration_type`,
`reflexive_objective`, and `allowed_delegate_agents`) in `workflow_definitions_v2` so Studio
configurations survive browser reloads (`F5`) and API process restarts.
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2

logger = get_logger("orcia.workflows.sql_workflows_v2")


class SqlWorkflowDefinitionsV2Store:
    """PostgreSQL 18 repository (`AsyncSession`) for `workflow_definitions_v2`."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        *,
        strict_sql: bool = False,
    ) -> None:
        self._session_maker = session_maker
        self._strict_sql = strict_sql
        self._memory_fallback: dict[str, dict[str, Any]] = {}

    async def upsert_workflow(self, workflow: WorkflowDefinitionV2) -> WorkflowDefinitionV2:
        """Persist `workflow` idempotently keyed by `(workflow_id, version)`."""
        spec_payload = workflow.model_dump(mode="json")
        key = f"{workflow.id}:{workflow.version}"
        self._memory_fallback[key] = spec_payload
        if self._session_maker is None:
            return workflow

        stmt = sa.text(
            """
            INSERT INTO workflow_definitions_v2 (
                id,
                workflow_id,
                slug,
                version,
                status,
                pack_id,
                execution_mode,
                spec_jsonb,
                updated_at
            )
            VALUES (
                CAST(:id AS UUID),
                :workflow_id,
                :slug,
                :version,
                :status,
                :pack_id,
                :execution_mode,
                CAST(:spec_jsonb AS JSONB),
                NOW()
            )
            ON CONFLICT (workflow_id, version) DO UPDATE SET
                slug = EXCLUDED.slug,
                status = EXCLUDED.status,
                pack_id = EXCLUDED.pack_id,
                execution_mode = EXCLUDED.execution_mode,
                spec_jsonb = EXCLUDED.spec_jsonb,
                updated_at = NOW()
            """
        )
        try:
            async with self._session_maker() as session:
                await session.execute(
                    stmt,
                    {
                        "id": new_uuid7_str(),
                        "workflow_id": workflow.id,
                        "slug": workflow.slug,
                        "version": workflow.version,
                        "status": str(workflow.status),
                        "pack_id": workflow.pack_id,
                        "execution_mode": str(workflow.execution_mode),
                        "spec_jsonb": json.dumps(spec_payload, ensure_ascii=False),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "workflow_v2_sql_upsert_degraded",
                workflow_id=workflow.id,
                version=workflow.version,
                error_type=type(exc).__name__,
            )
            if self._strict_sql:
                raise
        return workflow

    async def list_persisted_workflows(self) -> list[WorkflowDefinitionV2]:
        """Load all persisted `WorkflowDefinitionV2` specs ordered by `updated_at` ascending."""
        if self._session_maker is not None:
            stmt = sa.text(
                """
                SELECT spec_jsonb
                FROM workflow_definitions_v2
                ORDER BY updated_at ASC
                """
            )
            try:
                async with self._session_maker() as session:
                    rows = (await session.execute(stmt)).fetchall()
                results: list[WorkflowDefinitionV2] = []
                for row in rows:
                    raw = row[0]
                    data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                    results.append(WorkflowDefinitionV2.model_validate(data))
                return results
            except Exception as exc:
                logger.warning(
                    "workflow_v2_sql_list_degraded",
                    error_type=type(exc).__name__,
                )
                if self._strict_sql:
                    raise

        return [
            WorkflowDefinitionV2.model_validate(item) for item in self._memory_fallback.values()
        ]
