"""Bounded Workflow v2 Runner & `BoundedWorkflowLauncherAdapter` (`TASK-05`, `Story 16.3`).

Implements:
- Cyclic idempotency keys `f"{run_id}:{sub_step.id}:iter-{iteration}"` (`CA-9.5.3`, Golden Rule #7)
- `NATIVE_ORCIA` and `EXTERNAL_DELEGATED_GATE` execution modes (`CA-9.3.3`)
- Principle 7 Encapsulation: `agent_executor` sub-steps may execute an internal reflexive loop
  (`allow_sub_agent_delegation=False`) while persisting ONLY `ClaimCheckPointer`
  and `reflexive_execution_id` in `SubStepExecutionRecord` (zero scratchpad bloat).
- `BoundedWorkflowLauncherAdapter` implementing `orcia_core.ports.BoundedWorkflowLauncherPort`.
"""

from __future__ import annotations

from typing import Any, Literal

from orcia_connectors.bounded_workflow_hitl import (
    append_sub_step_record,
    apply_hitl_signal_to_run,
)
from orcia_connectors.bounded_workflow_models import (
    BoundedWorkflowRunState,
    HitlActionType,
    HitlSignalPayload,
    SubStepExecutionRecord,
    build_cyclic_idempotency_key,
    finalize_gates_and_anchor,
    generate_sub_step_markdown,
    to_bounded_launch_outcome,
)
from orcia_core.ports.bounded_workflow_port import (
    BoundedSubStepAgentCallback,
    BoundedWorkflowLauncherPort,
    BoundedWorkflowLaunchOutcome,
)
from orcia_core.storage.claim_check import (
    ClaimCheckStorageService,
    get_claim_check_storage,
)
from orcia_core.workflows.schemas_v2 import (
    ExecutionMode,
    WorkflowDefinitionV2,
)


def _prepare_initial_state(
    workflow: WorkflowDefinitionV2,
    *,
    run_id: str,
    inputs: dict[str, Any] | None,
    iteration: int,
    reentry_mode: Literal["initial", "corrections"],
    auto_approve_checkpoints: bool,
) -> tuple[BoundedWorkflowRunState, bool]:
    state = BoundedWorkflowRunState(
        run_id=run_id,
        workflow_id=workflow.id,
        workflow_slug=workflow.slug,
        workflow_version=workflow.version,
        orchestration_type=workflow.orchestration_type,
        execution_mode=workflow.execution_mode,
        iteration=iteration,
        reentry_mode=reentry_mode,
        inputs=dict(inputs or {}),
    )
    if workflow.execution_mode == ExecutionMode.EXTERNAL_DELEGATED_GATE:
        state.mcp_context_bundle = {
            "workflow_slug": workflow.slug,
            "external_tool_label": workflow.external_tool_label,
            "expected_event": workflow.external_completion_event or "git:pr_opened",
            "inputs": state.inputs,
            "guardrails": workflow.guardrails,
        }
        if not auto_approve_checkpoints:
            state.status = "WAITING_EXTERNAL_GATE"
            state.audit_trail.append(
                {
                    "event": "MCP_CONTEXT_BUNDLE_EXPOSED",
                    "iteration": iteration,
                    "expected_event": workflow.external_completion_event,
                }
            )
            return state, True
    return state, False


def run_bounded_workflow_v2(
    workflow: WorkflowDefinitionV2,
    *,
    run_id: str,
    inputs: dict[str, Any] | None = None,
    iteration: int = 1,
    reentry_mode: Literal["initial", "corrections"] = "initial",
    correction_remarks: str | None = None,
    auto_approve_checkpoints: bool = False,
    storage: ClaimCheckStorageService | None = None,
) -> BoundedWorkflowRunState:
    """Execute or initialize a bounded workflow v2 (`NATIVE_ORCIA` or `EXTERNAL_DELEGATED`)."""
    claim_storage = storage or get_claim_check_storage()
    state, halted_early = _prepare_initial_state(
        workflow,
        run_id=run_id,
        inputs=inputs,
        iteration=iteration,
        reentry_mode=reentry_mode,
        auto_approve_checkpoints=auto_approve_checkpoints,
    )
    if halted_early:
        return state

    enabled_sub_steps = [s for s in workflow.sub_steps if s.enabled]
    if not enabled_sub_steps:
        state.status = "COMPLETED_APPROVED"
        return state

    for idx, sub_step in enumerate(enabled_sub_steps):
        state.current_sub_step_index = idx
        md_content = generate_sub_step_markdown(
            workflow, sub_step, state.inputs, iteration, correction_remarks
        )
        append_sub_step_record(
            workflow=workflow,
            state=state,
            sub_step=sub_step,
            claim_storage=claim_storage,
            md_content=md_content,
            reflexive_execution_id=None,
            correction_remarks=correction_remarks,
            auto_approve_checkpoints=auto_approve_checkpoints,
        )
        if not auto_approve_checkpoints and sub_step.requires_human_checkpoint:
            state.status = "WAITING_SUBSTEP_HITL"
            return state

    return finalize_gates_and_anchor(
        workflow, state, claim_storage, auto_approve=auto_approve_checkpoints
    )


