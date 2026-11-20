"""Lifecycle & webhook verification operations for `TriggerDispatcherService` (`MAJOR-05`)."""

from __future__ import annotations

from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    WorkflowTriggerRepositoryPort,
)
from orcia_core.orchestration._triggers_crud_helpers import (
    CreateTriggerCommand,
    UpdateTriggerCommand,
    apply_trigger_update,
    now_iso,
    prepare_webhook_secret,
)
from orcia_core.orchestration._triggers_dispatch_helpers import build_new_trigger_entity
from orcia_core.orchestration._triggers_log_cron import validate_cron_expr
from orcia_core.orchestration.models import WorkflowTriggerEntity
from orcia_core.permissions.autonomy_contracts import AutonomyContract
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import unpack_encrypted_secret
from orcia_core.permissions.errors import (
    TriggerDuplicateKeyError,
    ValidationDomainError,
    WebhookSignatureInvalidError,
)
from orcia_core.permissions.webhook_security import verify_webhook_hmac_sha256
from orcia_kernel.events import SelfTriggerBlocked, TriggerCircuitOpened, TriggerFired
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.orchestration.triggers_lifecycle")


async def execute_create_trigger(
    *,
    cmd: CreateTriggerCommand,
    contract: AutonomyContract | None,
    cipher: PassthroughVaultCipher,
    repo: WorkflowTriggerRepositoryPort | None,
    triggers_mem: dict[str, WorkflowTriggerEntity],
    secrets_mem: dict[str, str],
) -> WorkflowTriggerEntity:
    """Persist or store in-memory a validated `WorkflowTriggerEntity`."""
    tid = new_uuid7_str()
    entropy_suffix = tid.replace("-", "")[-12:]
    tkey = (cmd.trigger_key or "").strip() or f"trg-{cmd.trigger_type.lower()}-{entropy_suffix}"
    enc, fp, hint, clear_flag, changed = prepare_webhook_secret(cipher, tid, cmd.webhook_secret)
    entity = build_new_trigger_entity(
        tid=tid,
        tkey=tkey,
        cmd=cmd,
        contract=contract,
        enc=enc,
        fp=fp,
        hint=hint,
        changed=changed,
        now_iso_str=now_iso(),
    )
    if repo is not None:
        return await repo.save_trigger(entity, encrypted_secret=enc, clear_secret=clear_flag)
    if any(t.trigger_key == tkey for t in triggers_mem.values()):
        raise TriggerDuplicateKeyError()
    triggers_mem[tid] = entity
    if enc:
        secrets_mem[tid] = enc
    return entity


async def execute_update_trigger(
    *,
    existing: WorkflowTriggerEntity,
    workspace_id: str,
    trigger_id: str,
    cmd: UpdateTriggerCommand,
    next_status: str,
    cid: str | None,
    sp_id: str | None,
    cipher: PassthroughVaultCipher,
    repo: WorkflowTriggerRepositoryPort | None,
    triggers_mem: dict[str, WorkflowTriggerEntity],
    secrets_mem: dict[str, str],
) -> WorkflowTriggerEntity:
    """Validate cron, update encrypted webhook secret, and persist `WorkflowTriggerEntity`."""
    next_cron = cmd.cron_expr if cmd.cron_expr is not None else existing.cron_expr
    if existing.trigger_type == "CRON" and next_cron:
        validate_cron_expr(next_cron)
    enc, fp, hint, clear_flag, changed = prepare_webhook_secret(
        cipher, trigger_id, cmd.webhook_secret
    )
    updated = apply_trigger_update(
        existing,
        cmd,
        next_status=next_status,  # type: ignore[arg-type]
        contract_id=cid,
        sp_id=sp_id,
        next_cron=next_cron,
        enc=enc,
        fp=fp,
        hint=hint,
        clear_flag=clear_flag,
        changed=changed,
    )
    if repo is not None:
        return await repo.save_trigger(updated, encrypted_secret=enc, clear_secret=clear_flag)
    triggers_mem[trigger_id] = updated
    if clear_flag:
        secrets_mem.pop(trigger_id, None)
    elif enc:
        secrets_mem[trigger_id] = enc
    return updated


