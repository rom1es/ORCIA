"""Thin API facade for token telemetry & `audit_ledger` sink resolution (`Story 26.2`)."""

from __future__ import annotations

from orcia_api.dependencies._telemetry_sinks import (
    resolve_assistant_outbox_emitter as resolve_assistant_outbox_emitter,
)
from orcia_api.dependencies._telemetry_sinks import (
    resolve_audit_ledger_sink as resolve_audit_ledger_sink,
)
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

__all__ = [
    "estimate_tokens_deterministic",
    "extract_usage_tokens_from_payload",
    "persist_assistant_turn_ledger_entry",
    "resolve_assistant_outbox_emitter",
    "resolve_audit_ledger_sink",
    "resolve_usage_with_fallback",
]
