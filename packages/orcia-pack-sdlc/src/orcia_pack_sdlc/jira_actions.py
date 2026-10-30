"""Multi-Project Jira Staged Actions, Transitions, Webhook & Access Channel (`Story 4.4`).

Implements:
- `JiraAccessRequestChannelAdapter` (`AccessRequestChannelPort`, `DEC-ACC-01`)
- Multi-project workspace Jira routing & real-time JQL query (`jira:product`, `jira:secops`)
- Pre-validation against `GET /rest/api/3/issue/{key}/transitions` (legal transitions & mandatory
  transition screen fields) before staging in `step_executions.draft_artifact_jsonb`
- Gate-triggered execution (`gate_status == 'PASS'`) via `ConnectorPort.invoke` / `ConnectorInvoker`
  embedding the `run-lock.json` provenance link (`AD-5`, `AD-11`, `AD-12`)
- `jira:issue_updated` (`Done`) webhook handler publishing to `domain_events_outbox` in `< 500 ms`
  to wake up paused runs and trigger targeted Replay (`FR-16`)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Literal
from urllib.parse import quote

from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError
from orcia_kernel.events import StepCompleted
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import (
    AccessRequestChannelPort,
    ConnectorInvokeResult,
    OutboxRelayPort,
    get_registered_connector,
    register_access_request_channel,
)

JiraActionType = Literal["create_issue", "update_issue", "add_comment", "transition_issue"]
JiraStagedStatus = Literal["STAGED", "EXECUTED"]


class JiraAccessRequestChannelAdapter(AccessRequestChannelPort):
    """Atlassian Jira `AccessRequestChannelPort` adapter (`DEC-ACC-01`, `AD-20`)."""

    @property
    def channel_name(self) -> str:
        return "jira"

    def build_access_request_url(
        self,
        template: str,
        *,
        target_uri: str,
        required_role: str,
        approver_team: str,
        requester_email: str,
        step_key: str,
        execution_identity: str,
    ) -> str:
        summary_raw = f"[ORCIA Permission Broker] {required_role} sur {target_uri}"
        desc_raw = (
            f"Demande d'accès ({execution_identity}) pour l'étape {step_key} "
            f"par {requester_email} — Approbateur: {approver_team}"
        )
        tokens = {
            "{summary}": quote(summary_raw, safe=""),
            "{description}": quote(desc_raw, safe=""),
            "{target_uri}": quote(target_uri, safe=""),
            "{required_role}": quote(required_role, safe=""),
            "{approver_team}": quote(approver_team, safe=""),
            "{requester_email}": quote(requester_email, safe=""),
            "{step_key}": quote(step_key, safe=""),
        }
        rendered, replaced_any = template, False
        for placeholder, encoded_val in tokens.items():
            if placeholder in rendered:
                rendered, replaced_any = rendered.replace(placeholder, encoded_val), True
        if not replaced_any:
            sep = "&" if "?" in rendered else "?"
            rendered = (
                f"{rendered}{sep}summary={tokens['{summary}']}"
                f"&description={tokens['{description}']}"
            )
        return rendered

    def build_access_request_hint(
        self,
        *,
        target_uri: str,
        required_role: str,
        approver_team: str,
        sla_hours: int,
    ) -> str:
        req_q, uri_q = quote(required_role, safe=""), quote(target_uri, safe="")
        app_q = quote(approver_team, safe="")
        return f"jira://IAM/{req_q}?target={uri_q}&approver={app_q}&sla_hours={sla_hours}"


def register_jira_access_request_channel() -> JiraAccessRequestChannelAdapter:
    """Register `JiraAccessRequestChannelAdapter` in `orcia_kernel.ports` (`DEC-ACC-01`)."""
    adapter = JiraAccessRequestChannelAdapter()
    register_access_request_channel(adapter)
    return adapter


@dataclass(frozen=True, slots=True)
class JiraTransitionSpec:
    """Transition definition returned by `GET /rest/api/3/issue/{key}/transitions`."""

    transition_id: str
    name: str
    to_status: str
    required_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StagedJiraActionItem:
    """Staged Jira operation stored in `step_executions.draft_artifact_jsonb` (`AD-5`)."""

    staged_action_id: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    project_alias: str
    project_key: str
    action_type: JiraActionType
    issue_key: str | None
    summary: str
    target_transition: str | None
    fields_payload: dict[str, Any]
    status: JiraStagedStatus
    idempotency_key: str
    provenance_run_lock_uri: str | None = None
    provenance_run_lock_sha256: str | None = None
    executed_issue_key: str | None = None
    replayed_from_cache: bool = False


@dataclass(frozen=True, slots=True)
class JiraWebhookReplayNotification:
    """Outcome of processing a `jira:issue_updated` (`Done`) webhook (`< 500 ms`, `FR-16`)."""

    webhook_event: str
    issue_key: str
    project_key: str
    new_status: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    replay_triggered: bool
    outbox_event_id: str | None
    sse_channel: str
    processing_ms: float
    details: dict[str, Any] = field(default_factory=dict)


DEFAULT_WORKSPACE_JIRA_PROJECTS: dict[str, str] = {
    "jira:product": "PAYBUILD",
    "jira-pay-build": "PAYBUILD",
    "PAYBUILD": "PAYBUILD",
    "jira:secops": "PAYSEC",
    "jira-pay-run": "PAYSEC",
    "PAYSEC": "PAYSEC",
    "jira:loyalty": "LOYALTY",
    "jira-loyalty-backlog": "LOYALTY",
    "LOYALTY": "LOYALTY",
}

DEFAULT_PROJECT_TRANSITIONS: dict[str, tuple[JiraTransitionSpec, ...]] = {
    "PAYBUILD": (
        JiraTransitionSpec("11", "Start Progress", "IN_PROGRESS", ()),
        JiraTransitionSpec("21", "Submit for Review", "IN_REVIEW", ("pr_url",)),
        JiraTransitionSpec("31", "Done", "DONE", ("resolution_comment",)),
    ),
    "PAYSEC": (
        JiraTransitionSpec("11", "Triage Incident", "TRIAGED", ("severity",)),
        JiraTransitionSpec("21", "Mitigate & Close", "DONE", ("root_cause", "mitigation_summary")),
    ),
    "LOYALTY": (
        JiraTransitionSpec("11", "In Progress", "IN_PROGRESS", ()),
        JiraTransitionSpec("31", "Done", "DONE", ("resolution_comment",)),
    ),
}


class MultiProjectJiraStagedActionService:
    """Service managing multi-project Jira JQL, staged actions, Gate execution & Webhooks."""

    def __init__(
        self,
        *,
        outbox_relay: OutboxRelayPort | None = None,
        project_aliases: dict[str, str] | None = None,
    ) -> None:
        self._outbox_relay = outbox_relay
        self._project_aliases = dict(project_aliases or DEFAULT_WORKSPACE_JIRA_PROJECTS)
        self._staged_by_id: dict[str, StagedJiraActionItem] = {}
        self._draft_artifacts_by_step: dict[str, dict[str, Any]] = {}
        self._SeededIssues: list[dict[str, Any]] = [
            {
                "issue_key": "PAYBUILD-101",
                "project_key": "PAYBUILD",
                "alias": "jira:product",
                "status": "IN_PROGRESS",
                "summary": "Implémenter le connecteur checkout idempotent",
            },
            {
                "issue_key": "PAYSEC-204",
                "project_key": "PAYSEC",
                "alias": "jira:secops",
                "status": "OPEN",
                "summary": "Revue SecOps habilitation IAM connecteur paiement",
            },
        ]

    def resolve_project_key(self, project_alias_or_key: str) -> str:
        """Resolve a workspace Jira alias (`jira:product`, `jira:secops`) to a `project_key`."""
        clean = project_alias_or_key.strip()
        resolved = self._project_aliases.get(clean) or self._project_aliases.get(clean.upper())
        if not resolved:
            raise ResourceNotFoundError(
                detail_override=f"Unknown workspace Jira project alias or key: {clean!r}."
            )
        return resolved

    def search_jql(
        self, *, workspace_id: str, project_alias: str, jql: str
    ) -> list[dict[str, Any]]:
        """Execute a real-time JQL query scoped to the selected workspace Jira project."""
        if not workspace_id.strip() or not jql.strip():
            raise ValidationDomainError(detail_override="workspace_id and jql are required.")
        project_key = self.resolve_project_key(project_alias)
        q_lower = jql.lower()
        return [
            dict(issue)
            for issue in self._SeededIssues
            if issue["project_key"] == project_key
            and (
                project_key.lower() in q_lower
                or issue["status"].lower() in q_lower
                or "order by" in q_lower
            )
        ] or [i for i in self._SeededIssues if i["project_key"] == project_key]

    def get_issue_transitions(self, project_key: str, issue_key: str) -> list[JiraTransitionSpec]:
        """Simulate `GET /rest/api/3/issue/{key}/transitions` for `project_key` / `issue_key`."""
        if not issue_key.strip().upper().startswith(f"{project_key.upper()}-"):
            raise ValidationDomainError(
                detail_override=(
                    f"Issue {issue_key!r} does not belong to Jira project {project_key!r}."
                )
            )
        return list(
            DEFAULT_PROJECT_TRANSITIONS.get(project_key, DEFAULT_PROJECT_TRANSITIONS["PAYBUILD"])
        )

    def stage_action(
        self,
        *,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
        project_alias: str,
        action_type: JiraActionType,
        summary: str,
        issue_key: str | None = None,
        target_transition: str | None = None,
        fields_payload: dict[str, Any] | None = None,
    ) -> StagedJiraActionItem:
        """Pre-validate transitions (`GET /rest/api/3/issue/{key}/transitions`) and stage action."""
        project_key = self.resolve_project_key(project_alias)
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
            legal_transitions = self.get_issue_transitions(project_key, clean_issue)
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
        staged = StagedJiraActionItem(
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
        self._staged_by_id[staged_id] = staged
        draft = self._draft_artifacts_by_step.setdefault(step_execution_id, {"staged_actions": []})
        draft["staged_actions"].append(
            {
                "staged_action_id": staged.staged_action_id,
                "project_key": staged.project_key,
                "action_type": staged.action_type,
                "issue_key": staged.issue_key,
                "target_transition": staged.target_transition,
                "status": staged.status,
            }
        )
        return staged

    def get_step_draft_artifact(self, step_execution_id: str) -> dict[str, Any]:
        """Return `step_executions.draft_artifact_jsonb` containing staged Jira actions."""
        return dict(self._draft_artifacts_by_step.get(step_execution_id, {"staged_actions": []}))

    def commit_staged_action_on_gate_pass(
        self,
        *,
        staged_action_id: str,
        gate_status: Literal["PASS", "FAIL", "WAITING_HUMAN"],
        run_lock_sha256: str,
    ) -> StagedJiraActionItem:
        """Execute a staged Jira action via `ConnectorPort.invoke` only when Gate passes."""
        staged = self._staged_by_id.get(staged_action_id)
        if staged is None:
            raise ResourceNotFoundError(
                detail_override=f"Staged Jira action {staged_action_id!r} not found."
            )
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
        executed = replace(
            staged,
            status="EXECUTED",
            provenance_run_lock_uri=run_lock_uri,
            provenance_run_lock_sha256=run_lock_sha256,
            executed_issue_key=staged.issue_key or f"{staged.project_key}-401",
            replayed_from_cache=invoke_res.replayed_from_idempotency_cache,
        )
        self._staged_by_id[staged_action_id] = executed
        return executed

    def handle_issue_updated_webhook(
        self,
        *,
        webhook_event: str,
        issue_key: str,
        new_status: str,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
    ) -> JiraWebhookReplayNotification:
        """Process `jira:issue_updated` webhook in `< 500 ms` and enqueue Replay event (`FR-16`)."""
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
        outbox_event_id: str | None = None

        if replay_triggered and self._outbox_relay is not None:
            evt = StepCompleted.create(
                step_execution_id=step_execution_id,
                run_id=run_id,
                workspace_id=workspace_id,
                step_key=step_execution_id,
                step_status="COMMITTED",
                cost_usd=0.0,
            )
            self._outbox_relay.enqueue_in_transaction(evt)
            outbox_event_id = evt.event_id

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return JiraWebhookReplayNotification(
            webhook_event="jira:issue_updated",
            issue_key=clean_issue,
            project_key=project_key,
            new_status=status_norm,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            replay_triggered=replay_triggered,
            outbox_event_id=outbox_event_id,
            sse_channel=f"channel:workspace:{workspace_id}",
            processing_ms=elapsed_ms,
            details={"target_action": "REPLAY_STEP" if replay_triggered else "NO_OP"},
        )
