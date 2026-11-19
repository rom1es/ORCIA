"""Pydantic v2 response serializers for Epic 3 orchestration routers (`AD-19`)."""

from __future__ import annotations

from orcia_api.schemas.blackboard import (
    ArbitrationOptionSchemaItem,
    BackgroundAuditReportSchemaItem,
    BlackboardSnapshotSchemaItem,
    HumanAnchorSignatureSchemaItem,
    HumanArbitrationRequestSchemaItem,
    HydratedStepContextSchemaItem,
    StepExecutionSchemaItem,
    StepMemlogSchemaItem,
)
from orcia_core.blackboard import (
    BackgroundAuditConsolidatedReport,
    BlackboardSnapshotEntity,
    HydratedStepContext,
    StepExecutionEntity,
    StepMemlogEntry,
)
from orcia_core.orchestration import (
    HumanAnchorSignatureEntity,
    HumanArbitrationRequestEntity,
)


def serialize_memlog(entry: StepMemlogEntry) -> StepMemlogSchemaItem:
    return StepMemlogSchemaItem(
        entry_id=entry.entry_id,
        step_key=entry.step_key,
        marker_type=entry.marker_type,
        summary=entry.summary,
        details=entry.details,
        source_uris=list(entry.source_uris),
    )


def serialize_snapshot(snap: BlackboardSnapshotEntity) -> BlackboardSnapshotSchemaItem:
    return BlackboardSnapshotSchemaItem(
        id=snap.id,
        snapshot_key=snap.snapshot_key,
        run_id=snap.run_id,
        step_execution_id=snap.step_execution_id,
        parent_snapshot_id=snap.parent_snapshot_id,
        step_key=snap.step_key,
        branch_status=snap.branch_status,
        artifact_payload=dict(snap.artifact_payload),
        artifact_cas_key=snap.artifact_cas_key,
        artifact_sha256=snap.artifact_sha256,
        memlog_summary=[serialize_memlog(m) for m in snap.memlog_summary],
        superseded_snapshot_ids=list(snap.superseded_snapshot_ids),
    )


def serialize_step_exec(step: StepExecutionEntity) -> StepExecutionSchemaItem:
    return StepExecutionSchemaItem(
        id=step.id,
        step_execution_key=step.step_execution_key,
        run_id=step.run_id,
        step_key=step.step_key,
        step_index=step.step_index,
        step_type=step.step_type,
        execution_mode=step.execution_mode,
        status=step.status,
        attempt_count=step.attempt_count,
        max_agent_retries=step.max_agent_retries,
        draft_artifact=dict(step.draft_artifact),
        draft_cas_key=step.draft_cas_key,
        step_memlog=[serialize_memlog(m) for m in step.step_memlog],
        hydrated_input_uris=list(step.hydrated_input_uris),
        child_run_id=step.child_run_id,
        committed_snapshot_id=step.committed_snapshot_id,
        cost_usd=step.cost_usd,
    )


def serialize_hydrated(ctx: HydratedStepContext) -> HydratedStepContextSchemaItem:
    return HydratedStepContextSchemaItem(
        run_id=ctx.run_id,
        step_key=ctx.step_key,
        step_title=ctx.step_title,
        step_type=ctx.step_type,
        execution_mode=ctx.execution_mode,
        step_directive=ctx.step_directive,
        declared_input_uris=list(ctx.declared_input_uris),
        resolved_inputs=dict(ctx.resolved_inputs),
        future_step_instructions_leaked=ctx.future_step_instructions_leaked,
        undeclared_artifacts_leaked=ctx.undeclared_artifacts_leaked,
    )


def serialize_audit_report(
    rep: BackgroundAuditConsolidatedReport,
) -> BackgroundAuditReportSchemaItem:
    return BackgroundAuditReportSchemaItem(
        run_id=rep.run_id,
        workflow_uri=rep.workflow_uri,
        total_steps_committed=rep.total_steps_committed,
        assumptions=[serialize_memlog(m) for m in rep.assumptions],
        suspected_code_bugs=[serialize_memlog(m) for m in rep.suspected_code_bugs],
        suspected_obsolete_docs=[serialize_memlog(m) for m in rep.suspected_obsolete_docs],
        sse_event_topic=rep.sse_event_topic,
        sse_latency_ms=rep.sse_latency_ms,
    )


def serialize_anchor(sig: HumanAnchorSignatureEntity) -> HumanAnchorSignatureSchemaItem:
    return HumanAnchorSignatureSchemaItem(
        id=sig.id,
        signature_key=sig.signature_key,
        workspace_id=sig.workspace_id,
        run_id=sig.run_id,
        step_execution_id=sig.step_execution_id,
        step_key=sig.step_key,
        section_key=sig.section_key,
        content_text=sig.content_text,
        content_sha256=sig.content_sha256,
        char_length=sig.char_length,
        authored_by_user_id=sig.authored_by_user_id,
        author_display_name=sig.author_display_name,
        signature_hash=sig.signature_hash,
    )


def serialize_arbitration(
    arb: HumanArbitrationRequestEntity,
) -> HumanArbitrationRequestSchemaItem:
    return HumanArbitrationRequestSchemaItem(
        id=arb.id,
        arbitration_key=arb.arbitration_key,
        workspace_id=arb.workspace_id,
        run_id=arb.run_id,
        step_execution_id=arb.step_execution_id,
        step_key=arb.step_key,
        tie_break_policy=arb.tie_break_policy,
        status=arb.status,
        question_title=arb.question_title,
        context_summary=arb.context_summary,
        options_matrix=[
            ArbitrationOptionSchemaItem(
                option_key=o.option_key,
                title=o.title,
                pros=list(o.pros),
                cons=list(o.cons),
                si_impact=o.si_impact,
                finops_impact=o.finops_impact,
                recommended=o.recommended,
                ontology_concept_key=o.ontology_concept_key,
            )
            for o in arb.options_matrix
        ],
        selected_option_key=arb.selected_option_key,
        human_justification=arb.human_justification,
        resolved_by_user_id=arb.resolved_by_user_id,
        resolved_by_axiom_key=arb.resolved_by_axiom_key,
        outbox_event_id=arb.outbox_event_id,
    )
