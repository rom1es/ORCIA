"""JitStepHydrator & DurableOrchestrationEngine (Story 3.2, Story 3.2e, AD-2, AD-12, AD-13, AD-20).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`) and zero SDLC
vocabulary (`AD-19`, `AD-20`, `AC-E2`).
"""

from __future__ import annotations

import importlib.metadata
import threading
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from orcia_core.blackboard.models import (
    BackgroundAuditConsolidatedReport,
    BlackboardSnapshotEntity,
    HydratedStepContext,
    StepExecutionEntity,
    StepMemlogEntry,
)
from orcia_core.blackboard.store import AppendOnlyBlackboardStore
from orcia_core.orchestration.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration.models import (
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
    WorkflowStepSpec,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.enums import normalize_memlog_marker
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService


@runtime_checkable
class MemlogMarkerPluginProtocol(Protocol):
    """Plugin protocol discovered via `entry_points(group='orcia.memlog_markers')` (`AD-20`)."""

    @property
    def primary_divergence_marker(self) -> str:
        """Return primary divergence marker key (e.g. `<namespace>.<marker>` or alias)."""
        ...

    @property
    def secondary_divergence_marker(self) -> str:
        """Return secondary divergence marker key (e.g. `<namespace>.<marker>` or alias)."""
        ...

    def build_fast_path_markers(
        self, step_key: str, divergence_note: str, datasources: tuple[str, ...]
    ) -> tuple[StepMemlogEntry, ...]:
        """Build fast-path divergence markers for a step execution."""
        ...


_MARKER_PLUGIN_LOCK = threading.Lock()
_MARKER_PLUGIN: MemlogMarkerPluginProtocol | None = None
_MARKER_ENTRY_POINTS_LOADED: bool = False


def register_memlog_marker_plugin(plugin: MemlogMarkerPluginProtocol) -> None:
    """Register a pack `MemlogMarkerPluginProtocol` (`AD-20`, `AC-E1`, `AC-E2`)."""
    global _MARKER_PLUGIN
    with _MARKER_PLUGIN_LOCK:
        _MARKER_PLUGIN = plugin


def _get_memlog_marker_plugin() -> MemlogMarkerPluginProtocol | None:
    global _MARKER_ENTRY_POINTS_LOADED, _MARKER_PLUGIN
    with _MARKER_PLUGIN_LOCK:
        if not _MARKER_ENTRY_POINTS_LOADED:
            _MARKER_ENTRY_POINTS_LOADED = True
            try:
                eps = importlib.metadata.entry_points(group="orcia.memlog_markers")
                for ep in eps:
                    loaded = ep.load()
                    instance = loaded() if callable(loaded) else loaded
                    if isinstance(instance, MemlogMarkerPluginProtocol):
                        _MARKER_PLUGIN = instance
            except Exception:
                pass
        return _MARKER_PLUGIN


class JitStepHydrator:
    """Just-In-Time Step Context Hydrator (`AD-13`).

    Injects ONLY step $k$'s directive and explicitly declared upstream artifacts (`orcia://`).
    Guarantees 0 instructions from future steps $k+1..N$ and 0 undeclared upstream artifacts.
    """

    @staticmethod
    def hydrate_step(
        *,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        step_key: str,
        blackboard: AppendOnlyBlackboardStore,
        seed_inputs: dict[str, Any] | None = None,
    ) -> HydratedStepContext:
        """Build isolated `HydratedStepContext` for `step_key` in `run`."""
        target_step: WorkflowStepSpec | None = None
        for step in workflow.steps:
            if step.step_key == step_key:
                target_step = step
                break
        if target_step is None:
            raise ResourceNotFoundError(
                detail_override=f"Étape '{step_key}' introuvable dans '{workflow.uri}'."
            )

        declared_uris: list[str] = []
        resolved_inputs: dict[str, Any] = dict(seed_inputs or {})

        # Resolve only explicitly mapped inputs or direct dependencies
        mapping_sources = dict(target_step.input_mapping)
        if not mapping_sources and target_step.depends_on:
            for dep_key in target_step.depends_on:
                mapping_sources[dep_key] = f"steps.{dep_key}.artifact"

        for alias, ref_expr in sorted(mapping_sources.items()):
            upstream_step_key, field_key = JitStepHydrator._parse_input_ref(ref_expr, run.id)
            canonical_uri = f"orcia://runs/{run.id}/steps/{upstream_step_key}/artifacts/{field_key}"
            declared_uris.append(canonical_uri)
            snap = blackboard.get_active_step_snapshot(run.id, upstream_step_key)
            if snap is None:
                raise ResourceNotFoundError(
                    detail_override=(
                        f"Snapshot amont requis introuvable pour '{canonical_uri}' "
                        f"lors de l'hydratation JIT de '{step_key}'."
                    )
                )
            if field_key in snap.artifact_payload:
                resolved_inputs[alias] = snap.artifact_payload[field_key]
            else:
                resolved_inputs[alias] = snap.artifact_payload

        return HydratedStepContext(
            run_id=run.id,
            step_key=target_step.step_key,
            step_title=target_step.title,
            step_type=target_step.step_type,
            execution_mode=run.execution_regime,
            step_directive=target_step.instructions,
            declared_input_uris=tuple(declared_uris),
            resolved_inputs=resolved_inputs,
            future_step_instructions_leaked=0,
            undeclared_artifacts_leaked=0,
        )

    @staticmethod
    def _parse_input_ref(ref_expr: str, run_id: str) -> tuple[str, str]:
        cleaned = ref_expr.strip()
        if cleaned.startswith("orcia://runs/"):
            parts = cleaned.removeprefix("orcia://runs/").split("/")
            if len(parts) >= 5 and parts[1] == "steps" and parts[3] == "artifacts":
                return parts[2], parts[4]
        if cleaned.startswith("steps."):
            parts = cleaned.split(".")
            if len(parts) >= 3:
                return parts[1], parts[2]
            if len(parts) == 2:
                return parts[1], "artifact"
        raise ValidationDomainError(
            detail_override=f"Référence d'entrée JIT invalide '{ref_expr}' sur le run '{run_id}'."
        )


class DurableOrchestrationEngine:
    """Durable workflow execution engine with append-only checkpoints & fractal SUB_WORKFLOWs."""

    def __init__(
        self,
        *,
        setup_service: WorkflowOrchestrationSetupService,
        blackboard: AppendOnlyBlackboardStore | None = None,
    ) -> None:
        self.setup_service = setup_service
        self.blackboard = blackboard or AppendOnlyBlackboardStore(resolver=setup_service.resolver)
        self._run_seed_inputs: dict[str, dict[str, Any]] = {}

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
        simulated_divergence: str | None = None,
        cost_usd: float = 0.25,
        instance: str | None = None,
    ) -> tuple[StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Execute a single step (`AGENT`, `SKILL`, `SUB_WORKFLOW`, `POST_ACTION_VERIFICATION`)."""
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
        else:
            draft_payload = {
                "step_key": step_key,
                "step_type": step_spec.step_type,
                "directive_applied": hydrated.step_directive,
                "inputs_received": list(hydrated.resolved_inputs.keys()),
                "artifact": f"Livrable généré pour {step_key} ({wf.uri})",
                "adr": f"ADR validé pour {step_key}",
                "report": f"Rapport de vérification {step_key} : PASS",
            }
            if simulated_divergence or run.execution_regime == "BACKGROUND_FAST_PATH":
                div_note = simulated_divergence or (
                    "Divergence détectée entre source documentaire (seuil 500€) "
                    "et source opérationnelle (seuil 350€)"
                )
                fast_markers = self._build_fast_path_markers(step_key, div_note, wf.datasources)
                memlog_entries.extend(fast_markers)
                draft_payload["fast_path_markers"] = [m.to_dict() for m in fast_markers]
            effective_step_cost = cost_usd

        draft_step = self.blackboard.save_step_draft(
            run.id,
            step_key,
            status="EXECUTING_AGENT",
            draft_artifact=draft_payload,
            memlog_entries=tuple(memlog_entries),
            hydrated_input_uris=hydrated.declared_input_uris,
            child_run_id=child_run_id,
            added_cost_usd=effective_step_cost,
        )

        if not commit_immediately:
            return draft_step, None

        active_snaps = self.blackboard.get_active_snapshots(run.id)
        parent_snap_id = active_snaps[-1].id if active_snaps else None
        snapshot = self.blackboard.commit_step_snapshot(
            run.id, step_key, parent_snapshot_id=parent_snap_id
        )
        committed_step = self.blackboard.get_step_execution(run.id, step_key)
        return committed_step, snapshot

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

    @staticmethod
    def _build_fast_path_markers(
        step_key: str, divergence_note: str, datasources: tuple[str, ...]
    ) -> tuple[StepMemlogEntry, ...]:
        plugin = _get_memlog_marker_plugin()
        if plugin is not None:
            return plugin.build_fast_path_markers(step_key, divergence_note, datasources)
        return (
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="ASSUMPTION",
                summary="[ASSUMPTION] Continuité d'audit en tâche de fond retenue",
                details=f"Hypothèse appliquée sans blocage worker: {divergence_note}",
                source_uris=datasources,
            ),
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="core.divergence_suspected",
                summary="[DIVERGENCE] Écart détecté entre sources fédérées",
                details=divergence_note,
                source_uris=datasources,
            ),
        )

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
                simulated_divergence=divergence_note,
                cost_usd=0.2,
                instance=instance,
            )
        all_memlogs = [
            entry for s in self.blackboard.list_step_executions(run.id) for entry in s.step_memlog
        ]
        plugin = _get_memlog_marker_plugin()
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
