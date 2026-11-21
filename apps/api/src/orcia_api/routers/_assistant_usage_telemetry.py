"""Thin API facade for token telemetry & `audit_ledger` sink resolution (`Story 26.2`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.llm_usage_telemetry import (
    estimate_tokens_deterministic as estimate_tokens_deterministic,
)
from orcia_core.orchestration.llm_usage_telemetry import (
    extract_usage_tokens_from_payload as extract_usage_tokens_from_payload,
)
from orcia_core.orchestration.llm_usage_telemetry import (
    persist_assistant_turn_ledger_entry as persist_assistant_turn_ledger_entry,
)
from orcia_core.orchestration.llm_usage_telemetry import (
    resolve_usage_with_fallback as resolve_usage_with_fallback,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort


def resolve_audit_ledger_sink(request: Any | None) -> AuditLedgerSinkPort | None:
    """Safely resolve `AuditLedgerSinkPort` from `request.app.state` without side effects."""
    state = getattr(getattr(request, "app", None), "state", None)
    if state is None:
        return None
    svc = getattr(state, "audit_ledger_service", None)
    if isinstance(svc, AuditLedgerSinkPort):
        return svc
    engine = getattr(state, "db_engine", None)
    if engine is not None:
        from orcia_core.audit_finops import SqlAuditLedgerService

        return SqlAuditLedgerService(engine=engine)
    return None


__all__ = [
    "estimate_tokens_deterministic",
    "extract_usage_tokens_from_payload",
    "persist_assistant_turn_ledger_entry",
    "resolve_audit_ledger_sink",
    "resolve_usage_with_fallback",
]
