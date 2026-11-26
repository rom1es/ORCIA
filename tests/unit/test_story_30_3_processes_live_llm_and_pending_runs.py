"""Unit tests for Story 30.3 (`UX30-06`, `UX30-07`): live LLM guard & pending runs."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.agents import GatewayReflexiveLlmAdapter
from orcia_core.agents.errors import ProcessModelNotConfiguredError
from orcia_core.ports.llm_port import (
    LlmCompletionResponse,
    LlmGatewayPort,
    LlmPromptRequest,
    compute_prompt_sha256,
)
from orcia_core.ports.reflexive_runtime_ports import ReflexiveTurnInput
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_core.workflows import SqlWorkflowV2RunsStore


@dataclass
class _StubNonCassetteGateway(LlmGatewayPort):
    """Test double simulating a live non-cassette LLM gateway without fallback_cassette."""

    response_content: str
    is_cassette_adapter: bool = False

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        return LlmCompletionResponse(
            content=self.response_content,
            model_family=request.model_family,
            model_id=request.model_id,
            prompt_sha256=compute_prompt_sha256(request),
            input_tokens=15,
            output_tokens=20,
            estimated_cost_usd=0.001,
            scenario_tag="LIVE_STUB",
        )


def _sample_turn(
    *,
    initial_resources: tuple[str, ...] = (),
    locale: str = "fr",
) -> ReflexiveTurnInput:
    return ReflexiveTurnInput(
        execution_id="exec-303-unit",
        actor_slug="redacteur-documentation-orcia",
        objective="Produire la note de synthèse",
        turn_index=1,
        max_turns=10,
        force_final=False,
        allow_sub_agent_delegation=False,
        available_delegate_agents=[],
        initial_resources=list(initial_resources),
        scratchpad=[],
        locale=locale,
    )


@pytest.mark.asyncio
async def test_gateway_reflexive_adapter_raises_when_no_gateway_or_empty_live_response() -> None:
    """Non-cassette mode never falls back to deterministic cassettes or capabilities.yaml."""
    no_gw_adapter = GatewayReflexiveLlmAdapter(None)
    with pytest.raises(ProcessModelNotConfiguredError) as exc_info:
        await no_gw_adapter.decide_next_turn(_sample_turn())
    assert exc_info.value.error_code == "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL"
    assert exc_info.value.http_status == 422

    empty_live_adapter = GatewayReflexiveLlmAdapter(_StubNonCassetteGateway(response_content="   "))
    with pytest.raises(ProcessModelNotConfiguredError):
        await empty_live_adapter.decide_next_turn(_sample_turn())


@pytest.mark.asyncio
async def test_gateway_reflexive_adapter_preserves_newlines_and_no_capabilities_fallback() -> None:
    """Keep newlines in live JSON/text; skip capabilities.yaml in cassette mode."""
    live_json = json.dumps(
        {
            "thought_text": "Ligne 1\nLigne 2",
            "action_kind": "final_answer",
            "final_markdown": "# Titre\n\n    indented()\n",
        },
        ensure_ascii=False,
    )
    live_adapter = GatewayReflexiveLlmAdapter(_StubNonCassetteGateway(response_content=live_json))
    decision = await live_adapter.decide_next_turn(_sample_turn())
    assert decision.action_kind == "final_answer"
    assert decision.final_markdown == "# Titre\n\n    indented()\n"

    chunks = [chunk async for chunk in live_adapter.stream_turn_deltas(_sample_turn(), decision)]
    assert "".join(c.thinking_delta for c in chunks) == "Ligne 1\nLigne 2"
    assert "".join(c.answer_delta for c in chunks) == "# Titre\n\n    indented()\n"

    cassette_adapter = GatewayReflexiveLlmAdapter(DeterministicCassetteLLM())
    cassette_decision = await cassette_adapter.decide_next_turn(_sample_turn(initial_resources=()))
    assert cassette_decision.action_kind == "final_answer"
    assert "capabilities.yaml" not in cassette_decision.final_markdown
    assert not cassette_decision.resource_uri


@pytest.mark.asyncio
async def test_sql_workflow_v2_runs_store_memory_filters_and_normalizes_statuses() -> None:
    """Memory-mode `SqlWorkflowV2RunsStore` filters pending vs completed and normalizes statuses."""
    store = SqlWorkflowV2RunsStore(session_maker=None)
    assert await store.list_pending_and_active_runs(workspace_ids=None) == []

    await store.upsert_run(
        run_id="run-pending-1",
        workspace_id="0195f000-0000-7000-8000-000000000101",
        workflow_id="wf-01-qualification-prd",
        workflow_slug="wf-01-qualification-prd",
        workflow_title="Qualification PRD",
        actor_slug="orchestrateur-produit",
        status="WAITING_FINAL_ANCHOR",
        reflexive_execution_id=None,
        state_payload={"run_id": "run-pending-1", "status": "WAITING_FINAL_ANCHOR"},
    )
    await store.upsert_run(
        run_id="run-completed-1",
        workspace_id="0195f000-0000-7000-8000-000000000101",
        workflow_id="wf-01-qualification-prd",
        workflow_slug="wf-01-qualification-prd",
        workflow_title="Qualification PRD",
        actor_slug="orchestrateur-produit",
        status="COMPLETED_APPROVED",
        reflexive_execution_id=None,
        state_payload={"run_id": "run-completed-1", "status": "COMPLETED_APPROVED"},
    )

    pending_only = await store.list_pending_and_active_runs(
        workspace_ids=("0195f000-0000-7000-8000-000000000101",),
        include_completed=False,
    )
    assert [r["run_id"] for r in pending_only] == ["run-pending-1"]
    assert pending_only[0]["is_pending"] is True

    with_completed = await store.list_pending_and_active_runs(
        workspace_ids=("0195f000-0000-7000-8000-000000000101",),
        include_completed=True,
    )
    assert [r["run_id"] for r in with_completed] == ["run-completed-1", "run-pending-1"]
    assert with_completed[0]["status"] == "COMPLETED"
    assert with_completed[0]["is_pending"] is False


def test_processes_live_mode_rejects_missing_llm_with_bilingual_rfc9457_and_empty_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject `POST .../runs` with 422 when live mode has no configured LLM."""
    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    monkeypatch.delenv("ORCIA_LLM_GATEWAY", raising=False)
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")

    with TestClient(create_app()) as client:
        empty_runs = client.get(
            "/api/v1/workflows/v2/runs",
            params={"workspace_id": "scope-global"},
        )
        assert empty_runs.status_code == 200
        assert empty_runs.json()["items"] == []
        assert empty_runs.json()["pending_count"] == 0

        fr_err = client.post(
            "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
            headers={"Accept-Language": "fr"},
            json={"inputs": {"objective": "Qualification"}},
        )
        assert fr_err.status_code == 422
        assert fr_err.headers["content-type"].startswith("application/problem+json")
        fr_body = fr_err.json()
        assert fr_body["error_code"] == "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL"
        assert "modèle" in fr_body["detail"].lower()

        en_err = client.post(
            "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
            headers={"Accept-Language": "en"},
            json={"inputs": {"objective": "Qualification"}},
        )
        assert en_err.status_code == 422
        en_body = en_err.json()
        assert en_body["error_code"] == "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL"
        assert "model" in en_body["detail"].lower()
