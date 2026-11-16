"""Audit & FinOps domain models (`AD-12`, `AD-19`, `Story 6.1`).

Pure domain contracts — zero framework dependencies, zero cross-domain cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.ports.finops_telemetry import CostSource

AuditTimeWindow = Literal["ALL", "1H", "24H", "7D", "30D"]


@dataclass(frozen=True, slots=True)
class AuditLedgerEntry:
    """Immutable domain representation of an `audit_ledger` row."""

    id: str
    source_event_id: str
    actor_type: str
    actor_id: str
    event_type: str
    summary: str
    trace_id: str = "00000000000000000000000000000000"
    workspace_id: str | None = None
    org_unit_id: str | None = None
    scope_path: str = "GLOBAL"
    run_id: str | None = None
    root_run_id: str | None = None
    step_execution_id: str | None = None
    actor_display_name: str | None = None
    actor_email: str | None = None
    model_id: str | None = None
    inference_tier: str | None = None
    effort: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_source: CostSource = "INTERNAL_VERIFIED"
    native_metric_type: str | None = None
    native_metric_value: float | None = None
    native_currency: str | None = None
    reported_by_remote: bool = False
    latency_ms: int = 0
    run_lock_sha256: str | None = None
    pre_prompt_sha256: str | None = None
    workflow_contract_sha256: str | None = None
    cas_references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class AuditProvenanceSummary:
    """Consolidated provenance summary for a given workflow run."""

    run_id: str
    root_run_id: str | None
    total_events: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    models_invoked: list[str]
    actors_involved: list[str]
    run_lock_sha256: str | None
    workflow_contract_sha256: str | None
    cas_references: list[str]
    is_run_lock_aligned: bool
    first_event_at: str | None
    last_event_at: str | None


@dataclass(frozen=True, slots=True)
class AuditProvenanceExport:
    """Sealed compliance dossier for a workflow run, in JSON or Markdown format."""

    run_id: str
    format: Literal["json", "md"]
    content: str
    exported_at: str
    manifest_sha256: str | None
    entries_count: int


@dataclass(frozen=True, slots=True)
class AuditLedgerFilterParams:
    """Filter parameters for querying the immutable audit ledger."""

    scope_path: str | None = None
    workspace_id: str | None = None
    actor_type: str | None = None
    actor_id: str | None = None
    actor_query: str | None = None
    event_type: str | None = None
    run_id: str | None = None
    time_window: AuditTimeWindow = "ALL"
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 100
    offset: int = 0
