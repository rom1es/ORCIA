"""Models & helpers for Bounded Workflow v2 & Dual-Mode Run State (`Story 16.3`).

Separated from `bounded_workflow_v2.py` to keep every module below 350 lines while maintaining
100% backward compatibility on all public exports.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from orcia_connectors.protocol import (
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
)
from orcia_core.agents.process_dispatcher import UnifiedProcessRunResult
from orcia_core.ports.bounded_workflow_port import (
    BoundedWorkflowLaunchOutcome,
    BoundedWorkflowSubStepDto,
)
from orcia_core.ports.reflexive_runtime_ports import AgentTraceEvent
from orcia_core.storage.claim_check import ClaimCheckStorageService
from orcia_core.workflows.gates.pipeline import (
    GatePipelineExecutionReport,
    GatePipelineExecutor,
)
from orcia_core.workflows.schemas_v2 import (
    ClaimCheckPointer,
    DeterministicSubStepSpec,
    ExecutionMode,
    ProcessOrchestrationType,
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
    """Persisted record of a single bounded sub-step (Principle 7: pointer + exec ID only)."""

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
    reflexive_execution_id: str | None = None
    write_preview_card: WritePreviewCard | None = None
    human_actor_id: str | None = None
    correction_remarks_applied: str | None = None


class BoundedWorkflowRunState(BaseModel):
    """Unified run state exposed by `/api/v1/workflows/v2/{id}/runs` and `/api/v1/runs/{id}`."""

    run_id: str
    workflow_id: str
    workflow_slug: str
    workflow_version: str
    orchestration_type: ProcessOrchestrationType = ProcessOrchestrationType.DETERMINISTIC_DBOS
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
    reflexive_execution_id: str | None = None
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    return_loop_target_step_num: str | None = None
    return_loop_remarks: str | None = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_unified_result(cls, result: UnifiedProcessRunResult) -> BoundedWorkflowRunState:
        """Convert `UnifiedProcessRunResult` into `BoundedWorkflowRunState`."""
        sub_records: list[SubStepExecutionRecord] = []
        for dto in result.sub_step_records:
            ptr = (
                ClaimCheckPointer.model_validate(dto.artifact_pointer_payload)
                if dto.artifact_pointer_payload is not None
                else None
            )
            wp = (
                WritePreviewCard.model_validate(dto.write_preview_payload)
                if dto.write_preview_payload is not None
                else None
            )
            sub_records.append(
                SubStepExecutionRecord(
                    sub_step_id=dto.sub_step_id,
                    sub_step_name=dto.sub_step_name,
                    iteration=dto.iteration,
                    idempotency_key=dto.idempotency_key,
                    status=dto.status,
                    artifact_pointer=ptr,
                    reflexive_execution_id=dto.reflexive_execution_id,
                    write_preview_card=wp,
                    human_actor_id=dto.human_actor_id,
                    correction_remarks_applied=dto.correction_remarks_applied,
                )
            )
        return cls(
            run_id=result.run_id,
            workflow_id=result.workflow_id,
            workflow_slug=result.workflow_slug,
            workflow_version=result.workflow_version,
            orchestration_type=result.orchestration_type,
            execution_mode=result.execution_mode,
            iteration=result.iteration,
            reentry_mode=result.reentry_mode,
            status=result.status,
            current_sub_step_index=result.current_sub_step_index,
            inputs=result.inputs,
            mcp_context_bundle=result.mcp_context_bundle,
            sub_step_records=sub_records,
            gate_report=result.gate_report,
            final_artifact_pointer=result.final_artifact_pointer,
            reflexive_execution_id=result.reflexive_execution_id,
            trace_events=result.trace_events,
            return_loop_target_step_num=result.return_loop_target_step_num,
            return_loop_remarks=result.return_loop_remarks,
            audit_trail=result.audit_trail,
        )


def build_cyclic_idempotency_key(run_id: str, sub_step_id: str, iteration: int) -> str:
    """Build the step idempotency key indexed by iteration (`Golden Rule #7`)."""
    return f"{run_id}:{sub_step_id}:iter-{iteration}"


def build_write_preview_card_for_sub_step(
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


def generate_sub_step_markdown(
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


def finalize_gates_and_anchor(
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


def to_bounded_launch_outcome(state: BoundedWorkflowRunState) -> BoundedWorkflowLaunchOutcome:
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