async def run_bounded_workflow_v2_async(
    workflow: WorkflowDefinitionV2,
    *,
    run_id: str,
    inputs: dict[str, Any] | None = None,
    iteration: int = 1,
    reentry_mode: Literal["initial", "corrections"] = "initial",
    correction_remarks: str | None = None,
    auto_approve_checkpoints: bool = False,
    storage: ClaimCheckStorageService | None = None,
    sub_step_agent_callback: BoundedSubStepAgentCallback | None = None,
) -> BoundedWorkflowRunState:
    """Async bounded workflow v2 runner encapsulating reflexive `agent_executor` sub-steps."""
    claim_storage = storage or get_claim_check_storage()
    state, halted_early = _prepare_initial_state(
        workflow,
        run_id=run_id,
        inputs=inputs,
        iteration=iteration,
        reentry_mode=reentry_mode,
        auto_approve_checkpoints=auto_approve_checkpoints,
    )
    if halted_early:
        return state

    enabled_sub_steps = [s for s in workflow.sub_steps if s.enabled]
    if not enabled_sub_steps:
        state.status = "COMPLETED_APPROVED"
        return state

    for idx, sub_step in enumerate(enabled_sub_steps):
        state.current_sub_step_index = idx
        reflexive_exec_id: str | None = None
        if sub_step.step_executor_type == "agent_executor" and sub_step_agent_callback is not None:
            agent_outcome = await sub_step_agent_callback(
                sub_step.id,
                sub_step.name,
                sub_step.instruction_prompt_or_ref,
                state.inputs,
                iteration,
                correction_remarks,
            )
            md_content = agent_outcome.final_markdown
            reflexive_exec_id = agent_outcome.reflexive_execution_id
            state.trace_events.extend(agent_outcome.trace_events)
        else:
            md_content = generate_sub_step_markdown(
                workflow, sub_step, state.inputs, iteration, correction_remarks
            )

        append_sub_step_record(
            workflow=workflow,
            state=state,
            sub_step=sub_step,
            claim_storage=claim_storage,
            md_content=md_content,
            reflexive_execution_id=reflexive_exec_id,
            correction_remarks=correction_remarks,
            auto_approve_checkpoints=auto_approve_checkpoints,
        )
        if not auto_approve_checkpoints and sub_step.requires_human_checkpoint:
            state.status = "WAITING_SUBSTEP_HITL"
            return state

    return finalize_gates_and_anchor(
        workflow, state, claim_storage, auto_approve=auto_approve_checkpoints
    )


class BoundedWorkflowLauncherAdapter(BoundedWorkflowLauncherPort):
    """Concrete adapter implementing `BoundedWorkflowLauncherPort` (`Story 16.3`)."""

    def __init__(self, storage: ClaimCheckStorageService | None = None) -> None:
        self._storage = storage

    async def launch_bounded_workflow(
        self,
        workflow_payload: dict[str, Any],
        *,
        run_id: str,
        inputs: dict[str, Any] | None = None,
        iteration: int = 1,
        reentry_mode: Literal["initial", "corrections"] = "initial",
        correction_remarks: str | None = None,
        auto_approve_checkpoints: bool = False,
        sub_step_agent_callback: BoundedSubStepAgentCallback | None = None,
    ) -> BoundedWorkflowLaunchOutcome:
        workflow = WorkflowDefinitionV2.model_validate(workflow_payload)
        state = await run_bounded_workflow_v2_async(
            workflow,
            run_id=run_id,
            inputs=inputs,
            iteration=iteration,
            reentry_mode=reentry_mode,
            correction_remarks=correction_remarks,
            auto_approve_checkpoints=auto_approve_checkpoints,
            storage=self._storage,
            sub_step_agent_callback=sub_step_agent_callback,
        )
        return to_bounded_launch_outcome(state)


__all__ = [
    "BoundedWorkflowLauncherAdapter",
    "BoundedWorkflowRunState",
    "HitlActionType",
    "HitlSignalPayload",
    "SubStepExecutionRecord",
    "apply_hitl_signal_to_run",
    "build_cyclic_idempotency_key",
    "run_bounded_workflow_v2",
    "run_bounded_workflow_v2_async",
]
