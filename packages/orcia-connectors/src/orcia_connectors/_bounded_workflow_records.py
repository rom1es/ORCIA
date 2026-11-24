"""Sub-step persistence helper for `bounded_workflow_hitl.py` (`Story 16.3`)."""

from __future__ import annotations

from typing import Any

from orcia_connectors.bounded_workflow_models import (
    BoundedWorkflowRunState,
    SubStepExecutionRecord,
    build_cyclic_idempotency_key,
    build_write_preview_card_for_sub_step,
)
from orcia_core.storage.claim_check import ClaimCheckStorageService
from orcia_core.workflows.schemas_v2 import DeterministicSubStepSpec, WorkflowDefinitionV2


def append_sub_step_record(
    *,
    workflow: WorkflowDefinitionV2,
    state: BoundedWorkflowRunState,
    sub_step: DeterministicSubStepSpec,
    claim_storage: ClaimCheckStorageService,
    md_content: str,
    reflexive_execution_id: str | None,
    correction_remarks: str | None,
    auto_approve_checkpoints: bool,
    codegraph_data: dict[str, Any] | None = None,
) -> None:
    """Persist a sub-step artifact via ClaimCheck and append its audit trail record."""
    idem_key = build_cyclic_idempotency_key(state.run_id, sub_step.id, state.iteration)
    pointer = claim_storage.store_artifact(
        run_id=state.run_id,
        step_id=sub_step.id,
        iteration=state.iteration,
        content=md_content,
    )
    preview_card = (
        build_write_preview_card_for_sub_step(
            run_id=state.run_id,
            workflow=workflow,
            sub_step=sub_step,
            iteration=state.iteration,
            pointer=pointer,
            md_content=md_content,
        )
        if sub_step.write_preview_required
        else None
    )
    rec = SubStepExecutionRecord(
        sub_step_id=sub_step.id,
        sub_step_name=sub_step.name,
        iteration=state.iteration,
        idempotency_key=idem_key,
        status="COMPLETED"
        if auto_approve_checkpoints
        else ("WAITING_WRITE_PREVIEW" if sub_step.write_preview_required else "WAITING_CHECKPOINT"),
        artifact_pointer=pointer,
        reflexive_execution_id=reflexive_execution_id,
        write_preview_card=preview_card,
        correction_remarks_applied=correction_remarks,
        codegraph_impact=codegraph_data,
    )
    state.sub_step_records.append(rec)
    state.final_artifact_pointer = pointer
    if reflexive_execution_id:
        state.reflexive_execution_id = reflexive_execution_id
    state.audit_trail.append(
        {
            "event": "SUBSTEP_EXECUTED",
            "sub_step_id": sub_step.id,
            "idempotency_key": idem_key,
            "s3_uri": pointer.s3_uri,
            "sha256": pointer.sha256,
            "reflexive_execution_id": reflexive_execution_id,
        }
    )
    if codegraph_data is not None:
        state.audit_trail.append(
            {
                "event": "CODEGRAPH_TOOL_EXECUTED",
                "sub_step_id": sub_step.id,
                "tool": "codegraph_calculate_blast_radius",
                "drift_warning": codegraph_data.get("drift_warning"),
                "blast_radius_score": codegraph_data.get("blast_radius_score"),
            }
        )
