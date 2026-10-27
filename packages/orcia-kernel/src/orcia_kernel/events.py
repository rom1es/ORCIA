"""Immutable Domain Events for the Transactional Outbox (`domain_events_outbox`, `AD-12`, `AD-19`).

Pure kernel module — zero framework or business domain dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orcia_kernel.enums import OutboxEventStatus, StepExecutionStatus
from orcia_kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base immutable domain event stored in `domain_events_outbox` (`Q2: 2A`, `C3`)."""

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    run_id: str | None
    workspace_id: str | None
    payload: dict[str, Any]
    trace_id: str = "00000000000000000000000000000000"
    status: OutboxEventStatus = "PENDING"
    attempts: int = 0

    def to_outbox_dict(self) -> dict[str, Any]:
        """Serialize domain event to an Outbox row dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "payload_jsonb": dict(self.payload),
            "trace_id": self.trace_id,
            "status": self.status,
            "attempts": self.attempts,
        }


@dataclass(frozen=True, slots=True)
class StepCompleted(DomainEvent):
    """Published when a step execution reaches `COMMITTED` or transitions state."""

    step_key: str = ""
    step_status: StepExecutionStatus = "COMMITTED"
    cost_usd: float = 0.0

    @classmethod
    def create(
        cls,
        *,
        step_execution_id: str,
        run_id: str,
        workspace_id: str | None,
        step_key: str,
        step_status: StepExecutionStatus = "COMMITTED",
        cost_usd: float = 0.0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> StepCompleted:
        return cls(
            event_id=new_uuid7_str(),
            event_type="StepCompleted",
            aggregate_type="step_execution",
            aggregate_id=step_execution_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "step_key": step_key,
                "step_status": step_status,
                "cost_usd": cost_usd,
            },
            trace_id=trace_id,
            step_key=step_key,
            step_status=step_status,
            cost_usd=cost_usd,
        )


@dataclass(frozen=True, slots=True)
class ArtifactProduced(DomainEvent):
    """Published when an immutable Blackboard snapshot is committed."""

    snapshot_id: str = ""
    artifact_cas_key: str = ""
    artifact_sha256: str = ""

    @classmethod
    def create(
        cls,
        *,
        snapshot_id: str,
        run_id: str,
        workspace_id: str | None,
        artifact_cas_key: str,
        artifact_sha256: str,
        trace_id: str = "00000000000000000000000000000000",
    ) -> ArtifactProduced:
        return cls(
            event_id=new_uuid7_str(),
            event_type="ArtifactProduced",
            aggregate_type="blackboard_snapshot",
            aggregate_id=snapshot_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "snapshot_id": snapshot_id,
                "artifact_cas_key": artifact_cas_key,
                "artifact_sha256": artifact_sha256,
            },
            trace_id=trace_id,
            snapshot_id=snapshot_id,
            artifact_cas_key=artifact_cas_key,
            artifact_sha256=artifact_sha256,
        )


@dataclass(frozen=True, slots=True)
class GateEvaluated(DomainEvent):
    """Published when a Deterministic, Agentic, or Human Gate completes evaluation."""

    gate_type: str = "DETERMINISTIC"
    passed: bool = True
    score: float = 1.0

    @classmethod
    def create(
        cls,
        *,
        gate_evaluation_id: str,
        run_id: str,
        workspace_id: str | None,
        gate_type: str,
        passed: bool,
        score: float = 1.0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> GateEvaluated:
        return cls(
            event_id=new_uuid7_str(),
            event_type="GateEvaluated",
            aggregate_type="gate_evaluation",
            aggregate_id=gate_evaluation_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "gate_type": gate_type,
                "passed": passed,
                "score": score,
            },
            trace_id=trace_id,
            gate_type=gate_type,
            passed=passed,
            score=score,
        )


@dataclass(frozen=True, slots=True)
class RunTerminated(DomainEvent):
    """Published when a Workflow Run reaches a terminal status (`COMPLETED` or `FAILED`)."""

    final_status: str = "COMPLETED"
    total_cost_usd: float = 0.0

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        workspace_id: str | None,
        final_status: str,
        total_cost_usd: float = 0.0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> RunTerminated:
        return cls(
            event_id=new_uuid7_str(),
            event_type="RunTerminated",
            aggregate_type="workflow_run",
            aggregate_id=run_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "final_status": final_status,
                "total_cost_usd": total_cost_usd,
            },
            trace_id=trace_id,
            final_status=final_status,
            total_cost_usd=total_cost_usd,
        )


@dataclass(frozen=True, slots=True)
class HumanArbitrationRequested(DomainEvent):
    """Published when a step pauses on `WAITING_FOR_HUMAN_ARBITRATION` (`AD-3`)."""

    step_key: str = ""
    options_count: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        arbitration_id: str,
        run_id: str,
        workspace_id: str | None,
        step_key: str,
        options_count: int = 2,
        trace_id: str = "00000000000000000000000000000000",
    ) -> HumanArbitrationRequested:
        return cls(
            event_id=new_uuid7_str(),
            event_type="HumanArbitrationRequested",
            aggregate_type="human_arbitration",
            aggregate_id=arbitration_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "step_key": step_key,
                "options_count": options_count,
            },
            trace_id=trace_id,
            step_key=step_key,
            options_count=options_count,
        )
