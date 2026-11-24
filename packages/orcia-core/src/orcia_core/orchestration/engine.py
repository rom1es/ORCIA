"""DurableOrchestrationEngine dispatching real `StepExecutorPort` implementations (`Story 3.2f`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`) and zero SDLC
vocabulary (`AD-19`, `AD-20`, `AC-E2`, `AC-F1`, `AC-F2`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.blackboard.models import (
    BackgroundAuditConsolidatedReport,
    BlackboardSnapshotEntity,
    StepExecutionEntity,
)
from orcia_core.blackboard.store import AppendOnlyBlackboardStore
from orcia_core.orchestration import _engine_step_helpers as _sh
from orcia_core.orchestration._engine_fast_path import (
    execute_isolated_sub_workflow_async,
    execute_isolated_sub_workflow_sync,
    finalize_step_outcome,
)
from orcia_core.orchestration._orchestration_ops_locales import (
    ENGINE_STEP_LOCALES,
    get_ops_copy,
)
from orcia_core.orchestration.challenge_and_replay import UpstreamChallengeAndReplayService
from orcia_core.orchestration.human_anchors_and_arbitration import (
    AuthorIdentityType,
    HumanAnchorAndArbitrationService,
)
from orcia_core.orchestration.jit_hydrator import (
    JitStepHydrator,
    MemlogMarkerPluginProtocol,
    register_memlog_marker_plugin,
)
from orcia_core.orchestration.models import WorkflowAsCodeDefinition, WorkflowRunEntity
from orcia_core.orchestration.step_executors import (
    execute_step_port_async,
    register_default_step_executors,
)
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService

_DEFAULT_AUDIT_DIVERGENCE = get_ops_copy(ENGINE_STEP_LOCALES)["default_audit_div"]


class DurableOrchestrationEngine:
    """Durable workflow execution engine dispatching real `orcia.step_executors` (`AC-F1`)."""

    def __init__(
        self,
        *,
        setup_service: WorkflowOrchestrationSetupService,
        blackboard: AppendOnlyBlackboardStore | None = None,
    ) -> None:
        self.setup_service = setup_service
        self.blackboard = blackboard or AppendOnlyBlackboardStore(resolver=setup_service.resolver)
        self._run_seed_inputs: dict[str, dict[str, Any]] = {}
        self.anchors_and_arbitration = HumanAnchorAndArbitrationService(engine=self)
        self.challenge_and_replay = UpstreamChallengeAndReplayService(engine=self)
        register_default_step_executors()

    def initialize_run_steps(
        self,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        *,
        initialize_anchored_as_waiting: bool = False,
    ) -> tuple[StepExecutionEntity, ...]:
        """Initialize `StepExecutionEntity` rows in topological order if not already created."""
        return _sh.initialize_run_steps_helper(
            self,
            run,
            workflow,
            initialize_anchored_as_waiting=initialize_anchored_as_waiting,
        )

    def get_root_accumulated_cost(self, root_run_id: str) -> float:
        """Compute total accumulated cost across `root_run_id` and all nested child runs."""
        return _sh.compute_root_accumulated_cost(self, root_run_id)

    async def execute_step_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        commit_immediately: bool = True,
        divergence_note: str | None = None,
        human_decision: str | None = None,
        executor_metadata: dict[str, Any] | None = None,
        cost_usd: float = 0.25,
        require_human_anchor: bool = False,
        author_type: AuthorIdentityType = "HUMAN",
        instance: str | None = None,
        **legacy_kwargs: Any,
    ) -> tuple[StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Execute a single step asynchronously via `StepExecutorPort` without loop blocking."""
        run, root_run, wf, step_spec, hydrated, cur_cost, eff_div = _sh.prepare_step_inputs(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            divergence_note=divergence_note,
            cost_usd=cost_usd,
            require_human_anchor=require_human_anchor,
            author_type=author_type,
            instance=instance,
            legacy_kwargs=legacy_kwargs,
        )
        sub_wf_res, exec_res = None, None
        if step_spec.step_type == "SUB_WORKFLOW" and step_spec.sub_workflow_uri:
            p_exec = self.blackboard.get_step_execution(run.id, step_key)
            sub_wf_res = await execute_isolated_sub_workflow_async(
                self,
                user,
                parent_run=run,
                parent_step_exec_id=p_exec.id,
                step_spec=step_spec,
                hydrated_inputs=hydrated.resolved_inputs,
                step_cost_usd=cost_usd,
                instance=instance,
            )
        else:
            executor, ctx = _sh.build_step_exec_ctx(
                run=run,
                root_run=root_run,
                wf=wf,
                step_spec=step_spec,
                hydrated=hydrated,
                current_root_cost=cur_cost,
                human_decision=human_decision,
                executor_metadata=executor_metadata,
                instance=instance,
            )
            exec_res = await execute_step_port_async(executor, ctx)
        return finalize_step_outcome(
            self,
            run=run,
            wf=wf,
            step_key=step_key,
            hydrated=hydrated,
            exec_result=exec_res,
            sub_wf_result=sub_wf_res,
            effective_divergence=eff_div,
            cost_usd=cost_usd,
            commit_immediately=commit_immediately,
        )

    def execute_step(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        commit_immediately: bool = True,
        divergence_note: str | None = None,
        human_decision: str | None = None,
        executor_metadata: dict[str, Any] | None = None,
        cost_usd: float = 0.25,
        require_human_anchor: bool = False,
        author_type: AuthorIdentityType = "HUMAN",
        instance: str | None = None,
        **legacy_kwargs: Any,
    ) -> tuple[StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Execute a single step synchronously via `StepExecutorPort`."""
        run, root_run, wf, step_spec, hydrated, cur_cost, eff_div = _sh.prepare_step_inputs(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            divergence_note=divergence_note,
            cost_usd=cost_usd,
            require_human_anchor=require_human_anchor,
            author_type=author_type,
            instance=instance,
            legacy_kwargs=legacy_kwargs,
        )
        sub_wf_res, exec_res = None, None
        if step_spec.step_type == "SUB_WORKFLOW" and step_spec.sub_workflow_uri:
            p_exec = self.blackboard.get_step_execution(run.id, step_key)
            sub_wf_res = execute_isolated_sub_workflow_sync(
                self,
                user,
                parent_run=run,
                parent_step_exec_id=p_exec.id,
                step_spec=step_spec,
                hydrated_inputs=hydrated.resolved_inputs,
                step_cost_usd=cost_usd,
                instance=instance,
            )
        else:
            executor, ctx = _sh.build_step_exec_ctx(
                run=run,
                root_run=root_run,
                wf=wf,
                step_spec=step_spec,
                hydrated=hydrated,
                current_root_cost=cur_cost,
                human_decision=human_decision,
                executor_metadata=executor_metadata,
                instance=instance,
            )
            exec_res = executor.execute_step(ctx)
        return finalize_step_outcome(
            self,
            run=run,
            wf=wf,
            step_key=step_key,
            hydrated=hydrated,
            exec_result=exec_res,
            sub_wf_result=sub_wf_res,
            effective_divergence=eff_div,
            cost_usd=cost_usd,
            commit_immediately=commit_immediately,
        )

    async def resume_human_task_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        decision: str,
        instance: str | None = None,
    ) -> tuple[StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Async resume of a paused `HUMAN_TASK` or arbitration step (`AC-F1`)."""
        return await self.execute_step_async(
            user,
            run_id=run_id,
            step_key=step_key,
            commit_immediately=True,
            human_decision=decision,
            cost_usd=0.0,
            instance=instance,
        )

    def resume_human_task(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        decision: str,
        instance: str | None = None,
    ) -> tuple[StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Resume a paused `HUMAN_TASK` or `WAITING_FOR_HUMAN_ARBITRATION` step (`AC-F1`)."""
        return self.execute_step(
            user,
            run_id=run_id,
            step_key=step_key,
            commit_immediately=True,
            human_decision=decision,
            cost_usd=0.0,
            instance=instance,
        )

    async def run_background_fast_path_audit_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        divergence_note: str = _DEFAULT_AUDIT_DIVERGENCE,
        instance: str | None = None,
    ) -> BackgroundAuditConsolidatedReport:
        """Async execution of all steps of `run_id` in `BACKGROUND_FAST_PATH` (`UJ-10`)."""
        return await _sh.run_background_fast_path_audit_async_helper(
            self, user, run_id=run_id, divergence_note=divergence_note, instance=instance
        )

    def run_background_fast_path_audit(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        divergence_note: str = _DEFAULT_AUDIT_DIVERGENCE,
        instance: str | None = None,
    ) -> BackgroundAuditConsolidatedReport:
        """Execute all steps of `run_id` in non-blocking `BACKGROUND_FAST_PATH` (`UJ-10`)."""
        return _sh.run_background_fast_path_audit_sync_helper(
            self, user, run_id=run_id, divergence_note=divergence_note, instance=instance
        )

    def _get_run(self, run_id: str, *, instance: str | None = None) -> WorkflowRunEntity:
        return _sh.resolve_engine_run(self, run_id, instance=instance)

    def _get_workflow(self, uri: str, *, instance: str | None = None) -> WorkflowAsCodeDefinition:
        return _sh.resolve_engine_workflow(self, uri, instance=instance)


__all__ = [
    "DurableOrchestrationEngine",
    "JitStepHydrator",
    "MemlogMarkerPluginProtocol",
    "register_memlog_marker_plugin",
]