async def execute_verify_webhook_request(
    *,
    entity: WorkflowTriggerEntity,
    enc_secret: str | None,
    trigger_id: str,
    raw_body: bytes,
    signature_header: str | None,
    delivery_key: str,
    cipher: PassthroughVaultCipher,
    repo: WorkflowTriggerRepositoryPort | None,
    deliveries_mem: set[tuple[str, str]],
) -> tuple[WorkflowTriggerEntity, bool]:
    """Verify HMAC-SHA256 webhook signature and deduplicate delivery."""
    if enc_secret:
        try:
            secret = unpack_encrypted_secret(
                cipher,
                owner_id=trigger_id,
                packed=enc_secret,
                scheme="webhook",
                host="trigger",
            )
        except Exception as exc:
            logger.warning(
                "webhook_secret_unpack_failed", trigger_id=trigger_id, error=type(exc).__name__
            )
            raise WebhookSignatureInvalidError() from exc
        if not verify_webhook_hmac_sha256(raw_body, secret, signature_header):
            raise WebhookSignatureInvalidError()
    elif signature_header:
        raise WebhookSignatureInvalidError()
    if repo is not None:
        is_new = await repo.record_webhook_delivery(
            trigger_id=trigger_id, delivery_key=delivery_key
        )
    else:
        key = (trigger_id, delivery_key)
        is_new = key not in deliveries_mem
        deliveries_mem.add(key)
    return entity, is_new


def validate_create_trigger_cron(cmd: CreateTriggerCommand) -> None:
    """Validate mandatory `cron_expr` when creating a CRON trigger."""
    if cmd.trigger_type == "CRON":
        if not (cmd.cron_expr or "").strip():
            raise ValidationDomainError(detail_override="cron_expr is required for CRON.")
        validate_cron_expr(cmd.cron_expr or "")


def build_self_trigger_blocked_event_and_outcome(
    *,
    trigger: WorkflowTriggerEntity,
    guard: Any,
    service_principal_id: str,
    idempotency_key: str,
    dbos_wf_id: str,
    trace_id: str,
) -> tuple[SelfTriggerBlocked, Any]:
    """Build `SelfTriggerBlocked` event and outcome when recursion is detected."""
    from orcia_core.orchestration._triggers_crud_helpers import TriggerDispatchOutcome

    evt = SelfTriggerBlocked.create(
        trigger_id=trigger.id,
        workspace_id=trigger.workspace_id,
        workflow_id=trigger.workflow_id,
        reason=guard.reason,
        origin_run_id=guard.origin_run_id,
        service_principal_id=service_principal_id,
        trace_id=trace_id,
    )
    outcome = TriggerDispatchOutcome(
        False,
        "SELF_TRIGGER_BLOCKED",
        trigger.id,
        idempotency_key,
        dbos_wf_id,
        reason=guard.reason,
    )
    return evt, outcome


def build_circuit_opened_event_and_outcome(
    *,
    trigger: WorkflowTriggerEntity,
    reason: str,
    failures: int,
    trace_id: str,
) -> tuple[TriggerCircuitOpened, Any]:
    """Build `TriggerCircuitOpened` event and circuit-open outcome."""
    from orcia_core.orchestration._triggers_crud_helpers import TriggerDispatchOutcome

    evt = TriggerCircuitOpened.create(
        trigger_id=trigger.id,
        workspace_id=trigger.workspace_id,
        workflow_id=trigger.workflow_id,
        reason=reason,
        consecutive_failures=failures,
        trace_id=trace_id,
    )
    return evt, TriggerDispatchOutcome(False, "CIRCUIT_OPEN", trigger.id, "", "", reason=reason)


def build_trigger_fired_event_and_outcome(
    *,
    trigger: WorkflowTriggerEntity,
    contract: AutonomyContract,
    run_id: str,
    idempotency_key: str,
    dbos_wf_id: str,
    attempts_used: int,
    trace_id: str,
) -> tuple[TriggerFired, Any]:
    """Build `TriggerFired` event and successful `DISPATCHED` outcome."""
    from orcia_core.orchestration._triggers_crud_helpers import TriggerDispatchOutcome

    fired = TriggerFired.create(
        trigger_id=trigger.id,
        workspace_id=trigger.workspace_id,
        workflow_id=trigger.workflow_id,
        trigger_type=trigger.trigger_type,
        run_id=run_id,
        idempotency_key=idempotency_key,
        service_principal_id=contract.service_principal_id,
        trace_id=trace_id,
    )
    outcome = TriggerDispatchOutcome(
        True,
        "DISPATCHED",
        trigger.id,
        idempotency_key,
        dbos_wf_id,
        run_id=run_id,
        attempts=attempts_used,
    )
    return fired, outcome


__all__ = [
    "Any",
    "build_circuit_opened_event_and_outcome",
    "build_self_trigger_blocked_event_and_outcome",
    "build_trigger_fired_event_and_outcome",
    "execute_create_trigger",
    "execute_update_trigger",
    "execute_verify_webhook_request",
    "validate_create_trigger_cron",
]
