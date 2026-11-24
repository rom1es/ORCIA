"""Multi-Project Jira Staged Actions, Transitions, Webhook & Access Channel (`24.1`)."""

from __future__ import annotations

from typing import Any, Literal

from orcia_connectors._connectors_locales import CONNECTOR_SEED_LOCALES
from orcia_connectors._internal.sql_jira_staged_actions import SqlJiraStagedActionsRepository
from orcia_connectors._jira_models import (
    DEFAULT_PROJECT_TRANSITIONS,
    DEFAULT_WORKSPACE_JIRA_PROJECTS,
    JiraAccessRequestChannelAdapter,
    JiraActionType,
    JiraStagedStatus,
    JiraTransitionSpec,
    JiraWebhookReplayNotification,
    StagedJiraActionItem,
    register_jira_access_request_channel,
)
from orcia_connectors._jira_sync_mixin import JiraActionsSyncMixin
from orcia_connectors._jira_validation import (
    build_jira_webhook_notification,
    invoke_jira_gate_commit,
)
from orcia_core.kernel.enums import DEFAULT_LOCALE
from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError
from orcia_kernel.events import ArtifactProduced, StepCompleted
from orcia_kernel.ports import OutboxRelayPort

__all__ = [
    "DEFAULT_PROJECT_TRANSITIONS",
    "DEFAULT_WORKSPACE_JIRA_PROJECTS",
    "JiraAccessRequestChannelAdapter",
    "JiraActionType",
    "JiraStagedStatus",
    "JiraTransitionSpec",
    "JiraWebhookReplayNotification",
    "MultiProjectJiraStagedActionService",
    "StagedJiraActionItem",
    "register_jira_access_request_channel",
]


class MultiProjectJiraStagedActionService(JiraActionsSyncMixin):
    """Service managing multi-project Jira JQL, staged actions in PG18, Gate commit & Webhooks."""

    def __init__(
        self,
        *,
        outbox_relay: OutboxRelayPort | None = None,
        project_aliases: dict[str, str] | None = None,
        repository: SqlJiraStagedActionsRepository | None = None,
        strict_sql: bool = False,
    ) -> None:
        self._outbox_relay = outbox_relay
        self._project_aliases = dict(project_aliases or DEFAULT_WORKSPACE_JIRA_PROJECTS)
        self._repository = repository
        self._strict_sql = strict_sql
        self._memory_staged: dict[str, StagedJiraActionItem] = {}
        seed_copy = CONNECTOR_SEED_LOCALES[DEFAULT_LOCALE]
        self._SeededIssues: list[dict[str, Any]] = [
            {
                "issue_key": "PAYBUILD-101",
                "project_key": "PAYBUILD",
                "alias": "jira:product",
                "status": "IN_PROGRESS",
                "summary": seed_copy["jira_paybuild_summary"],
            },
            {
                "issue_key": "PAYSEC-204",
                "project_key": "PAYSEC",
                "alias": "jira:secops",
                "status": "OPEN",
                "summary": seed_copy["jira_paysec_summary"],
            },
        ]

    async def stage_action_async(
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
        staged_by: str | None = None,
    ) -> StagedJiraActionItem:
        """Pre-validate Jira transitions and persist staged action + Outbox event in PG18."""
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
        if self._repository is None:
            if self._strict_sql:
                raise ValidationDomainError(
                    detail_override="Jira PG18 repository is required when strict_sql=True."
                )
            self._memory_staged[staged.staged_action_id] = staged
            return staged

        outbox_evt = ArtifactProduced.create(
            snapshot_id=staged.staged_action_id,
            run_id=staged.run_id,
            workspace_id=staged.workspace_id,
            artifact_cas_key=f"jira-staged:{staged.idempotency_key}",
            artifact_sha256="0" * 64,
        )
        return await self._repository.insert_staged_action(
            staged, staged_by=staged_by, outbox_event=outbox_evt
        )

    async def get_step_draft_artifact_async(self, step_execution_id: str) -> dict[str, Any]:
        """Return `step_executions.draft_artifact_jsonb` directly from PG18."""
        if self._repository is not None:
            return await self._repository.get_step_draft_artifact(step_execution_id)
        return self.get_step_draft_artifact(step_execution_id)

    async def list_staged_actions_async(
        self, *, workspace_id: str | None = None
    ) -> list[StagedJiraActionItem]:
        """List staged or executed Jira actions directly from PG18."""
        if self._repository is not None:
            return await self._repository.list_staged_actions(workspace_id=workspace_id)
        return self.list_staged_actions(workspace_id=workspace_id)

    async def commit_staged_action_on_gate_pass_async(
        self,
        *,
        staged_action_id: str,
        gate_status: Literal["PASS", "FAIL", "WAITING_HUMAN"],
        run_lock_sha256: str,
        approved_by: str | None = None,
    ) -> StagedJiraActionItem:
        """Execute a staged Jira action from PG18 on Gate PASS + write Outbox atomically."""
        if self._repository is None:
            if self._strict_sql:
                raise ValidationDomainError(
                    detail_override="Jira PG18 repository is required when strict_sql=True."
                )
            return self.commit_staged_action_on_gate_pass(
                staged_action_id=staged_action_id,
                gate_status=gate_status,
                run_lock_sha256=run_lock_sha256,
            )

        staged = await self._repository.get_staged_action(staged_action_id)
        if staged is None:
            raise ResourceNotFoundError(
                detail_override=f"Staged Jira action {staged_action_id!r} not found."
            )
        executed = invoke_jira_gate_commit(
            staged, gate_status=gate_status, run_lock_sha256=run_lock_sha256
        )
        outbox_evt = StepCompleted.create(
            step_execution_id=executed.step_execution_id,
            run_id=executed.run_id,
            workspace_id=executed.workspace_id,
            step_key=f"jira:{executed.action_type}:{executed.executed_issue_key or ''}",
            step_status="COMMITTED",
            cost_usd=0.0,
        )
        return await self._repository.mark_executed(
            executed, approved_by=approved_by, outbox_event=outbox_evt
        )

    async def handle_issue_updated_webhook_async(
        self,
        *,
        webhook_event: str,
        issue_key: str,
        new_status: str,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
    ) -> JiraWebhookReplayNotification:
        """Process `jira:issue_updated` webhook and persist Outbox event in PG18 (`FR-16`)."""
        notif, evt = build_jira_webhook_notification(
            webhook_event=webhook_event,
            issue_key=issue_key,
            new_status=new_status,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
        )
        if evt is not None:
            if self._repository is not None:
                await self._repository.enqueue_outbox_event(evt)
            elif self._strict_sql:
                raise ValidationDomainError(
                    detail_override="Jira PG18 repository is required when strict_sql=True."
                )
            if self._outbox_relay is not None:
                self._outbox_relay.enqueue_in_transaction(evt)
        return notif
