"""HTTP/OpenAPI 3.1 transport schemas for Story 6.1 (Audit Ledger & Provenance Dossier).

Follows RFC 9457 Problem Details and Pydantic v2 strict typing conventions (`AD-12`, `AD-19`).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AuditLedgerEntrySchema(BaseModel):
    """Single immutable audit ledger entry record."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_event_id: str
    actor_type: str
    actor_id: str
    event_type: str
    summary: str
    trace_id: str
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
    cost_source: str = "INTERNAL_VERIFIED"
    native_metric_type: str | None = None
    native_metric_value: float | None = None
    native_currency: str | None = None
    reported_by_remote: bool = False
    latency_ms: int = 0
    run_lock_sha256: str | None = None
    pre_prompt_sha256: str | None = None
    workflow_contract_sha256: str | None = None
    cas_references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class AuditLedgerPageResponse(BaseModel):
    """Paginated list of immutable audit ledger entries."""

    model_config = ConfigDict(extra="forbid")

    entries: list[AuditLedgerEntrySchema]
    total: int
    limit: int
    offset: int


class AuditProvenanceSummaryResponse(BaseModel):
    """Consolidated provenance summary for a workflow run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    root_run_id: str | None = None
    total_events: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    models_invoked: list[str]
    actors_involved: list[str]
    run_lock_sha256: str | None = None
    workflow_contract_sha256: str | None = None
    cas_references: list[str]
    is_run_lock_aligned: bool
    first_event_at: str | None = None
    last_event_at: str | None = None


class AuditExportResponse(BaseModel):
    """Sealed audit and compliance export payload in JSON or Markdown format."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    format: Literal["json", "md"]
    content: str
    exported_at: str
    manifest_sha256: str | None = None
    entries_count: int
