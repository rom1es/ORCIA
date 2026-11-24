"""Localized FR/EN outbox event summary builder for Audit & FinOps ledger (`Story 27.7`)."""

from __future__ import annotations

from typing import Any

from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale


def _norm_locale(locale: str) -> SupportedLocale:
    return "en" if (locale or DEFAULT_LOCALE).strip().lower().startswith("en") else "fr"


def build_localized_event_summary(
    event_type: str, payload: dict[str, Any], *, locale: str = DEFAULT_LOCALE
) -> str:
    """Build a localized FR/EN human-readable summary for a `DomainEvent`."""
    lang = _norm_locale(locale)
    if event_type in ("AdminConnectionTested", "ADMIN_CONNECTION_TEST"):
        target = payload.get("target_type") or "service"
        tid = payload.get("target_id") or ""
        status = payload.get("test_status") or "SUCCESS"
        prefix = "Admin connection test" if lang == "en" else "Test de connexion administrateur"
        return f"{prefix} [{target}] {tid}: {status}".strip()
    if event_type == "StepCompleted":
        sk = payload.get("step_key") or "step"
        st = payload.get("step_status") or "COMMITTED"
        return f"Step completed: {sk} ({st})" if lang == "en" else f"Étape exécutée : {sk} ({st})"
    if event_type == "GateEvaluated":
        gk = payload.get("gate_key") or "gate"
        dec = payload.get("decision") or "APPROVED"
        if lang == "en":
            return f"Gate evaluation: {gk} -> {dec}"
        return f"Évaluation de validation (Gate) : {gk} -> {dec}"
    if event_type == "ArtifactProduced":
        aid = payload.get("artifact_id") or "artifact"
        at = payload.get("artifact_type") or "document"
        return (
            f"Artifact produced: {aid} ({at})"
            if lang == "en"
            else f"Livrable produit : {aid} ({at})"
        )
    if event_type == "RunTerminated":
        st = payload.get("final_status") or "COMPLETED"
        return (
            f"Workflow run terminated: {st}"
            if lang == "en"
            else f"Fin d'exécution du processus : {st}"
        )
    if event_type == "SettingsChanged":
        cat = payload.get("category") or "settings"
        key = payload.get("key") or "item"
        lvl = payload.get("scope_level") or "PLATFORM"
        return (
            f"Settings updated: {cat}.{key} ({lvl})"
            if lang == "en"
            else f"Modification de paramètre : {cat}.{key} ({lvl})"
        )
    if event_type == "BudgetCircuitTripped":
        default_reason = "budget exceeded" if lang == "en" else "budget dépassé"
        reason = payload.get("trip_reason") or default_reason
        return (
            f"Budget circuit tripped: {reason}"
            if lang == "en"
            else f"Coupe-circuit budgétaire déclenché : {reason}"
        )
    if event_type == "BudgetOverrideApproved":
        amt = payload.get("override_amount_usd", 0.0)
        return (
            f"Budget override approved (+{amt} USD)"
            if lang == "en"
            else f"Dérogation budgétaire approuvée (+{amt} USD)"
        )
    if event_type == "RemoteUsageAnomalyCapped":
        cid = payload.get("connector_id", "")
        return (
            f"Anomalous remote telemetry capped on connector {cid}"
            if lang == "en"
            else f"Écrêtement de télémétrie anormale sur connecteur {cid}"
        )
    if event_type == "ConnectorCircuitTripped":
        cid = payload.get("connector_id", "")
        reason = payload.get("reason", "")
        return (
            f"Circuit breaker opened on connector {cid}: {reason}"
            if lang == "en"
            else f"Coupe-circuit ouvert sur connecteur {cid} : {reason}"
        )
    if event_type == "AutonomousContractSigned":
        wf = payload.get("workflow_id", "")
        sp = payload.get("service_principal_id", "")
        if lang == "en":
            return f"Autonomy contract signed on {wf} (service account {sp})"
        return f"Contrat d'autonomie signé sur {wf} (compte de service {sp})"
    if event_type == "AutonomousContractRevoked":
        wf = payload.get("workflow_id", "")
        return (
            f"Autonomy contract revoked on {wf}"
            if lang == "en"
            else f"Contrat d'autonomie révoqué sur {wf}"
        )
    if event_type == "AutonomousEscalated":
        wf = payload.get("workflow_id", "")
        reason = payload.get("reason", "")
        return (
            f"Autonomous execution escalated on {wf}: {reason}"
            if lang == "en"
            else f"Escalade d'exécution autonome sur {wf} : {reason}"
        )
    if event_type == "TriggerFired":
        tid = payload.get("trigger_id", "")
        ttype = payload.get("trigger_type", "")
        return (
            f"Trigger fired ({ttype}): {tid}"
            if lang == "en"
            else f"Déclencheur exécuté ({ttype}) : {tid}"
        )
    if event_type == "SelfTriggerBlocked":
        tid = payload.get("trigger_id", "")
        reason = payload.get("reason", "")
        return (
            f"Self-trigger blocked on {tid}: {reason}"
            if lang == "en"
            else f"Auto-déclenchement bloqué sur {tid} : {reason}"
        )
    if event_type == "TriggerCircuitOpened":
        tid = payload.get("trigger_id", "")
        reason = payload.get("reason", "")
        return (
            f"Circuit breaker opened on trigger {tid}: {reason}"
            if lang == "en"
            else f"Coupe-circuit ouvert sur déclencheur {tid} : {reason}"
        )
    if event_type == "WorkflowPublished":
        wf = payload.get("workflow_id", "")
        ver = payload.get("version", "")
        return (
            f"Workflow published: {wf} (v{ver})"
            if lang == "en"
            else f"Processus publié : {wf} (v{ver})"
        )
    if event_type == "PostHocSampleSelected":
        wf = payload.get("workflow_id", "")
        return (
            f"Run selected for post-hoc quality sampling: {wf}"
            if lang == "en"
            else f"Exécution sélectionnée pour contrôle qualité par échantillonnage : {wf}"
        )
    if event_type == "KillSwitchActivated":
        wf = payload.get("workflow_id", "")
        reason = payload.get("reason", "")
        base = (
            f"Kill switch activated on {wf}" if lang == "en" else f"Arrêt d'urgence activé sur {wf}"
        )
        sep = ": " if lang == "en" else " : "
        return base + (f"{sep}{reason}" if reason else "")
    if event_type == "AutonomousArtifactRolledBack":
        wf = payload.get("workflow_id", "")
        ver = payload.get("restored_version", "")
        if lang == "en":
            return f"Automated artifact rolled back and version {ver} restored on {wf}"
        return f"Livrable automatisé annulé et version {ver} rétablie sur {wf}"
    return (
        f"Event recorded: {event_type}" if lang == "en" else f"Événement enregistré : {event_type}"
    )
