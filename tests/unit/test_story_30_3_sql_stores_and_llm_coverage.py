"""Unit tests for Story 30.3 SQL runs store, LLM bridge, & runtime/dispatcher helpers (`AD-17`)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request

from orcia_api.dependencies._process_llm_bridge import (
    _resolve_default_scope_uuid,
    build_app_llm_endpoint_resolver,
    enforce_live_process_prerequisites,
    has_meaningful_step_inputs,
    is_test_cassette_active,
    resolve_workspace_datasource_uris,
)
from orcia_core.agents._cassette_reflexive_decisions import (
    build_deterministic_cassette_decision,
    is_surgical_inspectable_uri,
)
from orcia_core.agents._internal.dispatcher_helpers import (
    compose_goal_objective,
    default_self_heal_callback,
    ensure_contract_sections,
)
from orcia_core.agents._runtime_helpers import (
    assert_snapshot_not_expired,
    build_scratchpad_entry_from_observation,
)
from orcia_core.agents.errors import (
    ProcessDatasourcesRequiredError,
    ProcessModelNotConfiguredError,
    ReflexiveSessionExpiredError,
)
from orcia_core.agents.llm_adapter import (
    GatewayReflexiveLlmAdapter,
    _slice_preserving_newlines,
    _try_parse_json_decision,
)
from orcia_core.agents.reflexive_schemas import ReflexiveSessionSnapshot
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.llm_port import LlmCompletionResponse, LlmGatewayPort, LlmPromptRequest
from orcia_core.ports.llm_streaming_port import (
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)
from orcia_core.ports.reflexive_runtime_ports import ReflexiveTurnInput
from orcia_core.ports.surgical_explorer_port import (
    SurgicalObservation,
    SurgicalOutlineNode,
    SurgicalPrimitiveName,
    SurgicalSnippetMatch,
)
from orcia_core.workflows._internal._sql_workflow_v2_pending_query import (
    normalize_workflow_run_status,
    safe_uuid,
)
from orcia_core.workflows.schemas_v2 import (
    DeterministicControlSpec,
    ExecutionMode,
    StepControlsPipeline,
    WorkflowContract,
    WorkflowDefinitionV2,
)


@dataclass
class _StubStreamingPort(LlmStreamingPort):
    outcome: LlmChatTurnOutcome | None

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        del request
        return self.outcome

    async def stream_chat_events(self, request: LlmStreamRequest) -> Any:
        del request
        if False:
            yield None


@dataclass
class _StubPlainGateway(LlmGatewayPort):
    content: str
    is_cassette_adapter: bool = False

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        return LlmCompletionResponse(
            content=self.content,
            model_family=request.model_family,
            model_id=request.model_id,
            prompt_sha256="a" * 64,
            input_tokens=5,
            output_tokens=10,
            estimated_cost_usd=0.0,
            scenario_tag="LIVE",
        )


def test_workflow_v2_status_and_uuid_helpers() -> None:
    """Cover pure `safe_uuid` and `normalize_workflow_run_status` helpers."""
    assert safe_uuid(None) is None
    assert safe_uuid("not-a-uuid") is None
    assert normalize_workflow_run_status("PAUSED_CIRCUIT_BREAKER") == "PAUSED"
    assert normalize_workflow_run_status("WAITING_FOR_HUMAN_ARBITRATION") == "WAITING_SUBSTEP_HITL"


@pytest.mark.asyncio
async def test_process_llm_bridge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover `_process_llm_bridge.py` scope UUIDs, datasource queries, and input checks."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = FastAPI()
    assert is_test_cassette_active(app) is True
    assert await build_app_llm_endpoint_resolver(app)(None) is None

    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    app.state.auth_service = SimpleNamespace(
        evaluator=SimpleNamespace(workspaces=[SimpleNamespace(id="ws-default-1")]),
        vault_cipher=None,
    )
    assert _resolve_default_scope_uuid(app, "not-a-uuid") == "ws-default-1"
    app.state.auth_service = None
    assert _resolve_default_scope_uuid(app, None) == "00000000-0000-7000-8000-000000000000"

    assert has_meaningful_step_inputs(None) is False
    wf = WorkflowDefinitionV2(
        id="wf-bridge",
        slug="wf-bridge",
        title="Mon Titre",
        pack_id="orcia-pack-sdlc",
        execution_mode=ExecutionMode.NATIVE_ORCIA,
        controls=StepControlsPipeline(
            deterministic=[
                DeterministicControlSpec(
                    id="g1",
                    name="Contract",
                    short_label="Contract",
                    verifies_description="Headings",
                    runner_plugin_id="markdown_contract_runner",
                    on_ko_behavior="blocking",
                    config={"required_headings": ["# ", "## Résumé"], "min_chars_per_section": 50},
                )
            ]
        ),
        contract=WorkflowContract(required_markdown_sections=["# "]),
    )
    assert has_meaningful_step_inputs({"empty": "  ", "objective": "Mon Titre"}, wf) is False
    assert has_meaningful_step_inputs({"objective": "Custom objective"}, wf) is True

    # Test resolver with mocked snapshot & resolve_configured_llm_endpoint_from_sources
    fake_ep = LlmEndpointConfig(
        provider="openai",
        model_name="gpt-4o",
        endpoint_uri="https://api.test",
        auth_mode="BEARER",
    )
    app.state.db_engine = object()
    with (
        patch(
            "orcia_api.dependencies._process_llm_bridge.get_valid_platform_setup_snapshot_async",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "orcia_api.dependencies._process_llm_bridge.resolve_configured_llm_endpoint_from_sources",
            new=AsyncMock(return_value=(fake_ep, SimpleNamespace(ok=True))),
        ),
        patch(
            "orcia_api.dependencies._process_llm_bridge.set_cached_platform_setup_snapshot_async",
            new=AsyncMock(),
        ),
    ):
        ep = await build_app_llm_endpoint_resolver(app)("0195f000-0000-7000-8000-000000000101")
        assert ep == fake_ep

    # Datasource resolution with mocked SQL engine vs in-memory evaluator
    ws_uuid = "0195f000-0000-7000-8000-000000000101"
    user = UserIdentity(
        id="u-1",
        email="u@orcia.test",
        display_name="User",
        auth_mode="HYBRID",
        human_profile_archetype="TEAM_LEAD",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="ou-1",
    )
    fake_auth = SimpleNamespace(
        evaluator=SimpleNamespace(
            resolve_accessible_workspaces=lambda _u: [
                SimpleNamespace(
                    workspace=SimpleNamespace(
                        id=ws_uuid,
                        datasources=[SimpleNamespace(uri="docs/eval.md")],
                    )
                )
            ],
            get_workspace=lambda _ws: SimpleNamespace(
                datasources=[SimpleNamespace(uri="docs/ws-eval.md")]
            ),
        )
    )
    req_mem: Any = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(db_engine=None, auth_service=fake_auth)),
        url=SimpleNamespace(path="/api/v1/workflows/v2/wf-bridge/runs"),
    )
    assert await resolve_workspace_datasource_uris(req_mem, workspace_id=ws_uuid, user=user) == [
        "docs/ws-eval.md"
    ]
    assert await resolve_workspace_datasource_uris(
        req_mem, workspace_id="scope-global", user=user
    ) == ["docs/eval.md"]

    # Live prerequisite error when datasources missing
    app_empty = FastAPI()
    app_empty.state.db_engine = None
    app_empty.state.llm_gateway = _StubPlainGateway("ok")
    app_empty.state.auth_service = SimpleNamespace(
        evaluator=SimpleNamespace(
            resolve_accessible_workspaces=lambda _u: [],
            get_workspace=lambda _ws: None,
        )
    )
    req_empty = Request(
        scope={
            "type": "http",
            "app": app_empty,
            "path": "/api/v1/workflows/v2/wf-bridge/runs",
            "headers": [],
        }
    )
    with (
        patch(
            "orcia_api.dependencies._process_llm_bridge.build_app_llm_endpoint_resolver",
            return_value=AsyncMock(return_value=fake_ep),
        ),
        pytest.raises(ProcessDatasourcesRequiredError),
    ):
        await enforce_live_process_prerequisites(
            req_empty, user=user, workspace_id=ws_uuid, workflow=wf, inputs={}
        )


@pytest.mark.asyncio
async def test_llm_adapter_cassette_decisions_runtime_and_dispatcher_helpers() -> None:
    """Cover `llm_adapter.py`, cassette decisions, runtime helpers, & dispatcher."""
    assert _slice_preserving_newlines("") == []
    assert _try_parse_json_decision('```json\n{"action_kind":"final_answer"}\n```', 5) is not None
    assert _try_parse_json_decision("{bad json", 5) is None

    turn = ReflexiveTurnInput(
        execution_id="ex-1",
        actor_slug="assistant",
        objective="Obj",
        turn_index=1,
        max_turns=5,
        initial_resources=["packs/a.yaml"],
        allow_sub_agent_delegation=True,
        available_delegate_agents=["analyste"],
        requested_write_preview={"action": "publish"},
    )
    ep = LlmEndpointConfig(
        provider="openai",
        model_name="gpt-4o",
        endpoint_uri="https://api.test",
        auth_mode="BEARER",
    )

    # Streaming port edge cases
    for outcome, exc_cls in [
        (None, ProcessModelNotConfiguredError),
        (
            LlmChatTurnOutcome(content="   ", thinking_text="", latency_ms=10.0),
            ProcessModelNotConfiguredError,
        ),
    ]:
        ad = GatewayReflexiveLlmAdapter(
            streaming_port=_StubStreamingPort(outcome),
            endpoint_resolver=AsyncMock(return_value=ep),
        )
        with pytest.raises(exc_cls):
            await ad.decide_next_turn(turn)

    no_ep = GatewayReflexiveLlmAdapter(
        streaming_port=_StubStreamingPort(None),
        endpoint_resolver=AsyncMock(return_value=None),
    )
    with pytest.raises(ProcessModelNotConfiguredError):
        await no_ep.decide_next_turn(turn)

    json_no_thought = LlmChatTurnOutcome(
        content=json.dumps({"action_kind": "final_answer", "final_markdown": "# OK"}),
        thinking_text="Mon raisonnement",
        latency_ms=12.0,
        input_tokens=10,
        output_tokens=20,
    )
    ad_json = GatewayReflexiveLlmAdapter(
        streaming_port=_StubStreamingPort(json_no_thought),
        endpoint_resolver=AsyncMock(return_value=ep),
    )
    dec_json = await ad_json.decide_next_turn(turn)
    assert dec_json.thought_text == "Mon raisonnement"

    plain_out = LlmChatTurnOutcome(content="# Markdown", thinking_text="Step 1", latency_ms=8.0)
    ad_plain = GatewayReflexiveLlmAdapter(
        streaming_port=_StubStreamingPort(plain_out),
        endpoint_resolver=AsyncMock(return_value=ep),
    )
    assert (await ad_plain.decide_next_turn(turn)).final_markdown == "# Markdown"

    gw_plain = GatewayReflexiveLlmAdapter(_StubPlainGateway(content="# Plain gateway"))
    assert (await gw_plain.decide_next_turn(turn)).final_markdown == "# Plain gateway"

    # Cassette decisions & URI rules
    assert is_surgical_inspectable_uri("virtual://doc") is True
    assert is_surgical_inspectable_uri("https://example.com") is False
    assert (
        build_deterministic_cassette_decision(
            turn.model_copy(update={"force_final": True}), 10
        ).action_kind
        == "final_answer"
    )
    assert build_deterministic_cassette_decision(turn, 10).action_kind == "surgical_primitive"
    assert (
        build_deterministic_cassette_decision(
            turn.model_copy(
                update={
                    "initial_resources": [],
                    "allow_sub_agent_delegation": False,
                    "requested_write_preview": {"action": "pub"},
                }
            ),
            10,
        ).action_kind
        == "propose_external_write_preview"
    )

    # Runtime helper edge branches
    expired_snap = ReflexiveSessionSnapshot(
        execution_id="ex-exp",
        actor_slug="assistant",
        objective="Obj",
        expires_at_utc=(datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
        + "Z",
    )
    with pytest.raises(ReflexiveSessionExpiredError):
        assert_snapshot_not_expired(expired_snap)

    for obs in [
        SurgicalObservation(
            kind=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
            resource_uri="docs/a.md",
            display_filename="a.md",
            file_badge_code="M↓",
            formatted_badge="M↓ a.md",
            redacted=True,
        ),
        SurgicalObservation(
            kind=SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
            resource_uri="docs/a.md",
            display_filename="a.md",
            file_badge_code="M↓",
            formatted_badge="M↓ a.md",
            snippets=[
                SurgicalSnippetMatch(
                    resource_uri="docs/a.md",
                    display_filename="a.md",
                    line_anchor="#L1-2",
                    start_line=1,
                    end_line=2,
                    excerpt="hit",
                )
            ],
        ),
        SurgicalObservation(
            kind=SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
            resource_uri="docs/a.md",
            display_filename="a.md",
            file_badge_code="M↓",
            formatted_badge="M↓ a.md",
            outline=[SurgicalOutlineNode(line_number=1, kind="h1", title="Title")],
        ),
        SurgicalObservation(
            kind=SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
            resource_uri="docs/a.md",
            display_filename="a.md",
            file_badge_code="M↓",
            formatted_badge="M↓ a.md",
            summary="OK",
        ),
    ]:
        assert build_scratchpad_entry_from_observation(turn_index=1, obs=obs) is not None

    # Dispatcher helpers
    wf_min = WorkflowDefinitionV2(
        id="wf-d",
        slug="wf-d",
        title="Workflow D",
        pack_id="orcia-pack-sdlc",
        execution_mode=ExecutionMode.NATIVE_ORCIA,
        controls=StepControlsPipeline(
            deterministic=[
                DeterministicControlSpec(
                    id="g1",
                    name="Contract",
                    short_label="Contract",
                    verifies_description="Headings",
                    runner_plugin_id="markdown_contract_runner",
                    on_ko_behavior="blocking",
                    config={"required_headings": ["# ", "## Section"], "min_chars_per_section": 50},
                )
            ]
        ),
        contract=WorkflowContract(required_markdown_sections=["# "]),
    )
    assert "Corrections demandees" in compose_goal_objective(wf_min, {"k": "v"}, "Fix it")
    assert "Workflow D" in ensure_contract_sections(
        WorkflowDefinitionV2(
            id="wf-e",
            slug="wf-e",
            title="Workflow D",
            pack_id="orcia-pack-sdlc",
            execution_mode=ExecutionMode.NATIVE_ORCIA,
        ),
        "",
        step_label="S1",
        inputs={},
        iteration=1,
        remarks=None,
    )
    healed = default_self_heal_callback(wf_min)("TODO", "missing section", 1)
    assert "## Section" in healed
