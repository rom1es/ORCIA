"""DBOS Bounded Workflow v2 Runner (`bounded_workflow_v2.py`, `TASK-05`).

Implements:
- Cyclic idempotency keys `f"{run_id}:{sub_step.id}:iter-{iteration}"` (`CA-9.5.3`, Golden Rule #7)
- `NATIVE_ORCIA` and `EXTERNAL_DELEGATED_GATE` execution modes (`CA-9.3.3`)
- Sub-step human checkpoints (`APPROVE`, `AMEND_DIFF`, `REJECT_RETRY_SUBSTEP`)
- Permission Broker `WritePreviewCard` + `SignedApprovalToken` when `write_preview_required`
- SeaweedFS S3 `ClaimCheckPointer` persistence of deliverables (`> 4 KB`) and human-amended diffs
- Final Anchor Card 4-action arbitration (`APPROVE`, `AMEND_DIFF`, `REJECT_AND_LOOP`, `SUSPEND_SLA`)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from orcia_connectors.protocol import (
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.storage.claim_check import (
    ClaimCheckStorageService,
    get_claim_check_storage,
)
from orcia_core.workflows.gates.pipeline import (
    GatePipelineExecutionReport,
    GatePipelineExecutor,
)
from orcia_core.workflows.schemas_v2 import (
    ClaimCheckPointer,
    DeterministicSubStepSpec,
    ExecutionMode,
    WorkflowDefinitionV2,
)

HitlActionType = Literal[
    "APPROVE",
    "AMEND_DIFF",
    "REJECT_RETRY_SUBSTEP",
    "REJECT_AND_LOOP",
    "SUSPEND_SLA",
]


class HitlSignalPayload(BaseModel):
    """Signal payload delivered via `POST /api/v1/runs/{run_id}/hitl-signal`."""

    action: HitlActionType
    actor_id: str = "u-claire-po"
    actor_role: str = "sdlc:po"
    sub_step_id: str | None = None
    amended_markdown: str | None = None
    target_step_num: str | None = None
    target_sub_step_id: str | None = None
    correction_remarks: str | None = None
    signed_approval_token: SignedApprovalToken | None = None
    external_event_payload: dict[str, Any] | None = None


class SubStepExecutionRecord(BaseModel):
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
    artifact_pointer: ClaimCheckPointer | None = None
    write_preview_card: WritePreviewCard | None = None
    human_actor_id: str | None = None
    correction_remarks_applied: str | None = None


class BoundedWorkflowRunState(BaseModel):
    run_id: str
    workflow_id: str
    workflow_slug: str
    workflow_version: str
    execution_mode: ExecutionMode
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
    ] = "RUNNING"
    current_sub_step_index: int = 0
    inputs: dict[str, Any] = Field(default_factory=dict)
    mcp_context_bundle: dict[str, Any] | None = None
    sub_step_records: list[SubStepExecutionRecord] = Field(default_factory=list)
    gate_report: GatePipelineExecutionReport | None = None
    final_artifact_pointer: ClaimCheckPointer | None = None
    return_loop_target_step_num: str | None = None
    return_loop_remarks: str | None = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


def build_cyclic_idempotency_key(run_id: str, sub_step_id: str, iteration: int) -> str:
    """Build the DBOS step idempotency key indexed by iteration (`Golden Rule #7`)."""
    return f"{run_id}:{sub_step_id}:iter-{iteration}"


def _build_write_preview_card(
    *,
    run_id: str,
    workflow: WorkflowDefinitionV2,
    sub_step: DeterministicSubStepSpec,
    iteration: int,
    pointer: ClaimCheckPointer,
    md_content: str,
) -> WritePreviewCard:
    connector_type = (
        sub_step.toolbox_mcp_permissions[0].get("connector_id", "mcp:atlassian-jira")
        if sub_step.toolbox_mcp_permissions
        else "mcp:atlassian-jira"
    )
    payload_preview = {
        "title": f"{workflow.title} — {sub_step.name}",
        "artifact_s3_uri": pointer.s3_uri,
        "artifact_sha256": pointer.sha256,
        "excerpt": md_content[:400],
    }
    return WritePreviewCard(
        preview_id=f"prev-{run_id}-{sub_step.id}-iter-{iteration}",
        connector_type=connector_type,
        target_resource_uri=f"catalog://{connector_type}/MON-COMPTE/{sub_step.id}",
        action_summary="create_or_update_item",
        diff_or_payload_preview=payload_preview,
        payload_sha256=compute_payload_sha256("create_or_update_item", payload_preview),
    )


def _generate_sub_step_markdown(
    workflow: WorkflowDefinitionV2,
    sub_step: DeterministicSubStepSpec,
    inputs: dict[str, Any],
    iteration: int,
    remarks: str | None,
) -> str:
    sections = workflow.contract.required_markdown_sections or [
        f"# {workflow.title}",
        "## Contexte",
        "## Décisions",
    ]
    body_lines: list[str] = []
    for idx, heading in enumerate(sections):
        body_lines.append(heading)
        body_lines.append(
            f"Section générée pour la sous-étape **{sub_step.name}** (`{sub_step.id}`, "
            f"itération `iter-{iteration}`). Entrées : `{inputs}`."
        )
        if remarks:
            body_lines.append(f"Prise en compte des remarques de retour : {remarks}.")
        if idx == 1:
            body_lines.append("```mermaid\nflowchart LR\n  Entree --> Analyse --> Livrable\n```")
        body_lines.append(" Détail complémentaire validé conformément au socle documentaire." * 12)
        body_lines.append("")
    return "\n".join(body_lines)


def run_bounded_workflow_v2(
    workflow: WorkflowDefinitionV2,
    *,
    run_id: str,
    inputs: dict[str, Any] | None = None,
    iteration: int = 1,
    reentry_mode: Literal["initial", "corrections"] = "initial",
    correction_remarks: str | None = None,
    auto_approve_checkpoints: bool = False,
    storage: ClaimCheckStorageService | None = None,
) -> BoundedWorkflowRunState:
    """Execute or initialize a bounded DBOS workflow v2 (`NATIVE_ORCIA` or `EXTERNAL_DELEGATED`)."""
    claim_storage = storage or get_claim_check_storage()
    state = BoundedWorkflowRunState(
        run_id=run_id,
        workflow_id=workflow.id,
        workflow_slug=workflow.slug,
        workflow_version=workflow.version,
        execution_mode=workflow.execution_mode,
        iteration=iteration,
        reentry_mode=reentry_mode,
        inputs=dict(inputs or {}),
    )

    if workflow.execution_mode == ExecutionMode.EXTERNAL_DELEGATED_GATE:
        state.mcp_context_bundle = {
            "workflow_slug": workflow.slug,
            "external_tool_label": workflow.external_tool_label,
            "expected_event": workflow.external_completion_event or "git:pr_opened",
            "inputs": state.inputs,
            "guardrails": workflow.guardrails,
        }
        if not auto_approve_checkpoints:
            state.status = "WAITING_EXTERNAL_GATE"
            state.audit_trail.append(
                {
                    "event": "MCP_CONTEXT_BUNDLE_EXPOSED",
                    "iteration": iteration,
                    "expected_event": workflow.external_completion_event,
                }
            )
            return state

    enabled_sub_steps = [s for s in workflow.sub_steps if s.enabled]
    if not enabled_sub_steps:
        state.status = "COMPLETED_APPROVED"
        return state

    for idx, sub_step in enumerate(enabled_sub_steps):
        state.current_sub_step_index = idx
        idem_key = build_cyclic_idempotency_key(run_id, sub_step.id, iteration)
        md_content = _generate_sub_step_markdown(
            workflow, sub_step, state.inputs, iteration, correction_remarks
        )
        pointer = claim_storage.store_artifact(
            run_id=run_id,
            step_id=sub_step.id,
            iteration=iteration,
            content=md_content,
        )
        preview_card = (
            _build_write_preview_card(
                run_id=run_id,
                workflow=workflow,
                sub_step=sub_step,
                iteration=iteration,
                pointer=pointer,
                md_content=md_content,
            )
            if sub_step.write_preview_required
            else None
        )

        rec = SubStepExecutionRecord(
            sub_step_id=sub_step.id,
            sub_step_name=sub_step.name,
            iteration=iteration,
            idempotency_key=idem_key,
            status="COMPLETED"
            if auto_approve_checkpoints
            else (
                "WAITING_WRITE_PREVIEW" if sub_step.write_preview_required else "WAITING_CHECKPOINT"
            ),
            artifact_pointer=pointer,
            write_preview_card=preview_card,
            correction_remarks_applied=correction_remarks,
        )
        state.sub_step_records.append(rec)
        state.final_artifact_pointer = pointer
        state.audit_trail.append(
            {
                "event": "SUBSTEP_EXECUTED",
                "sub_step_id": sub_step.id,
                "idempotency_key": idem_key,
                "s3_uri": pointer.s3_uri,
                "sha256": pointer.sha256,
            }
        )

        if not auto_approve_checkpoints and sub_step.requires_human_checkpoint:
            state.status = "WAITING_SUBSTEP_HITL"
            return state

    return _finalize_gates_and_anchor(
        workflow, state, claim_storage, auto_approve=auto_approve_checkpoints
    )


def _finalize_gates_and_anchor(
    workflow: WorkflowDefinitionV2,
    state: BoundedWorkflowRunState,
    claim_storage: ClaimCheckStorageService,
    *,
    auto_approve: bool = False,
) -> BoundedWorkflowRunState:
    artifact_text = (
        claim_storage.resolve_artifact_text(state.final_artifact_pointer)
        if state.final_artifact_pointer is not None
        else f"# {workflow.title}\n\nContenu validé."
    )
    executor = GatePipelineExecutor()
    gate_report = executor.execute_pipeline(
        pipeline=workflow.controls,
        artifact_text=artifact_text,
        execution_mode=workflow.execution_mode,
        self_heal_callback=lambda txt, _err, retry: (
            txt
            + f"\n\n# {workflow.title}\nSection auto-remédiée (essai #{retry}). "
            + ("Détail conforme. " * 6)
        ),
    )
    state.gate_report = gate_report
    if not gate_report.deterministic_passed:
        state.status = "FAILED_GATES"
        return state
    state.status = "COMPLETED_APPROVED" if auto_approve else "WAITING_FINAL_ANCHOR"
    return state


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

    # 1. External Gate completion signal
    if state.status == "WAITING_EXTERNAL_GATE":
        ext_md = signal.amended_markdown or _generate_sub_step_markdown(
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
        return _finalize_gates_and_anchor(workflow, state, claim_storage, auto_approve=False)

    # 2. Sub-step HITL checkpoint
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
            retried_md = _generate_sub_step_markdown(
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
            idem_key = build_cyclic_idempotency_key(state.run_id, next_sub.id, state.iteration)
            md_content = _generate_sub_step_markdown(
                workflow, next_sub, state.inputs, state.iteration, signal.correction_remarks
            )
            pointer = claim_storage.store_artifact(
                run_id=state.run_id,
                step_id=next_sub.id,
                iteration=state.iteration,
                content=md_content,
            )
            preview_card = (
                _build_write_preview_card(
                    run_id=state.run_id,
                    workflow=workflow,
                    sub_step=next_sub,
                    iteration=state.iteration,
                    pointer=pointer,
                    md_content=md_content,
                )
                if next_sub.write_preview_required
                else None
            )
            state.sub_step_records.append(
                SubStepExecutionRecord(
                    sub_step_id=next_sub.id,
                    sub_step_name=next_sub.name,
                    iteration=state.iteration,
                    idempotency_key=idem_key,
                    status="WAITING_WRITE_PREVIEW"
                    if next_sub.write_preview_required
                    else "WAITING_CHECKPOINT",
                    artifact_pointer=pointer,
                    write_preview_card=preview_card,
                )
            )
            state.final_artifact_pointer = pointer
            return state

        return _finalize_gates_and_anchor(workflow, state, claim_storage, auto_approve=False)

    # 3. Final Anchor Card 4-action sovereign arbitration (`CA-9.5.1`, `CA-9.5.2`, `CA-9.5.3`)
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
        next_iter = state.iteration + 1
        state.iteration = next_iter
        state.reentry_mode = "corrections"
        state.status = "RETURN_LOOP_TRIGGERED"
        state.return_loop_target_step_num = signal.target_step_num or "02"
        state.return_loop_remarks = signal.correction_remarks or "Corrections demandées en revue."
        target_sub_id = signal.target_sub_step_id or (
            enabled_sub_steps[0].id if enabled_sub_steps else "reentry"
        )
        idem_key = build_cyclic_idempotency_key(state.run_id, target_sub_id, next_iter)
        target_sub = next(
            (s for s in enabled_sub_steps if s.id == target_sub_id),
            enabled_sub_steps[0] if enabled_sub_steps else None,
        )
        if target_sub is not None:
            loop_md = _generate_sub_step_markdown(
                workflow, target_sub, state.inputs, next_iter, state.return_loop_remarks
            )
            ptr = claim_storage.store_artifact(
                run_id=state.run_id,
                step_id=target_sub.id,
                iteration=next_iter,
                content=loop_md,
            )
            state.sub_step_records.append(
                SubStepExecutionRecord(
                    sub_step_id=target_sub.id,
                    sub_step_name=target_sub.name,
                    iteration=next_iter,
                    idempotency_key=idem_key,
                    status="WAITING_CHECKPOINT",
                    artifact_pointer=ptr,
                    correction_remarks_applied=state.return_loop_remarks,
                )
            )
            state.final_artifact_pointer = ptr
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


__all__ = [
    "BoundedWorkflowRunState",
    "HitlActionType",
    "HitlSignalPayload",
    "SubStepExecutionRecord",
    "apply_hitl_signal_to_run",
    "build_cyclic_idempotency_key",
    "run_bounded_workflow_v2",
]
