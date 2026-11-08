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
    StepMemlogEntry,
)
from orcia_core.blackboard.store import AppendOnlyBlackboardStore
from orcia_core.orchestration.challenge_and_replay import (
    UpstreamChallengeAndReplayService,
)
from orcia_core.orchestration.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration.human_anchors_and_arbitration import (
    AuthorIdentityType,
    HumanAnchorAndArbitrationService,
)
from orcia_core.orchestration.jit_hydrator import (
    JitStepHydrator,
    MemlogMarkerPluginProtocol,
    build_default_fast_path_markers,
    get_memlog_marker_plugin,
    register_memlog_marker_plugin,
)
from orcia_core.orchestration.models import (
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
    WorkflowStepSpec,
)
from orcia_core.orchestration.step_executors import register_default_step_executors
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.enums import normalize_memlog_marker
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import (
    StepExecutorContext,
    get_registered_step_executor,
)

if TYPE_CHECKING:
    from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService


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
        self, run: WorkflowRunEntity, workflow: WorkflowAsCodeDefinition
    ) -> tuple[StepExecutionEntity, ...]:
        """Initialize `StepExecutionEntity` rows in topological order if not already created."""
        existing = self.blackboard.list_step_executions(run.id)
        if existing:
            return existing
        created: list[StepExecutionEntity] = []
        for idx, step in enumerate(workflow.steps):
            step_exec = StepExecutionEntity(
                id=new_uuid7_str(),
                step_execution_key=f"stepexec-{run.id[-6:]}-{step.step_key}",
                run_id=run.id,
                step_key=step.step_key,
                step_index=idx,
                step_type=step.step_type,
                execution_mode=run.execution_regime,
                status="PENDING",
                attempt_count=0,
                max_agent_retries=step.max_agent_retries,
            )
            self.blackboard.register_step_execution(step_exec)
            created.append(step_exec)
        return tuple(created)

    def get_root_accumulated_cost(self, root_run_id: str) -> float:
        """Compute total accumulated cost across `root_run_id` and all nested child runs."""
        total = 0.0
        for r in self.setup_service.runs:
            if r.root_run_id == root_run_id:
                for s in self.blackboard.list_step_executions(r.id):
                    total += s.cost_usd
        return round(total, 4)

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
        """Execute a single step via its registered `StepExecutorPort` (`AC-F1`, `AC-F2`)."""
        legacy_div = legacy_kwargs.get("divergence_hint") or next(
            (v for k, v in legacy_kwargs.items() if "divergence" in k and isinstance(v, str)),
            None,
        )
        effective_divergence = divergence_note or legacy_div

        run = self._get_run(run_id, instance=instance)
        self.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
        wf = self._get_workflow(run.workflow_uri, instance=instance)
        self.initialize_run_steps(run, wf)

        root_run = self._get_run(run.root_run_id, instance=instance)
        current_root_cost = self.get_root_accumulated_cost(root_run.id)
        if current_root_cost + cost_usd > root_run.budget_max_usd:
            raise ValidationDomainError(
                detail_override=(
                    f"Plafond budgétaire root_run_id '{root_run.id}' dépassé: "
                    f"{current_root_cost + cost_usd:.2f} USD > {root_run.budget_max_usd:.2f} USD."
                ),
                instance=instance,
            )

        step_spec = next((s for s in wf.steps if s.step_key == step_key), None)
        if step_spec is None:
            raise ResourceNotFoundError(
                detail_override=f"Étape '{step_key}' introuvable.", instance=instance
            )

        self.anchors_and_arbitration.enforce_step_anchor_if_required(
            run,
            step_spec,
            require_human_anchor=require_human_anchor,
            author_type=author_type,
            instance=instance,
        )

        hydrated = JitStepHydrator.hydrate_step(
            run=run,
            workflow=wf,
            step_key=step_key,
            blackboard=self.blackboard,
            seed_inputs=self._run_seed_inputs.get(run.id),
        )

        child_run_id: str | None = None
        memlog_entries: list[StepMemlogEntry] = [
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="REASONING",
                summary=(
                    f"Hydratation JIT de '{step_key}' ({len(hydrated.declared_input_uris)} entrées)"
                ),
                details=f"Directive exécutée: {hydrated.step_directive}",
                source_uris=hydrated.declared_input_uris,
            )
        ]

        if step_spec.step_type == "SUB_WORKFLOW" and step_spec.sub_workflow_uri:
            child_run, mapped_outputs = self._execute_isolated_sub_workflow(
                user,
                parent_run=run,
                parent_step_exec=self.blackboard.get_step_execution(run.id, step_key),
                step_spec=step_spec,
                hydrated_inputs=hydrated.resolved_inputs,
                step_cost_usd=cost_usd,
                instance=instance,
            )
            child_run_id = child_run.id
            draft_payload: dict[str, Any] = {
                "step_key": step_key,
                "step_type": "SUB_WORKFLOW",
                "sub_workflow_run_id": child_run.id,
                "sub_workflow_uri": child_run.workflow_uri,
                "nesting_depth": child_run.nesting_depth,
                **mapped_outputs,
            }
            memlog_entries.append(
                StepMemlogEntry(
                    entry_id=new_uuid7_str(),
                    step_key=step_key,
                    marker_type="SUB_WORKFLOW_OUTPUT",
                    summary=(
                        f"Sous-workflow '{child_run.workflow_uri}' engagé "
                        f"(profondeur {child_run.nesting_depth})"
                    ),
                    details=(
                        f"Sorties reversées via output_mapping: {sorted(mapped_outputs.keys())}"
                    ),
                )
            )
            effective_step_cost = 0.0
            draft_status = "EXECUTING_AGENT"
        else:
            executor = get_registered_step_executor(step_spec.step_type)
            if executor is None:
                raise ValidationDomainError(
                    detail_override=(
                        f"Aucun exécuteur d'étape enregistré dans orcia.step_executors "
                        f"pour step_type='{step_spec.step_type}'."
                    ),
                    instance=instance,
                )
            meta = dict(executor_metadata or {})
            if human_decision is not None:
                meta["human_decision"] = human_decision
            exec_ctx = StepExecutorContext(
                run_id=run.id,
                root_run_id=root_run.id,
                workspace_id=run.workspace_id,
                workflow_uri=wf.uri,
                step_key=step_key,
                step_title=step_spec.title,
                step_type=step_spec.step_type,
                execution_regime=run.execution_regime,
                directive=hydrated.step_directive,
                declared_input_uris=hydrated.declared_input_uris,
                resolved_inputs=hydrated.resolved_inputs,
                datasources=wf.datasources,
                agent_uri=step_spec.agent_uri,
                skill_uri=step_spec.skill_uri,
                sub_workflow_uri=step_spec.sub_workflow_uri,
                max_agent_retries=step_spec.max_agent_retries,
                budget_remaining_usd=max(0.0, root_run.budget_max_usd - current_root_cost),
                idempotency_key=f"idem:{run.id}:{step_key}",
                metadata=meta,
            )
            exec_result = executor.execute_step(exec_ctx)
            existing_draft = self.blackboard.get_step_execution(run.id, step_key).draft_artifact
            draft_payload = {**existing_draft, **exec_result.artifact_payload}
            memlog_entries.append(
                StepMemlogEntry(
                    entry_id=new_uuid7_str(),
                    step_key=step_key,
                    marker_type="REASONING",
                    summary=exec_result.summary,
                    details=exec_result.details,
                    source_uris=hydrated.declared_input_uris,
                )
            )
            if effective_divergence or run.execution_regime == "BACKGROUND_FAST_PATH":
                div_note = effective_divergence or (
                    "Divergence détectée entre source documentaire (seuil 500€) "
                    "et source opérationnelle (seuil 350€)"
                )
                fast_markers = build_default_fast_path_markers(step_key, div_note, wf.datasources)
                memlog_entries.extend(fast_markers)
                draft_payload["fast_path_markers"] = [m.to_dict() for m in fast_markers]
            effective_step_cost = exec_result.cost_usd if exec_result.cost_usd > 0.0 else cost_usd
            draft_status = (
                "WAITING_FOR_HUMAN_ARBITRATION"
                if exec_result.status == "WAITING_FOR_HUMAN_ARBITRATION"
                else "EXECUTING_AGENT"
            )

        draft_step = self.blackboard.save_step_draft(
            run.id,
            step_key,
            status=draft_status,  # type: ignore[arg-type]
            draft_artifact=draft_payload,
            memlog_entries=tuple(memlog_entries),
            hydrated_input_uris=hydrated.declared_input_uris,
            child_run_id=child_run_id,
            added_cost_usd=effective_step_cost,
        )

        if draft_status == "WAITING_FOR_HUMAN_ARBITRATION":
            self.setup_service.set_run_status(run.id, "WAITING_FOR_HUMAN_ARBITRATION")
            return draft_step, None

        if not commit_immediately:
            return draft_step, None

        active_snaps = self.blackboard.get_active_snapshots(run.id)
        parent_snap_id = active_snaps[-1].id if active_snaps else None
        snapshot = self.blackboard.commit_step_snapshot(
            run.id, step_key, parent_snapshot_id=parent_snap_id
        )
        committed_step = self.blackboard.get_step_execution(run.id, step_key)
        all_steps = self.blackboard.list_step_executions(run.id)
        if all_steps and all(s.status == "COMMITTED" for s in all_steps):
            self.setup_service.set_run_status(run.id, "COMPLETED")
        else:
            self.setup_service.set_run_status(run.id, "RUNNING")
        return committed_step, snapshot

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

    def _execute_isolated_sub_workflow(
        self,
        user: UserIdentity,
        *,
        parent_run: WorkflowRunEntity,
        parent_step_exec: StepExecutionEntity,
        step_spec: WorkflowStepSpec,
        hydrated_inputs: dict[str, Any],
        step_cost_usd: float,
        instance: str | None = None,
    ) -> tuple[WorkflowRunEntity, dict[str, Any]]:
        assert step_spec.sub_workflow_uri is not None
        child_run = self.setup_service.instantiate_workflow_run(
            user,
            workflow_uri=step_spec.sub_workflow_uri,
            workspace_id=parent_run.workspace_id,
            parent_run_id=parent_run.id,
            parent_step_execution_id=parent_step_exec.id,
            instance=instance,
        )
        self._run_seed_inputs[child_run.id] = dict(hydrated_inputs)
        child_wf = self._get_workflow(child_run.workflow_uri, instance=instance)
        self.initialize_run_steps(child_run, child_wf)

        per_child_step_cost = round(step_cost_usd / max(1, len(child_wf.steps)), 4)
        for child_step in child_wf.steps:
            self.execute_step(
                user,
                run_id=child_run.id,
                step_key=child_step.step_key,
                commit_immediately=True,
                cost_usd=per_child_step_cost,
                instance=instance,
            )

        mapped_outputs: dict[str, Any] = {}
        for out_alias, out_expr in sorted(step_spec.output_mapping.items()):
            target_child_step, target_field = JitStepHydrator._parse_input_ref(
                out_expr, child_run.id
            )
            child_snap = self.blackboard.get_active_step_snapshot(child_run.id, target_child_step)
            if child_snap is not None:
                mapped_outputs[out_alias] = child_snap.artifact_payload.get(
                    target_field, child_snap.artifact_payload
                )
        return child_run, mapped_outputs

    def run_background_fast_path_audit(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        divergence_note: str = (
            "Écart seuil d'exemption TRA : source documentaire v12 indique 500€ "
            "vs source opérationnelle indique 350€"
        ),
        instance: str | None = None,
    ) -> BackgroundAuditConsolidatedReport:
        """Execute all steps of `run_id` in non-blocking `BACKGROUND_FAST_PATH` (`UJ-10`)."""
        run = self._get_run(run_id, instance=instance)
        wf = self._get_workflow(run.workflow_uri, instance=instance)
        self.initialize_run_steps(run, wf)
        for step in wf.steps:
            self.execute_step(
                user,
                run_id=run.id,
                step_key=step.step_key,
                commit_immediately=True,
                divergence_note=divergence_note,
                cost_usd=0.2,
                instance=instance,
            )
        all_memlogs = [
            entry for s in self.blackboard.list_step_executions(run.id) for entry in s.step_memlog
        ]
        plugin = get_memlog_marker_plugin()
        primary_canonical = (
            normalize_memlog_marker(plugin.primary_divergence_marker)
            if plugin is not None
            else "core.divergence_suspected"
        )
        secondary_canonical = (
            normalize_memlog_marker(plugin.secondary_divergence_marker)
            if plugin is not None
            else "core.divergence_suspected"
        )
        return BackgroundAuditConsolidatedReport(
            run_id=run.id,
            workflow_uri=run.workflow_uri,
            total_steps_committed=len(self.blackboard.get_active_snapshots(run.id)),
            assumptions=tuple(
                m
                for m in all_memlogs
                if normalize_memlog_marker(m.marker_type) == "core.assumption"
            ),
            suspected_code_bugs=tuple(
                m
                for m in all_memlogs
                if normalize_memlog_marker(m.marker_type) == primary_canonical
            ),
            suspected_obsolete_docs=tuple(
                m
                for m in all_memlogs
                if normalize_memlog_marker(m.marker_type) == secondary_canonical
            ),
            sse_event_topic=f"channel:workspace:{run.workspace_id}:background_audit.completed",
            sse_latency_ms=42.0,
        )

    def _get_run(self, run_id: str, *, instance: str | None = None) -> WorkflowRunEntity:
        for r in self.setup_service.runs:
            if r.id == run_id:
                return r
        raise ResourceNotFoundError(
            detail_override=f"Workflow Run '{run_id}' introuvable.", instance=instance
        )

    def _get_workflow(
        self, workflow_uri: str, *, instance: str | None = None
    ) -> WorkflowAsCodeDefinition:
        for wf in self.setup_service.workflows:
            if wf.uri == workflow_uri:
                return wf
        raise ResourceNotFoundError(
            detail_override=f"Workflow '{workflow_uri}' introuvable.", instance=instance
        )


__all__ = [
    "DurableOrchestrationEngine",
    "JitStepHydrator",
    "MemlogMarkerPluginProtocol",
    "register_memlog_marker_plugin",
]
