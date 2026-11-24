"""Serialization helper for `bounded_workflow_models.py` (`Story 16.3`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from orcia_core.ports.bounded_workflow_port import (
    BoundedWorkflowLaunchOutcome,
    BoundedWorkflowSubStepDto,
)

if TYPE_CHECKING:
    from orcia_connectors.bounded_workflow_models import BoundedWorkflowRunState


def serialize_bounded_launch_outcome(
    state: BoundedWorkflowRunState,
) -> BoundedWorkflowLaunchOutcome:
    """Serialize `BoundedWorkflowRunState` to pure hexagonal `BoundedWorkflowLaunchOutcome`."""
    dtos = [
        BoundedWorkflowSubStepDto(
            sub_step_id=rec.sub_step_id,
            sub_step_name=rec.sub_step_name,
            iteration=rec.iteration,
            idempotency_key=rec.idempotency_key,
            status=rec.status,
            artifact_pointer_payload=(
                rec.artifact_pointer.model_dump(mode="json")
                if rec.artifact_pointer is not None
                else None
            ),
            reflexive_execution_id=rec.reflexive_execution_id,
            write_preview_payload=(
                rec.write_preview_card.model_dump(mode="json")
                if rec.write_preview_card is not None
                else None
            ),
            human_actor_id=rec.human_actor_id,
            correction_remarks_applied=rec.correction_remarks_applied,
            codegraph_impact=rec.codegraph_impact,
        )
        for rec in state.sub_step_records
    ]
    return BoundedWorkflowLaunchOutcome(
        run_id=state.run_id,
        workflow_id=state.workflow_id,
        workflow_slug=state.workflow_slug,
        workflow_version=state.workflow_version,
        execution_mode=str(state.execution_mode),
        iteration=state.iteration,
        reentry_mode=state.reentry_mode,
        status=state.status,
        current_sub_step_index=state.current_sub_step_index,
        inputs=state.inputs,
        mcp_context_bundle=state.mcp_context_bundle,
        sub_step_records=dtos,
        gate_report_payload=(
            state.gate_report.model_dump(mode="json") if state.gate_report is not None else None
        ),
        final_artifact_payload=(
            state.final_artifact_pointer.model_dump(mode="json")
            if state.final_artifact_pointer is not None
            else None
        ),
        return_loop_target_step_num=state.return_loop_target_step_num,
        return_loop_remarks=state.return_loop_remarks,
        audit_trail=state.audit_trail,
        trace_events=state.trace_events,
    )
