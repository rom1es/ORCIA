"""Dual-Mode Process Orchestration Dispatcher (`Story 16.3`, `CAP-160`).

Routes any `WorkflowDefinitionV2` transparently according to `workflow.orchestration_type`:
- `NON_DETERMINISTIC` (Goal-driven): runs `NonDeterministicReflexiveRuntime` (`asyncio`, 1-level
  delegation enabled via `workflow.allowed_delegate_agents`), then enforces `GatePipelineExecutor`
  (up to 3 deterministic self-heal retries + probabilistic Hunters) before final human anchor.
- `DETERMINISTIC_DBOS` (Milestone-driven): delegates to `BoundedWorkflowLauncherPort`, encapsulating
  `agent_executor` sub-steps so only the final `ClaimCheckPointer` and `reflexive_execution_id` are
  persisted in the bounded workflow state (Principle 7 — zero scratchpad bloat).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from orcia_core.agents._internal.dispatcher_helpers import (
    UnifiedProcessRunResult,
    build_milestone_unified_result,
    compose_goal_objective,
    default_self_heal_callback,
    ensure_contract_sections,
    resolve_actor_slug,
)
from orcia_core.agents.reflexive_runtime import NonDeterministicReflexiveRuntime
from orcia_core.agents.reflexive_schemas import ReflexiveRuntimeConfig
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.bounded_workflow_port import (
    BoundedWorkflowLauncherPort,
    SubStepAgentExecutionOutcome,
)
from orcia_core.storage.claim_check import (
    ClaimCheckStorageService,
    get_claim_check_storage,
)
from orcia_core.workflows.gates.pipeline import (
    GatePipelineExecutor,
    SelfHealCallback,
)
from orcia_core.workflows.schemas_v2 import (
    ProcessOrchestrationType,
    WorkflowDefinitionV2,
)


class ProcessExecutionDispatcher:
    """Routes Goal-Driven (`NON_DETERMINISTIC`) and Milestone-Driven (`DETERMINISTIC_DBOS`) runs."""

    def __init__(
        self,
        *,
        reflexive_runtime: NonDeterministicReflexiveRuntime,
        bounded_launcher: BoundedWorkflowLauncherPort,
        gate_executor: GatePipelineExecutor | None = None,
        claim_check_storage: ClaimCheckStorageService | None = None,
        self_heal_callback: SelfHealCallback | None = None,
        encapsulate_agent_sub_steps: bool = True,
    ) -> None:
        self._reflexive_runtime = reflexive_runtime
        self._bounded_launcher = bounded_launcher
        self._gate_executor = gate_executor or GatePipelineExecutor()
        self._claim_check = claim_check_storage or get_claim_check_storage()
        self._self_heal_callback = self_heal_callback
        self._encapsulate_agent_sub_steps = encapsulate_agent_sub_steps

    async def dispatch(
        self,
        workflow: WorkflowDefinitionV2,
        *,
        run_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        iteration: int = 1,
        reentry_mode: Literal["initial", "corrections"] = "initial",
        correction_remarks: str | None = None,
        auto_approve_checkpoints: bool = False,
        workspace_id: str | None = None,
        actor_user_id: str | None = None,
        locale: str = "fr",
        initial_resources: Sequence[str] = (),
    ) -> UnifiedProcessRunResult:
        """Execute `workflow` using its configured `orchestration_type`."""
        resolved_run_id = run_id or f"run-{new_uuid7_str()}"
        raw_inputs = dict(inputs or {})
        resources = tuple(str(r).strip() for r in initial_resources if str(r).strip())

        if workflow.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC:
            return await self._dispatch_goal_driven(
                workflow,
                run_id=resolved_run_id,
                inputs=raw_inputs,
                iteration=iteration,
                reentry_mode=reentry_mode,
                correction_remarks=correction_remarks,
                auto_approve_checkpoints=auto_approve_checkpoints,
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                locale=locale,
                initial_resources=resources,
            )

        return await self._dispatch_milestone_driven(
            workflow,
            run_id=resolved_run_id,
            inputs=raw_inputs,
            iteration=iteration,
            reentry_mode=reentry_mode,
            correction_remarks=correction_remarks,
            auto_approve_checkpoints=auto_approve_checkpoints,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            locale=locale,
            initial_resources=resources,
        )

    async def _dispatch_goal_driven(
        self,
        workflow: WorkflowDefinitionV2,
        *,
        run_id: str,
        inputs: dict[str, Any],
        iteration: int,
        reentry_mode: Literal["initial", "corrections"],
        correction_remarks: str | None,
        auto_approve_checkpoints: bool,
        workspace_id: str | None,
        actor_user_id: str | None,
        locale: str,
        initial_resources: tuple[str, ...] = (),
    ) -> UnifiedProcessRunResult:
        config = ReflexiveRuntimeConfig.from_effort_level(
            workflow.effort,
            allow_sub_agent_delegation=True,
            available_delegate_agents=tuple(workflow.allowed_delegate_agents),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            locale=locale,
            initial_resources=initial_resources,
        )
        snap = await self._reflexive_runtime.run_execution(
            actor_slug=resolve_actor_slug(workflow),
            objective=compose_goal_objective(workflow, inputs, correction_remarks),
            config=config,
        )
        candidate_md = snap.final_markdown.strip() or (
            f"# {workflow.title}\n\nSynthese adaptative produite par {snap.actor_slug}."
        )
        heal_cb = self._self_heal_callback or default_self_heal_callback(workflow)
        gate_report = self._gate_executor.execute_pipeline(
            pipeline=workflow.controls,
            artifact_text=candidate_md,
            execution_mode=workflow.execution_mode,
            self_heal_callback=heal_cb,
        )
        final_ptr = self._claim_check.store_artifact(
            run_id=run_id,
            step_id="goal-synthesis",
            iteration=iteration,
            content=gate_report.final_artifact_text,
        )
        status: Literal["FAILED_GATES", "COMPLETED_APPROVED", "WAITING_FINAL_ANCHOR"]
        if not gate_report.deterministic_passed:
            status = "FAILED_GATES"
        elif auto_approve_checkpoints:
            status = "COMPLETED_APPROVED"
        else:
            status = "WAITING_FINAL_ANCHOR"

        return UnifiedProcessRunResult(
            run_id=run_id,
            workflow_id=workflow.id,
            workflow_slug=workflow.slug,
            workflow_version=workflow.version,
            orchestration_type=ProcessOrchestrationType.NON_DETERMINISTIC,
            execution_mode=workflow.execution_mode,
            iteration=iteration,
            reentry_mode=reentry_mode,
            status=status,
            inputs=inputs,
            gate_report=gate_report,
            final_artifact_pointer=final_ptr,
            reflexive_execution_id=snap.execution_id,
            trace_events=list(snap.trace_events),
            audit_trail=[
                {
                    "event": "GOAL_DRIVEN_EXECUTION_COMPLETED",
                    "reflexive_execution_id": snap.execution_id,
                    "turns_executed": snap.turns_used,
                    "tokens_consumed": snap.tokens_used,
                    "s3_uri": final_ptr.s3_uri,
                    "sha256": final_ptr.sha256,
                }
            ],
        )

    async def _dispatch_milestone_driven(
        self,
        workflow: WorkflowDefinitionV2,
        *,
        run_id: str,
        inputs: dict[str, Any],
        iteration: int,
        reentry_mode: Literal["initial", "corrections"],
        correction_remarks: str | None,
        auto_approve_checkpoints: bool,
        workspace_id: str | None,
        actor_user_id: str | None,
        locale: str,
        initial_resources: tuple[str, ...] = (),
    ) -> UnifiedProcessRunResult:
        async def _run_encapsulated_sub_step(
            sub_step_id: str,
            sub_step_name: str,
            instruction_ref: str,
            step_inputs: dict[str, Any],
            step_iteration: int,
            step_remarks: str | None,
        ) -> SubStepAgentExecutionOutcome:
            step_cfg = ReflexiveRuntimeConfig.from_effort_level(
                workflow.effort,
                allow_sub_agent_delegation=False,
                available_delegate_agents=(),
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                locale=locale,
                initial_resources=initial_resources,
            )
            step_obj = f"{workflow.title} — {sub_step_name} ({sub_step_id}, iter-{step_iteration})"
            if step_remarks:
                step_obj = f"{step_obj}\nCorrections: {step_remarks}"
            snap = await self._reflexive_runtime.run_execution(
                actor_slug=resolve_actor_slug(workflow, instruction_ref),
                objective=step_obj,
                config=step_cfg,
            )
            consolidated_md = ensure_contract_sections(
                workflow,
                snap.final_markdown,
                step_label=sub_step_name,
                inputs=step_inputs,
                iteration=step_iteration,
                remarks=step_remarks,
            )
            return SubStepAgentExecutionOutcome(
                reflexive_execution_id=snap.execution_id,
                final_markdown=consolidated_md,
                trace_events=list(snap.trace_events),
            )

        outcome = await self._bounded_launcher.launch_bounded_workflow(
            workflow.model_dump(mode="json"),
            run_id=run_id,
            inputs=inputs,
            iteration=iteration,
            reentry_mode=reentry_mode,
            correction_remarks=correction_remarks,
            auto_approve_checkpoints=auto_approve_checkpoints,
            sub_step_agent_callback=(
                _run_encapsulated_sub_step if self._encapsulate_agent_sub_steps else None
            ),
        )
        return build_milestone_unified_result(outcome)


__all__ = [
    "ProcessExecutionDispatcher",
    "UnifiedProcessRunResult",
]
