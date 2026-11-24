"""HITL Signal Transition Handler for Bounded Workflows v2 (`TASK-05` & `Story 16.3`)."""

from __future__ import annotations

from orcia_connectors._bounded_workflow_records import (
    append_sub_step_record as append_sub_step_record,
)
from orcia_connectors._connectors_locales import BOUNDED_WORKFLOW_LOCALES
from orcia_connectors.bounded_workflow_models import (
    BoundedWorkflowRunState,
    HitlSignalPayload,
    SubStepExecutionRecord,
    build_cyclic_idempotency_key,
    finalize_gates_and_anchor,
    generate_sub_step_markdown,
)
from orcia_connectors.protocol import (
    SignedApprovalToken,
    verify_signed_approval_token,
)
from orcia_core.kernel.enums import DEFAULT_LOCALE
from orcia_core.storage.claim_check import (
    ClaimCheckStorageService,
    get_claim_check_storage,
)
from orcia_core.workflows.schemas_v2 import (
    DeterministicSubStepSpec,
    ProcessOrchestrationType,
    WorkflowDefinitionV2,
)


def apply_hitl_signal_to_run(
    workflow: WorkflowDefinitionV2,
    state: BoundedWorkflowRunState,
    signal: HitlSignalPayload,
    *,
    storage: ClaimCheckStorageService | None = None,
) -> BoundedWorkflowRunState:
    """Apply a human signal (`APPROVE`, `AMEND_DIFF`, `REJECT_RETRY_SUBSTEP`, `REJECT_AND_LOOP`)."""
    claim_storage = storage or get_claim_check_storage()
    enabled_sub_steps = [s for s in workflow.sub_steps if s.enabled]

    if state.status == "WAITING_EXTERNAL_GATE":
        ext_md = signal.amended_markdown or generate_sub_step_markdown(
            workflow,
            enabled_sub_steps[-1]
            if enabled_sub_steps
            else DeterministicSubStepSpec(
                id="ext-gate",
                name="Sas Externe",
                short_label="Sas",
                trigger_condition_label="Webhook",
                role_description="Gatekeeper",
                instruction_prompt_or_ref="gate",
                output_description="PR",
                checkpoint_label="Revue",
            ),
            state.inputs,
            state.iteration,
            signal.correction_remarks,
        )
        pointer = claim_storage.store_artifact(
            run_id=state.run_id,
            step_id="external-pr-gatekeeper",
            iteration=state.iteration,
            content=ext_md,
        )
        state.final_artifact_pointer = pointer
        state.audit_trail.append(
            {
                "event": "EXTERNAL_EVENT_RECEIVED",
                "actor_id": signal.actor_id,
                "s3_uri": pointer.s3_uri,
                "sha256": pointer.sha256,
            }
        )
        return finalize_gates_and_anchor(workflow, state, claim_storage, auto_approve=False)

    if state.status == "WAITING_SUBSTEP_HITL" and state.sub_step_records:
        current_rec = state.sub_step_records[-1]
        current_sub = enabled_sub_steps[state.current_sub_step_index]

        if signal.action == "AMEND_DIFF" and signal.amended_markdown:
            amended_ptr = claim_storage.amend_diff_in_s3(
                run_id=state.run_id,
                step_id=current_rec.sub_step_id,
                iteration=state.iteration,
                amended_markdown=signal.amended_markdown,
            )
            current_rec.artifact_pointer = amended_ptr
            state.final_artifact_pointer = amended_ptr
            state.audit_trail.append(
                {
                    "event": "SUBSTEP_DIFF_AMENDED_IN_S3",
                    "sub_step_id": current_rec.sub_step_id,
                    "actor_id": signal.actor_id,
                    "s3_uri": amended_ptr.s3_uri,
                    "sha256": amended_ptr.sha256,
                }
            )

        if signal.action == "REJECT_RETRY_SUBSTEP":
            next_iter = state.iteration + 1
            state.iteration = next_iter
            idem_key = build_cyclic_idempotency_key(state.run_id, current_sub.id, next_iter)
            retried_md = generate_sub_step_markdown(
                workflow, current_sub, state.inputs, next_iter, signal.correction_remarks
            )
            ptr = claim_storage.store_artifact(
                run_id=state.run_id,
                step_id=current_sub.id,
                iteration=next_iter,
                content=retried_md,
            )
            state.sub_step_records.append(
                SubStepExecutionRecord(
                    sub_step_id=current_sub.id,
                    sub_step_name=current_sub.name,
                    iteration=next_iter,
                    idempotency_key=idem_key,
                    status="WAITING_CHECKPOINT",
                    artifact_pointer=ptr,
                    correction_remarks_applied=signal.correction_remarks,
                )
            )
            state.final_artifact_pointer = ptr
            state.audit_trail.append(
                {
                    "event": "SUBSTEP_RETRIED",
                    "sub_step_id": current_sub.id,
                    "idempotency_key": idem_key,
                    "remarks": signal.correction_remarks,
                }
            )
            return state

        if current_sub.write_preview_required and current_rec.write_preview_card is not None:
            token = signal.signed_approval_token or SignedApprovalToken.issue(
                preview_card=current_rec.write_preview_card,
                approver_user_id=signal.actor_id,
            )
            verify_signed_approval_token(
                token,
                action=current_rec.write_preview_card.action_summary,
                payload=current_rec.write_preview_card.diff_or_payload_preview,
            )

        current_rec.status = "COMPLETED"
        current_rec.human_actor_id = signal.actor_id

        next_idx = state.current_sub_step_index + 1
        if next_idx < len(enabled_sub_steps):
            state.current_sub_step_index = next_idx
            next_sub = enabled_sub_steps[next_idx]
            md_content = generate_sub_step_markdown(
                workflow, next_sub, state.inputs, state.iteration, signal.correction_remarks
            )
            append_sub_step_record(
                workflow=workflow,
                state=state,
                sub_step=next_sub,
                claim_storage=claim_storage,
                md_content=md_content,
                reflexive_execution_id=None,
                correction_remarks=signal.correction_remarks,
                auto_approve_checkpoints=False,
            )
            return state

        return finalize_gates_and_anchor(workflow, state, claim_storage, auto_approve=False)

    if signal.action == "AMEND_DIFF" and signal.amended_markdown:
        amended_ptr = claim_storage.amend_diff_in_s3(
            run_id=state.run_id,
            step_id="final-anchor",
            iteration=state.iteration,
            amended_markdown=signal.amended_markdown,
        )
        state.final_artifact_pointer = amended_ptr
        state.status = "COMPLETED_APPROVED"
        state.audit_trail.append(
            {
                "event": "ANCHOR_AMENDED_AND_APPROVED",
                "actor_id": signal.actor_id,
                "s3_uri": amended_ptr.s3_uri,
                "sha256": amended_ptr.sha256,
            }
        )
        return state

    if signal.action == "APPROVE":
        state.status = "COMPLETED_APPROVED"
        state.audit_trail.append(
            {"event": "ANCHOR_APPROVED", "actor_id": signal.actor_id, "iteration": state.iteration}
        )
        return state

    if signal.action == "SUSPEND_SLA":
        state.status = "SLA_SUSPENDED"
        state.audit_trail.append(
            {
                "event": "SLA_SUSPENDED",
                "actor_id": signal.actor_id,
                "reason": signal.correction_remarks,
            }
        )
        return state

    if signal.action == "REJECT_AND_LOOP":
        copy = BOUNDED_WORKFLOW_LOCALES[DEFAULT_LOCALE]
        next_iter = state.iteration + 1
        state.iteration = next_iter
        state.reentry_mode = "corrections"
        state.status = "RETURN_LOOP_TRIGGERED"
        state.return_loop_target_step_num = signal.target_step_num or "02"
        state.return_loop_remarks = signal.correction_remarks or copy["default_remarks"]
        target_sub_id = signal.target_sub_step_id or (
            enabled_sub_steps[0].id
            if enabled_sub_steps
            and state.orchestration_type == ProcessOrchestrationType.DETERMINISTIC_DBOS
            else "goal-reentry"
        )
        idem_key = build_cyclic_idempotency_key(state.run_id, target_sub_id, next_iter)
        target_sub = next(
            (s for s in enabled_sub_steps if s.id == target_sub_id),
            enabled_sub_steps[0] if enabled_sub_steps else None,
        )
        if (
            target_sub is not None
            and state.orchestration_type == ProcessOrchestrationType.DETERMINISTIC_DBOS
        ):
            loop_md = generate_sub_step_markdown(
                workflow, target_sub, state.inputs, next_iter, state.return_loop_remarks
            )
            append_sub_step_record(
                workflow=workflow,
                state=state,
                sub_step=target_sub,
                claim_storage=claim_storage,
                md_content=loop_md,
                reflexive_execution_id=None,
                correction_remarks=state.return_loop_remarks,
                auto_approve_checkpoints=False,
            )
        else:
            goal_loop_md = copy["goal_reentry_body"].format(
                title=workflow.title,
                iteration=next_iter,
                remarks=state.return_loop_remarks,
            )
            state.final_artifact_pointer = claim_storage.store_artifact(
                run_id=state.run_id,
                step_id="goal-reentry",
                iteration=next_iter,
                content=goal_loop_md,
            )
        state.audit_trail.append(
            {
                "event": "RETURN_LOOP_REENTRY",
                "actor_id": signal.actor_id,
                "target_step_num": state.return_loop_target_step_num,
                "target_sub_step_id": target_sub_id,
                "idempotency_key": idem_key,
                "iteration": next_iter,
                "reentry_mode": "corrections",
            }
        )
        return state

    return state
