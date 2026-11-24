"""Story 27.7 — Comprehensive branch coverage for bilingual locale bundles and catalogs."""

from __future__ import annotations

import pytest

from orcia_api.locales._router_locale_messages import get_router_copy, get_shell_scope_copy
from orcia_api.routers._assistant_turn_locale_messages import (
    build_budget_reached_prompt,
    build_synthesize_now_prompt,
    format_governed_tool_round_summary,
    format_zero_tokens_error_detail,
)
from orcia_core.audit_finops._audit_finops_locales import get_audit_finops_locale_bundle
from orcia_core.audit_finops._outbox_locale_messages import build_localized_event_summary
from orcia_core.bootstrap._bootstrap_locales import (
    get_bootstrap_rag_seed_copy,
    get_otp_email_copy,
)
from orcia_core.catalog._contextual_help_locales import build_localized_assistant_prefill
from orcia_core.gates._gate_locales import get_gate_locale_bundle
from orcia_core.kernel.errors import get_localized_error_text, resolve_locale

_OUTBOX_EVENT_CASES: list[tuple[str, dict[str, object]]] = [
    ("AdminConnectionTested", {"target_type": "llm", "target_id": "m1", "test_status": "OK"}),
    ("ADMIN_CONNECTION_TEST", {"target_type": "git", "target_id": "g1", "test_status": "FAIL"}),
    ("StepCompleted", {"step_key": "spec", "step_status": "COMMITTED"}),
    ("GateEvaluated", {"gate_key": "arch", "decision": "APPROVED"}),
    ("ArtifactProduced", {"artifact_id": "a1", "artifact_type": "markdown"}),
    ("RunTerminated", {"final_status": "COMPLETED"}),
    ("SettingsChanged", {"category": "auth", "key": "mode", "scope_level": "PLATFORM"}),
    ("BudgetCircuitTripped", {"trip_reason": "limit"}),
    ("BudgetCircuitTripped", {}),
    ("BudgetOverrideApproved", {"override_amount_usd": 25.0}),
    ("RemoteUsageAnomalyCapped", {"connector_id": "jira-1"}),
    ("ConnectorCircuitTripped", {"connector_id": "git-1", "reason": "timeout"}),
    ("AutonomousContractSigned", {"workflow_id": "wf-1", "service_principal_id": "sp-1"}),
    ("AutonomousContractRevoked", {"workflow_id": "wf-1"}),
    ("AutonomousEscalated", {"workflow_id": "wf-1", "reason": "low confidence"}),
    ("TriggerFired", {"trigger_id": "tr-1", "trigger_type": "cron"}),
    ("SelfTriggerBlocked", {"trigger_id": "tr-1", "reason": "loop"}),
    ("TriggerCircuitOpened", {"trigger_id": "tr-1", "reason": "errors"}),
    ("WorkflowPublished", {"workflow_id": "wf-1", "version": 3}),
    ("PostHocSampleSelected", {"workflow_id": "wf-1"}),
    ("KillSwitchActivated", {"workflow_id": "wf-1", "reason": "manual"}),
    ("KillSwitchActivated", {"workflow_id": "wf-1"}),
    ("AutonomousArtifactRolledBack", {"workflow_id": "wf-1", "restored_version": 2}),
    ("UnknownCustomEvent", {}),
]


@pytest.mark.parametrize(("event_type", "payload"), _OUTBOX_EVENT_CASES)
def test_outbox_locale_messages_all_events_fr_and_en(
    event_type: str, payload: dict[str, object]
) -> None:
    """Every Outbox event type renders distinct FR and EN audit summaries."""
    fr_summary = build_localized_event_summary(event_type, payload, locale="fr")
    en_summary = build_localized_event_summary(event_type, payload, locale="en")
    assert fr_summary and en_summary
    assert fr_summary != en_summary


def test_assistant_turn_locale_messages_fr_and_en() -> None:
    """Assistant turn prompt helpers handle FR, EN, and singular/plural tool counts."""
    assert "Synthèse anticipée" in build_synthesize_now_prompt("fr")
    assert "Early synthesis" in build_synthesize_now_prompt("en")
    assert "Budget d'exécution" in build_budget_reached_prompt("fr")
    assert "Execution budget" in build_budget_reached_prompt("en")
    assert "1 appel d'outil" in format_governed_tool_round_summary(1, "fr")
    assert "2 appels d'outils" not in format_governed_tool_round_summary(2, "fr")
    assert "appels d'outil gouvernés exécutés" in format_governed_tool_round_summary(2, "fr")
    assert "2 governed tool call(s)" in format_governed_tool_round_summary(2, "en")
    assert "jeton" in format_zero_tokens_error_detail("gpt-5", "https://api.example/v1", "fr")
    assert "zero tokens" in format_zero_tokens_error_detail("gpt-5", "https://api.example/v1", "en")


def test_kernel_error_catalog_resolution_edge_cases() -> None:
    """Cover Accept-Language q-weight parsing, fallback, overrides, and safe formatting."""
    assert resolve_locale(None) == "fr"
    assert resolve_locale("") == "fr"
    assert resolve_locale(" , ; ") == "fr"
    assert resolve_locale("de-DE;q=0.9, en-US;q=bad, fr-FR;q=0.8") == "fr"
    assert resolve_locale("en-US;q=0, fr-FR;q=0.5") == "fr"
    assert resolve_locale("en-US;q=1.5, de;q=0.9") == "fr"
    assert resolve_locale("de-DE, es-ES") == "fr"
    assert resolve_locale("fr-FR;q=0.7, en-GB;q=0.9") == "en"

    fallback = get_localized_error_text("ERR_DOES_NOT_EXIST_999", "en")
    assert fallback.title == "Internal platform error"

    overridden = get_localized_error_text(
        "ERR_VALIDATION_FAILED", "fr", detail_override="Custom detail"
    )
    assert overridden.detail == "Custom detail"

    preserved = get_localized_error_text(
        "ERR_MODEL_ORTHOGONALITY_VIOLATION_DETAIL",
        "en",
        detail_code="ERR_MODEL_ORTHOGONALITY_VIOLATION_DETAIL",
        detail_params={"evaluator_model_family": "anthropic"},
    )
    assert "anthropic" in preserved.detail
    assert "{executor_model_family}" in preserved.detail


def test_bootstrap_catalog_gates_finops_and_router_locale_bundles() -> None:
    """Cover remaining FR/EN locale bundle helpers for bootstrap, help, gates, finops, router."""
    subj_fr, body_fr = get_otp_email_copy("fr", otp_code="123456", ttl_minutes=10)
    subj_en, body_en = get_otp_email_copy("en", otp_code="123456", ttl_minutes=10)
    assert subj_fr != subj_en and "123456" in body_fr and "123456" in body_en

    assert (
        get_bootstrap_rag_seed_copy("fr").jira_title != get_bootstrap_rag_seed_copy("en").jira_title
    )
    assert build_localized_assistant_prefill("/inbox", "Inbox", "fr") != (
        build_localized_assistant_prefill("/inbox", "Inbox", "en")
    )
    assert get_gate_locale_bundle("fr").lens3_pass != get_gate_locale_bundle("en").lens3_pass
    assert (
        get_audit_finops_locale_bundle("fr").prov_aligned
        != get_audit_finops_locale_bundle("en").prov_aligned
    )
    assert get_router_copy("fr").pack_builder_title != get_router_copy("en").pack_builder_title
    assert get_shell_scope_copy("fr")["scope_bu"] != get_shell_scope_copy("en")["scope_bu"]
