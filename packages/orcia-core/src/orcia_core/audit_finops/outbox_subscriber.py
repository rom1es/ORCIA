"""Idempotent domain event subscriber for immutable audit ledger ingestion (`Story 6.1`).

Listens to `domain_events_outbox` stream, scrubs sensitive data (`DEC-SEC-01`),
and persists immutable records with strict idempotency on `source_event_id`.
"""

from __future__ import annotations

from orcia_core.audit_finops._outbox_locale_messages import build_localized_event_summary
from orcia_core.kernel.events import DomainEvent
from orcia_core.observability.logging import get_logger, scrub_sensitive_dict
from orcia_core.ports.finops_telemetry import (
    AuditLedgerSinkPort,
    CostSource,
    FinopsCostLedgerEntry,
)

logger = get_logger("orcia.core.audit_finops.outbox_subscriber")

AUDITABLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "StepCompleted",
        "GateEvaluated",
        "ArtifactProduced",
        "RunTerminated",
        "SettingsChanged",
        "AdminConnectionTested",
        "ADMIN_CONNECTION_TEST",
        "BudgetCircuitTripped",
        "BudgetOverrideApproved",
        "RemoteUsageAnomalyCapped",
        "ConnectorCircuitTripped",
        "AutonomousContractSigned",
        "AutonomousContractRevoked",
        "AutonomousEscalated",
        "TriggerFired",
        "SelfTriggerBlocked",
        "TriggerCircuitOpened",
        "WorkflowPublished",
        "PostHocSampleSelected",
        "KillSwitchActivated",
        "AutonomousArtifactRolledBack",
        "ORG_UNIT_CREATED",
        "ORG_UNIT_UPDATED",
        "ORG_UNIT_DELETED",
        "IAM_ACCOUNT_CREATED",
        "IAM_ACCOUNT_UPDATED",
        "IAM_ACCOUNT_DELETED",
        "IAM_ACCOUNT_INVITED",
    }
)


def _build_event_summary(event: DomainEvent, *, locale: str = "fr") -> str:
    return build_localized_event_summary(event.event_type, dict(event.payload), locale=locale)


def map_domain_event_to_ledger_entry(event: DomainEvent) -> FinopsCostLedgerEntry:
    """Map a domain event into an immutable FinopsCostLedgerEntry with secret scrubbing."""
    payload = dict(event.payload)
    clean_payload = scrub_sensitive_dict(payload)

    etype = event.event_type
    summary = str(clean_payload.get("summary") or _build_event_summary(event))

    actor_type = str(
        clean_payload.get("actor_type")
        or (
            "ADMIN_CONNECTION_TEST"
            if etype in ("AdminConnectionTested", "ADMIN_CONNECTION_TEST")
            else "USER"
        )
    )
    actor_id = str(clean_payload.get("actor_id") or clean_payload.get("user_id") or "system")
    actor_display = (
        str(clean_payload["actor_display_name"])
        if clean_payload.get("actor_display_name")
        else None
    )
    actor_email = str(clean_payload["actor_email"]) if clean_payload.get("actor_email") else None

    in_tok = clean_payload.get("input_tokens")
    input_tokens = (
        int(in_tok) if isinstance(in_tok, (int, float, str)) and str(in_tok).isdigit() else 0
    )
    out_tok = clean_payload.get("output_tokens")
    output_tokens = (
        int(out_tok) if isinstance(out_tok, (int, float, str)) and str(out_tok).isdigit() else 0
    )

    cost_val = clean_payload.get("cost_usd")
    cost_usd = float(cost_val) if isinstance(cost_val, (int, float)) else 0.0

    cost_src_raw = clean_payload.get("cost_source") or "INTERNAL_VERIFIED"
    cost_source: CostSource = (
        cost_src_raw
        if cost_src_raw in ("INTERNAL_VERIFIED", "EXTERNAL_REPORTED", "ESTIMATED_SCALE")
        else "INTERNAL_VERIFIED"
    )

    native_val = clean_payload.get("native_metric_value")
    native_metric_value = float(native_val) if isinstance(native_val, (int, float)) else None

    latency_val = clean_payload.get("latency_ms")
    latency_ms = int(latency_val) if isinstance(latency_val, (int, float)) else 0

    cas_refs_raw = clean_payload.get("cas_references") or clean_payload.get("cas_references_jsonb")
    cas_refs: list[str] = [str(r) for r in cas_refs_raw] if isinstance(cas_refs_raw, list) else []

    scope_path = str(clean_payload.get("scope_path") or "GLOBAL")
    org_unit_id = str(clean_payload["org_unit_id"]) if clean_payload.get("org_unit_id") else None

    return FinopsCostLedgerEntry(
        source_event_id=event.event_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_display_name=actor_display,
        actor_email=actor_email,
        event_type=etype,
        summary=summary,
        trace_id=event.trace_id,
        workspace_id=event.workspace_id,
        org_unit_id=org_unit_id,
        scope_path=scope_path,
        run_id=event.run_id,
        root_run_id=str(clean_payload["root_run_id"]) if clean_payload.get("root_run_id") else None,
        step_execution_id=(
            str(clean_payload["step_execution_id"])
            if clean_payload.get("step_execution_id")
            else (event.aggregate_id if event.aggregate_type == "step_execution" else None)
        ),
        model_id=str(clean_payload["model_id"]) if clean_payload.get("model_id") else None,
        inference_tier=(
            str(clean_payload["inference_tier"]) if clean_payload.get("inference_tier") else None
        ),
        effort=str(clean_payload["effort"]) if clean_payload.get("effort") else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        cost_source=cost_source,
        native_metric_type=(
            str(clean_payload["native_metric_type"])
            if clean_payload.get("native_metric_type")
            else None
        ),
        native_metric_value=native_metric_value,
        native_currency=(
            str(clean_payload["native_currency"]) if clean_payload.get("native_currency") else None
        ),
        reported_by_remote=bool(clean_payload.get("reported_by_remote", False)),
        latency_ms=latency_ms,
        run_lock_sha256=(
            str(clean_payload["run_lock_sha256"]) if clean_payload.get("run_lock_sha256") else None
        ),
        pre_prompt_sha256=(
            str(clean_payload["pre_prompt_sha256"])
            if clean_payload.get("pre_prompt_sha256")
            else None
        ),
        workflow_contract_sha256=(
            str(clean_payload["workflow_contract_sha256"])
            if clean_payload.get("workflow_contract_sha256")
            else None
        ),
        cas_references=cas_refs,
        metadata=clean_payload,
    )


class AuditLedgerOutboxSubscriber:
    """Subscriber consuming domain events and persisting them to the immutable audit ledger."""

    def __init__(self, sink: AuditLedgerSinkPort) -> None:
        self._sink = sink

    async def on_domain_event(self, event: DomainEvent) -> str | None:
        """Process an incoming DomainEvent idempotently."""
        if event.event_type not in AUDITABLE_EVENT_TYPES:
            return None

        entry = map_domain_event_to_ledger_entry(event)
        try:
            return await self._sink.record_entry(entry)
        except Exception as exc:
            logger.error(
                "Failed to ingest outbox event into audit_ledger: event_id=%s, type=%s: %s",
                event.event_id,
                event.event_type,
                exc,
                exc_info=True,
            )
            raise
