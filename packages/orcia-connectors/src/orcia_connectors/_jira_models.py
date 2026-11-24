"""Domain models, constants & access-request adapter for Multi-Project Jira actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import quote

from orcia_connectors._connectors_locales import JIRA_ACCESS_REQUEST_LOCALES
from orcia_core.kernel.enums import DEFAULT_LOCALE
from orcia_kernel.ports import AccessRequestChannelPort, register_access_request_channel

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
        copy = JIRA_ACCESS_REQUEST_LOCALES[DEFAULT_LOCALE]
        summary_raw = copy["summary"].format(required_role=required_role, target_uri=target_uri)
        desc_raw = copy["description"].format(
            execution_identity=execution_identity,
            step_key=step_key,
            requester_email=requester_email,
            approver_team=approver_team,
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
    """Staged Jira operation persisted in `jira_staged_actions` (`AD-5`)."""

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
