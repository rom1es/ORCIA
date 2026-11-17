"""Durable PROC-01 helper execution for cognitive tier router (`Story 8.2`).

Extracted to ensure core router file remains under 350 lines.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Literal

from orcia_core.orchestration._cognitive_router_models import (
    DurableProc01RunState,
    InferenceEffort,
    ResolvedInferenceTier,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.cognitive_router import CognitiveModelRouterService


async def start_proc01_durable_run_helper(
    router: CognitiveModelRouterService,
    *,
    workspace_id: str,
    user_prompt: str,
    effort: InferenceEffort = "balanced",
) -> DurableProc01RunState:
    run_id, step_id = new_uuid7_str(), new_uuid7_str()

    def _gate_requires_medium(
        content: str, resolved_tier: ResolvedInferenceTier
    ) -> tuple[bool, str]:
        _ = content
        return (
            (False, "Schema validation requires medium tier precision")
            if resolved_tier == "simple"
            else (True, "")
        )

    outcome = await router.execute_with_tier_routing(
        run_id=run_id,
        step_execution_id=step_id,
        scope_id=workspace_id,
        system_prompt="ORCIA Durable Cognitive Step 1",
        user_prompt=user_prompt,
        inference_tier="auto",
        effort=effort,
        deterministic_gate_fn=_gate_requires_medium,
    )
    status: Literal[
        "RUNNING", "WAITING_FOR_HUMAN_ARBITRATION", "PAUSED_BUDGET_EXCEEDED", "PAUSED_MAX_RETRIES"
    ] = (
        "PAUSED_BUDGET_EXCEEDED"
        if outcome.paused_budget_exceeded
        else "PAUSED_MAX_RETRIES"
        if outcome.paused_max_retries
        else "WAITING_FOR_HUMAN_ARBITRATION"
    )
    state = DurableProc01RunState(
        run_id=run_id,
        workspace_id=workspace_id,
        status=status,
        step_1_outcome=outcome,
    )
    return state


async def replay_and_resume_proc01_run_helper(
    router: CognitiveModelRouterService,
    current: DurableProc01RunState | None,
    *,
    run_id: str,
    arbitration_choice: str,
) -> DurableProc01RunState:
    if current is None:
        raise ResourceNotFoundError(detail_override=f"PROC-01 run not found: {run_id}")

    step_1_id = current.step_1_outcome.step_execution_id
    replayed_outcome = await router.execute_with_tier_routing(
        run_id=run_id,
        step_execution_id=step_1_id,
        scope_id=current.workspace_id,
        system_prompt="ORCIA Durable Cognitive Step 1",
        user_prompt="Replayed prompt",
        inference_tier="auto",
        effort=current.step_1_outcome.effort,
    )
    return replace(
        current,
        status="COMPLETED",
        step_1_outcome=replayed_outcome,
        arbitration_resolution=arbitration_choice,
        final_artifact={
            "verified_tier": replayed_outcome.final_resolved_tier,
            "attempts_count": len(replayed_outcome.attempts),
            "arbitration_choice": arbitration_choice,
            "content": replayed_outcome.response_content,
        },
        replayed_after_restart=True,
    )


__all__ = [
    "replay_and_resume_proc01_run_helper",
    "start_proc01_durable_run_helper",
]
