"""WorkflowOrchestrationSetupService & Recursive `run-lock.json` Pinning (Story 3.1, AD-5, AD-18).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import json

from orcia_core.catalog.cas_resolver import FederatedUriResolver, compute_bytes_sha256
from orcia_core.catalog.models import (
    CustomizationOverrideEntity,
    RunLockSourceTriplet,
    WorkflowDefinitionEntity,
    WorkflowStepDefinition,
)
from orcia_core.catalog.override_merger import FourLayerOverrideMerger
from orcia_core.ontology import OntologyGovernanceService, build_seeded_ontology_service
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    SubWorkflowCycleDetectedError,
    SubWorkflowMaxDepthExceededError,
)
from orcia_core.orchestration.models import (
    MAX_SUB_WORKFLOW_NESTING_DEPTH,
    ArtifactTemplateDefinition,
    CompiledArtifactTemplate,
    RecursiveRunLockManifest,
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


def _to_catalog_workflow(wf: WorkflowAsCodeDefinition) -> WorkflowDefinitionEntity:
    return WorkflowDefinitionEntity(
        id=wf.id,
        workspace_id=wf.workspace_id,
        uri=wf.uri,
        title=wf.title,
        description=wf.description,
        version=wf.version,
        source_format="ORCIA",
        adaptive_gate_policy=wf.adaptive_gate_policy,
        scalars=dict(wf.scalars),
        datasources=wf.datasources,
        rules=wf.rules,
        facts=wf.facts,
        lenses=(),
        steps=tuple(
            WorkflowStepDefinition(
                step_key=s.step_key,
                title=s.title,
                instructions=s.instructions,
                human_authored_required=s.human_authored_required,
            )
            for s in wf.steps
        ),
        sha256=wf.sha256,
    )


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
                detail_override=f"Gabarit d'artefact '{template_key}' introuvable.",
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
        entries: list[SubWorkflowLockEntry] = []
        for step in wf.steps:
            if step.step_type != "SUB_WORKFLOW" or not step.sub_workflow_uri:
                continue
            target_uri = step.sub_workflow_uri
            next_depth = depth + 1
            if target_uri in call_stack:
                raise SubWorkflowCycleDetectedError(
                    detail_override=(
                        f"Cycle d'appels SUB_WORKFLOW détecté: "
                        f"{' -> '.join((*call_stack, target_uri))}."
                    ),
                    instance=instance,
                )
            if next_depth > MAX_SUB_WORKFLOW_NESTING_DEPTH:
                raise SubWorkflowMaxDepthExceededError(
                    detail_override=(
                        f"Profondeur SUB_WORKFLOW {next_depth} > {MAX_SUB_WORKFLOW_NESTING_DEPTH} "
                        f"pour '{target_uri}'."
                    ),
                    instance=instance,
                )
            child_wf = self._workflows_by_uri.get(target_uri)
            if child_wf is None:
                raise ResourceNotFoundError(
                    detail_override=f"Sous-workflow cible '{target_uri}' introuvable.",
                    instance=instance,
                )
            merged_child = FourLayerOverrideMerger.merge_and_lock(
                base_workflow=_to_catalog_workflow(child_wf),
                org_units=self.evaluator.org_units,
                workspace=workspace,
                user_id=user_id,
                overrides=tuple(self._overrides),
                resolver=self.resolver,
            )
            nested_locks = self._build_recursive_sub_locks(
                child_wf,
                workspace=workspace,
                user_id=user_id,
                depth=next_depth,
                call_stack=(*call_stack, target_uri),
                instance=instance,
            )
            entries.append(
                SubWorkflowLockEntry(
                    step_key=step.step_key,
                    workflow_uri=child_wf.uri,
                    workflow_version=child_wf.version,
                    workflow_sha256=child_wf.sha256,
                    effective_workflow_sha256=merged_child.effective_workflow.sha256,
                    nesting_depth=next_depth,
                    applied_override_keys=merged_child.applied_override_keys,
                    sources=merged_child.run_lock.sources,
                    sub_workflow_locks=nested_locks,
                )
            )
        return tuple(entries)

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

        wf = self._workflows_by_uri.get(workflow_uri.strip())
        if wf is None:
            raise ResourceNotFoundError(
                detail_override=f"Workflow '{workflow_uri}' introuvable.", instance=instance
            )

        if trigger_id and trigger_idempotency_key:
            existing_run_id = self._idempotency_index.get((trigger_id, trigger_idempotency_key))
            if existing_run_id and existing_run_id in self._runs_by_id:
                return self._runs_by_id[existing_run_id]

        nesting_depth = 0
        root_run_id_candidate: str | None = None
        if parent_run_id is not None:
            parent_run = self._runs_by_id.get(parent_run_id)
            if parent_run is None:
                raise ResourceNotFoundError(
                    detail_override=f"Run parent '{parent_run_id}' introuvable.", instance=instance
                )
            nesting_depth = parent_run.nesting_depth + 1
            if nesting_depth > MAX_SUB_WORKFLOW_NESTING_DEPTH:
                raise SubWorkflowMaxDepthExceededError(instance=instance)
            root_run_id_candidate = parent_run.root_run_id

        merged = FourLayerOverrideMerger.merge_and_lock(
            base_workflow=_to_catalog_workflow(wf),
            org_units=self.evaluator.org_units,
            workspace=workspace,
            user_id=user.id,
            overrides=tuple(self._overrides),
            resolver=self.resolver,
        )

        extra_triplets: list[RunLockSourceTriplet] = list(merged.run_lock.sources)
        seen_uris = {t.uri for t in extra_triplets}
        for step in wf.steps:
            for step_uri in (step.agent_uri, step.skill_uri, *step.kb_uris):
                if step_uri and step_uri not in seen_uris:
                    res = self.resolver.resolve(step_uri)
                    seen_uris.add(res.uri)
                    extra_triplets.append(
                        RunLockSourceTriplet(
                            alias=f"step-{step.step_key}-{res.scheme}",
                            scheme=res.scheme,
                            uri=res.uri,
                            resolved_version=res.resolved_version,
                            sha256=res.sha256,
                            cas_key=res.cas_key,
                        )
                    )

        sorted_sources = tuple(sorted(extra_triplets, key=lambda t: (t.alias, t.uri)))
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
        overrides_sha256 = compute_bytes_sha256(
            json.dumps(list(merged.applied_override_keys)).encode("utf-8")
        )
        manifest_payload = json.dumps(
            {
                "run_id": run_id,
                "workspace_id": workspace.id,
                "workflow_uri": wf.uri,
                "workflow_version": wf.version,
                "workflow_sha256": wf.sha256,
                "effective_workflow_sha256": merged.effective_workflow.sha256,
                "overrides_sha256": overrides_sha256,
                "kb_snapshot_hash": self.kb_snapshot_hash,
                "applied_override_keys": list(merged.applied_override_keys),
                "sources": [
                    {
                        "alias": s.alias,
                        "scheme": s.scheme,
                        "uri": s.uri,
                        "resolved_version": s.resolved_version,
                        "sha256": s.sha256,
                        "cas_key": s.cas_key,
                    }
                    for s in sorted_sources
                ],
                "sub_workflow_locks": [sub.to_dict() for sub in sub_locks],
            },
            sort_keys=True,
        )
        recursive_lock = RecursiveRunLockManifest(
            run_id=run_id,
            workspace_id=workspace.id,
            workflow_uri=wf.uri,
            workflow_version=wf.version,
            workflow_sha256=wf.sha256,
            effective_workflow_sha256=merged.effective_workflow.sha256,
            overrides_sha256=overrides_sha256,
            kb_snapshot_hash=self.kb_snapshot_hash,
            applied_override_keys=merged.applied_override_keys,
            sources=sorted_sources,
            sub_workflow_locks=sub_locks,
            manifest_sha256=compute_bytes_sha256(manifest_payload.encode("utf-8")),
        )
        run_entity = WorkflowRunEntity(
            id=run_id,
            run_key=f"run-{wf.uri.split('/')[-1]}-{run_id[-6:]}",
            workspace_id=workspace.id,
            workflow_def_id=wf.id,
            workflow_uri=wf.uri,
            parent_run_id=parent_run_id,
            parent_step_execution_id=parent_step_execution_id,
            root_run_id=root_run_id,
            nesting_depth=nesting_depth,
            execution_regime=wf.execution_regime,
            criticality=wf.criticality,
            trigger_id=trigger_id,
            trigger_idempotency_key=trigger_idempotency_key,
            status="INITIALIZED",
            initiated_by_user_id=user.id,
            execution_identity_mode=execution_identity_mode,
            budget_max_usd=wf.max_cost_usd,
            run_lock=recursive_lock,
        )
        self._runs_by_id[run_id] = run_entity
        self.engine.initialize_run_steps(run_entity, wf)
        if trigger_id and trigger_idempotency_key:
            self._idempotency_index[(trigger_id, trigger_idempotency_key)] = run_id
        return run_entity
