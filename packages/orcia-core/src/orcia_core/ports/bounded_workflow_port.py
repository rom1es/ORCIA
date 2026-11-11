"""Pure hexagonal port for launching Milestone-Driven bounded workflows (`Story 16.3`, `AD-19`).

Enforces strict inversion of dependencies: `orcia_core` never imports `orcia_connectors` or `dbos`.
Instead, `ProcessExecutionDispatcher` awaits `BoundedWorkflowLauncherPort`, implemented by
`orcia_connectors.bounded_workflow_v2.BoundedWorkflowLauncherAdapter`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.ports.reflexive_runtime_ports import AgentTraceEvent


class SubStepAgentExecutionOutcome(BaseModel):
    """Encapsulated outcome of a reflexive loop inside a single bounded sub-step (Principle 7).

    Persists only the consolidated deliverable text and `reflexive_execution_id`
    so the bounded workflow checkpoint never accumulates internal scratchpad history.
    """

    model_config = ConfigDict(extra="forbid")

    reflexive_execution_id: str
    final_markdown: str
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)


BoundedSubStepAgentCallback = Callable[
    [str, str, str, dict[str, Any], int, str | None],
    Awaitable[SubStepAgentExecutionOutcome],
]


class BoundedWorkflowSubStepDto(BaseModel):
    """Pure port DTO representing an executed sub-step record without connector coupling."""

    model_config = ConfigDict(extra="forbid")

    sub_step_id: str
    sub_step_name: str
    iteration: int
    idempotency_key: str
    status: Literal[
        "WAITING_CHECKPOINT",
        "WAITING_WRITE_PREVIEW",
        "WAITING_EXTERNAL_EVENT",
        "COMPLETED",
        "SKIPPED",
    ]
    artifact_pointer_payload: dict[str, Any] | None = None
    reflexive_execution_id: str | None = None
    write_preview_payload: dict[str, Any] | None = None
    human_actor_id: str | None = None
    correction_remarks_applied: str | None = None


class BoundedWorkflowLaunchOutcome(BaseModel):
    """Pure port outcome returned by `BoundedWorkflowLauncherPort`."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_id: str
    workflow_slug: str
    workflow_version: str
    execution_mode: str
    iteration: int = 1
    reentry_mode: Literal["initial", "corrections"] = "initial"
    status: Literal[
        "RUNNING",
        "WAITING_SUBSTEP_HITL",
        "WAITING_EXTERNAL_GATE",
        "WAITING_FINAL_ANCHOR",
        "COMPLETED_APPROVED",
        "RETURN_LOOP_TRIGGERED",
        "SLA_SUSPENDED",
        "FAILED_GATES",
    ]
    current_sub_step_index: int = 0
    inputs: dict[str, Any] = Field(default_factory=dict)
    mcp_context_bundle: dict[str, Any] | None = None
    sub_step_records: list[BoundedWorkflowSubStepDto] = Field(default_factory=list)
    gate_report_payload: dict[str, Any] | None = None
    final_artifact_payload: dict[str, Any] | None = None
    return_loop_target_step_num: str | None = None
    return_loop_remarks: str | None = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)


@runtime_checkable
class BoundedWorkflowLauncherPort(Protocol):
    """Hexagonal port delegating milestone workflows to the durable bounded runner."""

    async def launch_bounded_workflow(
        self,
        workflow_payload: dict[str, Any],
        *,
        run_id: str,
        inputs: dict[str, Any] | None = None,
        iteration: int = 1,
        reentry_mode: Literal["initial", "corrections"] = "initial",
        correction_remarks: str | None = None,
        auto_approve_checkpoints: bool = False,
        sub_step_agent_callback: BoundedSubStepAgentCallback | None = None,
    ) -> BoundedWorkflowLaunchOutcome: ...


__all__ = [
    "BoundedSubStepAgentCallback",
    "BoundedWorkflowLaunchOutcome",
    "BoundedWorkflowLauncherPort",
    "BoundedWorkflowSubStepDto",
    "SubStepAgentExecutionOutcome",
]
