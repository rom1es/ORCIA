"""Unit tests for Story 24.1: Jira Staged Actions, Governed MCP & VSM v2 PG18 services."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from tests.unit.fakes.in_memory_stores import InMemoryOutboxRelay

from orcia_connectors._jira_models import StagedJiraActionItem
from orcia_connectors.jira_actions import MultiProjectJiraStagedActionService
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration.mcp_server import GovernedMcpServerService
from orcia_core.workflows._internal.sql_vsm_v2 import (
    SqlVsmDefinitionsV2Store,
    upsert_vsm_definitions_v2_sql,
)
from orcia_core.workflows.schemas_v2 import ValueStreamMapSpec, VsmStepNodeSpec
from orcia_kernel.events import ArtifactProduced, DomainEvent, StepCompleted


class _FakeJiraStagedRepo:
    def __init__(self) -> None:
        self.items: dict[str, StagedJiraActionItem] = {}
        self.outbox_events: list[DomainEvent] = []

    async def insert_staged_action(
        self,
        item: StagedJiraActionItem,
        *,
        staged_by: str | None = None,
        outbox_event: DomainEvent | None = None,
    ) -> StagedJiraActionItem:
        self.items[item.staged_action_id] = item
        if outbox_event is not None:
            self.outbox_events.append(outbox_event)
        return item

    async def get_staged_action(self, staged_action_id: str) -> StagedJiraActionItem | None:
        return self.items.get(staged_action_id)

    async def list_staged_actions(
        self, *, workspace_id: str | None = None
    ) -> list[StagedJiraActionItem]:
        if workspace_id is None:
            return list(self.items.values())
        return [i for i in self.items.values() if i.workspace_id == workspace_id]

    async def get_step_draft_artifact(self, step_execution_id: str) -> dict[str, Any]:
        matched = [i for i in self.items.values() if i.step_execution_id == step_execution_id]
        return {
            "staged_actions": [
                {
                    "staged_action_id": i.staged_action_id,
                    "status": i.status,
                    "issue_key": i.issue_key,
                }
                for i in matched
            ]
        }

    async def mark_executed(
        self,
        item: StagedJiraActionItem,
        *,
        approved_by: str | None = None,
        outbox_event: DomainEvent | None = None,
    ) -> StagedJiraActionItem:
        updated = replace(item, status="EXECUTED")
        self.items[updated.staged_action_id] = updated
        if outbox_event is not None:
            self.outbox_events.append(outbox_event)
        return updated

    async def enqueue_outbox_event(self, event: DomainEvent) -> None:
        self.outbox_events.append(event)


class _FakeMcpProposalRepo:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def record_proposal(
        self,
        *,
        workspace_id: str,
        run_id: str,
        section_key: str,
        content_markdown: str,
        ide_client: str,
        execution_identity: str = "passthrough",
        proposed_by: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "proposal_id": f"prop-{len(self.rows) + 1}",
            "workspace_id": workspace_id,
            "run_id": run_id,
            "section_key": section_key,
            "content_markdown": content_markdown,
            "ide_client": ide_client,
            "execution_identity": execution_identity,
            "status": "PROPOSED",
            "proposed_by": proposed_by,
        }
        self.rows.append(row)
        return row

    async def list_proposals(
        self,
        *,
        workspace_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            r
            for r in self.rows
            if r["workspace_id"] == workspace_id and (run_id is None or r["run_id"] == run_id)
        ]


def _make_sample_vsm(
    vsm_id: str = "vsm-test-01",
    slug: str = "vsm-test-slug",
) -> ValueStreamMapSpec:
    return ValueStreamMapSpec(
        id=vsm_id,
        slug=slug,
        title="Test VSM 11 étapes",
        subtitle="Idea to Prod",
        source_note="Unit test",
        guiding_principle="PG18 first",
        pack_id="sdlc",
        phases=[{"num": "1", "id": "phase-1", "label": "Cadrage", "subtitle": "Qualifier"}],
        nodes=[
            VsmStepNodeSpec(
                num="01",
                phase_id="phase-1",
                title="Qualification PRD",
                linked_workflow_id="wf-01-qualification-prd",
                input_actuel="Demande brute",
                input_ia="Demande structurée",
                output_actuel="PRD",
                output_ia="PRD vérifié",
                actor_actuel="PM",
                actor_ia="PM + Agent",
                validation_actuel="Revue manuelle",
                validation_ia="Gate tri-modale",
            )
        ],
    )


@pytest.mark.asyncio
async def test_jira_staged_service_strict_sql_fail_closed_without_repo() -> None:
    svc = MultiProjectJiraStagedActionService(repository=None, strict_sql=True)

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await svc.stage_action_async(
            workspace_id="ws-1",
            run_id="run-1",
            step_execution_id="step-1",
            project_alias="jira:product",
            action_type="transition_issue",
            issue_key="PAYBUILD-101",
            target_transition="IN_REVIEW",
            summary="Passage en revue",
            fields_payload={"pr_url": "https://git.local/pr/1"},
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await svc.commit_staged_action_on_gate_pass_async(
            staged_action_id="0195f000-0000-7000-8000-000000000001",
            gate_status="PASS",
            run_lock_sha256="sha256:abc",
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await svc.handle_issue_updated_webhook_async(
            webhook_event="jira:issue_updated",
            issue_key="PAYBUILD-101",
            new_status="Done",
            workspace_id="ws-1",
            run_id="run-1",
            step_execution_id="step-1",
        )

    # Non-Done webhook emits no outbox event, so no repository write is needed
    noop = await svc.handle_issue_updated_webhook_async(
        webhook_event="jira:issue_updated",
        issue_key="PAYBUILD-101",
        new_status="IN_PROGRESS",
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
    )
    assert noop.replay_triggered is False
    assert noop.outbox_event_id is None


@pytest.mark.asyncio
async def test_jira_staged_service_async_transitions_commit_and_webhook_outbox() -> None:
    repo = _FakeJiraStagedRepo()
    outbox = InMemoryOutboxRelay()
    svc = MultiProjectJiraStagedActionService(
        outbox_relay=outbox,
        repository=repo,  # type: ignore[arg-type]
        strict_sql=True,
    )

    with pytest.raises(ValidationDomainError, match="ERR_JIRA_TRANSITION_ILLEGAL"):
        await svc.stage_action_async(
            workspace_id="ws-1",
            run_id="run-1",
            step_execution_id="step-1",
            project_alias="jira:product",
            action_type="transition_issue",
            issue_key="PAYBUILD-101",
            target_transition="INVALID_STATE",
            summary="Bad transition",
        )

    with pytest.raises(ValidationDomainError, match="ERR_JIRA_TRANSITION_FIELDS_MISSING"):
        await svc.stage_action_async(
            workspace_id="ws-1",
            run_id="run-1",
            step_execution_id="step-1",
            project_alias="jira:product",
            action_type="transition_issue",
            issue_key="PAYBUILD-101",
            target_transition="IN_REVIEW",
            summary="Missing fields",
            fields_payload={},
        )

    staged = await svc.stage_action_async(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
        project_alias="jira:product",
        action_type="transition_issue",
        issue_key="PAYBUILD-101",
        target_transition="IN_REVIEW",
        summary="Ready for review",
        fields_payload={"pr_url": "https://git.local/pr/42"},
        staged_by="usr-1",
    )
    assert staged.status == "STAGED"
    assert isinstance(repo.outbox_events[0], ArtifactProduced)

    listed = await svc.list_staged_actions_async(workspace_id="ws-1")
    assert len(listed) == 1
    draft = await svc.get_step_draft_artifact_async("step-1")
    assert draft["staged_actions"][0]["staged_action_id"] == staged.staged_action_id

    with pytest.raises(ResourceNotFoundError):
        await svc.commit_staged_action_on_gate_pass_async(
            staged_action_id="0195f000-0000-7000-8000-000000000999",
            gate_status="PASS",
            run_lock_sha256="sha256:deadbeef",
        )

    with pytest.raises(ValidationDomainError, match="requires 'PASS'"):
        await svc.commit_staged_action_on_gate_pass_async(
            staged_action_id=staged.staged_action_id,
            gate_status="WAITING_HUMAN",
            run_lock_sha256="sha256:deadbeef",
        )

    executed = await svc.commit_staged_action_on_gate_pass_async(
        staged_action_id=staged.staged_action_id,
        gate_status="PASS",
        run_lock_sha256="sha256:deadbeef",
        approved_by="usr-lead",
    )
    assert executed.status == "EXECUTED"
    assert executed.provenance_run_lock_sha256 == "sha256:deadbeef"
    assert isinstance(repo.outbox_events[1], StepCompleted)

    notif = await svc.handle_issue_updated_webhook_async(
        webhook_event="jira:issue_updated",
        issue_key="PAYBUILD-101",
        new_status="Done",
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
    )
    assert notif.replay_triggered is True
    assert notif.outbox_event_id is not None
    assert isinstance(repo.outbox_events[2], StepCompleted)
    assert len(outbox.pending_events) == 1


@pytest.mark.asyncio
async def test_governed_mcp_service_strict_sql_and_repository_persistence() -> None:
    strict_no_repo = GovernedMcpServerService(proposals_repository=None, strict_sql=True)

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        strict_no_repo.call_tool(
            tool_name="blackboard.propose_draft",
            workspace_id="ws-1",
            arguments={"section_key": "architecture-notes", "content_markdown": "Draft"},
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await strict_no_repo.call_tool_async(
            tool_name="blackboard.propose_draft",
            workspace_id="ws-1",
            arguments={"section_key": "architecture-notes", "content_markdown": "Draft"},
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await strict_no_repo.list_draft_proposals_async(workspace_id="ws-1")

    non_strict = GovernedMcpServerService(proposals_repository=None, strict_sql=False)
    assert await non_strict.list_draft_proposals_async(workspace_id="ws-1") == []

    repo = _FakeMcpProposalRepo()
    svc = GovernedMcpServerService(proposals_repository=repo, strict_sql=True)

    # Protected sections & human_authored_required=True are blocked even with repo
    for protected in ("intention-metier", "business-intent", "human-anchor"):
        with pytest.raises(HumanAnchorRequiredError):
            await svc.call_tool_async(
                tool_name="blackboard.propose_draft",
                workspace_id="ws-1",
                arguments={"section_key": protected, "content_markdown": "Overwrite"},
            )

    with pytest.raises(HumanAnchorRequiredError):
        await svc.call_tool_async(
            tool_name="blackboard.propose_draft",
            workspace_id="ws-1",
            arguments={
                "section_key": "custom-section",
                "human_authored_required": True,
                "content_markdown": "Overwrite",
            },
        )

    with pytest.raises(ObserverModeReadOnlyError):
        await svc.call_tool_async(
            tool_name="blackboard.propose_draft",
            workspace_id="ws-1",
            arguments={"section_key": "custom-section", "content_markdown": "Draft"},
            is_read_only_observer=True,
        )

    with pytest.raises(ValidationDomainError, match="passthrough"):
        await svc.call_tool_async(
            tool_name="blackboard.read",
            workspace_id="ws-1",
            arguments={},
            execution_identity="service_principal",
        )

    with pytest.raises(ValidationDomainError, match="workspace_id"):
        await svc.call_tool_async(
            tool_name="blackboard.read",
            workspace_id="   ",
            arguments={},
        )

    with pytest.raises(ResourceNotFoundError, match="Unknown MCP tool"):
        await svc.call_tool_async(
            tool_name="unknown.tool",
            workspace_id="ws-1",
            arguments={},
        )

    propose_res = await svc.call_tool_async(
        tool_name="blackboard.propose_draft",
        workspace_id="ws-1",
        arguments={
            "run_id": "run-241",
            "section_key": "sequence-diagram",
            "content_markdown": "```mermaid\nsequenceDiagram\n```",
        },
        ide_client="cursor",
        proposed_by="usr-dev",
    )
    assert propose_res.status == "OK"
    assert propose_res.data["draft_recorded"] is True
    assert propose_res.data["proposal"]["proposal_id"] == "prop-1"

    read_res = await svc.call_tool_async(
        tool_name="blackboard.read",
        workspace_id="ws-1",
        arguments={"run_id": "run-241"},
    )
    assert read_res.status == "OK"
    assert len(read_res.data["draft_proposals"]) == 1
    assert read_res.data["draft_proposals"][0]["section_key"] == "sequence-diagram"

    listed = await svc.list_draft_proposals_async(workspace_id="ws-1", run_id="run-241")
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_sql_vsm_definitions_v2_store_strict_and_memory_fallback() -> None:
    strict_store = SqlVsmDefinitionsV2Store(session_maker=None, strict_sql=True)
    spec = _make_sample_vsm()

    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_store.upsert_vsm(spec)
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_store.upsert_many_vsm([spec])
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_store.list_vsm()
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_store.get_vsm("vsm-test-01")

    mem_store = SqlVsmDefinitionsV2Store(session_maker=None, strict_sql=False)
    assert await mem_store.upsert_many_vsm([]) == []
    saved = await mem_store.upsert_vsm(spec)
    assert saved.id == spec.id
    all_vsm = await mem_store.list_vsm()
    assert [v.id for v in all_vsm] == [spec.id]
    assert (await mem_store.get_vsm(spec.id)) is not None
    assert (await mem_store.get_vsm(spec.slug)) is not None
    assert (await mem_store.get_vsm("  ")) is None
    assert (await mem_store.get_vsm("does-not-exist")) is None

    assert await upsert_vsm_definitions_v2_sql(object(), [spec]) == []  # type: ignore[arg-type]


def test_resolve_request_user_recovers_from_concurrent_auth_service_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `resolve_request_user` and `bearer_auth_rehydration_middleware` survive swap."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient

    from orcia_api.main import create_app
    from orcia_api.routers import _auth_token_issuer
    from orcia_core.permissions import AuthAndOrganizationService, UserIdentity

    app = create_app()
    orig_svc: AuthAndOrganizationService = app.state.auth_service
    user = UserIdentity(
        id="0195f241-0000-7000-8000-000000000777",
        email="swap.241@orcia.io",
        display_name="Swap User",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
        is_active=True,
        must_change_password=False,
        roles=["PLATFORM_ADMIN"],
    )
    orig_svc.register_user(user)
    token = orig_svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token

    # 1. Direct `resolve_request_user` fallback when `app.state.auth_service` was swapped empty
    swapped_svc = AuthAndOrganizationService(
        evaluator=orig_svc.evaluator,
        users=(),
        persona_map={},
        jwt_manager=orig_svc.jwt_manager,
    )
    fake_req = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(auth_service=swapped_svc)),
        state=SimpleNamespace(resolved_bearer_user=user),
        headers={"Authorization": f"Bearer {token}"},
    )
    resolved = _auth_token_issuer.resolve_request_user(fake_req)  # type: ignore[arg-type]
    assert resolved.id == user.id
    assert swapped_svc.has_user_in_memory(user.id)

    # 2. Middleware retries `rehydrate_bearer_subject_from_pg_if_missing` when first auth raises
    rehydrate_calls = 0

    async def _fake_rehydrate(request: Any) -> AuthAndOrganizationService:
        nonlocal rehydrate_calls
        rehydrate_calls += 1
        if rehydrate_calls >= 2:
            request.app.state.auth_service.register_user(user)
        return request.app.state.auth_service

    # Remove user from `orig_svc` so first `authenticate_access_token` raises ResourceNotFoundError
    orig_svc.unregister_user(user.id)
    monkeypatch.setattr(
        "orcia_api.main.rehydrate_bearer_subject_from_pg_if_missing",
        AsyncMock(side_effect=_fake_rehydrate),
    )
    client = TestClient(app)
    res = client.get(
        "/api/v1/vsm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert rehydrate_calls == 2


@pytest.mark.asyncio
async def test_story_24_1_mappers_and_dependency_upgrade_edge_cases() -> None:
    """Cover helper edge cases in `_sql_jira_mappers`, `SqlMcpProposalsRepository`, and DI."""
    from types import SimpleNamespace

    from orcia_api.dependencies.jira_and_mcp import (
        get_jira_staged_action_service,
        get_mcp_server_service,
    )
    from orcia_connectors._internal._sql_jira_mappers import (
        parse_json_dict,
        valid_uuid_or_none,
    )
    from orcia_core.orchestration._internal.sql_mcp_proposals import SqlMcpProposalsRepository

    assert parse_json_dict({"a": 1}) == {"a": 1}
    assert parse_json_dict('{"b": 2}') == {"b": 2}
    assert parse_json_dict("[1, 2]") == {}
    assert parse_json_dict(123) == {}
    assert valid_uuid_or_none("") is None
    assert valid_uuid_or_none("not-a-uuid") is None
    assert valid_uuid_or_none("0195f241-0000-7000-8000-000000000777") is not None

    empty_mcp_repo = SqlMcpProposalsRepository()
    assert await empty_mcp_repo.list_proposals(workspace_id="ws-1") == []
    with pytest.raises(RuntimeError, match="requires session_maker or engine"):
        await empty_mcp_repo.record_proposal(
            workspace_id="ws-1",
            run_id="run-1",
            section_key="sec",
            content_markdown="md",
            ide_client="vscode",
        )

    fake_engine = object()
    jira_svc = MultiProjectJiraStagedActionService(repository=None, strict_sql=False)
    mcp_svc = GovernedMcpServerService(proposals_repository=None, strict_sql=False)
    req = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                db_engine=fake_engine,
                session_maker=None,
                jira_staged_action_service=jira_svc,
                mcp_server_service=mcp_svc,
            )
        )
    )
    upgraded_jira = get_jira_staged_action_service(req)  # type: ignore[arg-type]
    upgraded_mcp = get_mcp_server_service(req)  # type: ignore[arg-type]
    assert upgraded_jira._repository is not None
    assert upgraded_jira._strict_sql is True
    assert upgraded_mcp._proposals_repository is not None
    assert upgraded_mcp._strict_sql is True
