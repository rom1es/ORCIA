"""HTTP Transport Schemas (`*Request`, `*Response`) for Adaptive Human Gates (`Story 4.3`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChunkApprovalSchemaItem(BaseModel):
    """Serialized `ChunkApprovalRecord` (`chunk_approvals` table, `UX-DR5`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=128)
    gate_evaluation_id: str = Field(..., min_length=1, max_length=128)
    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)
    chunk_key: str = Field(..., min_length=1, max_length=128)
    section_title: str = Field(..., min_length=1, max_length=255)
    section_index: int = Field(default=0, ge=0)
    content_markdown: str = Field(default="")
    word_count: int = Field(default=0, ge=0)
    human_authored_required: bool = Field(default=False)
    status: Literal["PENDING", "APPROVED", "CO_EDITED", "CHALLENGED"] = Field(default="PENDING")
    reviewer_user_id: str | None = Field(default=None)
    human_anchor_signature_id: str | None = Field(default=None)
    human_anchor_sha256: str | None = Field(default=None)
    challenge_reason: str | None = Field(default=None)
    reviewed_at: datetime | None = Field(default=None)


class HumanGateEvaluationSchemaItem(BaseModel):
    """Serialized `HumanGateEvaluationRecord` (`Story 4.3`, `AD-11`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=128)
    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    policy: Literal["mandatory_full", "risk_or_exception_based", "sampling"]
    status: Literal["PASS", "FAIL", "PENDING_HUMAN_REVIEW"]
    auto_passed: bool
    deterministic_status: str
    agentic_score: float
    ontology_conflicts: int
    stale_warnings: int
    total_word_count: int
    briefing_4blocks_jsonb: dict[str, Any]
    hypotheses_block_inspected: bool
    chunks: list[ChunkApprovalSchemaItem]
    review_duration_ms: int
    fast_approval_warning: bool
    reviewer_user_id: str | None = None
    outbox_event_id: str | None = None
    evaluated_at: datetime


class HumanGateEvaluateRequest(BaseModel):
    """Request payload for `POST /api/v1/gates/human/evaluate` (`Story 4.3`, `AD-11`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    policy: Literal["mandatory_full", "risk_or_exception_based", "sampling"] = Field(
        default="risk_or_exception_based"
    )
    artifact_payload: dict[str, Any] = Field(default_factory=dict)
    deterministic_status: str = Field(default="PASS")
    agentic_score: float = Field(default=0.92, ge=0.0, le=1.0)
    ontology_conflicts: int = Field(default=0, ge=0)
    stale_warnings: int = Field(default=0, ge=0)
    briefing_4blocks_jsonb: dict[str, Any] | None = Field(default=None)
    sampling_override: bool | None = Field(default=None)


class HumanGateEvaluateResponse(BaseModel):
    """Response for `POST /api/v1/gates/human/evaluate` (`Story 4.3`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation: HumanGateEvaluationSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class HumanGateChunkDecideRequest(BaseModel):
    """Request payload for chunk decision endpoint (`UX-DR5`, `Story 4.3`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal["APPROVE", "CO_EDIT", "CHALLENGE"]
    co_edited_content: str | None = Field(default=None)
    challenge_reason: str | None = Field(default=None, max_length=2048)


class HumanGateChunkDecideResponse(BaseModel):
    """Response for `POST /api/v1/gates/human/{gate_evaluation_id}/chunks/{chunk_key}/decide`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: ChunkApprovalSchemaItem
    evaluation: HumanGateEvaluationSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class HumanGateFinalizeRequest(BaseModel):
    """Request payload for `POST /api/v1/gates/human/{gate_evaluation_id}/finalize` (`AD-11`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_duration_ms: int = Field(..., ge=0)
    explicit_hypotheses_confirmation: bool = Field(default=False)


class HumanGateFinalizeResponse(BaseModel):
    """Response for `POST /api/v1/gates/human/{gate_evaluation_id}/finalize` (`AD-11`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation: HumanGateEvaluationSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)
