"""SQL / Outbox / DBOS Persistence Wiring for Epic 3 Routers (`AD-2`, `AD-19`, `REM-09`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.routers._orchestration_sql_hydration import (
    hydrate_orchestration_runs_from_sql,
    hydrate_run_from_sql_if_missing,
    read_sql_blackboard_if_available,
    resolve_optional_dbos_uow,
    resolve_optional_sql_orchestration_repo,
    resolve_optional_sql_outbox_repo,
)
from orcia_api.routers._orchestration_sql_serializers import (
    serialize_anchor,
    serialize_arbitration,
    serialize_audit_report,
    serialize_hydrated,
    serialize_memlog,
    serialize_snapshot,
    serialize_step_exec,
)
from orcia_core.blackboard import BlackboardSnapshotEntity, StepExecutionEntity
from orcia_core.orchestration import (
    DbosDurableWorkflowEngine,
    DbosSqlAlchemyUnitOfWork,
    DurableWorkflowRunSummary,
    HumanAnchorSignatureEntity,
    HumanArbitrationRequestEntity,
    SqlOrchestrationRepository,
    UpstreamChallengeEntity,
    WorkflowRunEntity,
    ensure_run_row_exists_in_session,
    ensure_workflow_definition_sql,
    mark_upstream_challenges_replayed_sql,
    resolve_existing_user_id_sql,
    upsert_human_anchor_signature_sql,
    upsert_human_arbitration_sql,
    upsert_run_lock_manifest_sql,
    upsert_upstream_challenge_sql,
)
from orcia_kernel.events import (
    ArtifactProduced,
    HumanArbitrationRequested,
    RunTerminated,
    StepCompleted,
)


def resolve_optional_dbos_durable_engine(request: Request) -> DbosDurableWorkflowEngine | None:
    uow = resolve_optional_dbos_uow(request)
    if uow is None:
        return None
    engine = DbosDurableWorkflowEngine(
        system_database_url="postgresql://localhost:5432/orcia",
        application_database_url="postgresql+asyncpg://localhost:5432/orcia",
    )
    engine._uow = uow
    engine._repository = SqlOrchestrationRepository(uow)
    return engine


async def _ensure_run_and_lock_in_sql(
    uow: DbosSqlAlchemyUnitOfWork,
    sql_repo: SqlOrchestrationRepository,
    run: WorkflowRunEntity,
    steps: tuple[StepExecutionEntity, ...] = (),
) -> None:
    async with uow.session_scope() as session:
        await ensure_run_row_exists_in_session(session, run)
    await upsert_run_lock_manifest_sql(uow, run.run_lock)
    for step in steps:
        await sql_repo.upsert_step_execution(step)


async def sync_instantiated_run_to_sql(
    request: Request,
    run: WorkflowRunEntity,
    *,
    initial_steps: tuple[StepExecutionEntity, ...] = (),
) -> None:
    """Persist `workflow_runs`, `run_lock_manifests`, and initial `step_executions` in PG18."""
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    if uow is None or sql_repo is None:
        return
    async with uow.session_scope() as session:
        resolved_wf_def_id = await ensure_workflow_definition_sql(
            session,
            workflow_def_id=run.workflow_def_id,
            workspace_id=run.workspace_id,
            workflow_uri=run.workflow_uri,
            workflow_sha256=run.run_lock.workflow_sha256,
        )
        resolved_user_id = await resolve_existing_user_id_sql(
            session, run.initiated_by_user_id, fallback_to_any=False
        )
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
        initiated_by_user_id=resolved_user_id,
        execution_identity_mode=run.execution_identity_mode,
        budget_max_usd=run.budget_max_usd,
    )
    await upsert_run_lock_manifest_sql(uow, run.run_lock)
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
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if uow is None or sql_repo is None or outbox_repo is None:
        return
    await _ensure_run_and_lock_in_sql(uow, sql_repo, run)
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


async def sync_human_anchor_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    step_exec: StepExecutionEntity,
    signature: HumanAnchorSignatureEntity,
) -> None:
    """Persist `human_anchor_signatures` immediately in PG18 even when `snapshot` is `None`."""
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    if uow is None or sql_repo is None:
        return
    await _ensure_run_and_lock_in_sql(uow, sql_repo, run, (step_exec,))
    await upsert_human_anchor_signature_sql(uow, signature)


async def sync_arbitration_request_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    arb: HumanArbitrationRequestEntity,
    step_exec: StepExecutionEntity,
    trace_id: str,
) -> None:
    """Persist arbitration step status, `human_arbitration_requests`, and Outbox event."""
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if uow is None or sql_repo is None or outbox_repo is None:
        return
    await _ensure_run_and_lock_in_sql(uow, sql_repo, run, (step_exec,))
    await sql_repo.update_run_status(run.id, run.status)
    await upsert_human_arbitration_sql(uow, arb)
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


async def sync_arbitration_resolution_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    arb: HumanArbitrationRequestEntity,
) -> None:
    """Persist resolved `human_arbitration_requests` row into PG18."""
    uow = resolve_optional_dbos_uow(request)
    if uow is None:
        return
    await upsert_human_arbitration_sql(uow, arb)


async def sync_upstream_challenge_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    challenge: UpstreamChallengeEntity,
    trace_id: str,
    step_exec: StepExecutionEntity | None = None,
) -> None:
    """Persist `upstream_challenges` and enqueue `HumanArbitrationRequested` into Outbox."""
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if uow is None or sql_repo is None or outbox_repo is None:
        return
    await _ensure_run_and_lock_in_sql(uow, sql_repo, run, (step_exec,) if step_exec else ())
    await upsert_upstream_challenge_sql(uow, challenge)
    await outbox_repo.enqueue_event(
        HumanArbitrationRequested.create(
            arbitration_id=challenge.id,
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_key=challenge.target_upstream_step_key,
            options_count=len(challenge.invalidated_downstream_step_keys),
            trace_id=trace_id,
        )
    )


async def sync_replay_fork_to_sql(
    request: Request,
    *,
    run: WorkflowRunEntity,
    step_key: str,
    revised_payload: dict[str, Any] | None,
    steps_to_sync: tuple[StepExecutionEntity, ...] = (),
) -> DurableWorkflowRunSummary | None:
    """Append an `ACTIVE` rewind/fork snapshot superseding downstream snapshots (0 UPDATE)."""
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    if uow is None or sql_repo is None:
        return None
    await _ensure_run_and_lock_in_sql(uow, sql_repo, run, steps_to_sync)
    status = await sql_repo.get_run_status(run.id)
    snapshots = await sql_repo.list_snapshots(run.id)
    steps = await sql_repo.list_step_executions(run.id)
    step_index_by_key = {s.step_key: s.step_index for s in steps}
    target_step = next((s for s in steps if s.step_key == step_key), None)
    if target_step is None:
        return None
    target_idx = target_step.step_index
    superseded_ids = tuple(
        sn.id
        for sn in snapshots
        if sn.branch_status == "ACTIVE" and step_index_by_key.get(sn.step_key, 0) >= target_idx
    )
    parent_id = snapshots[-1].id if snapshots else None
    payload_to_commit = dict(
        revised_payload
        if revised_payload
        else (target_step.draft_artifact or {"replayed": True, "step_key": step_key})
    )
    snap = await sql_repo.append_snapshot(
        run_id=run.id,
        step_execution_id=target_step.id,
        step_key=step_key,
        branch_status="ACTIVE",
        artifact_payload=payload_to_commit,
        memlog_summary=target_step.step_memlog,
        parent_snapshot_id=parent_id,
        superseded_snapshot_ids=superseded_ids,
    )
    await mark_upstream_challenges_replayed_sql(
        uow, run_id=run.id, target_upstream_step_key=step_key
    )
    return DurableWorkflowRunSummary(
        workflow_id=f"wf-{run.id}",
        run_id=run.id,
        final_status=status,
        committed_snapshot_ids=(*(s.id for s in snapshots), snap.id),
    )


__all__ = [
    "hydrate_orchestration_runs_from_sql",
    "hydrate_run_from_sql_if_missing",
    "read_sql_blackboard_if_available",
    "resolve_optional_dbos_durable_engine",
    "resolve_optional_dbos_uow",
    "resolve_optional_sql_orchestration_repo",
    "resolve_optional_sql_outbox_repo",
    "serialize_anchor",
    "serialize_arbitration",
    "serialize_audit_report",
    "serialize_hydrated",
    "serialize_memlog",
    "serialize_snapshot",
    "serialize_step_exec",
    "sync_arbitration_request_to_sql",
    "sync_arbitration_resolution_to_sql",
    "sync_human_anchor_to_sql",
    "sync_instantiated_run_to_sql",
    "sync_replay_fork_to_sql",
    "sync_step_execution_and_snapshot_to_sql",
    "sync_upstream_challenge_to_sql",
]
