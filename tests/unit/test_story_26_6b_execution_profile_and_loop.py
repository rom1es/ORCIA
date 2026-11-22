"""Unit tests for `ExecutionProfile='ASSISTANT'` & Multi-Step API Tool Loop (`Story 26.6b`)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import pytest

from orcia_api.routers._assistant_turn_producer_tool_loop import (
    execute_sync_tool_followup,
    run_streaming_tool_loop,
)
from orcia_connectors.reflexive_write_gate import ConnectorReflexiveWriteGateAdapter
from orcia_core.agents import (
    GovernedAssistantToolRouter,
    NonDeterministicReflexiveRuntime,
    ReflexiveRuntimeConfig,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
    assert_assistant_profile_write_gate_unreachable,
    assert_profile_allows_write_action,
)
from orcia_core.agents.errors import PolicyDeniedError
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    SkillCatalogEntry,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import (
    ContentDelta,
    Finish,
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamingPort,
    LlmStreamRequest,
    ReasoningDelta,
    ToolCallDelta,
    Usage,
    typed_event_to_delta,
)
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveEventStreamPort,
    ReflexiveLlmPort,
    ReflexiveSessionStorePort,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalLineEntry,
    SurgicalObservation,
    SurgicalPrimitiveName,
)


class _NoopExplorer(SurgicalExplorerPort):
    async def execute_primitive(
        self,
        primitive: SurgicalPrimitiveName,
        *,
        resource_uri: str,
        workspace_id: str,
        actor_id: str,
        has_read_source: bool = True,
        query: str = "",
        start_line: int = 1,
        end_line: int = 200,
        max_results: int = 20,
    ) -> SurgicalObservation:
        del workspace_id, actor_id, has_read_source, query, start_line, end_line, max_results
        return SurgicalObservation(
            kind=primitive,
            resource_uri=resource_uri,
            display_filename="doc.md",
            summary="Clean doc",
            lines=[SurgicalLineEntry(line_number=1, content="Clean doc")],
        )


class _MemSessionStore(ReflexiveSessionStorePort):
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    async def save_session_record(
        self,
        execution_id: str,
        *,
        workspace_id: str | None,
        actor_slug: str,
        orchestration_mode: str,
        effort_level: str,
        status: str,
        snapshot_payload: dict[str, Any],
        expires_at_utc: str,
    ) -> None:
        del workspace_id, actor_slug, orchestration_mode, effort_level, status, expires_at_utc
        self.records[execution_id] = dict(snapshot_payload)

    async def load_session_record(self, execution_id: str) -> dict[str, Any] | None:
        return self.records.get(execution_id)


class _MemEventStream(ReflexiveEventStreamPort):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish_event(self, execution_id: str, event: dict[str, Any]) -> None:
        del execution_id
        self.events.append(event)


class _WriteProposingLlm(ReflexiveLlmPort):
    async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
        del turn_input
        return ReflexiveTurnDecision(
            action_kind="propose_external_write_preview",
            thought_text="Attempt external write",
            connector_type="jira",
            write_action="update_issue",
            write_target_uri="jira://ISSUE-1",
            write_payload={"a": 1},
        )

    async def stream_turn_deltas(
        self, turn_input: ReflexiveTurnInput, decision: ReflexiveTurnDecision
    ) -> AsyncIterator[Any]:
        del turn_input, decision
        if False:
            yield None


def test_execution_profile_assistant_rejects_write_gate_and_write_preview() -> None:
    gate = ConnectorReflexiveWriteGateAdapter()
    with pytest.raises(PolicyDeniedError) as init_exc:
        NonDeterministicReflexiveRuntime(
            llm_port=_WriteProposingLlm(),
            surgical_explorer=_NoopExplorer(),
            session_store=_MemSessionStore(),
            event_stream=_MemEventStream(),
            write_gate=gate,
            execution_profile="ASSISTANT",
        )
    assert init_exc.value.error_code == "ERR_POLICY_DENIED"
    assert "ERR_ASSISTANT_WRITE_GATE_FORBIDDEN" in str(init_exc.value)

    with pytest.raises(ValueError, match="ASSISTANT"):
        ReflexiveRuntimeConfig(
            execution_profile="ASSISTANT",
            requested_write_preview={"target_uri": "jira://X"},
        )

    assert_assistant_profile_write_gate_unreachable("PROCESS", gate)
    assert_profile_allows_write_action("PROCESS")
    with pytest.raises(PolicyDeniedError):
        assert_profile_allows_write_action("ASSISTANT")


@pytest.mark.asyncio
async def test_assistant_profile_runtime_blocks_write_decision_and_keeps_process_default() -> None:
    default_cfg = ReflexiveRuntimeConfig()
    assert default_cfg.execution_profile == "PROCESS"

    rt = NonDeterministicReflexiveRuntime(
        llm_port=_WriteProposingLlm(),
        surgical_explorer=_NoopExplorer(),
        session_store=_MemSessionStore(),
        event_stream=_MemEventStream(),
        execution_profile="ASSISTANT",
    )
    with pytest.raises(PolicyDeniedError) as run_exc:
        await rt.run_execution(
            actor_slug="assistant-agent",
            objective="Test invariant",
            config=ReflexiveRuntimeConfig(execution_profile="ASSISTANT", max_turns=2),
        )
    assert run_exc.value.error_code == "ERR_POLICY_DENIED"
    assert "ERR_ASSISTANT_WRITE_GATE_FORBIDDEN" in str(run_exc.value)


def test_deterministic_v5_and_human_anchor_guard_helper() -> None:
    guard = AssistantCitationAndV5GuardService()
    blocked_anchor = guard.evaluate_tool_v5_and_human_anchor_guard(
        tool_name="skill_update",
        is_si_write=False,
        human_authored_required=True,
    )
    assert blocked_anchor is not None
    assert blocked_anchor["reason_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"
    assert blocked_anchor["transition_action"] == "CONTINUE_IN_PROCESS"

    allowed_read = guard.evaluate_tool_v5_and_human_anchor_guard(
        tool_name="check_resource_state",
        is_si_write=False,
        human_authored_required=False,
        target_uri="orcia://workspace/page",
    )
    assert allowed_read is None


class _MultiRoundStreamingPort(LlmStreamingPort):
    def __init__(self) -> None:
        self.round_count = 0

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        self.round_count += 1
        assert "<untrusted_tool_output" in str(request.messages)
        return LlmChatTurnOutcome(
            content="Grounded final answer from untrusted tool evidence.",
            thinking_text="",
            latency_ms=5.0,
            input_tokens=20,
            output_tokens=15,
            usage_source="provider",
        )

    async def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        self.round_count += 1
        if self.round_count == 1:
            yield typed_event_to_delta(ReasoningDelta(delta="Checking resource first"))
            tc1 = {
                "id": "tc-1",
                "name": "check_resource_state",
                "arguments": '{"resource_uri": "orcia://workspace/doc.md"}',
            }
            yield typed_event_to_delta(
                ToolCallDelta(
                    tool_call_id="tc-1",
                    name="check_resource_state",
                    arguments_delta='{"resource_uri": "orcia://workspace/doc.md"}',
                )
            )
            yield typed_event_to_delta(Finish(finish_reason="tool_calls", tool_calls=(tc1,)))
            return
        if self.round_count == 2:
            assert any(
                m.get("role") == "tool" and "<untrusted_tool_output" in str(m.get("content", ""))
                for m in request.messages
            )
            tc2 = {
                "id": "tc-2",
                "name": "skill_write_si",
                "arguments": '{"target_uri": "orcia://workspace/anchor"}',
            }
            yield typed_event_to_delta(
                ToolCallDelta(
                    tool_call_id="tc-2",
                    name="skill_write_si",
                    arguments_delta='{"target_uri": "orcia://workspace/anchor"}',
                )
            )
            yield typed_event_to_delta(Finish(finish_reason="tool_calls", tool_calls=(tc2,)))
            return
        msg = "Cannot write directly; approval proposal surfaced."
        yield typed_event_to_delta(ContentDelta(delta=msg, accumulated_text=msg))
        yield typed_event_to_delta(
            Usage(input_tokens=42, output_tokens=18, usage_source="provider")
        )  # noqa: E501
        yield typed_event_to_delta(
            Finish(
                finish_reason="stop",
                accumulated_text=msg,
                input_tokens=42,
                output_tokens=18,
                usage_source="provider",
            )
        )


@pytest.mark.asyncio
async def test_multi_step_streaming_and_sync_tool_loops_via_router() -> None:
    outbox_events: list[Any] = []

    async def _outbox(evt: Any) -> str | None:
        outbox_events.append(evt)
        return str(evt.event_id)

    router = GovernedAssistantToolRouter(
        surgical_explorer=_NoopExplorer(),
        outbox_enqueue_fn=_outbox,
    )
    ctx = AssistantToolCatalogContext(
        workspace_id="ws-loop-1",
        user_id="u-loop-1",
        user_role="CONTRIBUTOR",
        skills=(
            SkillCatalogEntry(
                skill_id="sk-w",
                slug="write_si",
                name="Write SI",
                objective="SI write",
                enabled_in_workspace=True,
                is_si_write=True,
                human_authored_required=True,
            ),
        ),
    )
    catalog = router.build_authorized_catalog(ctx)
    openai_tools = tuple(d.to_llm_tool_schema() for d in catalog)

    registry = RedisAssistantTurnRegistry()
    rec = AssistantTurnRecord(
        turn_id="turn-loop-1",
        workspace_id="ws-loop-1",
        user_id="u-loop-1",
        status="RUNNING",
        user_prompt="Check doc then mutate SI",
        assembled_system_prompt="Sys",
        speed_mode="SPEED_2_AGENT_TOOLS",
        trace_id="0" * 32,
    )
    await registry.register_turn(rec)

    port = _MultiRoundStreamingPort()
    ep = LlmEndpointConfig(
        provider="openai",
        model_name="gpt-4.1-mini",
        endpoint_uri="https://api.openai.com/v1/chat/completions",
        auth_mode="BEARER",
        supports_tools=True,
    )
    from orcia_core.permissions.models import UserIdentity

    contrib_user = UserIdentity(
        id="u-loop-1",
        email="u@orcia.local",
        display_name="Loop User",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-root",
    )
    result = await run_streaming_tool_loop(
        active_port=port,
        stream_ep=ep,
        initial_messages=[{"role": "system", "content": "Sys"}, {"role": "user", "content": "Go"}],
        tools=openai_tools,
        tool_catalog=catalog,
        tool_router=router,
        registry=registry,
        record=rec,
        user_email="u@orcia.local",
        user_display_name="Loop User",
        locale="en",
        t0=time.perf_counter(),
        user_identity=contrib_user,
    )
    assert result["has_approval_required"] is True
    assert "Lock V5 / Process Write Gate" in result["streamed_text"]
    assert result["emitted_tokens"] is True

    entries = await registry.read_events("turn-loop-1", after_cursor="0-0", count=50, block_ms=0)
    ev_names = [e.event for e in entries]
    assert "tool_call" in ev_names
    assert "tool_result" in ev_names
    assert "approval_required" in ev_names
    assert len(outbox_events) == 1

    sync_txt, sync_in, sync_out, sync_src = await execute_sync_tool_followup(
        tool_router=router,
        catalog=catalog,
        active_port=port,
        ep=ep,
        messages=[{"role": "user", "content": "Check doc"}],
        tool_calls=[
            {
                "id": "sync-tc-1",
                "name": "check_resource_state",
                "arguments": '{"resource_uri": "orcia://workspace/doc.md"}',
            }
        ],
        workspace_id="ws-loop-1",
        user_id="u-loop-1",
        user=contrib_user,
        active_hat="ARCHITECT",
        trace_id="0" * 32,
        locale="en",
    )
    assert "Grounded final answer" in sync_txt
    assert (sync_in, sync_out, sync_src) == (20, 15, "provider")
