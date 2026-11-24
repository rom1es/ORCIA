"""Memlog item and background fast-path audit schemas (`Story 3.2`, split from `blackboard.py`)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.blackboard.models import MemlogMarkerType


class StepMemlogSchemaItem(BaseModel):
    """Structured reasoning, assumption, or divergence entry in `step_memlog_jsonb`."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    step_key: str
    marker_type: MemlogMarkerType
    summary: str
    details: str
    source_uris: list[str] = Field(default_factory=list)


class BackgroundAuditRunRequest(BaseModel):
    """Request payload for `POST /api/v1/orchestration/runs/fast-path-audit` (`UJ-10`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=128)
    divergence_note: str = Field(
        default=(
            "TRA threshold divergence: Confluence v12 states 500 EUR "
            "vs git:// codebase states 350 EUR"
        ),
        min_length=1,
        max_length=512,
    )


class BackgroundAuditReportSchemaItem(BaseModel):
    """Consolidated report for `BACKGROUND_FAST_PATH` (`UJ-10`, `AD-13`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_uri: str
    total_steps_committed: int = Field(..., ge=0)
    assumptions: list[StepMemlogSchemaItem]
    suspected_code_bugs: list[StepMemlogSchemaItem]
    suspected_obsolete_docs: list[StepMemlogSchemaItem]
    sse_event_topic: str
    sse_latency_ms: float = Field(..., ge=0.0, lt=500.0)


class BackgroundAuditRunResponse(BaseModel):
    """Response payload for `POST /api/v1/orchestration/runs/fast-path-audit`."""

    model_config = ConfigDict(extra="forbid")

    report: BackgroundAuditReportSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class ArbitrationOptionSchemaItem(BaseModel):
    """Comparative option inside an `Arbitration Tie-Break Matrix` (`UX-DR6`)."""

    model_config = ConfigDict(extra="forbid")

    option_key: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=255)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    si_impact: str = Field(..., min_length=1, max_length=512)
    finops_impact: str = Field(..., min_length=1, max_length=512)
    recommended: bool = Field(default=False)
    ontology_concept_key: str | None = Field(default=None, max_length=160)
