"""SQL / Outbox / DBOS Persistence Wiring & Serializers for Epic 3 Routers (`AD-2`, `AD-19`).

Bridges FastAPI orchestration routes (`orchestration.py`, `blackboard_and_engine.py`,
`challenge_and_replay.py`) with `SqlOrchestrationRepository`, `SqlDomainEventsOutboxRepository`,
`DbosSqlAlchemyUnitOfWork`, and `DbosDurableWorkflowEngine` when `dbos_uow` (or `session_maker`)
is attached to `request.app.state`, while keeping router files well below `350` lines.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

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
    DbosDurableWorkflowEngine,
    DbosSqlAlchemyUnitOfWork,
    DurableWorkflowRunSummary,
    HumanAnchorSignatureEntity,
    HumanArbitrationRequestEntity,
    SqlDomainEventsOutboxRepository,
    SqlOrchestrationRepository,
    WorkflowRunEntity,
)
from orcia_kernel.events import (
    ArtifactProduced,
    HumanArbitrationRequested,
    RunTerminated,
    StepCompleted,
)


def resolve_optional_dbos_uow(request: Request) -> DbosSqlAlchemyUnitOfWork | None:
    """Return `DbosSqlAlchemyUnitOfWork` when attached to `request.app.state`."""
    uow: DbosSqlAlchemyUnitOfWork | None = getattr(request.app.state, "dbos_uow", None)
    if uow is not None:
        return uow
    datasource: Any = getattr(request.app.state, "dbos_datasource", None)
    if datasource is not None:
        uow = DbosSqlAlchemyUnitOfWork(datasource)
        request.app.state.dbos_uow = uow
        return uow
    return None


def resolve_optional_sql_orchestration_repo(request: Request) -> SqlOrchestrationRepository | None:
    """Build `SqlOrchestrationRepository` when `dbos_uow` is available on `request.app.state`."""
    uow = resolve_optional_dbos_uow(request)
    if uow is None:
        return None
    return SqlOrchestrationRepository(uow)


def resolve_optional_sql_outbox_repo(request: Request) -> SqlDomainEventsOutboxRepository | None:
    """Build `SqlDomainEventsOutboxRepository` when `dbos_uow` is present on `app.state`."""
    uow = resolve_optional_dbos_uow(request)
    if uow is None:
        return None
    return SqlDomainEventsOutboxRepository(uow)


def resolve_optional_dbos_durable_engine(request: Request) -> DbosDurableWorkflowEngine | None:
    """Build `DbosDurableWorkflowEngine` when `dbos_uow` is available on `request.app.state`."""
    uow = resolve_optional_dbos_uow(request)
    if uow is None:
        return None
    sys_url = "postgresql://localhost:5432/orcia"
    app_url = "postgresql+asyncpg://localhost:5432/orcia"
    engine = DbosDurableWorkflowEngine(
        system_database_url=sys_url,
        application_database_url=app_url,
    )
    engine._uow = uow
    engine._repository = SqlOrchestrationRepository(uow)
    return engine


async def sync_instantiated_run_to_sql(
    request: Request,
    run: WorkflowRunEntity,
    *,
    initial_steps: tuple[StepExecutionEntity, ...] = (),
) -> None:
    """Persist an instantiated `WorkflowRunEntity` and its initial steps in PostgreSQL 18."""
    import sqlalchemy as sa

    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    if uow is None or sql_repo is None:
        return
    resolved_wf_def_id = run.workflow_def_id
    async with uow.session_scope() as session:
        existing_id = (
            await session.execute(
                sa.text("SELECT id::text FROM workflow_definitions WHERE uri = :uri LIMIT 1"),
                {"uri": run.workflow_uri},
            )
        ).scalar_one_or_none()
        if existing_id is not None:
            resolved_wf_def_id = str(existing_id)

    await sql_repo.upsert_workflow_run(
        run_id=run.id,
        run_key=run.run_key,
        workspace_id=run.workspace_id,
        workflow_def_id=resolved_wf_def_id,
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
    )
    for step in initial_steps:
        await sql_repo.upsert_step_execution(step)


async def sync_step_execution_and_snapshot_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    step_exec: StepExecutionEntity,
    snapshot: BlackboardSnapshotEntity | None,
    trace_id: str,
) -> None:
    """Persist `step_executions`, append-only `blackboard_snapshots` and `domain_events_outbox`."""
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if sql_repo is None or outbox_repo is None:
        return

    await sql_repo.upsert_step_execution(step_exec)
    await sql_repo.update_run_status(run.id, run.status)

    if snapshot is not None:
        evt_step = StepCompleted.create(
            step_execution_id=step_exec.id,
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_key=step_exec.step_key,
            cost_usd=step_exec.cost_usd,
            trace_id=trace_id,
        )
        evt_art = ArtifactProduced.create(
            snapshot_id=snapshot.id,
            run_id=run.id,
            workspace_id=run.workspace_id,
            artifact_cas_key=snapshot.artifact_cas_key or f"cas/sha256/{step_exec.step_key}",
            artifact_sha256=snapshot.artifact_sha256 or ("a" * 64),
            trace_id=trace_id,
        )
        await sql_repo.append_snapshot(
            run_id=run.id,
            step_execution_id=step_exec.id,
            step_key=snapshot.step_key,
            branch_status=snapshot.branch_status,
            artifact_payload=dict(snapshot.artifact_payload),
            parent_snapshot_id=snapshot.parent_snapshot_id,
            memlog_summary=snapshot.memlog_summary,
            superseded_snapshot_ids=snapshot.superseded_snapshot_ids,
            outbox_events=(evt_step, evt_art),
        )
        if run.status == "COMPLETED":
            await outbox_repo.enqueue_event(
                RunTerminated.create(
                    run_id=run.id,
                    workspace_id=run.workspace_id,
                    final_status=run.status,
                    total_cost_usd=step_exec.cost_usd,
                    trace_id=trace_id,
                )
            )


async def sync_arbitration_request_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    arb: HumanArbitrationRequestEntity,
    step_exec: StepExecutionEntity,
    trace_id: str,
) -> None:
    """Persist paused arbitration step status and enqueue `HumanArbitrationRequested` in Outbox."""
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if sql_repo is None or outbox_repo is None:
        return
    await sql_repo.upsert_step_execution(step_exec)
    await sql_repo.update_run_status(run.id, run.status)
    await outbox_repo.enqueue_event(
        HumanArbitrationRequested.create(
            arbitration_id=arb.id,
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_key=arb.step_key,
            options_count=len(arb.options_matrix),
            trace_id=trace_id,
        )
    )


async def read_sql_blackboard_if_available(
    request: Request,
    run_id: str,
) -> tuple[str | None, tuple[StepExecutionEntity, ...], tuple[BlackboardSnapshotEntity, ...]]:
    """Read `run_status`, `step_executions`, and `blackboard_snapshots` from PostgreSQL 18."""
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if sql_repo is None or outbox_repo is None:
        return None, (), ()
    try:
        status = await sql_repo.get_run_status(run_id)
    except Exception as exc:
        from orcia_core.observability.logging import get_logger

        get_logger("orcia.api.orchestration").warning(
            "sql_blackboard_get_run_status_fallback", run_id=run_id, error_type=type(exc).__name__
        )
        return None, (), ()
    steps = await sql_repo.list_step_executions(run_id)
    snapshots = await sql_repo.list_snapshots(run_id)
    await outbox_repo.list_events_by_run(run_id)
    return status, steps, snapshots


async def sync_replay_fork_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    step_key: str,
    revised_payload: dict[str, Any] | None,
) -> DurableWorkflowRunSummary | None:
    """Persist an append-only rewind/fork snapshot via `DbosDurableWorkflowEngine`."""
    durable_engine = resolve_optional_dbos_durable_engine(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    if durable_engine is None or sql_repo is None:
        return None
    try:
        status = await sql_repo.get_run_status(run.id)
    except Exception as exc:
        from orcia_core.observability.logging import get_logger

        get_logger("orcia.api.orchestration").warning(
            "sql_replay_fork_get_run_status_fallback", run_id=run.id, error_type=type(exc).__name__
        )
        return None
    snapshots = await sql_repo.list_snapshots(run.id)
    parent_id = snapshots[-1].id if snapshots else None
    steps = await sql_repo.list_step_executions(run.id)
    target_step = next((s for s in steps if s.step_key == step_key), None)
    step_index = target_step.step_index if target_step is not None else 0
    snap = await durable_engine.persist_step_and_commit_snapshot(
        run_id=run.id,
        step_key=step_key,
        step_index=step_index,
        artifact_payload=dict(revised_payload or {"replayed": True}),
        parent_snapshot_id=parent_id,
    )
    return DurableWorkflowRunSummary(
        workflow_id=f"wf-{run.id}",
        run_id=run.id,
        final_status=status,
        committed_snapshot_ids=(*(s.id for s in snapshots), snap.id),
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
