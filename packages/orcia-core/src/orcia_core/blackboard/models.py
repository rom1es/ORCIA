"""Pure domain models for Bounded Context 2: Blackboard & Durable Step Executions (Story 3.2).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orcia_kernel.enums import (
    MemlogMarkerType,
    SnapshotBranchStatus,
    StepExecutionStatus,
    WorkflowExecutionRegime,
    WorkflowStepType,
)


@dataclass(frozen=True, slots=True)
class StepMemlogEntry:
    """Structured reasoning, assumption, or divergence entry in `step_memlog_jsonb`."""

    entry_id: str
    step_key: str
    marker_type: MemlogMarkerType
    summary: str
    details: str
    source_uris: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize memlog entry to JSON-compatible dict."""
        return {
            "entry_id": self.entry_id,
            "step_key": self.step_key,
            "marker_type": self.marker_type,
            "summary": self.summary,
            "details": self.details,
            "source_uris": list(self.source_uris),
        }


@dataclass(frozen=True, slots=True)
class BlackboardSnapshotEntity:
    """Immutable append-only checkpoint row in `blackboard_snapshots` (`AD-2`, `NFR-SEC-3`)."""

    id: str
    snapshot_key: str
    run_id: str
    step_execution_id: str
    parent_snapshot_id: str | None
    step_key: str
    branch_status: SnapshotBranchStatus
    artifact_payload: dict[str, Any]
    artifact_cas_key: str
    artifact_sha256: str
    memlog_summary: tuple[StepMemlogEntry, ...] = ()
    superseded_snapshot_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StepExecutionEntity:
    """Durable step execution state separating mutable drafts from committed snapshots (`AD-2`)."""

    id: str
    step_execution_key: str
    run_id: str
    step_key: str
    step_index: int
    step_type: WorkflowStepType
    execution_mode: WorkflowExecutionRegime
    status: StepExecutionStatus
    attempt_count: int = 0
    max_agent_retries: int = 3
    draft_artifact: dict[str, Any] = field(default_factory=dict)
    draft_cas_key: str | None = None
    step_memlog: tuple[StepMemlogEntry, ...] = ()
    hydrated_input_uris: tuple[str, ...] = ()
    child_run_id: str | None = None
    committed_snapshot_id: str | None = None
    cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class HydratedStepContext:
    """Filtered Just-In-Time context injected into Step $k$ (`JitStepHydrator`, `AD-13`).

    Guarantees 0 instructions from future steps $k+1..N$ and 0 undeclared upstream artifacts.
    """

    run_id: str
    step_key: str
    step_title: str
    step_type: WorkflowStepType
    execution_mode: WorkflowExecutionRegime
    step_directive: str
    declared_input_uris: tuple[str, ...]
    resolved_inputs: dict[str, Any]
    future_step_instructions_leaked: int = 0
    undeclared_artifacts_leaked: int = 0


@dataclass(frozen=True, slots=True)
class BackgroundAuditConsolidatedReport:
    """Consolidated end-of-run report for `BACKGROUND_FAST_PATH` (`UJ-10`, `AD-13`)."""

    run_id: str
    workflow_uri: str
    total_steps_committed: int
    assumptions: tuple[StepMemlogEntry, ...]
    suspected_code_bugs: tuple[StepMemlogEntry, ...]
    suspected_obsolete_docs: tuple[StepMemlogEntry, ...]
    sse_event_topic: str
    sse_latency_ms: float


__all__ = [
    "BackgroundAuditConsolidatedReport",
    "BlackboardSnapshotEntity",
    "HydratedStepContext",
    "MemlogMarkerType",
    "SnapshotBranchStatus",
    "StepExecutionEntity",
    "StepExecutionStatus",
    "StepMemlogEntry",
    "WorkflowExecutionRegime",
    "WorkflowStepType",
]
