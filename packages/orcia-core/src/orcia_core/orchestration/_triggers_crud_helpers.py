"""Trigger command models and entity update helpers (`Story 7.2`, `AD-18`)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal

from orcia_core.orchestration.models import (
    WorkflowTriggerEntity,
    WorkflowTriggerStatus,
    WorkflowTriggerType,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    compute_secret_fingerprint,
    pack_encrypted_secret,
)
from orcia_core.permissions.secret_hint import SecretInputSpec, compute_secret_masked_hint

DispatchResultKind = Literal[
    "DISPATCHED",
    "DUPLICATE_SUPPRESSED",
    "SELF_TRIGGER_BLOCKED",
    "CIRCUIT_OPEN",
    "PAUSED",
    "FAILED_FUNCTIONAL",
]


@dataclass(frozen=True, slots=True)
class CreateTriggerCommand:
    """Command to register a governed autonomous workflow trigger."""

    workspace_id: str
    workflow_id: str
    trigger_type: WorkflowTriggerType
    trigger_key: str | None = None
    cron_expr: str | None = None
    cooldown_window_seconds: int = 300
    max_runs_per_hour: int = 10
    max_daily_cost_usd: float = 25.0
    max_consecutive_failures: int = 3
    auto_help_on_publish: bool = False
    webhook_secret: SecretInputSpec | None = None
    log_sink_service: str | None = None
    log_sink_query_text: str | None = None
    outbox_event_filter: str | None = None
    status: WorkflowTriggerStatus = "ACTIVE"
    actor_id: str = "system"


@dataclass(frozen=True, slots=True)
class UpdateTriggerCommand:
    """Partial update command for an existing workflow trigger."""

    status: WorkflowTriggerStatus | None = None
    cron_expr: str | None = None
    cooldown_window_seconds: int | None = None
    max_runs_per_hour: int | None = None
    max_daily_cost_usd: float | None = None
    max_consecutive_failures: int | None = None
    auto_help_on_publish: bool | None = None
    webhook_secret: SecretInputSpec | None = None
    log_sink_service: str | None = None
    log_sink_query_text: str | None = None
    outbox_event_filter: str | None = None
    actor_id: str = "system"


@dataclass(frozen=True, slots=True)
class TriggerDispatchOutcome:
    """Deterministic dispatch result returned by `TriggerDispatcherService`."""

    dispatched: bool
    outcome: DispatchResultKind
    trigger_id: str
    idempotency_key: str
    dbos_workflow_id: str
    run_id: str | None = None
    attempts: int = 0
    reason: str | None = None


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def prepare_webhook_secret(
    cipher: PassthroughVaultCipher,
    trigger_id: str,
    secret_input: SecretInputSpec | None,
) -> tuple[str | None, str | None, str | None, bool, bool]:
    """Return `(encrypted, fingerprint, masked_hint, clear_flag, changed)`."""
    if secret_input is None or secret_input.action == "keep":
        return None, None, None, False, False
    if secret_input.action == "clear":
        return None, None, None, True, True
    raw = (secret_input.plaintext_value or "").strip()
    enc = pack_encrypted_secret(
        cipher, owner_id=trigger_id, plaintext=raw, scheme="webhook", host="trigger"
    )
    return (
        enc,
        compute_secret_fingerprint(trigger_id, raw),
        compute_secret_masked_hint(raw),
        False,
        True,
    )


def apply_trigger_update(
    existing: WorkflowTriggerEntity,
    cmd: UpdateTriggerCommand,
    *,
    next_status: WorkflowTriggerStatus,
    contract_id: str | None,
    sp_id: str | None,
    next_cron: str | None,
    enc: str | None,
    fp: str | None,
    hint: str | None,
    clear_flag: bool,
    changed: bool,
) -> WorkflowTriggerEntity:
    """Apply partial update fields onto an immutable `WorkflowTriggerEntity`."""
    return replace(
        existing,
        contract_id=contract_id,
        service_principal_id=sp_id,
        cron_expr=next_cron,
        cooldown_window_seconds=(
            max(0, cmd.cooldown_window_seconds)
            if cmd.cooldown_window_seconds is not None
            else existing.cooldown_window_seconds
        ),
        max_runs_per_hour=(
            max(1, cmd.max_runs_per_hour)
            if cmd.max_runs_per_hour is not None
            else existing.max_runs_per_hour
        ),
        max_daily_cost_usd=(
            max(0.0, cmd.max_daily_cost_usd)
            if cmd.max_daily_cost_usd is not None
            else existing.max_daily_cost_usd
        ),
        max_consecutive_failures=(
            max(1, cmd.max_consecutive_failures)
            if cmd.max_consecutive_failures is not None
            else existing.max_consecutive_failures
        ),
        status=next_status,
        auto_help_on_publish=(
            bool(cmd.auto_help_on_publish)
            if cmd.auto_help_on_publish is not None
            else existing.auto_help_on_publish
        ),
        webhook_secret_configured=(
            False if clear_flag else (True if enc else existing.webhook_secret_configured)
        ),
        webhook_secret_fingerprint=(
            None if clear_flag else (fp or existing.webhook_secret_fingerprint)
        ),
        webhook_secret_masked_hint=(
            None if clear_flag else (hint or existing.webhook_secret_masked_hint)
        ),
        webhook_secret_updated_at=now_iso() if changed else existing.webhook_secret_updated_at,
        webhook_secret_updated_by=cmd.actor_id if changed else existing.webhook_secret_updated_by,
        log_sink_service=(
            cmd.log_sink_service if cmd.log_sink_service is not None else existing.log_sink_service
        ),
        log_sink_query_text=(
            cmd.log_sink_query_text
            if cmd.log_sink_query_text is not None
            else existing.log_sink_query_text
        ),
        outbox_event_filter=(
            cmd.outbox_event_filter
            if cmd.outbox_event_filter is not None
            else existing.outbox_event_filter
        ),
    )


__all__ = [
    "CreateTriggerCommand",
    "DispatchResultKind",
    "TriggerDispatchOutcome",
    "UpdateTriggerCommand",
    "apply_trigger_update",
    "now_iso",
    "prepare_webhook_secret",
]
