"""Story 26.10 — Offline `$0` Golden Evals for Tool Loops, Anchors/V5 & Citations (`AD-17` C4)."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.evals._golden_26_10_helpers import (
    ANCHOR_WORKFLOW_YAML,
    WS_EVAL,
    build_eval_router,
    eval_catalog_ctx,
    eval_user,
    load_jsonl,
)

from orcia_api.main import create_app
from orcia_api.routers._assistant_turn_producer_tool_loop import run_streaming_tool_loop
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawSourceCandidate,
)
from orcia_core.orchestration.assistant_loop_budgets import (
    AssistantLoopBudgetController,
    BudgetCheckResult,
    resolve_loop_budget_for_speed,
)
from orcia_core.orchestration.assistant_process_launcher import AssistantProcessLauncherService
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.ports.assistant_tool_executor_port import AssistantToolExecutionRequest
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig
from orcia_core.testing.cassette_llm import (
    DeterministicCassetteLLM,
    DeterministicCassetteLlmStreamingAdapter,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", load_jsonl("assistant_tool_loop.jsonl"), ids=lambda c: str(c["id"])
)
async def test_golden_assistant_tool_loop_and_citations_zero_cost(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify multi-turn OpenAI/Anthropic tool loops, zero unauthorized tools & zero phantoms."""
    budget_checks: list[BudgetCheckResult] = []
    orig_check_budget = AssistantLoopBudgetController.check_budget

    def _spied_check_budget(self: AssistantLoopBudgetController) -> BudgetCheckResult:
        res = orig_check_budget(self)
        budget_checks.append(res)
        return res

    monkeypatch.setattr(AssistantLoopBudgetController, "check_budget", _spied_check_budget)
    unauthorized_calls: list[str] = []
    outbox_events: list[Any] = []
    router, audit_sink = build_eval_router(unauthorized_calls, outbox_events)
    catalog = router.build_authorized_catalog(eval_catalog_ctx())
    registry = RedisAssistantTurnRegistry()
    user = eval_user()
    rec = AssistantTurnRecord(
        turn_id=f"turn-{case['id']}",
        workspace_id=WS_EVAL,
        user_id=user.id,
        status="RUNNING",
        user_prompt=str(case["prompt"]),
        assembled_system_prompt="System Layer 1",
        speed_mode="SPEED_2_AGENT_TOOLS",
        trace_id="0" * 32,
    )
    await registry.register_turn(rec)
    ep = LlmEndpointConfig(
        provider=str(case["provider"]),
        model_name="cassette-eval-model",
        endpoint_uri="https://api.example.test/v1",
        auth_mode="none_local",
        protocol_mode=str(case["protocol_mode"]),
        supports_tools=True,
    )
    guard = AssistantCitationAndV5GuardService(audit_ledger_sink=audit_sink)
    turn_engine = AssistantTurnEngine(citation_guard=guard)
    result = await run_streaming_tool_loop(
        active_port=DeterministicCassetteLlmStreamingAdapter(),
        stream_ep=ep,
        initial_messages=[
            {"role": "system", "content": "Layer 1"},
            {"role": "user", "content": str(case["prompt"])},
        ],
        tools=tuple(d.to_llm_tool_schema() for d in catalog),
        tool_catalog=catalog,
        tool_router=router,
        registry=registry,
        record=rec,
        user_email=user.email,
        user_display_name=user.display_name,
        locale="en",
        t0=time.perf_counter(),
        user_identity=user,
        active_hat="ARCHITECT",
        turn_engine=turn_engine,
    )
    assert len(unauthorized_calls) == int(case["expect_unauthorized_execs"])
    assert case["expect_dialect_tag"] in str(result["streamed_text"])
    if case["expect_verdict"] == "DENIED":
        assert any(e.event_type == "ASSISTANT_TOOL_DENIED" for e in audit_sink.entries)
    else:
        invoked = [e for e in audit_sink.entries if e.event_type == "ASSISTANT_TOOL_INVOKED"]
        assert len(invoked) >= int(case["expect_min_rounds"]) - 1
        assert len(result.get("tool_outputs") or ()) >= 1
        if case["id"] == "loop-06-budget-cap-halt":
            max_iter = resolve_loop_budget_for_speed(rec.speed_mode).max_iterations
            assert len(invoked) == max_iter
            assert any(
                (not b.can_continue) and b.exceeded_kind == "iterations" for b in budget_checks
            )

    base_table = guard.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="orcia://kb/settlement",
                title="Settlement Policy",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="Settlement policy.",
            ),
        )
    )
    final_table, _ = turn_engine.n4_build_evidence_table(
        base_table=base_table, tool_outputs=tuple(result.get("tool_outputs") or ())
    )
    cit_res, cmap, _ = await turn_engine.n6_verify_citations_async(
        response_text=f"{result['streamed_text']} [S1] [S99]",
        evidence_table=final_table,
        workspace_id=WS_EVAL,
        user_id=user.id,
    )
    assert "[S99]" not in cit_res.sanitized_text and "[S1]" in cit_res.sanitized_text
    assert "S99" not in cmap["citations"] and "S1" in cmap["citations"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", load_jsonl("assistant_anchor_and_v5.jsonl"), ids=lambda c: str(c["id"])
)
async def test_golden_assistant_anchor_and_v5_halts(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify FR-4 refusal, Lock V5 SI write interception, and DBOS anchor halts/422."""
    kind = str(case["kind"])
    user = eval_user()
    if kind == "n1_intent_refusal":
        intent = AssistantTurnEngine().n1_intent_guard(
            user, user_prompt=str(case["prompt"]), require_write=True
        )
        assert intent == case["expected_intent"]
        return

    if kind == "tool_v5_gate":
        unauthorized_calls: list[str] = []
        outbox_events: list[Any] = []
        router, _ = build_eval_router(unauthorized_calls, outbox_events)
        catalog = router.build_authorized_catalog(eval_catalog_ctx())
        res = await router.execute_tool_call(
            AssistantToolExecutionRequest(
                turn_id=f"turn-{case['id']}",
                iteration=0,
                tool_call_id="tc-v5-1",
                tool_name=str(case["tool_name"]),
                workspace_id=WS_EVAL,
                user_id=user.id,
                user_role=user.platform_role,
                active_hat="ARCHITECT",
                arguments=dict(case.get("arguments", {})),
            ),
            catalog=catalog,
        )
        assert unauthorized_calls == []
        assert res.verdict == case["expected_verdict"]
        assert res.audit_event_type == case["expected_audit"]
        assert any(e.event_type == case["expect_outbox_event"] for e in outbox_events)
        return

    anchor_md = str(case["human_anchor_markdown"])
    if "expect_error_code" in case:
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            t_resp = client.post(
                "/api/v1/assistant/turns?persona_key=marc",
                json={"workspace_id": WS_EVAL, "user_prompt": "Propose change"},
            )
            bad = client.post(
                f"/api/v1/assistant/turns/{t_resp.json()['turn_id']}/approve?persona_key=marc",
                json={
                    "workspace_id": WS_EVAL,
                    "proposal_id": "prop-eval-1",
                    "approved": True,
                    "human_authored_required": True,
                    "human_anchor_markdown": anchor_md,
                },
            )
            assert bad.status_code == int(case["expected_status_code"])
            assert bad.json()["error_code"] == case["expect_error_code"]
        return

    from orcia_core.orchestration.step_executors import _DEFAULT_AGENT_EXECUTOR

    _DEFAULT_AGENT_EXECUTOR.set_llm_gateway(DeterministicCassetteLLM())
    marc = build_default_auth_and_org_service().resolve_user(persona_key="marc")
    setup_svc = build_default_orchestration_setup_service()
    rep = setup_svc.validate_workflow_manifest(
        ANCHOR_WORKFLOW_YAML, workspace_id=WS_EVAL, raise_on_error=True
    )
    assert rep.workflow is not None
    setup_svc.register_validated_workflow(rep.workflow)
    launcher = AssistantProcessLauncherService(
        setup_service=setup_svc, engine=DurableOrchestrationEngine(setup_service=setup_svc)
    )
    outcome = await launcher.launch_process_async(
        marc,
        workspace_id=WS_EVAL,
        workflow_uri="orcia://workflows/golden-26-10-anchor-halt",
        idempotency_token="golden-anchor-halt-1",
        seed_inputs={"human_anchor_markdown": anchor_md},
    )
    assert outcome.run_status == case["expect_run_status"]
    assert case["expect_waiting_step"] in outcome.waiting_step_keys


def test_golden_datasets_minimum_volume() -> None:
    """Enforce minimum golden coverage across tool loop, anchor/V5, and injection datasets."""
    assert len(load_jsonl("assistant_tool_loop.jsonl")) >= 7
    assert len(load_jsonl("assistant_anchor_and_v5.jsonl")) >= 7
    assert len(load_jsonl("assistant_tool_output_injection.jsonl")) >= 10
