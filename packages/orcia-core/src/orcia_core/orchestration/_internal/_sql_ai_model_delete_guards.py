"""PostgreSQL 18 delete-impact and active-run pin guards for AI Model Mappings (`AD-21` §5)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._internal.sql_ai_model_queries import (
    get_ai_model_mapping_pg18,
)
from orcia_core.orchestration.ai_models_errors import LastTierModelInUseError
from orcia_core.orchestration.ai_models_records import (
    AiModelDeleteImpact,
    AiModelMappingRecord,
    PinRemovalMode,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourcePinnedByActiveRunsError,
)

logger = get_logger("orcia.core.orchestration.ai_model_delete_guards")

ACTIVE_WORKFLOW_RUN_STATUSES: tuple[str, ...] = (
    "INITIALIZED",
    "RUNNING",
    "WAITING_FOR_HUMAN_ARBITRATION",
    "WAITING_FOR_HUMAN_GATE",
    "WAITING_FOR_HUMAN_ANCHOR",
    "WAITING_FOR_PERMISSION",
    "PAUSED",
    "PAUSED_CIRCUIT_BREAKER",
    "PAUSED_BUDGET_EXCEEDED",
    "PAUSED_MAX_RETRIES",
    "PAUSED_AUTONOMOUS_ESCALATION",
)


async def evaluate_ai_model_delete_impact_pg18(
    conn: AsyncConnection, mapping_id: str, *, instance: str | None = None
) -> AiModelDeleteImpact:
    """Analyze active-run pinning impact before deleting or draining an AI model mapping."""
    current = await get_ai_model_mapping_pg18(conn, mapping_id, instance=instance)

    count_res = await conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM workspace_llm_tier_mappings
            WHERE id != :id AND inference_tier = :tier
              AND is_active = TRUE AND draining = FALSE
            """
        ),
        {"id": mapping_id, "tier": current.inference_tier},
    )
    other_active_count = int(count_res.scalar_one_or_none() or 0)
    is_last_for_tier = other_active_count == 0

    active_run_ids: list[str] = []
    dependent_wf_ids: list[str] = []
    status_placeholders = ", ".join(f"'{st}'" for st in ACTIVE_WORKFLOW_RUN_STATUSES)
    try:
        async with conn.begin_nested():
            run_res = await conn.execute(
                sa.text(
                    f"""
                    SELECT DISTINCT
                        wr.id::text AS run_id,
                        wr.workflow_def_id::text AS wf_def_id
                    FROM workflow_runs wr
                    JOIN inference_attempts ia ON ia.run_id = wr.id
                    WHERE wr.status IN ({status_placeholders})
                      AND (
                          ia.model_name = :model_name
                          OR (
                              :is_last
                              AND (ia.requested_tier = :tier OR ia.resolved_tier = :tier)
                          )
                      )
                    """
                ),
                {
                    "model_name": current.model_name,
                    "tier": current.inference_tier,
                    "is_last": is_last_for_tier,
                },
            )
            seen_runs: set[str] = set()
            seen_wfs: set[str] = set()
            for row in run_res.fetchall():
                run_id = str(row[0])
                wf_def_id = str(row[1]) if row[1] is not None else ""
                if run_id not in seen_runs:
                    seen_runs.add(run_id)
                    active_run_ids.append(run_id)
                if is_last_for_tier and wf_def_id and wf_def_id not in seen_wfs:
                    seen_wfs.add(wf_def_id)
                    dependent_wf_ids.append(wf_def_id)
    except Exception as exc:
        logger.warning(
            "ai_model_delete_impact.active_runs_lookup_failed",
            mapping_id=mapping_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        active_run_ids = []
        dependent_wf_ids = []

    return AiModelDeleteImpact(
        mapping_id=mapping_id,
        inference_tier=current.inference_tier,
        model_name=current.model_name,
        remaining_active_for_tier=other_active_count,
        dependent_workflows_count=len(dependent_wf_ids),
        dependent_workflow_ids=tuple(dependent_wf_ids),
        pinned_active_runs_count=len(active_run_ids),
        pinned_run_ids=tuple(active_run_ids),
        is_last_active_for_tier=is_last_for_tier,
    )


async def delete_or_drain_ai_model_mapping_pg18(
    conn: AsyncConnection,
    mapping_id: str,
    *,
    mode: PinRemovalMode = "reject",
    actor_role: str = "PLATFORM_ADMIN",
    instance: str | None = None,
) -> AiModelMappingRecord | None:
    """Enforce active-run pinning guard and drain/delete transition (`AD-21` §5)."""
    if actor_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    impact = await evaluate_ai_model_delete_impact_pg18(conn, mapping_id, instance=instance)

    if impact.pinned_active_runs_count > 0 and mode == "drain":
        await conn.execute(
            sa.text(
                """
                UPDATE workspace_llm_tier_mappings
                SET draining = TRUE, is_active = FALSE, updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": mapping_id},
        )
        return await get_ai_model_mapping_pg18(conn, mapping_id, instance=instance)

    if impact.dependent_workflows_count > 0 and impact.is_last_active_for_tier and mode != "force":
        raise LastTierModelInUseError(instance=instance)

    if impact.pinned_active_runs_count > 0 and mode == "reject":
        raise ResourcePinnedByActiveRunsError(instance=instance)

    await conn.execute(
        sa.text("DELETE FROM workspace_llm_tier_mappings WHERE id = :id"),
        {"id": mapping_id},
    )
    return None


__all__ = [
    "ACTIVE_WORKFLOW_RUN_STATUSES",
    "delete_or_drain_ai_model_mapping_pg18",
    "evaluate_ai_model_delete_impact_pg18",
]
