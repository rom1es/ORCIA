"""Durable assistant process launch and human-anchor resume domain service (`Story 26.8`).

Routes both interactive approval continuation (`CONTINUE_IN_PROCESS`) and thematic
folder process launches through durable `WorkflowRunEntity` instantiation, mandatory
`WAITING_FOR_HUMAN_ANCHOR` pausing, and DBOS/PostgreSQL orchestration ports (`AD-19`,
`AD-20` zero SDLC vocabulary).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Protocol

from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.orchestration.models import WorkflowAsCodeDefinition, WorkflowRunEntity
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_core.permissions.models import UserIdentity

PILOT_DEFAULT_WORKFLOW_URI = "orcia://workflows/claims-engineering-delivery"


@dataclass(frozen=True, slots=True)
class DurableProcessExecutionSnapshot:
    """Durable workflow execution summary returned by `DurableProcessBackendPort`."""

    workflow_id: str
    run_status: str
    waiting_step_keys: tuple[str, ...]
    executed_step_keys: tuple[str, ...]
    snapshot_count: int


class DurableProcessBackendPort(Protocol):
    """Port connecting domain orchestration to DBOS + PostgreSQL 18 durability."""

    def is_available(self) -> bool:
        """Return True when the durable DBOS/PostgreSQL backend is active."""

    async def launch_durable_run_async(
        self,
        *,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        seed_inputs: dict[str, Any],
        trace_id: str,
    ) -> DurableProcessExecutionSnapshot:
        """Persist `run` + initial steps to SQL and start DBOS workflow execution."""

    async def resume_after_anchor_async(
        self,
        *,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        step_key: str,
        signature_id: str = "signed",
        trace_id: str = "0" * 32,
    ) -> DurableProcessExecutionSnapshot | None:
        """Signal DBOS workflow resume after human anchor signature verification."""


@dataclass(frozen=True, slots=True)
class LaunchedProcessOutcome:
    """Domain outcome of launching a durable assistant-initiated process run."""

    run: WorkflowRunEntity
    workflow_uri: str
    run_status: str
    dbos_workflow_id: str | None
    waiting_step_keys: tuple[str, ...] = field(default_factory=tuple)
    executed_step_keys: tuple[str, ...] = field(default_factory=tuple)
    snapshot_count: int = 0


class AssistantProcessLauncherService:
    """Domain service launching durable assistant processes with `WAITING_FOR_HUMAN_ANCHOR`."""

    def __init__(
        self,
        *,
        setup_service: WorkflowOrchestrationSetupService,
        engine: DurableOrchestrationEngine,
        durable_backend: DurableProcessBackendPort | None = None,
    ) -> None:
        self._setup_service = setup_service
        self._engine = engine
        self._durable_backend = durable_backend

    def set_durable_backend(self, backend: DurableProcessBackendPort | None) -> None:
        """Bind or refresh the durable DBOS/PostgreSQL backend port."""
        self._durable_backend = backend

    def resolve_workflow_definition(
        self,
        workflow_uri: str | None,
        *,
        instance: str | None = None,
    ) -> WorkflowAsCodeDefinition:
        """Resolve an explicit workflow URI or select a valid registered workflow fallback."""
        workflows = self._setup_service._workflows_by_uri
        clean_uri = (workflow_uri or "").strip()
        if clean_uri and clean_uri in workflows:
            return workflows[clean_uri]
        if clean_uri and "/" in clean_uri:
            slug = clean_uri.rsplit("/", 1)[-1]
            slug_matches = [wf for uri, wf in workflows.items() if uri.rsplit("/", 1)[-1] == slug]
            if len(slug_matches) == 1:
                return slug_matches[0]
        if clean_uri in (
            "",
            "orcia://system/workflows/assistant-agent",
            "orcia://workflows/assistant-agent",
        ):
            if PILOT_DEFAULT_WORKFLOW_URI in workflows:
                return workflows[PILOT_DEFAULT_WORKFLOW_URI]
            if workflows:
                return next(iter(workflows.values()))
        raise ResourceNotFoundError(
            detail_override=f"Workflow '{clean_uri}' introuvable.",
            instance=instance,
        )

    async def launch_process_async(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        workflow_uri: str | None,
        idempotency_token: str,
        seed_inputs: dict[str, Any] | None = None,
        trace_id: str = "0" * 32,
        instance: str | None = None,
    ) -> LaunchedProcessOutcome:
        """Instantiate durable `WorkflowRunEntity`, initialize anchors, and halt at `WAITING_*`."""
        wf = self.resolve_workflow_definition(workflow_uri, instance=instance)
        run = self._setup_service.instantiate_workflow_run(
            user,
            workflow_uri=wf.uri,
            workspace_id=workspace_id,
            trigger_id=None,
            trigger_idempotency_key=f"assistant-process:{idempotency_token}",
            execution_identity_mode="passthrough",
            instance=instance,
        )
        merged_inputs = dict(seed_inputs or {})
        self._engine._run_seed_inputs[run.id] = merged_inputs
        steps = self._engine.initialize_run_steps(
            run,
            wf,
            initialize_anchored_as_waiting=True,
        )

        if self._durable_backend is not None and self._durable_backend.is_available():
            snap = await self._durable_backend.launch_durable_run_async(
                run=run,
                workflow=wf,
                seed_inputs=merged_inputs,
                trace_id=trace_id,
            )
            return LaunchedProcessOutcome(
                run=run,
                workflow_uri=wf.uri,
                run_status=snap.run_status,
                dbos_workflow_id=snap.workflow_id,
                waiting_step_keys=snap.waiting_step_keys,
                executed_step_keys=snap.executed_step_keys,
                snapshot_count=snap.snapshot_count,
            )

        executed_keys, waiting_keys, run_status = await self._execute_in_process_until_wait_async(
            user=user,
            run=run,
            wf=wf,
            steps=steps,
            instance=instance,
        )
        snaps = self._engine.blackboard.list_all_snapshots(run.id)
        return LaunchedProcessOutcome(
            run=run,
            workflow_uri=wf.uri,
            run_status=run_status,
            dbos_workflow_id=None,
            waiting_step_keys=waiting_keys,
            executed_step_keys=executed_keys,
            snapshot_count=len(snaps),
        )

    async def resume_after_anchor_signature_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        signature_id: str = "signed",
        trace_id: str = "0" * 32,
        instance: str | None = None,
    ) -> DurableProcessExecutionSnapshot | None:
        """Resume a paused run once `step_key` has been signed in `human_anchor_signatures`."""
        run = self._engine._get_run(run_id, instance=instance)
        wf = self._engine._get_workflow(run.workflow_uri, instance=instance)
        if self._durable_backend is not None and self._durable_backend.is_available():
            return await self._durable_backend.resume_after_anchor_async(
                run=run,
                workflow=wf,
                step_key=step_key,
                signature_id=signature_id,
                trace_id=trace_id,
            )
        steps = self._engine.initialize_run_steps(run, wf, initialize_anchored_as_waiting=True)
        executed_keys, waiting_keys, run_status = await self._execute_in_process_until_wait_async(
            user=user,
            run=run,
            wf=wf,
            steps=steps,
            instance=instance,
        )
        snaps = self._engine.blackboard.list_all_snapshots(run.id)
        return DurableProcessExecutionSnapshot(
            workflow_id=f"inproc-{run.id}",
            run_status=run_status,
            waiting_step_keys=waiting_keys,
            executed_step_keys=executed_keys,
            snapshot_count=len(snaps),
        )

    async def _execute_in_process_until_wait_async(
        self,
        *,
        user: UserIdentity,
        run: WorkflowRunEntity,
        wf: WorkflowAsCodeDefinition,
        steps: tuple[Any, ...],
        instance: str | None,
    ) -> tuple[tuple[str, ...], tuple[str, ...], str]:
        """Execute steps until the first `WAITING_*` pause (never auto-advancing past an anchor)."""
        specs_by_key = {s.step_key: s for s in wf.steps}
        executed_keys: list[str] = []
        waiting_keys: list[str] = []
        for step_exec in steps:
            if step_exec.status == "COMMITTED":
                executed_keys.append(step_exec.step_key)
                continue
            spec = specs_by_key.get(step_exec.step_key)
            has_anchor = bool(
                self._engine.anchors_and_arbitration.get_step_anchors(run.id, step_exec.step_key)
            )
            if step_exec.status.startswith("WAITING_") or (
                spec is not None and spec.human_authored_required and not has_anchor
            ):
                if step_exec.status != "WAITING_FOR_HUMAN_ANCHOR" and not has_anchor:
                    self._engine.blackboard.save_step_draft(
                        run.id,
                        step_exec.step_key,
                        status="WAITING_FOR_HUMAN_ANCHOR",
                        draft_artifact=step_exec.draft_artifact,
                    )
                waiting_keys.append(step_exec.step_key)
                break
            await self._engine.execute_step_async(
                user,
                run_id=run.id,
                step_key=step_exec.step_key,
                commit_immediately=True,
                instance=instance,
            )
            executed_keys.append(step_exec.step_key)

        if waiting_keys:
            self._setup_service._runs_by_id[run.id] = replace(
                run, status="WAITING_FOR_HUMAN_ARBITRATION"
            )
            return tuple(executed_keys), tuple(waiting_keys), "WAITING_FOR_HUMAN_ARBITRATION"
        self._setup_service._runs_by_id[run.id] = replace(run, status="COMPLETED")
        return tuple(executed_keys), (), "COMPLETED"


__all__ = [
    "AssistantProcessLauncherService",
    "DurableProcessBackendPort",
    "DurableProcessExecutionSnapshot",
    "LaunchedProcessOutcome",
    "PILOT_DEFAULT_WORKFLOW_URI",
]
