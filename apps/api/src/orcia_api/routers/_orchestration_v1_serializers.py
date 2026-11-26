"""Response serializers for `orcia_api.routers.orchestration` (`Story 3.1`, `<= 200 L`)."""

from __future__ import annotations

from orcia_api.schemas.catalog import RunLockSourceTripletItem
from orcia_api.schemas.orchestration import (
    CompiledArtifactTemplateSchemaItem,
    CompiledMarkdownChunkSchemaItem,
    RecursiveRunLockManifestSchemaItem,
    SubWorkflowLockSchemaItem,
    WorkflowAsCodeDefinitionSchemaItem,
    WorkflowRunSchemaItem,
    WorkflowStepSpecSchemaItem,
)
from orcia_core.orchestration import (
    CompiledArtifactTemplate,
    RecursiveRunLockManifest,
    SubWorkflowLockEntry,
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
)


def serialize_workflow(wf: WorkflowAsCodeDefinition) -> WorkflowAsCodeDefinitionSchemaItem:
    return WorkflowAsCodeDefinitionSchemaItem(
        id=wf.id,
        workspace_id=wf.workspace_id,
        uri=wf.uri,
        title=wf.title,
        description=wf.description,
        version=wf.version,
        criticality=wf.criticality,
        execution_regime=wf.execution_regime,
        tie_break_policy=wf.tie_break_policy,
        mode=wf.mode,
        adaptive_gate_policy=wf.adaptive_gate_policy,
        max_cost_usd=wf.max_cost_usd,
        scalars=dict(wf.scalars),
        datasources=list(wf.datasources),
        rules=list(wf.rules),
        facts=list(wf.facts),
        steps=[
            WorkflowStepSpecSchemaItem(
                step_key=s.step_key,
                title=s.title,
                step_type=s.step_type,
                instructions=s.instructions,
                depends_on=list(s.depends_on),
                feedback_target_step_key=s.feedback_target_step_key,
                max_agent_retries=s.max_agent_retries,
                agent_uri=s.agent_uri,
                skill_uri=s.skill_uri,
                sub_workflow_uri=s.sub_workflow_uri,
                input_mapping=dict(s.input_mapping),
                output_mapping=dict(s.output_mapping),
                template_key=s.template_key,
                kb_uris=list(s.kb_uris),
                human_authored_required=s.human_authored_required,
                requires_human_gate=s.requires_human_gate,
                declares_intention=s.declares_intention or ("sdlc.declares_intention" in s.tags),
                writes_code="sdlc.writes_code" in s.tags,
                reverse_doc_from_code=s.reverse_doc_from_code
                or ("sdlc.reverse_doc_from_code" in s.tags),
                tags=list(s.tags),
                policies=list(s.policies),
                verification_window_seconds=s.verification_window_seconds,
                line_number=s.line_number,
            )
            for s in wf.steps
        ],
        sha256=wf.sha256,
        max_nesting_depth=wf.max_nesting_depth,
    )


def serialize_compiled_template(
    compiled: CompiledArtifactTemplate,
) -> CompiledArtifactTemplateSchemaItem:
    return CompiledArtifactTemplateSchemaItem(
        template_key=compiled.template_key,
        uri=compiled.uri,
        version=compiled.version,
        human_markdown_view=compiled.human_markdown_view,
        cognitive_chunks=[
            CompiledMarkdownChunkSchemaItem(
                chunk_index=c.chunk_index,
                section_key=c.section_key,
                section_title=c.section_title,
                markdown_content=c.markdown_content,
                word_count=c.word_count,
                human_authored_required=c.human_authored_required,
            )
            for c in compiled.cognitive_chunks
        ],
        agent_json_schema=dict(compiled.agent_json_schema),
        bound_ontology_terms=list(compiled.bound_ontology_terms),
        sha256=compiled.sha256,
    )


def serialize_sub_lock(entry: SubWorkflowLockEntry) -> SubWorkflowLockSchemaItem:
    return SubWorkflowLockSchemaItem(
        step_key=entry.step_key,
        workflow_uri=entry.workflow_uri,
        workflow_version=entry.workflow_version,
        workflow_sha256=entry.workflow_sha256,
        effective_workflow_sha256=entry.effective_workflow_sha256,
        nesting_depth=entry.nesting_depth,
        applied_override_keys=list(entry.applied_override_keys),
        sources=[
            RunLockSourceTripletItem(
                alias=s.alias,
                scheme=s.scheme,
                uri=s.uri,
                resolved_version=s.resolved_version,
                sha256=s.sha256,
                cas_key=s.cas_key,
            )
            for s in entry.sources
        ],
        sub_workflow_locks=[serialize_sub_lock(child) for child in entry.sub_workflow_locks],
    )


def serialize_run_lock(rl: RecursiveRunLockManifest) -> RecursiveRunLockManifestSchemaItem:
    return RecursiveRunLockManifestSchemaItem(
        run_id=rl.run_id,
        workspace_id=rl.workspace_id,
        workflow_uri=rl.workflow_uri,
        workflow_version=rl.workflow_version,
        workflow_sha256=rl.workflow_sha256,
        effective_workflow_sha256=rl.effective_workflow_sha256,
        overrides_sha256=rl.overrides_sha256,
        kb_snapshot_hash=rl.kb_snapshot_hash,
        applied_override_keys=list(rl.applied_override_keys),
        sources=[
            RunLockSourceTripletItem(
                alias=s.alias,
                scheme=s.scheme,
                uri=s.uri,
                resolved_version=s.resolved_version,
                sha256=s.sha256,
                cas_key=s.cas_key,
            )
            for s in rl.sources
        ],
        sub_workflow_locks=[serialize_sub_lock(sub) for sub in rl.sub_workflow_locks],
        manifest_sha256=rl.manifest_sha256,
    )


def serialize_run(run: WorkflowRunEntity) -> WorkflowRunSchemaItem:
    return WorkflowRunSchemaItem(
        id=run.id,
        run_key=run.run_key,
        workspace_id=run.workspace_id,
        workflow_def_id=run.workflow_def_id,
        workflow_uri=run.workflow_uri,
        parent_run_id=run.parent_run_id,
        parent_step_execution_id=run.parent_step_execution_id,
        root_run_id=run.root_run_id,
        nesting_depth=run.nesting_depth,
        execution_regime=run.execution_regime,
        criticality=run.criticality,
        trigger_id=run.trigger_id,
        trigger_idempotency_key=run.trigger_idempotency_key,
        status=run.status,
        initiated_by_user_id=run.initiated_by_user_id,
        execution_identity_mode=run.execution_identity_mode,
        budget_max_usd=run.budget_max_usd,
        run_lock=serialize_run_lock(run.run_lock),
    )


__all__ = [
    "serialize_compiled_template",
    "serialize_run",
    "serialize_run_lock",
    "serialize_sub_lock",
    "serialize_workflow",
]
