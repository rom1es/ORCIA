"""Full dispatch pipeline extracted from `_triggers_lifecycle_ops.py` (`MAJOR-05`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._triggers_crud_helpers import now_iso
from orcia_core.orchestration._triggers_dispatch_helpers import (
    check_initial_trigger_state,
    check_rate_and_cost_limits,
    execute_trigger_dbos_dispatch,
    format_failure_outcome,
    record_dispatch_failure,
    reserve_idempotent_run_slot,
)
from orcia_core.orchestration._triggers_lifecycle_ops import (
    build_self_trigger_blocked_event_and_outcome,
    build_trigger_fired_event_and_outcome,
)
from orcia_core.orchestration._triggers_log_cron import evaluate_self_trigger_guard
from orcia_core.orchestration._triggers_runtime_ports import run_with_error_taxonomy
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.orchestration.triggers_pipeline")


async def execute_full_dispatch_pipeline(
    service: Any,
    *,
    trigger_id: str,
    idempotency_key: str,
    headers: dict[str, str] | None,
    payload: dict[str, Any] | None,
    execution_fn: Any,
    estimated_cost_usd: float,
    trace_id: str,
    raise_on_circuit_open: bool,
) -> Any:
    """Orchestrate trigger lookup, self-trigger guard, rate/cost limits, NX lock & DBOS."""
    trigger, _ = await service.get_trigger(trigger_id)
    dbos_wf_id = f"{trigger.id}:{idempotency_key}"
    early = check_initial_trigger_state(
        trigger=trigger,
        idempotency_key=idempotency_key,
        dbos_wf_id=dbos_wf_id,
        raise_on_circuit_open=raise_on_circuit_open,
    )
    if early is not None:
        return early
    contract = await service._require_active_contract(
        workspace_id=trigger.workspace_id, workflow_id=trigger.workflow_id
    )
    guard = evaluate_self_trigger_guard(
        trigger=trigger,
        contract_service_principal_id=contract.service_principal_id,
        headers=headers,
        payload=payload,
    )
    if guard.blocked:
        evt, blocked_out = build_self_trigger_blocked_event_and_outcome(
            trigger=trigger,
            guard=guard,
            service_principal_id=contract.service_principal_id,
            idempotency_key=idempotency_key,
            dbos_wf_id=dbos_wf_id,
            trace_id=trace_id,
        )
        await service._publish_event(evt, sse_name="SelfTriggerBlocked")
        return blocked_out
    limit_reason = await check_rate_and_cost_limits(
        repo=service._repo,
        runs_by_trigger=service._runs_by_trigger,
        trigger=trigger,
        estimated_cost_usd=estimated_cost_usd,
    )
    if limit_reason is not None:
        res = await service._open_circuit(
            trigger,
            reason=limit_reason,
            failures=trigger.consecutive_failures,
            trace_id=trace_id,
        )
        return replace(res, idempotency_key=idempotency_key, dbos_workflow_id=dbos_wf_id)
    run_id = new_uuid7_str()
    dup = await reserve_idempotent_run_slot(
        repo=service._repo,
        lock=service._lock,
        run_keys=service._run_keys,
        runs_by_trigger=service._runs_by_trigger,
        trigger=trigger,
        idempotency_key=idempotency_key,
        dbos_wf_id=dbos_wf_id,
        budget_max_usd=min(contract.max_cost_per_run_usd, trigger.max_daily_cost_usd),
        estimated_cost_usd=estimated_cost_usd,
        run_id=run_id,
    )
    if dup is not None:
        return dup
    ok, attempts_used, exc = await execute_trigger_dbos_dispatch(
        dbos_dispatcher=service._dbos,
        run_with_taxonomy_fn=run_with_error_taxonomy,
        autonomous_executor=service._autonomous_executor,
        execution_fn=execution_fn,
        trigger=trigger,
        contract=contract,
        run_id=run_id,
        idempotency_key=idempotency_key,
        dbos_wf_id=dbos_wf_id,
        payload=payload,
        trace_id=trace_id,
    )
    if not ok and exc is not None:
        logger.warning("trigger_execution_failed", trigger_id=trigger.id, error=str(exc))
        fails, opened = await record_dispatch_failure(
            repo=service._repo, triggers_mem=service._triggers, trigger=trigger
        )
        opened_res = (
            await service._open_circuit(
                trigger,
                reason=f"Consecutive failures {fails}",
                failures=fails,
                trace_id=trace_id,
            )
            if opened
            else None
        )
        return format_failure_outcome(
            opened_res=opened_res,
            trigger=trigger,
            idempotency_key=idempotency_key,
            dbos_wf_id=dbos_wf_id,
            run_id=run_id,
            attempts_used=attempts_used,
            error_reason=str(exc),
        )
    if service._repo is not None:
        await service._repo.mark_trigger_fired(trigger_id=trigger.id)
    else:
        service._triggers[trigger.id] = replace(
            trigger, consecutive_failures=0, last_fired_at_iso=now_iso()
        )
    fired, ok_out = build_trigger_fired_event_and_outcome(
        trigger=trigger,
        contract=contract,
        run_id=run_id,
        idempotency_key=idempotency_key,
        dbos_wf_id=dbos_wf_id,
        attempts_used=attempts_used,
        trace_id=trace_id,
    )
    await service._publish_event(fired, sse_name="TriggerFired")
    return ok_out
