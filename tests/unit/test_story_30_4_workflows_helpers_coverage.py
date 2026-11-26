"""Pure unit coverage tests for `orcia_api.routers._workflows_helpers` (`Story 30.4`)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from orcia_api.routers import _workflows_helpers as helpers
from orcia_core.agents.errors import ObserverModeReadOnlyError
from orcia_core.permissions import UserIdentity
from orcia_core.workflows.schemas_v2 import (
    ExecutionMode,
    ProcessOrchestrationType,
    ValueStreamMapSpec,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
)
from orcia_kernel.errors import OrciaDomainError


def _make_request(
    *,
    headers: dict[str, str] | None = None,
    state_attrs: dict[str, object] | None = None,
) -> Request:
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/workflows/v2/test",
        "headers": raw_headers,
    }
    req = Request(scope)
    for k, v in (state_attrs or {}).items():
        setattr(req.state, k, v)
    return req


def _make_user(role: str = "TEAM_LEAD") -> UserIdentity:
    return UserIdentity(
        id="0195f000-0000-7000-8000-000000000010",
        email="lead@orcia.test",
        display_name="Lead",
        auth_mode="LOCAL",  # type: ignore[arg-type]
        human_profile_archetype="tech_lead",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="0195f000-0000-7000-8000-000000000001",
    )


def _make_workflow(
    status: WorkflowLifecycleStatus = WorkflowLifecycleStatus.DRAFT,
) -> WorkflowDefinitionV2:
    return WorkflowDefinitionV2(
        id="wf-304-test",
        slug="wf-304-test",
        title="Workflow 30.4 Test",
        version="1.0.0-draft" if status == WorkflowLifecycleStatus.DRAFT else "1.0.0",
        status=status,
        pack_id="sdlc",
        orchestration_type=ProcessOrchestrationType.DETERMINISTIC_DBOS,
        execution_mode=ExecutionMode.NATIVE_ORCIA,
        global_system_prompt_or_ref="@assistant",
        sub_steps=[],
        guardrails=[],
    )


def _make_vsm(
    vsm_id: str = "vsm-mon-compte-idea-to-prod",
    slug: str = "mon-compte-idea-to-prod",
) -> ValueStreamMapSpec:
    return ValueStreamMapSpec(
        id=vsm_id,
        slug=slug,
        title="Idea to Production",
        subtitle="SDLC Agentic Workflow",
        source_note="SDLC",
        guiding_principle="Human-led",
        pack_id="sdlc",
        phases=[],
        nodes=[],
    )


def test_enforce_not_observer_rejects_header_and_workspace_observer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req_hdr = _make_request(headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"})
    monkeypatch.setattr(
        helpers,
        "resolve_request_user",
        lambda _req, persona_key=None: _make_user("CONTRIBUTOR"),
    )
    with pytest.raises(ObserverModeReadOnlyError):
        helpers.enforce_not_observer(req_hdr)

    req_ws = _make_request()
    monkeypatch.setattr(
        helpers,
        "get_auth_service",
        lambda _req: SimpleNamespace(
            evaluator=SimpleNamespace(
                resolve_workspace_access=lambda _u, _ws: SimpleNamespace(
                    access_mode="READ_ONLY_OBSERVER"
                )
            )
        ),
    )
    with pytest.raises(ObserverModeReadOnlyError):
        helpers.enforce_not_observer(req_ws, workspace_id="ws-ro")

    monkeypatch.setattr(
        helpers,
        "get_auth_service",
        lambda _req: SimpleNamespace(
            evaluator=SimpleNamespace(
                resolve_workspace_access=lambda _u, _ws: SimpleNamespace(
                    access_mode="CONTRIBUTOR_ACTION_REQUIRED"
                )
            )
        ),
    )
    user = helpers.enforce_not_observer(req_ws, workspace_id="ws-rw")
    assert user.email == "lead@orcia.test"


@pytest.mark.asyncio
async def test_load_workflows_store_indexes_draft_key() -> None:
    req = _make_request()
    wf_pub = _make_workflow(WorkflowLifecycleStatus.PUBLISHED)
    wf_draft = _make_workflow(WorkflowLifecycleStatus.DRAFT)
    sql_store = SimpleNamespace(list_persisted_workflows=AsyncMock(return_value=[wf_pub, wf_draft]))
    store = await helpers.load_workflows_store(req, sql_store)  # type: ignore[arg-type]
    assert store["wf-304-test:draft"] is wf_draft
    assert store["wf-304-test"] is wf_draft


@pytest.mark.asyncio
async def test_vsm_loading_and_sdlc_alias_fallback() -> None:
    req = _make_request()
    vsm = _make_vsm()
    populated_store = SimpleNamespace(
        get_vsm=AsyncMock(return_value=None),
        list_vsm=AsyncMock(return_value=[vsm]),
    )
    loaded = await helpers.load_vsm_definitions_from_pg18(req, populated_store)  # type: ignore[arg-type]
    assert loaded == [vsm]

    slug_store = SimpleNamespace(
        get_vsm=AsyncMock(return_value=None),
        list_vsm=AsyncMock(return_value=[vsm]),
    )
    by_slug = await helpers.get_vsm_definition_from_pg18(
        req,
        slug_store,  # type: ignore[arg-type]
        "mon-compte-idea-to-prod",
    )
    assert by_slug is vsm

    by_alias = await helpers.get_vsm_definition_from_pg18(
        req,
        slug_store,  # type: ignore[arg-type]
        "vsm-sdlc-idea-to-prod",
    )
    assert by_alias is vsm

    missing = await helpers.get_vsm_definition_from_pg18(
        req,
        slug_store,  # type: ignore[arg-type]
        "nonexistent-vsm",
    )
    assert missing is None

    completely_empty_store = SimpleNamespace(
        get_vsm=AsyncMock(return_value=None),
        list_vsm=AsyncMock(return_value=[]),
    )
    res_empty = await helpers.get_vsm_definition_from_pg18(
        req,
        completely_empty_store,  # type: ignore[arg-type]
        "vsm-sdlc-idea-to-prod",
    )
    assert res_empty is None


@pytest.mark.asyncio
async def test_publish_workflow_outbox_event_repo_domain_error_and_generic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wf = _make_workflow(WorkflowLifecycleStatus.PUBLISHED)
    ws_uuid = "0195f000-0000-7000-8000-000000000999"
    req = _make_request(
        headers={"X-Orcia-Workspace-Id": ws_uuid},
        state_attrs={"trace_id": "trace-304"},
    )

    repo_publish = AsyncMock()
    handle_published = AsyncMock()
    dispatcher = SimpleNamespace(
        _repo=SimpleNamespace(publish_outbox_event=repo_publish),
        _outbox_events=[],
        handle_workflow_published=handle_published,
    )
    monkeypatch.setattr(helpers, "get_trigger_dispatcher_service", lambda _req: dispatcher)
    monkeypatch.setattr(
        helpers,
        "get_help_generation_and_attachment_service",
        lambda _req: object(),
    )

    await helpers.publish_workflow_outbox_event(req, wf)
    repo_publish.assert_awaited_once()
    handle_published.assert_awaited_once()

    dispatcher_domain_err = SimpleNamespace(
        _repo=None,
        _outbox_events=[],
        handle_workflow_published=AsyncMock(
            side_effect=OrciaDomainError(detail_override="Domain boom")
        ),
    )
    monkeypatch.setattr(
        helpers,
        "get_trigger_dispatcher_service",
        lambda _req: dispatcher_domain_err,
    )
    with pytest.raises(OrciaDomainError):
        await helpers.publish_workflow_outbox_event(req, wf)

    dispatcher_generic_err = SimpleNamespace(
        _repo=None,
        _outbox_events=[],
        handle_workflow_published=AsyncMock(side_effect=RuntimeError("transient hook error")),
    )
    monkeypatch.setattr(
        helpers,
        "get_trigger_dispatcher_service",
        lambda _req: dispatcher_generic_err,
    )
    await helpers.publish_workflow_outbox_event(req, wf)
    assert len(dispatcher_generic_err._outbox_events) == 1
