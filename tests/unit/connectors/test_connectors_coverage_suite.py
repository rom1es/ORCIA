"""Coverage suite for `orcia_connectors` reaching >= 90% unit test coverage."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from orcia_connectors.adapters import (
    AtlassianConfluenceConnector,
    AtlassianJiraConnector,
    GitProviderConnector,
    McpClientBridgeConnector,
    SqlReadonlyConnector,
    get_default_enterprise_connectors,
)
from orcia_connectors.bounded_workflow_v2 import (
    HitlSignalPayload,
    apply_hitl_signal_to_run,
    run_bounded_workflow_v2,
)
from orcia_connectors.codegraph.providers import (
    GitNexusMcpHttpProvider,
)
from orcia_connectors.codegraph_tool_runner import (
    async_run_codegraph_blast_radius,
    has_codegraph_permission,
)
from orcia_connectors.formats_and_indexers import (
    get_bmad_pack_format_adapter,
    get_git_code_ast_indexer,
    get_jira_hybrid_indexer,
    get_tripartite_graph_indexer,
)
from orcia_connectors.jira_actions import (
    JiraAccessRequestChannelAdapter,
    MultiProjectJiraStagedActionService,
)
from orcia_connectors.legacy_sdlc import activate_sdlc_pack
from orcia_connectors.markers import create_sdlc_memlog_marker_plugin
from orcia_connectors.policies import create_sdlc_fr13_policy_plugin
from orcia_connectors.protocol import (
    SignedApprovalToken,
)
from orcia_connectors.sdlc_connectors import (
    create_confluence_connector,
    create_git_connector,
    create_jira_connector,
    create_nexus_connector,
    register_all_sdlc_connectors,
)
from orcia_core.kernel.errors import (
    PolicyDeniedError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.workflows.schemas_v2 import (
    DeterministicSubStepSpec,
    ExecutionMode,
    StepControlsPipeline,
    WorkflowContract,
    WorkflowDefinitionV2,
)


def _make_spec(**kwargs: Any) -> DeterministicSubStepSpec:
    defaults = {
        "id": "s1",
        "name": "Step 1",
        "short_label": "S1",
        "enabled": True,
        "trigger_condition_label": "on start",
        "role_description": "role",
        "instruction_prompt_or_ref": "prompt://ref",
        "output_description": "output",
        "checkpoint_label": "checkpoint",
        "toolbox_mcp_permissions": [],
    }
    defaults.update(kwargs)
    return DeterministicSubStepSpec(**defaults)


def test_get_default_enterprise_connectors() -> None:
    connectors = get_default_enterprise_connectors()
    assert "mcp:codegraph" in connectors
    assert "mcp:atlassian-jira" in connectors
    assert "mcp:atlassian-confluence" in connectors
    assert "mcp:git-provider" in connectors
    assert "sql:readonly" in connectors
    assert "mcp:client-bridge" in connectors


@pytest.mark.asyncio
async def test_connector_adapters_read_and_preview_validation() -> None:
    jira = AtlassianJiraConnector()
    with pytest.raises(ValidationDomainError):
        await jira.read("")
    res_issue = await jira.read("issue://MCIA-101")
    assert res_issue["issue"]["status"] == "EN_REVUE"
    res_jql = await jira.read("jql://project=MCIA", {"jql": "project=MCIA"})
    assert "issues" in res_jql
    with pytest.raises(ResourceNotFoundError):
        await jira.read("issue://404-NOT-FOUND")

    with pytest.raises(ValidationDomainError):
        await jira.preview_write("  ", {})

    conf = AtlassianConfluenceConnector()
    with pytest.raises(ValidationDomainError):
        await conf.read("")
    res_page = await conf.read("page://ARCHI/123")
    assert res_page["page"]["title"] == "Page 123"
    res_cql = await conf.read("cql://space=ARCHI", {"cql": "space=ARCHI"})
    assert "pages" in res_cql
    with pytest.raises(ResourceNotFoundError):
        await conf.read("page://ARCHI/404")

    with pytest.raises(ValidationDomainError):
        await conf.preview_write("  ", {})

    git = GitProviderConnector()
    with pytest.raises(ValidationDomainError):
        await git.read("")
    res_git = await git.read("git://mon-compte/crl-back/file/README.md")
    assert "content" in res_git
    with pytest.raises(ResourceNotFoundError):
        await git.read("git://mon-compte/crl-back/404")

    with pytest.raises(ValidationDomainError):
        await git.preview_write("  ", {})

    sql = SqlReadonlyConnector()
    with pytest.raises(ValidationDomainError):
        await sql.read("")
    preview_sql = await sql.preview_write("mutate", {"q": "UPDATE users"})
    assert preview_sql.connector_type == sql.connector_type
    dummy_tok = SignedApprovalToken.issue(
        preview_card=preview_sql,
        approver_user_id="u1",
    )
    with pytest.raises(PolicyDeniedError):
        await sql.execute_write(dummy_tok, "mutate", {"q": "UPDATE users"})

    bridge = McpClientBridgeConnector()
    with pytest.raises(ValidationDomainError):
        await bridge.read("")
    with pytest.raises(ValidationDomainError):
        await bridge.preview_write("  ", {})


@pytest.mark.asyncio
async def test_gitnexus_mcp_http_provider_mocked_calls() -> None:
    async def _mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": {
                    "indexed_commit_sha": "gitnexus-sha-999",
                    "symbols": [
                        {"file_path": "a.py", "start_line": 1, "end_line": 5, "symbol_name": "foo"}
                    ],
                    "nodes": [{"symbol": "foo", "file_path": "a.py", "line": 1}],
                    "references": [{"file_path": "b.py", "line": 10}],
                    "impacted_files": ["a.py", "b.py"],
                    "impacted_symbols": ["foo"],
                    "blast_radius_score": 2.5,
                    "content": "def foo(): pass",
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_transport))
    provider = GitNexusMcpHttpProvider(
        endpoint="http://mock-gitnexus/mcp",
        http_client=client,
    )

    h = await provider.provider_healthcheck()
    assert h["ok"] is True

    sym = await provider.locate_symbol(repo_alias="r1", query="foo")
    assert sym.indexed_commit_sha == "gitnexus-sha-999"
    assert len(sym.symbols) == 1

    call_hier = await provider.get_call_hierarchy(repo_alias="r1", symbol="foo", file_path="a.py")
    assert len(call_hier.nodes) == 1

    refs = await provider.find_references(repo_alias="r1", symbol="foo")
    assert len(refs.references) == 1

    blast = await provider.calculate_blast_radius(
        repo_alias="r1", modified_files=["a.py"], run_lock_commit_sha="locked-diff"
    )
    assert blast.drift_warning == "GRAPH_MOVED_SINCE_RUN_LOCK"
    assert blast.blast_radius_score == 2.5

    span = await provider.read_span(repo_alias="r1", file_path="a.py", start_line=1, end_line=5)
    assert span.content == "def foo(): pass"


@pytest.mark.asyncio
async def test_codegraph_tool_runner_helpers() -> None:
    step_no_perm = _make_spec(id="s1", name="Step 1")
    assert has_codegraph_permission(step_no_perm) is False
    assert await async_run_codegraph_blast_radius(step_no_perm, {}) is None

    step_with_perm = _make_spec(
        id="s2",
        name="Step 2",
        toolbox_mcp_permissions=[{"connector_id": "mcp:codegraph", "scope": "read"}],
    )
    assert has_codegraph_permission(step_with_perm) is True

    res = await async_run_codegraph_blast_radius(
        step_with_perm,
        {"repo_alias": "my-repo", "modified_files": ["f1.py"], "run_lock_commit_sha": "diff"},
    )
    assert res is not None
    assert res["repo_alias"] == "my-repo"


def test_bounded_workflow_v2_hitl_signals() -> None:
    wf = WorkflowDefinitionV2(
        id="wf-test-hitl",
        slug="wf-test-hitl",
        title="Test HITL",
        version="1.0.0",
        status="published",
        pack_id="sdlc",
        execution_mode=ExecutionMode.NATIVE_ORCIA,
        contract=WorkflowContract(),
        controls=StepControlsPipeline(),
        sub_steps=[
            _make_spec(
                id="step-1",
                name="Step 1",
                requires_human_checkpoint=True,
                write_preview_required=True,
                toolbox_mcp_permissions=[{"connector_id": "mcp:atlassian-jira", "scope": "write"}],
            ),
            _make_spec(
                id="step-2",
                name="Step 2",
                requires_human_checkpoint=True,
            ),
        ],
    )

    state = run_bounded_workflow_v2(wf, run_id="run-hitl-1", auto_approve_checkpoints=False)
    assert state.status == "WAITING_SUBSTEP_HITL"

    # 0. Reject and retry
    state_retry = apply_hitl_signal_to_run(
        wf,
        state,
        HitlSignalPayload(action="REJECT_RETRY_SUBSTEP", correction_remarks="Ajuster intro"),
    )
    assert state_retry.status == "WAITING_SUBSTEP_HITL"
    state = state_retry

    # 1. Amend diff
    sig_amend = HitlSignalPayload(action="AMEND_DIFF", amended_markdown="# Amended Step 1")
    state = apply_hitl_signal_to_run(wf, state, sig_amend)

    # 2. Approve checkpoint
    preview = state.sub_step_records[0].write_preview_card
    assert preview is not None
    token = SignedApprovalToken.issue(preview_card=preview, approver_user_id="user.lead")
    sig_app = HitlSignalPayload(action="APPROVE", signed_approval_token=token)
    state = apply_hitl_signal_to_run(wf, state, sig_app)

    # 3. Final anchor: approve
    if state.status == "WAITING_SUBSTEP_HITL":
        state = apply_hitl_signal_to_run(wf, state, HitlSignalPayload(action="APPROVE"))

    # Final anchor actions
    state_loop = apply_hitl_signal_to_run(
        wf,
        state,
        HitlSignalPayload(
            action="REJECT_AND_LOOP", target_step_num="01", correction_remarks="Refaire"
        ),
    )
    assert state_loop.status == "RETURN_LOOP_TRIGGERED"

    state_sla = apply_hitl_signal_to_run(
        wf, state, HitlSignalPayload(action="SUSPEND_SLA", correction_remarks="Blocage externe")
    )
    assert state_sla.status == "SLA_SUSPENDED"


def test_legacy_sdlc_and_indexers_instantiation() -> None:
    assert get_bmad_pack_format_adapter() is not None
    assert get_git_code_ast_indexer() is not None
    assert get_jira_hybrid_indexer() is not None
    assert get_tripartite_graph_indexer() is not None
    policy = create_sdlc_fr13_policy_plugin()
    assert policy is not None
    marker = create_sdlc_memlog_marker_plugin()
    assert marker is not None
    activate_sdlc_pack()
    assert register_all_sdlc_connectors() is not None
    git_conn = create_git_connector()
    assert git_conn.capabilities() is not None
    assert git_conn.health().state in ("HEALTHY", "OK")
    jira_conn = create_jira_connector()
    assert jira_conn.health().state in ("HEALTHY", "OK")
    conf_conn = create_confluence_connector()
    assert conf_conn.health().state in ("HEALTHY", "OK")
    nexus_conn = create_nexus_connector()
    assert nexus_conn.health().state in ("HEALTHY", "OK")

    # Fetch and invoke coverage on sdlc_connectors
    fetch_res = git_conn.fetch("git://github.com/mon-compte/app.tar.gz@main")
    assert fetch_res.sha256 is not None
    with pytest.raises(ValidationDomainError):
        git_conn.fetch("http://invalid-scheme")
    with pytest.raises(ValidationDomainError):
        git_conn.fetch("git://no-path")
    with pytest.raises(ResourceNotFoundError):
        git_conn.fetch("git://github.com/404-file")

    inv1 = git_conn.invoke("commit", {"msg": "c1"}, idempotency_key="key-id-1")
    assert inv1.replayed_from_idempotency_cache is False
    inv2 = git_conn.invoke("commit", {"msg": "c1"}, idempotency_key="key-id-1")
    assert inv2.replayed_from_idempotency_cache is True
    with pytest.raises(ValidationDomainError):
        git_conn.invoke("", {}, "")
    assert git_conn.map_error(FileNotFoundError("not found")) is not None

    channel = JiraAccessRequestChannelAdapter()
    url = channel.build_access_request_url(
        "https://jira.corp/secure/CreateIssue.jspa?summary={summary}&description={description}",
        target_uri="catalog://git/repo",
        required_role="sdlc:lead",
        approver_team="team-core",
        requester_email="dev@corp.fr",
        step_key="03",
        execution_identity="bot",
    )
    assert "https://jira.corp" in url

    jira_svc = MultiProjectJiraStagedActionService()
    assert jira_svc.resolve_project_key("jira:product") == "PAYBUILD"
    assert jira_svc.resolve_project_key("jira:secops") == "PAYSEC"
    transitions = jira_svc.get_issue_transitions("PAYBUILD", "PAYBUILD-101")
    assert len(transitions) >= 1
    staged = jira_svc.stage_action(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
        project_alias="jira:product",
        action_type="create_issue",
        summary="New Issue",
        fields_payload={"summary": "New Issue", "issue_type": "Task"},
    )
    assert staged.status == "STAGED"
    staged_trans = jira_svc.stage_action(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
        project_alias="jira:product",
        action_type="transition_issue",
        summary="Transition Issue",
        issue_key="PAYBUILD-101",
        target_transition="IN_PROGRESS",
    )
    assert staged_trans.status == "STAGED"

    assert jira_svc.get_step_draft_artifact("step-1") is not None
    assert len(jira_svc.list_staged_actions()) >= 1

    committed = jira_svc.commit_staged_action_on_gate_pass(
        staged_action_id=staged_trans.staged_action_id,
        gate_status="PASS",
        run_lock_sha256="0" * 64,
    )
    assert committed.status == "EXECUTED"

    notif = jira_svc.handle_issue_updated_webhook(
        webhook_event="jira:issue_updated",
        issue_key="PAYBUILD-101",
        new_status="DONE",
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
    )
    assert notif.replay_triggered is True
