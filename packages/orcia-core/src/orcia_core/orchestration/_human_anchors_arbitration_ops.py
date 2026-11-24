"""Arbitration Request & Resolution Helpers extracted from `human_anchors_and_arbitration.py`."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from orcia_core.blackboard.models import StepExecutionEntity, StepMemlogEntry
from orcia_core.orchestration._human_anchors_models import (
    ArbitrationOptionItem,
    HumanArbitrationRequestEntity,
)
from orcia_core.orchestration._orchestration_ops_locales import (
    HUMAN_ANCHOR_LOCALES,
    get_ops_copy,
)
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration.models import TieBreakPolicy
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import HumanArbitrationRequested
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.human_anchors_and_arbitration import (
        HumanAnchorAndArbitrationService,
    )


def execute_request_human_arbitration(
    svc: HumanAnchorAndArbitrationService,
    user: UserIdentity,
    *,
    run_id: str,
    step_key: str,
    question_title: str,
    context_summary: str,
    options_matrix: tuple[ArbitrationOptionItem, ...],
    tie_break_policy: TieBreakPolicy | None,
    trace_id: str,
    instance: str | None,
) -> tuple[HumanArbitrationRequestEntity, StepExecutionEntity]:
    """Evaluate `tie_break_policy` and persist arbitration request + Outbox event if escalated."""
    run = svc.engine._get_run(run_id, instance=instance)
    svc.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
    wf = svc.engine._get_workflow(run.workflow_uri, instance=instance)
    svc.engine.initialize_run_steps(run, wf)
    step_exec = svc.engine.blackboard.get_step_execution(run.id, step_key)

    if len(options_matrix) < 2:
        raise ValidationDomainError(
            detail_override="L'arbitrage humain exige au moins 2 options dans options_matrix.",
            instance=instance,
        )

    effective_policy: TieBreakPolicy = tie_break_policy or wf.tie_break_policy
    if (
        run.criticality == "HIGH_CRITICAL"
        and effective_policy == "DEFER_AND_CONTINUE_WITH_ASSUMPTION"
    ):
        effective_policy = "PAUSE_AND_ESCALATE"

    arb_id = new_uuid7_str()
    arb_key = f"arb-{run.id[-6:]}-{step_key}-{arb_id[-6:]}"

    if effective_policy == "ONTOLOGY_AXIOM_FIRST":
        matched = svc._resolve_by_ontology_axiom(run, options_matrix)
        if matched is not None:
            opt, axiom_key = matched
            req = HumanArbitrationRequestEntity(
                id=arb_id,
                arbitration_key=arb_key,
                workspace_id=run.workspace_id,
                run_id=run.id,
                step_execution_id=step_exec.id,
                step_key=step_key,
                tie_break_policy=effective_policy,
                status="RESOLVED_BY_AXIOM",
                question_title=question_title.strip(),
                context_summary=context_summary.strip(),
                options_matrix=options_matrix,
                selected_option_key=opt.option_key,
                resolved_by_axiom_key=axiom_key,
            )
            svc._arbitrations_by_id[arb_id] = req
            updated_step = svc.engine.blackboard.save_step_draft(
                run.id,
                step_key,
                status="EXECUTING_AGENT",
                draft_artifact={
                    **step_exec.draft_artifact,
                    "arbitration_resolution": {
                        "arbitration_id": arb_id,
                        "status": "RESOLVED_BY_AXIOM",
                        "selected_option_key": opt.option_key,
                        "resolved_by_axiom_key": axiom_key,
                    },
                },
                memlog_entries=(
                    StepMemlogEntry(
                        entry_id=new_uuid7_str(),
                        step_key=step_key,
                        marker_type="REASONING",
                        summary=get_ops_copy(HUMAN_ANCHOR_LOCALES)["axiom_summary"].format(
                            axiom_key=axiom_key, opt_key=opt.option_key
                        ),
                        details=get_ops_copy(HUMAN_ANCHOR_LOCALES)["axiom_details"].format(
                            opt_title=opt.title
                        ),
                    ),
                ),
            )
            return req, updated_step

    if effective_policy == "DEFER_AND_CONTINUE_WITH_ASSUMPTION":
        chosen = next((o for o in options_matrix if o.recommended), options_matrix[0])
        hc = get_ops_copy(HUMAN_ANCHOR_LOCALES)
        req = HumanArbitrationRequestEntity(
            id=arb_id,
            arbitration_key=arb_key,
            workspace_id=run.workspace_id,
            run_id=run.id,
            step_execution_id=step_exec.id,
            step_key=step_key,
            tie_break_policy=effective_policy,
            status="DEFERRED_WITH_ASSUMPTION",
            question_title=question_title.strip(),
            context_summary=context_summary.strip(),
            options_matrix=options_matrix,
            selected_option_key=chosen.option_key,
        )
        svc._arbitrations_by_id[arb_id] = req
        assumption_entry = StepMemlogEntry(
            entry_id=new_uuid7_str(),
            step_key=step_key,
            marker_type="ASSUMPTION",
            summary=hc["assumption_summary"].format(
                opt_key=chosen.option_key, opt_title=chosen.title, q=question_title.strip()
            ),
            details=hc["assumption_details"].format(si=chosen.si_impact, fin=chosen.finops_impact),
        )
        updated_step = svc.engine.blackboard.save_step_draft(
            run.id,
            step_key,
            status="EXECUTING_AGENT",
            draft_artifact={
                **step_exec.draft_artifact,
                "arbitration_resolution": {
                    "arbitration_id": arb_id,
                    "status": "DEFERRED_WITH_ASSUMPTION",
                    "selected_option_key": chosen.option_key,
                },
            },
            memlog_entries=(assumption_entry,),
        )
        return req, updated_step

    event = HumanArbitrationRequested.create(
        arbitration_id=arb_id,
        run_id=run.id,
        workspace_id=run.workspace_id,
        step_key=step_key,
        options_count=len(options_matrix),
        trace_id=trace_id,
    )
    svc._outbox_events.append(event)
    req = HumanArbitrationRequestEntity(
        id=arb_id,
        arbitration_key=arb_key,
        workspace_id=run.workspace_id,
        run_id=run.id,
        step_execution_id=step_exec.id,
        step_key=step_key,
        tie_break_policy=effective_policy,
        status="PENDING",
        question_title=question_title.strip(),
        context_summary=context_summary.strip(),
        options_matrix=options_matrix,
        outbox_event_id=event.event_id,
    )
    svc._arbitrations_by_id[arb_id] = req
    updated_step = svc.engine.blackboard.save_step_draft(
        run.id,
        step_key,
        status="WAITING_FOR_HUMAN_ARBITRATION",
        draft_artifact={
            **step_exec.draft_artifact,
            "pending_arbitration_id": arb_id,
            "arbitration_question_title": question_title.strip(),
            "arbitration_context_summary": context_summary.strip(),
            "arbitration_tie_break_policy": effective_policy,
            "options_matrix": [o.to_dict() for o in options_matrix],
        },
        memlog_entries=(
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="HUMAN_ARBITRATION_REQUESTED",
                summary=get_ops_copy(HUMAN_ANCHOR_LOCALES)["escalate_summary"].format(
                    q=question_title.strip()
                ),
                details=get_ops_copy(HUMAN_ANCHOR_LOCALES)["escalate_details"].format(
                    count=len(options_matrix), event_id=event.event_id
                ),
            ),
        ),
    )
    svc.engine.setup_service.set_run_status(run.id, "WAITING_FOR_HUMAN_ARBITRATION")
    return req, updated_step


def prepare_arbitration_resolution(
    svc: HumanAnchorAndArbitrationService,
    user: UserIdentity,
    *,
    run_id: str,
    step_key: str,
    arbitration_id: str,
    selected_option_key: str,
    human_justification: str | None,
    instance: str | None,
) -> tuple[HumanArbitrationRequestEntity, str]:
    """Validate and record human arbitration choice prior to resuming the workflow step."""
    run = svc.engine._get_run(run_id, instance=instance)
    svc.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
    req = svc._arbitrations_by_id.get(arbitration_id)
    if req is None or req.run_id != run.id or req.step_key != step_key:
        raise ResourceNotFoundError(
            detail_code="ERR_ARBITRATION_NOT_FOUND",
            detail_params={"arbitration_id": arbitration_id},
            instance=instance,
        )
    chosen = next((o for o in req.options_matrix if o.option_key == selected_option_key), None)
    if chosen is None:
        raise ValidationDomainError(
            detail_code="ERR_ARBITRATION_OPTION_MISSING",
            detail_params={"option_key": selected_option_key},
            instance=instance,
        )
    just_clean = human_justification.strip() if human_justification else None
    resolved_req = replace(
        req,
        status="RESOLVED_BY_HUMAN",
        selected_option_key=chosen.option_key,
        human_justification=just_clean,
        resolved_by_user_id=user.id,
    )
    svc._arbitrations_by_id[arbitration_id] = resolved_req
    step_exec = svc.engine.blackboard.get_step_execution(run.id, step_key)
    hc = get_ops_copy(HUMAN_ANCHOR_LOCALES)
    svc.engine.blackboard.save_step_draft(
        run.id,
        step_key,
        status="EXECUTING_AGENT",
        draft_artifact={
            **step_exec.draft_artifact,
            "arbitration_resolution": {
                "arbitration_id": arbitration_id,
                "status": "RESOLVED_BY_HUMAN",
                "selected_option_key": chosen.option_key,
                "selected_option_title": chosen.title,
                "human_justification": just_clean,
                "resolved_by_user_id": user.id,
            },
        },
        memlog_entries=(
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="HUMAN_ARBITRATION_RESOLVED",
                summary=hc["resolved_summary"].format(
                    opt_key=chosen.option_key, opt_title=chosen.title
                ),
                details=just_clean or hc["resolved_no_note"],
            ),
        ),
    )
    decision_summary = f"{chosen.option_key}: {just_clean}" if just_clean else chosen.option_key
    return resolved_req, decision_summary
