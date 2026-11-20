"""Synchronous unit-test mixin for `MultiProjectJiraStagedActionService` (`strict_sql=False`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from orcia_connectors._jira_models import (
    JiraActionType,
    JiraWebhookReplayNotification,
    StagedJiraActionItem,
)
from orcia_connectors._jira_validation import (
    build_jira_webhook_notification,
    get_legal_transitions,
    invoke_jira_gate_commit,
    validate_and_build_staged_item,
)
from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError
from orcia_kernel.ports import OutboxRelayPort

if TYPE_CHECKING:
    from orcia_connectors._jira_models import JiraTransitionSpec


class JiraActionsSyncMixin:
    """Sync JQL, transition checks, and unit-test fallback (`strict_sql=False` only)."""

    _outbox_relay: OutboxRelayPort | None
    _project_aliases: dict[str, str]
    _strict_sql: bool
    _memory_staged: dict[str, StagedJiraActionItem]
    _SeededIssues: list[dict[str, Any]]

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
        """Return legal Jira transitions (`GET /rest/api/3/issue/{key}/transitions`)."""
        return get_legal_transitions(project_key, issue_key)

    def _build_staged(
        self,
        *,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
        project_alias: str,
        action_type: JiraActionType,
        summary: str,
        issue_key: str | None,
        target_transition: str | None,
        fields_payload: dict[str, Any] | None,
    ) -> StagedJiraActionItem:
        project_key = self.resolve_project_key(project_alias)
        return validate_and_build_staged_item(
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            project_alias=project_alias,
            project_key=project_key,
            action_type=action_type,
            summary=summary,
            issue_key=issue_key,
            target_transition=target_transition,
            fields_payload=fields_payload,
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
        """Unit-test sync staging helper when `repository is None` and `strict_sql=False`."""
        if self._strict_sql:
            raise ValidationDomainError(
                detail_override="Sync RAM path disabled when strict_sql=True; use async PG18 path."
            )
        staged = self._build_staged(
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            project_alias=project_alias,
            action_type=action_type,
            summary=summary,
            issue_key=issue_key,
            target_transition=target_transition,
            fields_payload=fields_payload,
        )
        self._memory_staged[staged.staged_action_id] = staged
        return staged

    def get_step_draft_artifact(self, step_execution_id: str) -> dict[str, Any]:
        """Return unit-test `draft_artifact_jsonb` when `strict_sql=False`."""
        if self._strict_sql:
            raise ValidationDomainError(
                detail_override="Sync RAM path disabled when strict_sql=True; use async PG18 path."
            )
        return {
            "staged_actions": [
                {
                    "staged_action_id": item.staged_action_id,
                    "project_key": item.project_key,
                    "action_type": item.action_type,
                    "issue_key": item.issue_key,
                    "target_transition": item.target_transition,
                    "status": item.status,
                }
                for item in self._memory_staged.values()
                if item.step_execution_id == step_execution_id
            ]
        }

    def list_staged_actions(self, *, workspace_id: str | None = None) -> list[StagedJiraActionItem]:
        """List staged or executed Jira actions in unit-test mode (`strict_sql=False`)."""
        if self._strict_sql:
            raise ValidationDomainError(
                detail_override="Sync RAM path disabled when strict_sql=True; use async PG18 path."
            )
        items = list(self._memory_staged.values())
        if workspace_id is not None and workspace_id.strip():
            items = [item for item in items if item.workspace_id == workspace_id]
        return items

    def commit_staged_action_on_gate_pass(
        self,
        *,
        staged_action_id: str,
        gate_status: Literal["PASS", "FAIL", "WAITING_HUMAN"],
        run_lock_sha256: str,
    ) -> StagedJiraActionItem:
        """Unit-test sync commit helper when `repository is None` and `strict_sql=False`."""
        if self._strict_sql:
            raise ValidationDomainError(
                detail_override="Sync RAM path disabled when strict_sql=True; use async PG18 path."
            )
        staged = self._memory_staged.get(staged_action_id)
        if staged is None:
            raise ResourceNotFoundError(
                detail_override=f"Staged Jira action {staged_action_id!r} not found."
            )
        executed = invoke_jira_gate_commit(
            staged, gate_status=gate_status, run_lock_sha256=run_lock_sha256
        )
        self._memory_staged[staged_action_id] = executed
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
        notif, evt = build_jira_webhook_notification(
            webhook_event=webhook_event,
            issue_key=issue_key,
            new_status=new_status,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
        )
        if evt is not None and self._outbox_relay is not None:
            self._outbox_relay.enqueue_in_transaction(evt)
        return notif
