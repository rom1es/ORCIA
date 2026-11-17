"""Unit tests for `GatewayReflexiveLlmAdapter`, `ReflexiveEventStreamBroker`, & Gate (`16.2`)."""

from __future__ import annotations

import json

import pytest

from orcia_connectors import (
    ConnectorReflexiveWriteGateAdapter,
    SurgicalContextExplorer,
    issue_broker_write_approval,
)
from orcia_core.agents import (
    GatewayReflexiveLlmAdapter,
    NonDeterministicReflexiveRuntime,
    ReflexiveEventStreamBroker,
    ReflexiveRuntimeConfig,
    SqlReflexiveSessionStore,
)
from orcia_core.agents.errors import PolicyDeniedError
from orcia_core.storage.claim_check import ClaimCheckStorageService
from orcia_core.testing.cassette_llm import CassetteEntry, DeterministicCassetteLLM


@pytest.mark.asyncio
async def test_gateway_reflexive_llm_adapter_cassette_and_write_gate_end_to_end() -> None:
    """Verify `GatewayReflexiveLlmAdapter` + `DeterministicCassetteLLM` + fallback Write Gate."""
    cassette = DeterministicCassetteLLM()
    adapter = GatewayReflexiveLlmAdapter(cassette)
    explorer = SurgicalContextExplorer()
    store = SqlReflexiveSessionStore(session_maker=None)
    broker = ReflexiveEventStreamBroker(redis_url=None)
    write_gate = ConnectorReflexiveWriteGateAdapter()
    claim_check = ClaimCheckStorageService()

    runtime = NonDeterministicReflexiveRuntime(
        llm_port=adapter,
        surgical_explorer=explorer,
        session_store=store,
        event_stream=broker,
        write_gate=write_gate,
        claim_check_storage=claim_check,
    )

    cfg = ReflexiveRuntimeConfig(
        effort_mode="approfondi",
        initial_resources=("docs/product/capabilities.yaml",),
        requested_write_preview={
            "connector_type": "mcp:unregistered",
            "action": "publish_note",
            "target_resource_uri": "catalog://docs/note-16-2",
            "action_summary": "Publier la note gouvernée",
            "payload": {"title": "Note 16.2"},
        },
    )
    exec_id, bg_task = runtime.start_background_execution(
        actor_slug="assistant-agent",
        objective="Documenter Story 16.2",
        config=cfg,
    )
    paused = await bg_task
    assert paused.execution_id == exec_id
    assert paused.status == "WAITING_WRITE_PREVIEW"
    assert paused.pending_write_preview is not None

    # Stream events while paused: terminates cleanly at `write_preview_requested`
    broker.sync_history_from_snapshot(
        exec_id,
        [ev.model_dump(mode="json") for ev in paused.trace_events],
    )
    paused_events = [ev async for ev in broker.subscribe_events(exec_id)]
    assert paused_events[-1]["kind"] == "write_preview_requested"

    # Mismatched preview_id must raise PolicyDeniedError
    approval = issue_broker_write_approval(
        preview=paused.pending_write_preview,
        approver_user_id="user-marc",
    )
    bad_approval = approval.model_copy(update={"preview_id": "wrong-preview-id"})
    with pytest.raises(PolicyDeniedError):
        await write_gate.execute_approved_write(
            preview=paused.pending_write_preview,
            approval=bad_approval,
        )

    # Valid approval resumes and completes with ClaimCheckPointer + full SSE stream
    completed = await runtime.resume_after_write_decision(
        exec_id,
        approved=True,
        approval=approval,
    )
    assert completed.status == "COMPLETED"
    assert len(write_gate.executed_writes) == 1
    assert completed.artifact_pointer is not None

    broker.sync_history_from_snapshot(
        exec_id,
        [ev.model_dump(mode="json") for ev in completed.trace_events],
    )
    all_events = [ev async for ev in broker.subscribe_events(exec_id)]
    assert all_events[-1]["kind"] == "loop_completed"


@pytest.mark.asyncio
async def test_gateway_reflexive_llm_adapter_parses_explicit_json_completion() -> None:
    """Verify `GatewayReflexiveLlmAdapter` parses JSON `ReflexiveTurnDecision` & keeps `\\n`."""
    json_payload = json.dumps(
        {
            "thought_text": "Analyse directe JSON.\nSeconde ligne.",
            "action_kind": "final_answer",
            "final_markdown": "## Réponse JSON\n\n    code_indente()\n",
        },
        ensure_ascii=False,
    )
    cassette = DeterministicCassetteLLM(
        entries={
            "json-agent": CassetteEntry(
                content=json_payload,
                input_tokens=40,
                output_tokens=60,
            )
        }
    )
    adapter = GatewayReflexiveLlmAdapter(cassette)
    runtime = NonDeterministicReflexiveRuntime(
        llm_port=adapter,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=SqlReflexiveSessionStore(session_maker=None),
        event_stream=ReflexiveEventStreamBroker(redis_url=None),
        claim_check_storage=ClaimCheckStorageService(),
    )
    snap = await runtime.run_execution(
        actor_slug="json-agent",
        objective="Produire une réponse JSON directe",
        config=ReflexiveRuntimeConfig(),
    )
    assert snap.status == "COMPLETED"
    assert snap.tokens_used == 100
    assert "    code_indente()\n" in snap.final_markdown
