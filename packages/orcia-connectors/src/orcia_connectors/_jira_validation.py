"""Validation, staging, execution & webhook builders for Multi-Project Jira actions."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Literal

from orcia_connectors._jira_models import (
    DEFAULT_PROJECT_TRANSITIONS,
    JiraActionType,
    JiraTransitionSpec,
    JiraWebhookReplayNotification,
    StagedJiraActionItem,
)
from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError
from orcia_kernel.events import StepCompleted
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import ConnectorInvokeResult, get_registered_connector


def get_legal_transitions(project_key: str, issue_key: str) -> list[JiraTransitionSpec]:
    """Return legal Jira transitions (`GET /rest/api/3/issue/{key}/transitions`)."""
    if not issue_key.strip().upper().startswith(f"{project_key.upper()}-"):
        raise ValidationDomainError(
            detail_override=f"Issue {issue_key!r} does not belong to Jira project {project_key!r}."
        )
    return list(
        DEFAULT_PROJECT_TRANSITIONS.get(project_key, DEFAULT_PROJECT_TRANSITIONS["PAYBUILD"])
    )


def validate_and_build_staged_item(
    *,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    project_alias: str,
    project_key: str,
    action_type: JiraActionType,
    summary: str,
    issue_key: str | None,
    target_transition: str | None,
    fields_payload: dict[str, Any] | None,
) -> StagedJiraActionItem:
    """Pre-validate Jira transitions and mandatory screen fields before staging."""
    fields = dict(fields_payload or {})
    clean_issue = issue_key.strip().upper() if issue_key else None

    if action_type in ("update_issue", "add_comment", "transition_issue") and not clean_issue:
        raise ValidationDomainError(
            detail_override=f"issue_key is required for Jira action {action_type!r}."
        )

    if action_type == "transition_issue":
        assert clean_issue is not None
        if not target_transition or not target_transition.strip():
            raise ValidationDomainError(
                detail_override="target_transition is required for transition_issue."
            )
        legal_transitions = get_legal_transitions(project_key, clean_issue)
        target_norm = target_transition.strip().upper()
        matched = next(
            (
                t
                for t in legal_transitions
                if t.to_status.upper() == target_norm
                or t.name.upper() == target_norm
                or t.transition_id == target_transition.strip()
            ),
            None,
        )
        if matched is None:
            allowed_names = ", ".join(t.to_status for t in legal_transitions)
            raise ValidationDomainError(
                detail_override=(
                    f"ERR_JIRA_TRANSITION_ILLEGAL: Transition {target_transition!r} is not "
                    f"legal for {clean_issue} (allowed: {allowed_names})."
                )
            )
        missing_fields = [
            req_f for req_f in matched.required_fields if not str(fields.get(req_f, "")).strip()
        ]
        if missing_fields:
            raise ValidationDomainError(
                detail_override=(
                    f"ERR_JIRA_TRANSITION_FIELDS_MISSING: Missing mandatory screen fields "
                    f"{missing_fields} for transition {matched.to_status!r} on {clean_issue}."
                )
            )

    staged_id = new_uuid7_str()
    idem_key = (
        f"jira:{workspace_id}:{run_id}:{step_execution_id}:{action_type}:"
        f"{clean_issue or project_key}:{target_transition or summary[:24]}"
    )
    return StagedJiraActionItem(
        staged_action_id=staged_id,
        workspace_id=workspace_id,
        run_id=run_id,
        step_execution_id=step_execution_id,
        project_alias=project_alias,
        project_key=project_key,
        action_type=action_type,
        issue_key=clean_issue,
        summary=summary.strip(),
        target_transition=target_transition.strip().upper() if target_transition else None,
        fields_payload=fields,
        status="STAGED",
        idempotency_key=idem_key,
    )


def invoke_jira_gate_commit(
    staged: StagedJiraActionItem,
    *,
    gate_status: Literal["PASS", "FAIL", "WAITING_HUMAN"],
    run_lock_sha256: str,
) -> StagedJiraActionItem:
    """Execute staged Jira action via `ConnectorPort.invoke` when `gate_status == 'PASS'`."""
    if gate_status != "PASS":
        raise ValidationDomainError(
            detail_override=(
                f"Cannot execute staged Jira action while gate_status={gate_status!r} "
                "(requires 'PASS')."
            )
        )
    connector = get_registered_connector("jira")
    if connector is None:
        raise ResourceNotFoundError(detail_override="Connector 'jira' is not registered.")

    run_lock_uri = f"orcia://runs/{staged.run_id}/run-lock.json"
    payload = {
        "project_key": staged.project_key,
        "issue_key": staged.issue_key or f"{staged.project_key}-NEW",
        "action_type": staged.action_type,
        "summary": staged.summary,
        "target_transition": staged.target_transition,
        "fields": staged.fields_payload,
        "provenance": {
            "run_id": staged.run_id,
            "step_execution_id": staged.step_execution_id,
            "run_lock_uri": run_lock_uri,
            "run_lock_sha256": run_lock_sha256,
        },
    }
    invoke_res: ConnectorInvokeResult = connector.invoke(
        staged.action_type, payload, staged.idempotency_key
    )
    return replace(
        staged,
        status="EXECUTED",
        provenance_run_lock_uri=run_lock_uri,
        provenance_run_lock_sha256=run_lock_sha256,
        executed_issue_key=staged.issue_key or f"{staged.project_key}-401",
        replayed_from_cache=invoke_res.replayed_from_idempotency_cache,
    )


def build_jira_webhook_notification(
    *,
    webhook_event: str,
    issue_key: str,
    new_status: str,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
) -> tuple[JiraWebhookReplayNotification, StepCompleted | None]:
    """Validate `jira:issue_updated` webhook and construct notification + Outbox event."""
    started = time.perf_counter()
    if webhook_event.strip() != "jira:issue_updated":
        raise ValidationDomainError(
            detail_override=f"Unsupported Jira webhook event: {webhook_event!r}."
        )
    clean_issue = issue_key.strip().upper()
    if "-" not in clean_issue:
        raise ValidationDomainError(detail_override=f"Invalid Jira issue key: {issue_key!r}.")
    project_key = clean_issue.split("-", 1)[0]
    status_norm = new_status.strip().upper()
    replay_triggered = status_norm == "DONE"
    evt: StepCompleted | None = None
    if replay_triggered:
        evt = StepCompleted.create(
            step_execution_id=step_execution_id,
            run_id=run_id,
            workspace_id=workspace_id,
            step_key=step_execution_id,
            step_status="COMMITTED",
            cost_usd=0.0,
        )
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    notif = JiraWebhookReplayNotification(
        webhook_event="jira:issue_updated",
        issue_key=clean_issue,
        project_key=project_key,
        new_status=status_norm,
        workspace_id=workspace_id,
        run_id=run_id,
        step_execution_id=step_execution_id,
        replay_triggered=replay_triggered,
        outbox_event_id=evt.event_id if evt is not None else None,
        sse_channel=f"channel:workspace:{workspace_id}",
        processing_ms=elapsed_ms,
        details={"target_action": "REPLAY_STEP" if replay_triggered else "NO_OP"},
    )
    return notif, evt
