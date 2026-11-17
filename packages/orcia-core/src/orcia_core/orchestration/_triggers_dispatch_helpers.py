"""Shared dispatch helpers & autonomous execution bridge types (`Story 7.2`, `MAJOR-05`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    WorkflowTriggerRepositoryPort,
)
from orcia_core.orchestration._triggers_crud_helpers import (
    DispatchResultKind,
    TriggerDispatchOutcome,
)
from orcia_core.orchestration.models import WorkflowTriggerEntity
from orcia_core.permissions.autonomy_contracts import AutonomyContract
from orcia_core.permissions.errors import TriggerCircuitOpenError


@dataclass(frozen=True, slots=True)
class TriggerAutonomousExecutionContext:
    """Context passed to the `orcia_connectors` autonomous contract runner bridge."""

    trigger: WorkflowTriggerEntity
    contract: AutonomyContract
    run_id: str
    idempotency_key: str
    dbos_workflow_id: str
    payload: dict[str, Any]
    trace_id: str


AutonomousTriggerExecutor = Callable[[TriggerAutonomousExecutionContext], Awaitable[dict[str, Any]]]


async def check_rate_and_cost_limits(
    *,
    repo: WorkflowTriggerRepositoryPort | None,
    runs_by_trigger: dict[str, list[tuple[datetime, float]]],
    trigger: WorkflowTriggerEntity,
    estimated_cost_usd: float,
) -> str | None:
    """Return circuit-open reason if hourly run cap or daily cost cap is exceeded."""
    if repo is not None:
        hourly = await repo.count_runs_last_hour(trigger_id=trigger.id)
        daily_cost = await repo.sum_daily_cost_usd(trigger_id=trigger.id)
    else:
        now = datetime.now(UTC)
        hist = runs_by_trigger.get(trigger.id, [])
        hourly = sum(1 for ts, _ in hist if (now - ts).total_seconds() <= 3600)
        daily_cost = sum(c for ts, c in hist if ts.date() == now.date())
    if hourly >= trigger.max_runs_per_hour:
        return "max_runs_per_hour exceeded"
    if daily_cost + estimated_cost_usd > trigger.max_daily_cost_usd:
        return "max_daily_cost_usd exceeded"
    return None


def check_initial_trigger_state(
    *,
    trigger: WorkflowTriggerEntity,
    idempotency_key: str,
    dbos_wf_id: str,
    raise_on_circuit_open: bool,
) -> TriggerDispatchOutcome | None:
    """Reject `CIRCUIT_OPEN` or `PAUSED` triggers before acquiring idempotency locks."""
    if trigger.status == "CIRCUIT_OPEN":
        if raise_on_circuit_open:
            raise TriggerCircuitOpenError()
        return TriggerDispatchOutcome(
            False, "CIRCUIT_OPEN", trigger.id, idempotency_key, dbos_wf_id, reason="Circuit open"
        )
    if trigger.status == "PAUSED":
        return TriggerDispatchOutcome(
            False, "PAUSED", trigger.id, idempotency_key, dbos_wf_id, reason="Trigger paused"
        )
    return None


def format_duplicate_outcome(
    trigger: WorkflowTriggerEntity,
    idempotency_key: str,
    dbos_wf_id: str,
    reason: str,
) -> TriggerDispatchOutcome:
    """Build a canonical `DUPLICATE_SUPPRESSED` dispatch outcome."""
    return TriggerDispatchOutcome(
        False,
        "DUPLICATE_SUPPRESSED",
        trigger.id,
        idempotency_key,
        dbos_wf_id,
        reason=reason,
    )


def format_failure_outcome(
    *,
    opened_res: TriggerDispatchOutcome | None,
    trigger: WorkflowTriggerEntity,
    idempotency_key: str,
    dbos_wf_id: str,
    run_id: str,
    attempts_used: int,
    error_reason: str,
) -> TriggerDispatchOutcome:
    """Return `CIRCUIT_OPEN` or `FAILED_FUNCTIONAL` dispatch outcome on execution failure."""
    if opened_res is not None:
        return replace(
            opened_res,
            idempotency_key=idempotency_key,
            dbos_workflow_id=dbos_wf_id,
            run_id=run_id,
            attempts=attempts_used,
            reason=error_reason,
        )
    kind: DispatchResultKind = "FAILED_FUNCTIONAL"
    return TriggerDispatchOutcome(
        False,
        kind,
        trigger.id,
        idempotency_key,
        dbos_wf_id,
        run_id=run_id,
        attempts=attempts_used,
        reason=error_reason,
    )


async def reserve_idempotent_run_slot(
    *,
    repo: WorkflowTriggerRepositoryPort | None,
    lock: Any,
    run_keys: set[tuple[str, str]],
    runs_by_trigger: dict[str, list[tuple[datetime, float]]],
    trigger: WorkflowTriggerEntity,
    idempotency_key: str,
    dbos_wf_id: str,
    budget_max_usd: float,
    estimated_cost_usd: float,
    run_id: str,
) -> TriggerDispatchOutcome | None:
    """Enforce Redis NX lock + SQL UNIQUE `(trigger_id, idempotency_key)` slot."""
    if not await lock.try_acquire(trigger_id=trigger.id, idempotency_key=idempotency_key):
        return format_duplicate_outcome(
            trigger, idempotency_key, dbos_wf_id, "Duplicate suppressed by Redis NX lock"
        )
    if repo is not None:
        inserted = await repo.create_idempotent_trigger_run(
            run_id=run_id,
            trigger=trigger,
            idempotency_key=idempotency_key,
            status="INITIALIZED",
            budget_max_usd=budget_max_usd,
        )
    else:
        rk = (trigger.id, idempotency_key)
        inserted = rk not in run_keys
        if inserted:
            run_keys.add(rk)
            runs_by_trigger.setdefault(trigger.id, []).append(
                (datetime.now(UTC), estimated_cost_usd)
            )
    if not inserted:
        return format_duplicate_outcome(
            trigger, idempotency_key, dbos_wf_id, "Duplicate suppressed by SQL UNIQUE constraint"
        )
    return None


def build_new_trigger_entity(
    *,
    tid: str,
    tkey: str,
    cmd: Any,
    contract: AutonomyContract | None,
    enc: str | None,
    fp: str | None,
    hint: str | None,
    changed: bool,
    now_iso_str: str,
) -> WorkflowTriggerEntity:
    """Build a new `WorkflowTriggerEntity` from `CreateTriggerCommand`."""
    return WorkflowTriggerEntity(
        id=tid,
        trigger_key=tkey,
        workspace_id=cmd.workspace_id,
        workflow_def_id=tid,
        trigger_type=cmd.trigger_type,
        workflow_id=cmd.workflow_id,
        contract_id=contract.id if contract else None,
        cron_expr=cmd.cron_expr.strip() if cmd.cron_expr else None,
        cooldown_window_seconds=max(0, cmd.cooldown_window_seconds),
        service_principal_id=contract.service_principal_id if contract else None,
        max_runs_per_hour=max(1, cmd.max_runs_per_hour),
        max_daily_cost_usd=max(0.0, cmd.max_daily_cost_usd),
        max_consecutive_failures=max(1, cmd.max_consecutive_failures),
        post_hoc_sampling_rate=contract.post_hoc_sampling_rate if contract else 0.10,
        status=cmd.status,
        auto_help_on_publish=bool(cmd.auto_help_on_publish),
        webhook_secret_configured=bool(enc),
        webhook_secret_fingerprint=fp,
        webhook_secret_masked_hint=hint,
        webhook_secret_updated_at=now_iso_str if changed else None,
        webhook_secret_updated_by=cmd.actor_id if changed else None,
        log_sink_service=cmd.log_sink_service,
        log_sink_query_text=cmd.log_sink_query_text,
        outbox_event_filter=cmd.outbox_event_filter,
    )


async def execute_trigger_dbos_dispatch(
    *,
    dbos_dispatcher: Any,
    run_with_taxonomy_fn: Callable[[Callable[[], Awaitable[Any]]], Awaitable[tuple[Any, int]]],
    autonomous_executor: AutonomousTriggerExecutor | None,
    execution_fn: Callable[[], Awaitable[dict[str, Any]]] | None,
    trigger: WorkflowTriggerEntity,
    contract: AutonomyContract,
    run_id: str,
    idempotency_key: str,
    dbos_wf_id: str,
    payload: dict[str, Any] | None,
    trace_id: str,
) -> tuple[bool, int, Exception | None]:
    """Run DBOS dispatch (wiring `autonomous_executor` when needed) and return status."""
    resolved_exec = execution_fn
    if resolved_exec is None and autonomous_executor is not None:
        ctx = TriggerAutonomousExecutionContext(
            trigger=trigger,
            contract=contract,
            run_id=run_id,
            idempotency_key=idempotency_key,
            dbos_workflow_id=dbos_wf_id,
            payload=dict(payload or {}),
            trace_id=trace_id,
        )

        async def _run_bridge() -> dict[str, Any]:
            return await autonomous_executor(ctx)

        resolved_exec = _run_bridge
    attempts_used = 1
    try:
        if resolved_exec is not None:
            _, attempts_used = await run_with_taxonomy_fn(
                lambda: dbos_dispatcher.dispatch(
                    dbos_workflow_id=dbos_wf_id,
                    trigger=trigger,
                    run_id=run_id,
                    idempotency_key=idempotency_key,
                    payload=dict(payload or {}),
                    execution_fn=resolved_exec,
                )
            )
        else:
            await dbos_dispatcher.dispatch(
                dbos_workflow_id=dbos_wf_id,
                trigger=trigger,
                run_id=run_id,
                idempotency_key=idempotency_key,
                payload=dict(payload or {}),
            )
        return True, attempts_used, None
    except Exception as exc:
        return False, attempts_used, exc


async def record_dispatch_failure(
    *,
    repo: WorkflowTriggerRepositoryPort | None,
    triggers_mem: dict[str, WorkflowTriggerEntity],
    trigger: WorkflowTriggerEntity,
) -> tuple[int, bool]:
    """Increment failure count and indicate if consecutive failures tripped the circuit."""
    if repo is not None:
        return await repo.record_trigger_failure(
            trigger_id=trigger.id,
            max_consecutive_failures=trigger.max_consecutive_failures,
        )
    fails = trigger.consecutive_failures + 1
    opened = fails >= trigger.max_consecutive_failures
    triggers_mem[trigger.id] = replace(
        trigger,
        consecutive_failures=fails,
        status="CIRCUIT_OPEN" if opened else trigger.status,
    )
    return fails, opened
