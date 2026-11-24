"""WorkflowOrchestrationSetupService & Recursive `run-lock.json` Pinning (Story 3.1, AD-5, AD-18).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import json
from typing import Any

from orcia_core.catalog.cas_resolver import FederatedUriResolver
from orcia_core.catalog.models import (
    CustomizationOverrideEntity,
)
from orcia_core.catalog.override_merger import FourLayerOverrideMerger
from orcia_core.ontology import OntologyGovernanceService, build_seeded_ontology_service
from orcia_core.orchestration._run_lock_entity_builder import build_initialized_run_entity
from orcia_core.orchestration._run_lock_helpers import (
    assemble_recursive_run_lock,
    build_recursive_sub_locks_helper,
    collect_step_lock_sources,
    resolve_workflow_and_parent,
    to_catalog_workflow,
)
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.orchestration.models import (
    ArtifactTemplateDefinition,
    CompiledArtifactTemplate,
    SubWorkflowLockEntry,
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
    WorkflowTriggerEntity,
    WorkflowValidationReport,
)
from orcia_core.orchestration.template_compiler import MultiAudienceTemplateCompiler
from orcia_core.orchestration.yaml_validator import WorkflowAsCodeValidator
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import ExecutionIdentityMode, UserIdentity, WorkspaceEntity
from orcia_kernel.ids import new_uuid7_str


def _to_catalog_workflow(wf: WorkflowAsCodeDefinition) -> Any:
    return to_catalog_workflow(wf)


class WorkflowOrchestrationSetupService:
    """Domain service for Story 3.1: Workflow-as-Code, Templates & `run-lock.json`."""

    def __init__(
        self,
        *,
        evaluator: MatrixPermissionEvaluator,
        resolver: FederatedUriResolver | None = None,
        ontology_service: OntologyGovernanceService | None = None,
        workflows: tuple[WorkflowAsCodeDefinition, ...] = (),
        templates: tuple[ArtifactTemplateDefinition, ...] = (),
        overrides: tuple[CustomizationOverrideEntity, ...] = (),
        triggers: tuple[WorkflowTriggerEntity, ...] = (),
        kb_snapshot_hash: str = "kb-snap-sha256-000000000000000000000000000000000000000000000001",
    ) -> None:
        self.evaluator = evaluator
        self.resolver = resolver or FederatedUriResolver()
        self.ontology_service = ontology_service or build_seeded_ontology_service()
        self._workflows_by_uri: dict[str, WorkflowAsCodeDefinition] = {}
        self._templates_by_key: dict[str, ArtifactTemplateDefinition] = {
            t.template_key: t for t in templates
        }
        self._overrides: list[CustomizationOverrideEntity] = list(overrides)
        self._triggers_by_id: dict[str, WorkflowTriggerEntity] = {t.id: t for t in triggers}
        self._runs_by_id: dict[str, WorkflowRunEntity] = {}
        self._idempotency_index: dict[tuple[str, str], str] = {}
        self.kb_snapshot_hash = kb_snapshot_hash
        self.engine = DurableOrchestrationEngine(setup_service=self)

        for wf in workflows:
            self.register_validated_workflow(wf)

    def register_validated_workflow(self, wf: WorkflowAsCodeDefinition) -> None:
        """Register an already validated workflow definition and prewarm CAS."""
        self._workflows_by_uri[wf.uri] = wf
        self.resolver.register_upstream_payload(
            wf.uri,
            json.dumps({"uri": wf.uri, "version": wf.version, "sha256": wf.sha256}, sort_keys=True),
            resolved_version=wf.version,
            prewarm_cas=True,
        )

    @property
    def workflows(self) -> tuple[WorkflowAsCodeDefinition, ...]:
        return tuple(self._workflows_by_uri.values())

    @property
    def templates(self) -> tuple[ArtifactTemplateDefinition, ...]:
        return tuple(self._templates_by_key.values())

    @property
    def runs(self) -> tuple[WorkflowRunEntity, ...]:
        return tuple(self._runs_by_id.values())

    @property
    def triggers(self) -> tuple[WorkflowTriggerEntity, ...]:
        return tuple(self._triggers_by_id.values())

    def set_run_status(self, run_id: str, status: str) -> WorkflowRunEntity:
        """Update the lifecycle status of a registered `WorkflowRunEntity` (`Story 3.2f`)."""
        from dataclasses import replace

        existing = self._runs_by_id.get(run_id)
        if existing is None:
            raise ResourceNotFoundError(
                detail_code="ERR_WORKFLOW_RUN_NOT_FOUND",
                detail_params={"run_id": run_id},
            )
        updated = replace(existing, status=status)  # type: ignore[arg-type]
        self._runs_by_id[run_id] = updated
        return updated

    def _enforce_mutation_guard(
        self, user: UserIdentity, workspace_id: str | None, *, instance: str | None = None
    ) -> None:
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        if workspace_id is not None:
            self.evaluator.enforce_scope_mutation_guard(user, workspace_id, instance=instance)
        elif user.platform_role == "BU_DIRECTOR":
            raise ObserverModeReadOnlyError(instance=instance)

    def validate_workflow_manifest(
        self,
        raw_manifest: str,
        *,
        workspace_id: str | None = None,
        raise_on_error: bool = False,
        instance: str | None = None,
    ) -> WorkflowValidationReport:
        """Validate a YAML/JSON Workflow-as-Code manifest against known sub-workflows."""
        return WorkflowAsCodeValidator.validate_manifest(
            raw_manifest,
            workspace_id=workspace_id,
            known_workflows=self._workflows_by_uri,
            raise_on_error=raise_on_error,
            instance=instance,
        )

    def register_workflow_manifest(
        self,
        user: UserIdentity,
        raw_manifest: str,
        *,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> WorkflowAsCodeDefinition:
        """Validate and register a Workflow-as-Code YAML/JSON manifest (`ScopeAccessGuard`)."""
        self._enforce_mutation_guard(user, workspace_id, instance=instance)
        report = self.validate_workflow_manifest(
            raw_manifest, workspace_id=workspace_id, raise_on_error=True, instance=instance
        )
        assert report.workflow is not None
        self.register_validated_workflow(report.workflow)
        return report.workflow

    def compile_artifact_template(
        self,
        template_key: str,
        *,
        variables: dict[str, str] | None = None,
        workspace_id: str = "ws-solution-paiement",
        instance: str | None = None,
    ) -> CompiledArtifactTemplate:
        """Compile a registered Multi-Audience Artifact Template against active Ontology."""
        template = self._templates_by_key.get(template_key)
        if template is None:
            raise ResourceNotFoundError(
                detail_code="ERR_ARTIFACT_TEMPLATE_NOT_FOUND",
                detail_params={"template_key": template_key},
                instance=instance,
            )
        snapshot = self.ontology_service.resolve_snapshot(workspace_scope_id=workspace_id)
        return MultiAudienceTemplateCompiler.compile_template(
            template,
            variables=variables,
            ontology_snapshot=snapshot,
            instance=instance,
        )

    def _build_recursive_sub_locks(
        self,
        wf: WorkflowAsCodeDefinition,
        *,
        workspace: WorkspaceEntity,
        user_id: str | None,
        depth: int,
        call_stack: tuple[str, ...],
        instance: str | None = None,
    ) -> tuple[SubWorkflowLockEntry, ...]:
        return build_recursive_sub_locks_helper(
            wf,
            workflows_by_uri=self._workflows_by_uri,
            org_units=self.evaluator.org_units,
            overrides=tuple(self._overrides),
            resolver=self.resolver,
            workspace=workspace,
            user_id=user_id,
            depth=depth,
            call_stack=call_stack,
            instance=instance,
        )

    def instantiate_workflow_run(
        self,
        user: UserIdentity,
        *,
        workflow_uri: str,
        workspace_id: str,
        parent_run_id: str | None = None,
        parent_step_execution_id: str | None = None,
        trigger_id: str | None = None,
        trigger_idempotency_key: str | None = None,
        execution_identity_mode: ExecutionIdentityMode = "passthrough",
        instance: str | None = None,
    ) -> WorkflowRunEntity:
        """Instantiate a `Workflow Run` and recursively lock `run-lock.json` (`FR-15`, `FR-30`)."""
        self._enforce_mutation_guard(user, workspace_id, instance=instance)
        workspace = self.evaluator.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError(instance=instance)
        if self.evaluator.resolve_workspace_access(user, workspace.id) is None:
            raise ScopeAccessDeniedError(instance=instance)

        if trigger_id and trigger_idempotency_key:
            existing_run_id = self._idempotency_index.get((trigger_id, trigger_idempotency_key))
            if existing_run_id and existing_run_id in self._runs_by_id:
                return self._runs_by_id[existing_run_id]

        wf, nesting_depth, root_run_id_candidate = resolve_workflow_and_parent(
            self._workflows_by_uri,
            self._runs_by_id,
            workflow_uri=workflow_uri,
            parent_run_id=parent_run_id,
            instance=instance,
        )

        merged = FourLayerOverrideMerger.merge_and_lock(
            base_workflow=_to_catalog_workflow(wf),
            org_units=self.evaluator.org_units,
            workspace=workspace,
            user_id=user.id,
            overrides=tuple(self._overrides),
            resolver=self.resolver,
        )

        sorted_sources = collect_step_lock_sources(wf, merged.run_lock.sources, self.resolver)
        sub_locks = self._build_recursive_sub_locks(
            wf,
            workspace=workspace,
            user_id=user.id,
            depth=nesting_depth,
            call_stack=(wf.uri,),
            instance=instance,
        )

        run_id = new_uuid7_str()
        root_run_id = root_run_id_candidate or run_id
        recursive_lock = assemble_recursive_run_lock(
            run_id=run_id,
            workspace=workspace,
            wf=wf,
            effective_workflow_sha256=merged.effective_workflow.sha256,
            applied_override_keys=merged.applied_override_keys,
            kb_snapshot_hash=self.kb_snapshot_hash,
            sorted_sources=sorted_sources,
            sub_locks=sub_locks,
        )
        run_entity = build_initialized_run_entity(
            run_id=run_id,
            root_run_id=root_run_id,
            workspace_id=workspace.id,
            wf=wf,
            parent_run_id=parent_run_id,
            parent_step_execution_id=parent_step_execution_id,
            nesting_depth=nesting_depth,
            trigger_id=trigger_id,
            trigger_idempotency_key=trigger_idempotency_key,
            user_id=user.id,
            execution_identity_mode=execution_identity_mode,
            recursive_lock=recursive_lock,
        )
        self._runs_by_id[run_id] = run_entity
        self.engine.initialize_run_steps(run_entity, wf)
        if trigger_id and trigger_idempotency_key:
            self._idempotency_index[(trigger_id, trigger_idempotency_key)] = run_id
        return run_entity
