"""PG18 Hydration & Blackboard Read Helpers for Epic 3 Orchestration Routers (`REM-09`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_core.blackboard import BlackboardSnapshotEntity, StepExecutionEntity
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import (
    DbosSqlAlchemyUnitOfWork,
    HumanAnchorSignatureEntity,
    HumanArbitrationRequestEntity,
    SqlDomainEventsOutboxRepository,
    SqlOrchestrationRepository,
    WorkflowOrchestrationSetupService,
    list_human_anchor_signatures_sql,
    list_human_arbitrations_sql,
    list_upstream_challenges_sql,
    list_workflow_runs_with_locks_sql,
)

logger = get_logger("orcia.api.orchestration")


def resolve_optional_dbos_uow(request: Request) -> DbosSqlAlchemyUnitOfWork | None:
    """Return `DbosSqlAlchemyUnitOfWork` from `app.state` (`dbos_uow`/`datasource`/`db_engine`)."""
    uow: DbosSqlAlchemyUnitOfWork | None = getattr(request.app.state, "dbos_uow", None)
    if uow is not None:
        return uow
    datasource: Any = getattr(request.app.state, "dbos_datasource", None)
    if datasource is not None:
        uow = DbosSqlAlchemyUnitOfWork(datasource)
        request.app.state.dbos_uow = uow
        return uow
    db_engine: Any = getattr(request.app.state, "db_engine", None)
    if db_engine is not None:
        session_maker: Any = getattr(request.app.state, "session_maker", None)
        uow = DbosSqlAlchemyUnitOfWork.from_engine(db_engine, session_factory=session_maker)
        request.app.state.dbos_uow = uow
        return uow
    return None


def resolve_optional_sql_orchestration_repo(request: Request) -> SqlOrchestrationRepository | None:
    uow = resolve_optional_dbos_uow(request)
    return SqlOrchestrationRepository(uow) if uow is not None else None


def resolve_optional_sql_outbox_repo(request: Request) -> SqlDomainEventsOutboxRepository | None:
    uow = resolve_optional_dbos_uow(request)
    return SqlDomainEventsOutboxRepository(uow) if uow is not None else None


async def read_sql_blackboard_if_available(
    request: Request,
    run_id: str,
) -> tuple[str | None, tuple[StepExecutionEntity, ...], tuple[BlackboardSnapshotEntity, ...]]:
    """Read `run_status`, `step_executions`, and `blackboard_snapshots` from PG18."""
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    outbox_repo = resolve_optional_sql_outbox_repo(request)
    if sql_repo is None or outbox_repo is None:
        return None, (), ()
    try:
        status = await sql_repo.get_run_status(run_id)
    except Exception as exc:
        logger.warning(
            "sql_blackboard_get_run_status_fallback", run_id=run_id, error_type=type(exc).__name__
        )
        return None, (), ()
    steps = await sql_repo.list_step_executions(run_id)
    snapshots = await sql_repo.list_snapshots(run_id)
    await outbox_repo.list_events_by_run(run_id)
    return status, steps, snapshots


async def hydrate_orchestration_runs_from_sql(
    request: Request, svc: WorkflowOrchestrationSetupService
) -> None:
    """Synchronize `svc._runs_by_id` strictly with PostgreSQL 18 `workflow_runs` rows."""
    uow = resolve_optional_dbos_uow(request)
    if uow is None:
        return
    try:
        sql_runs = await list_workflow_runs_with_locks_sql(uow)
    except Exception as exc:
        logger.warning("hydrate_orchestration_runs_skipped", error_type=type(exc).__name__)
        return
    sql_run_ids = {r.id for r in sql_runs}
    for stale_id in [rid for rid in svc._runs_by_id if rid not in sql_run_ids]:
        svc._runs_by_id.pop(stale_id, None)
    for idemp_key, rid in list(svc._idempotency_index.items()):
        if rid not in sql_run_ids:
            svc._idempotency_index.pop(idemp_key, None)
    for r in sql_runs:
        svc._runs_by_id[r.id] = r


async def read_sql_run_governance_if_available(
    request: Request,
    svc: WorkflowOrchestrationSetupService,
    run_id: str,
) -> tuple[tuple[HumanArbitrationRequestEntity, ...], tuple[HumanAnchorSignatureEntity, ...]]:
    """Return pending arbitrations and signed human anchors for `run_id` from PG18 or service."""
    uow = resolve_optional_dbos_uow(request)
    if uow is not None:
        try:
            arbs = await list_human_arbitrations_sql(uow, run_id=run_id)
            anchors = await list_human_anchor_signatures_sql(uow, run_id=run_id)
            return tuple(a for a in arbs if a.status == "PENDING"), anchors
        except Exception as exc:
            logger.warning(
                "sql_run_governance_read_fallback", run_id=run_id, error_type=type(exc).__name__
            )
    mem_arbs = tuple(
        a
        for a in svc.engine.anchors_and_arbitration.list_arbitrations(run_id)
        if a.status == "PENDING"
    )
    mem_anchors = tuple(
        sig
        for (r_id, _, _), sig in svc.engine.anchors_and_arbitration._anchors_by_step_section.items()
        if r_id == run_id
    )
    return mem_arbs, mem_anchors


async def hydrate_run_from_sql_if_missing(
    request: Request, svc: WorkflowOrchestrationSetupService, run_id: str
) -> None:
    """Rehydrate a run, its steps, snapshots, anchors, arbitrations & challenges from PG18."""
    uow = resolve_optional_dbos_uow(request)
    sql_repo = resolve_optional_sql_orchestration_repo(request)
    if uow is None or sql_repo is None:
        return
    if run_id not in svc._runs_by_id:
        try:
            runs = await list_workflow_runs_with_locks_sql(uow, run_id=run_id)
        except Exception as exc:
            logger.warning(
                "hydrate_run_from_sql_skipped", run_id=run_id, error_type=type(exc).__name__
            )
            return
        for r in runs:
            svc._runs_by_id[r.id] = r
    if run_id not in svc._runs_by_id:
        return
    for step in await sql_repo.list_step_executions(run_id):
        svc.engine.blackboard.register_step_execution(step)
    for snap in await sql_repo.list_snapshots(run_id):
        svc.engine.blackboard.hydrate_snapshot(snap)
    for sig in await list_human_anchor_signatures_sql(uow, run_id=run_id):
        svc.engine.anchors_and_arbitration._anchors_by_step_section[
            (sig.run_id, sig.step_key, sig.section_key)
        ] = sig
    for arb in await list_human_arbitrations_sql(uow, run_id=run_id):
        svc.engine.anchors_and_arbitration._arbitrations_by_id[arb.id] = arb
    for chal in await list_upstream_challenges_sql(uow, run_id=run_id):
        svc.engine.challenge_and_replay._challenges_by_id[chal.id] = chal
        run_cids = svc.engine.challenge_and_replay._challenges_by_run.setdefault(chal.run_id, [])
        if chal.id not in run_cids:
            run_cids.append(chal.id)
