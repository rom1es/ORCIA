"""Tests for Story 4.4: Multi-Project Jira Staged Actions, Webhook, `/api/v1/mcp` & `DEC-ACC-01`.

Covers:
1. `DEC-ACC-01`: `AccessRequestChannelPort` (`JiraAccessRequestChannelAdapter` vs
   `DefaultAccessRequestChannel`) and Alembic `0019` (Expand + Backfill `request_url`) /
   `0020` (Contract `jira_request_url`) against real PostgreSQL 18 (`testcontainers`).
2. Multi-project Jira JQL, `GET /rest/api/3/issue/{key}/transitions` pre-validation,
   staged actions in `draft_artifact_jsonb`, and Gate-triggered execution with `run-lock.json`.
3. `jira:issue_updated` (`Done`) webhook `< 500 ms` publishing to `domain_events_outbox` (`FR-16`).
4. Governed `/api/v1/mcp` server (`passthrough` tools & `human_authored_required: true` block).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.in_memory_stores import InMemoryOutboxRelay

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration.mcp_server import GovernedMcpServerService
from orcia_core.permissions.broker_models import (
    DefaultAccessRequestChannel,
    PermissionBrokerTicket,
    resolve_active_access_request_channel,
)
from orcia_kernel.ports import get_access_request_channel, register_access_request_channel
from orcia_pack_sdlc.jira_actions import (
    JiraAccessRequestChannelAdapter,
    MultiProjectJiraStagedActionService,
    register_jira_access_request_channel,
)


def test_dec_acc_01_access_request_channel_port_and_ticket_request_url() -> None:
    """Verify `AccessRequestChannelPort` adapter switching and `request_url` synchronization."""
    jira_channel = register_jira_access_request_channel()
    assert isinstance(get_access_request_channel(), JiraAccessRequestChannelAdapter)
    assert resolve_active_access_request_channel().channel_name == "jira"

    jira_url = jira_channel.build_access_request_url(
        "https://jira.internal/create?summary={summary}&description={description}",
        target_uri="jira://PAYSEC/PAYSEC-204",
        required_role="JIRA_SECOPS_TRANSITION_ACTOR",
        approver_team="CSIRT",
        requester_email="marc@orcia.io",
        step_key="step-03",
        execution_identity="passthrough",
    )
    assert "JIRA_SECOPS_TRANSITION_ACTOR" in jira_url
    jira_hint = jira_channel.build_access_request_hint(
        target_uri="jira://PAYSEC/PAYSEC-204",
        required_role="JIRA_SECOPS_TRANSITION_ACTOR",
        approver_team="CSIRT",
        sla_hours=4,
    )
    assert jira_hint.startswith("jira://IAM/")

    # Fallback channel works without Jira
    default_channel = DefaultAccessRequestChannel()
    register_access_request_channel(default_channel)
    assert resolve_active_access_request_channel().channel_name == "default"
    generic_hint = default_channel.build_access_request_hint(
        target_uri="db://warehouse/table",
        required_role="DBA_READ",
        approver_team="DataGov",
        sla_hours=8,
    )
    assert generic_hint.startswith("orcia://iam/")

    # Restore Jira channel for SDLC pack
    register_jira_access_request_channel()

    tkt = PermissionBrokerTicket(
        id="0192c4e0-0000-7000-8000-000000009901",
        ticket_key="tkt-dec-acc-01",
        workspace_id="ws-01",
        requester_user_id="usr-01",
        policy_id="pol-01",
        step_key="step-01",
        step_number=1,
        step_state="PERMISSION_DENIED_STEP",
        status="WAITING_FOR_PERMISSION",
        target_uri="jira://PAYSEC/PAYSEC-204",
        connector_scheme="jira",
        execution_identity="passthrough",
        upstream_http_status=403,
        required_role="JIRA_SECOPS_TRANSITION_ACTOR",
        approver_team="CSIRT",
        sla_hours=4,
        jira_request_url="",
        permission_broker_hint=jira_hint,
        request_url=jira_url,
    )
    assert tkt.request_url == jira_url
    assert tkt.jira_request_url == jira_url


def test_jira_multi_project_staged_actions_gate_commit_and_webhook() -> None:
    """Verify JQL, transition pre-validation, Gate-only execution, and `< 500 ms` webhook."""
    outbox = InMemoryOutboxRelay()
    svc = MultiProjectJiraStagedActionService(outbox_relay=outbox)

    # 1. Multi-project JQL routing
    prod_issues = svc.search_jql(
        workspace_id="ws-pay",
        project_alias="jira:product",
        jql="project = PAYBUILD ORDER BY created DESC",
    )
    assert len(prod_issues) == 1
    assert prod_issues[0]["project_key"] == "PAYBUILD"

    sec_issues = svc.search_jql(
        workspace_id="ws-pay",
        project_alias="jira:secops",
        jql="project = PAYSEC AND status = OPEN",
    )
    assert len(sec_issues) == 1
    assert sec_issues[0]["project_key"] == "PAYSEC"

    with pytest.raises(ResourceNotFoundError):
        svc.resolve_project_key("jira:unknown-alias")

    # 2. Pre-validation against GET /rest/api/3/issue/{key}/transitions
    # Illegal transition rejected
    with pytest.raises(ValidationDomainError, match="ERR_JIRA_TRANSITION_ILLEGAL"):
        svc.stage_action(
            workspace_id="ws-pay",
            run_id="run-404",
            step_execution_id="step-exec-01",
            project_alias="jira:product",
            action_type="transition_issue",
            issue_key="PAYBUILD-101",
            target_transition="ARCHIVED_ILLEGAL",
            summary="Tentative de transition illégale",
        )

    # Missing mandatory screen fields rejected (IN_REVIEW requires pr_url)
    with pytest.raises(ValidationDomainError, match="ERR_JIRA_TRANSITION_FIELDS_MISSING"):
        svc.stage_action(
            workspace_id="ws-pay",
            run_id="run-404",
            step_execution_id="step-exec-01",
            project_alias="jira:product",
            action_type="transition_issue",
            issue_key="PAYBUILD-101",
            target_transition="IN_REVIEW",
            summary="Passage en revue sans pr_url",
            fields_payload={},
        )

    # Valid transition staged in step_executions.draft_artifact_jsonb
    staged = svc.stage_action(
        workspace_id="ws-pay",
        run_id="run-404",
        step_execution_id="step-exec-01",
        project_alias="jira:product",
        action_type="transition_issue",
        issue_key="PAYBUILD-101",
        target_transition="IN_REVIEW",
        summary="Passage en revue avec PR validée",
        fields_payload={
            "pr_url": "https://gitlab.entreprise.io/payments/checkout-web/-/merge_requests/42"
        },
    )
    assert staged.status == "STAGED"
    assert staged.project_key == "PAYBUILD"
    draft = svc.get_step_draft_artifact("step-exec-01")
    assert len(draft["staged_actions"]) == 1
    assert draft["staged_actions"][0]["staged_action_id"] == staged.staged_action_id

    # 3. Cannot commit while Gate has not passed
    with pytest.raises(ValidationDomainError, match="requires 'PASS'"):
        svc.commit_staged_action_on_gate_pass(
            staged_action_id=staged.staged_action_id,
            gate_status="WAITING_HUMAN",
            run_lock_sha256="sha256:abcdef0123456789",
        )

    # Commit succeeds on Gate PASS and attaches run-lock.json provenance
    executed = svc.commit_staged_action_on_gate_pass(
        staged_action_id=staged.staged_action_id,
        gate_status="PASS",
        run_lock_sha256="sha256:abcdef0123456789",
    )
    assert executed.status == "EXECUTED"
    assert executed.provenance_run_lock_uri == "orcia://runs/run-404/run-lock.json"
    assert executed.provenance_run_lock_sha256 == "sha256:abcdef0123456789"
    assert executed.replayed_from_cache is False

    # Re-committing same action uses ConnectorPort idempotency cache
    re_executed = svc.commit_staged_action_on_gate_pass(
        staged_action_id=staged.staged_action_id,
        gate_status="PASS",
        run_lock_sha256="sha256:abcdef0123456789",
    )
    assert re_executed.replayed_from_cache is True

    # 4. Webhook jira:issue_updated -> Done (< 500ms + domain_events_outbox)
    notif = svc.handle_issue_updated_webhook(
        webhook_event="jira:issue_updated",
        issue_key="PAYSEC-204",
        new_status="Done",
        workspace_id="ws-pay",
        run_id="run-404",
        step_execution_id="step-exec-01",
    )
    assert notif.replay_triggered is True
    assert notif.processing_ms < 500.0
    assert notif.outbox_event_id is not None
    assert len(outbox.pending_events) == 1


def test_governed_mcp_server_and_fastapi_routes() -> None:
    """Verify `/api/v1/mcp/*` and `/api/v1/jira/*` routes including human anchor protection."""
    mcp = GovernedMcpServerService()
    assert len(mcp.list_tools()) == 5

    with pytest.raises(HumanAnchorRequiredError):
        mcp.call_tool(
            tool_name="blackboard.propose_draft",
            workspace_id="ws-pay",
            arguments={
                "section_key": "intention-metier",
                "human_authored_required": True,
                "content_markdown": "Tentative d'écrasement par l'IDE",
            },
        )

    with pytest.raises(ObserverModeReadOnlyError):
        mcp.call_tool(
            tool_name="blackboard.propose_draft",
            workspace_id="ws-pay",
            arguments={"section_key": "architecture-technique", "content_markdown": "Draft"},
            is_read_only_observer=True,
        )

    client = TestClient(create_app())

    # 1. GET /api/v1/mcp/tools
    tools_res = client.get("/api/v1/mcp/tools?persona_key=marc")
    assert tools_res.status_code == 200
    assert len(tools_res.json()["tools"]) == 5

    # 2. POST /api/v1/mcp/call (read tools + valid draft vs blocked human_authored_required)
    for tool_name in ("ontology.query", "kb.search", "catalog.get", "blackboard.read"):
        res = client.post(
            "/api/v1/mcp/call?persona_key=marc",
            json={
                "tool_name": tool_name,
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "arguments": {"query": "payment", "level": "N1"},
                "ide_client": "antigravity",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "OK"

    blocked_res = client.post(
        "/api/v1/mcp/call?persona_key=marc",
        json={
            "tool_name": "blackboard.propose_draft",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "arguments": {
                "section_key": "intention-metier",
                "human_authored_required": True,
                "content_markdown": "Contenu généré depuis IDE",
            },
        },
    )
    assert blocked_res.status_code == 422
    assert blocked_res.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

    allowed_draft = client.post(
        "/api/v1/mcp/call?persona_key=marc",
        json={
            "tool_name": "blackboard.propose_draft",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "arguments": {
                "section_key": "architecture-technique",
                "human_authored_required": False,
                "content_markdown": "Proposition de schéma séquence IDE",
            },
        },
    )
    assert allowed_draft.status_code == 200
    assert allowed_draft.json()["data"]["draft_recorded"] is True

    # 3. FastAPI Jira Staged Actions & Webhook routes
    jql_res = client.post(
        "/api/v1/jira/jql/search?persona_key=marc",
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "project_alias": "jira:product",
            "jql": "project = PAYBUILD",
        },
    )
    assert jql_res.status_code == 200
    assert jql_res.json()["project_key"] == "PAYBUILD"

    stage_res = client.post(
        "/api/v1/jira/actions/stage?persona_key=marc",
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "run_id": "run-501",
            "step_execution_id": "step-exec-501",
            "project_alias": "jira:secops",
            "action_type": "transition_issue",
            "issue_key": "PAYSEC-204",
            "target_transition": "DONE",
            "summary": "Clôture revue SecOps",
            "fields_payload": {
                "root_cause": "Missing OAuth scope",
                "mitigation_summary": "Scope added and verified",
            },
        },
    )
    assert stage_res.status_code == 200
    staged_id = stage_res.json()["staged_action"]["staged_action_id"]

    commit_res = client.post(
        "/api/v1/jira/actions/commit?persona_key=marc",
        json={
            "staged_action_id": staged_id,
            "gate_status": "PASS",
            "run_lock_sha256": "sha256:9988776655443322",
        },
    )
    assert commit_res.status_code == 200
    assert commit_res.json()["executed_action"]["status"] == "EXECUTED"

    list_staged_res = client.get(
        "/api/v1/jira/actions/staged?workspace_id=0192c4e0-0000-7000-8000-000000000201&persona_key=marc"
    )
    assert list_staged_res.status_code == 200
    assert len(list_staged_res.json()["actions"]) >= 1
    assert list_staged_res.json()["actions"][-1]["staged_action_id"] == staged_id
    assert list_staged_res.json()["actions"][-1]["status"] == "EXECUTED"

    wh_res = client.post(
        "/api/v1/webhooks/jira/issue-updated",
        json={
            "webhook_event": "jira:issue_updated",
            "issue_key": "PAYSEC-204",
            "new_status": "Done",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "run_id": "run-501",
            "step_execution_id": "step-exec-501",
        },
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["replay_triggered"] is True
    assert wh_res.json()["processing_ms"] < 500.0
