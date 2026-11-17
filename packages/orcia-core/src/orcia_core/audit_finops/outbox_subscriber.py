"""Idempotent domain event subscriber for immutable audit ledger ingestion (`Story 6.1`).

Listens to `domain_events_outbox` stream, scrubs sensitive data (`DEC-SEC-01`),
and persists immutable records with strict idempotency on `source_event_id`.
"""

from __future__ import annotations

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
    }
)


def _build_event_summary(event: DomainEvent) -> str:
    payload = event.payload
    etype = event.event_type
    if etype == "AdminConnectionTested":
        target = payload.get("target_type") or "service"
        target_id = payload.get("target_id") or ""
        status = payload.get("test_status") or "SUCCESS"
        return f"Test de connexion administrateur [{target}] {target_id}: {status}".strip()
    if etype == "StepCompleted":
        step_key = payload.get("step_key") or "step"
        status = payload.get("step_status") or "COMMITTED"
        return f"Étape exécutée : {step_key} ({status})"
    if etype == "GateEvaluated":
        gate_key = payload.get("gate_key") or "gate"
        decision = payload.get("decision") or "APPROVED"
        return f"Évaluation de validation (Gate) : {gate_key} -> {decision}"
    if etype == "ArtifactProduced":
        art_id = payload.get("artifact_id") or "artefact"
        art_type = payload.get("artifact_type") or "document"
        return f"Livrable produit : {art_id} ({art_type})"
    if etype == "RunTerminated":
        status = payload.get("final_status") or "COMPLETED"
        return f"Fin d'exécution du processus : {status}"
    if etype == "SettingsChanged":
        cat = payload.get("category") or "settings"
        key = payload.get("key") or "item"
        level = payload.get("scope_level") or "PLATFORM"
        return f"Modification de paramètre : {cat}.{key} ({level})"
    if etype == "BudgetCircuitTripped":
        reason = payload.get("trip_reason") or "budget dépassé"
        return f"Coupe-circuit budgétaire déclenché : {reason}"
    if etype == "BudgetOverrideApproved":
        amount = payload.get("override_amount_usd", 0.0)
        return f"Dérogation budgétaire approuvée (+{amount} USD)"
    if etype == "RemoteUsageAnomalyCapped":
        cid = payload.get("connector_id", "")
        return f"Écrêtement de télémétrie anormale sur connecteur {cid}"
    if etype == "ConnectorCircuitTripped":
        cid = payload.get("connector_id", "")
        reason = payload.get("reason", "")
        return f"Coupe-circuit ouvert sur connecteur {cid} : {reason}"
    if etype == "AutonomousContractSigned":
        wf_id = payload.get("workflow_id", "")
        sp_id = payload.get("service_principal_id", "")
        return f"Contrat d'autonomie signé sur {wf_id} (compte de service {sp_id})"
    if etype == "AutonomousContractRevoked":
        wf_id = payload.get("workflow_id", "")
        return f"Contrat d'autonomie révoqué sur {wf_id}"
    if etype == "AutonomousEscalated":
        wf_id = payload.get("workflow_id", "")
        reason = payload.get("reason", "")
        return f"Escalade d'exécution autonome sur {wf_id} : {reason}"
    if etype == "TriggerFired":
        trig_id = payload.get("trigger_id", "")
        trig_type = payload.get("trigger_type", "")
        return f"Déclencheur exécuté ({trig_type}) : {trig_id}"
    if etype == "SelfTriggerBlocked":
        trig_id = payload.get("trigger_id", "")
        reason = payload.get("reason", "")
        return f"Auto-déclenchement bloqué sur {trig_id} : {reason}"
    if etype == "TriggerCircuitOpened":
        trig_id = payload.get("trigger_id", "")
        reason = payload.get("reason", "")
        return f"Coupe-circuit ouvert sur déclencheur {trig_id} : {reason}"
    if etype == "WorkflowPublished":
        wf_id = payload.get("workflow_id", "")
        ver = payload.get("version", "")
        return f"Processus publié : {wf_id} (v{ver})"
    if etype == "PostHocSampleSelected":
        wf_id = payload.get("workflow_id", "")
        return f"Exécution sélectionnée pour contrôle qualité par échantillonnage : {wf_id}"
    if etype == "KillSwitchActivated":
        wf_id = payload.get("workflow_id", "")
        reason = payload.get("reason", "")
        return f"Arrêt d'urgence activé sur {wf_id}" + (f" : {reason}" if reason else "")
    if etype == "AutonomousArtifactRolledBack":
        wf_id = payload.get("workflow_id", "")
        ver = payload.get("restored_version", "")
        return f"Livrable automatisé annulé et version {ver} rétablie sur {wf_id}"
    return f"Événement enregistré : {etype}"


def map_domain_event_to_ledger_entry(event: DomainEvent) -> FinopsCostLedgerEntry:
    """Map a domain event into an immutable FinopsCostLedgerEntry with secret scrubbing."""
    payload = dict(event.payload)
    clean_payload = scrub_sensitive_dict(payload)

    etype = event.event_type
    summary = str(clean_payload.get("summary") or _build_event_summary(event))

    actor_type = str(
        clean_payload.get("actor_type")
        or ("ADMIN_CONNECTION_TEST" if etype == "AdminConnectionTested" else "USER")
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
