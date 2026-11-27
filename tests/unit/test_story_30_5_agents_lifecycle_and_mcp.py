"""Unit & Router Contract Tests for Story 30.5 (`UX30-11`..`UX30-15`)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.workflows_seed import create_seeded_test_app as create_app

from orcia_core.orchestration import AgentsAndSkillsManagementService
from orcia_core.orchestration.errors import (
    AgentDraftLifecycleBlockedError,
    TierModelNotConfiguredError,
)


def test_agent_defaults_to_draft_untested_and_tracks_factual_bench_status() -> None:
    """New agents start DRAFT/UNTESTED; passing promotes to ACTIVE/PASSED; failing sets FAILED."""
    from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

    svc = AgentsAndSkillsManagementService(llm_gateway=None)
    agent = svc.upsert_agent(
        name="Brouillon Audit",
        role_mission="Verify regulatory rules",
        instructions="Inspect controls carefully.",
    )
    assert agent.lifecycle_status == "DRAFT"
    assert agent.test_bench_status == "UNTESTED"
    assert agent.test_bench_validated is False

    # Execution fails because no LLM / tier model is configured -> factual FAILED status
    with pytest.raises(TierModelNotConfiguredError):
        svc.execute_agent(agent.agent_id, prompt="Run compliance check")
    failed = svc.get_agent(agent.agent_id)
    assert failed.test_bench_status == "FAILED"
    assert failed.test_bench_validated is False
    assert failed.lifecycle_status == "DRAFT"

    # Cannot activate an agent with FAILED Test Bench status
    with pytest.raises(AgentDraftLifecycleBlockedError):
        svc.set_agent_lifecycle_status(agent.agent_id, lifecycle_status="ACTIVE")

    # Passing Test Bench promotes to PASSED and ACTIVE
    svc_ok = AgentsAndSkillsManagementService(llm_gateway=DeterministicCassetteLLM())
    ok_agent = svc_ok.upsert_agent(
        name="Brouillon Audit",
        role_mission="Verify regulatory rules",
        instructions="Inspect controls carefully.",
    )
    outcome = svc_ok.execute_agent(ok_agent.agent_id, prompt="Run compliance check")
    assert outcome.test_bench_status == "PASSED"
    assert outcome.lifecycle_status == "ACTIVE"
    stored = svc_ok.get_agent(ok_agent.agent_id)
    assert stored.test_bench_status == "PASSED"
    assert stored.test_bench_validated is True
    assert stored.lifecycle_status == "ACTIVE"

    # Demoting ACTIVE -> DRAFT automatically clears mcp_exposed
    svc_ok.set_agent_mcp_exposure(ok_agent.agent_id, mcp_exposed=True)
    assert svc_ok.get_agent(ok_agent.agent_id).mcp_exposed is True
    demoted = svc_ok.set_agent_lifecycle_status(ok_agent.agent_id, lifecycle_status="DRAFT")
    assert demoted.lifecycle_status == "DRAFT"
    assert demoted.mcp_exposed is False


def test_draft_agent_blocked_across_mcp_assistant_and_processes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DRAFT agents return HTTP 422 across MCP, Mon Assistant, and Mes Processus; ACTIVE succeed."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    app = create_app()
    client = TestClient(app)

    # 1. Create a DRAFT agent
    created = client.post(
        "/api/v1/agents-and-skills/agents?persona_key=marc",
        json={
            "agent_id": "agent-brouillon-securite",
            "name": "Brouillon Sécurité",
            "role_mission": "Control cloud posture",
            "instructions": "Verify security controls.",
            "thinking_level": "medium",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["lifecycle_status"] == "DRAFT"
    assert body["test_bench_status"] == "UNTESTED"
    assert body["test_bench_validated"] is False

    # 2. MCP exposure on DRAFT agent returns HTTP 422 (FR & EN localized)
    mcp_fr = client.patch(
        "/api/v1/agents-and-skills/agents/agent-brouillon-securite/governance?persona_key=marc",
        headers={"Accept-Language": "fr"},
        json={"mcp_exposed": True},
    )
    assert mcp_fr.status_code == 422
    assert mcp_fr.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"
    assert "DRAFT" in mcp_fr.json()["detail"]

    mcp_en = client.patch(
        "/api/v1/agents-and-skills/agents/agent-brouillon-securite/governance?persona_key=marc",
        headers={"Accept-Language": "en"},
        json={"mcp_exposed": True},
    )
    assert mcp_en.status_code == 422
    assert "DRAFT status" in mcp_en.json()["detail"]

    # 3. Mon Assistant @agent invocation on DRAFT agent returns HTTP 422
    turn_draft = client.post(
        "/api/v1/assistant/turns?persona_key=marc",
        headers={"Accept-Language": "en"},
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "user_prompt": "Please ask @brouillon-securite to review the API.",
        },
    )
    assert turn_draft.status_code == 422, turn_draft.text
    assert turn_draft.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    # 4. Mes Processus workflow save/run referencing DRAFT agent returns HTTP 422
    wf_res = client.get("/api/v1/workflows/v2")
    assert wf_res.status_code == 200
    base_wf = wf_res.json()["items"][0]
    draft_wf = {
        **base_wf,
        "id": "wf-draft-guard-test",
        "slug": "wf-draft-guard-test",
        "allowed_delegate_agents": ["brouillon-securite"],
    }
    save_draft_wf = client.put(
        "/api/v1/workflows/v2/wf-draft-guard-test?persona_key=marc",
        json={"workflow": draft_wf, "publish": False},
    )
    assert save_draft_wf.status_code == 422, save_draft_wf.text
    assert save_draft_wf.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    # 5. Execute Test Bench -> agent transitions to PASSED & ACTIVE
    exec_res = client.post(
        "/api/v1/agents-and-skills/agents/agent-brouillon-securite/execute?persona_key=marc",
        json={"prompt": "Confirm readiness"},
    )
    assert exec_res.status_code == 200, exec_res.text
    assert exec_res.json()["test_bench_status"] == "PASSED"
    assert exec_res.json()["lifecycle_status"] == "ACTIVE"

    # 6. Now MCP exposure, Assistant @agent, and Process save all succeed!
    mcp_ok = client.patch(
        "/api/v1/agents-and-skills/agents/agent-brouillon-securite/governance?persona_key=marc",
        json={"mcp_exposed": True},
    )
    assert mcp_ok.status_code == 200, mcp_ok.text
    assert mcp_ok.json()["mcp_exposed"] is True

    turn_ok = client.post(
        "/api/v1/assistant/turns?persona_key=marc",
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "user_prompt": "Please ask @brouillon-securite to review the API.",
        },
    )
    assert turn_ok.status_code == 202, turn_ok.text

    save_ok_wf = client.put(
        "/api/v1/workflows/v2/wf-draft-guard-test?persona_key=marc",
        json={"workflow": draft_wf, "publish": False},
    )
    assert save_ok_wf.status_code == 200, save_ok_wf.text


def test_execute_agent_endpoint_persists_failed_bench_status_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When live LLM execution fails during Test Bench, agent records factual FAILED status."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "0")
    app = create_app()
    client = TestClient(app)

    client.post(
        "/api/v1/agents-and-skills/agents?persona_key=marc",
        json={
            "agent_id": "agent-echec-banc",
            "name": "Agent Echec Banc",
            "role_mission": "Test failure propagation",
            "instructions": "Run analysis.",
            "thinking_level": "medium",
        },
    )
    fail_exec = client.post(
        "/api/v1/agents-and-skills/agents/agent-echec-banc/execute?persona_key=marc",
        json={"prompt": "Trigger failure without configured tier model"},
    )
    assert fail_exec.status_code == 422

    listed = client.get("/api/v1/agents-and-skills").json()["agents"]
    target = next(a for a in listed if a["agent_id"] == "agent-echec-banc")
    assert target["test_bench_status"] == "FAILED"
    assert target["test_bench_validated"] is False
    assert target["lifecycle_status"] == "DRAFT"

    # P0-1: forbid client self-promotion of test_bench_status / activation on FAILED agent
    forbid_bench = client.post(
        "/api/v1/agents-and-skills/agents?persona_key=marc",
        json={
            "agent_id": "agent-echec-banc",
            "name": "Agent Echec Banc",
            "role_mission": "Test failure propagation",
            "instructions": "Run analysis.",
            "test_bench_status": "PASSED",
        },
    )
    assert forbid_bench.status_code == 422

    forbid_gov_bench = client.patch(
        "/api/v1/agents-and-skills/agents/agent-echec-banc/governance?persona_key=marc",
        json={"test_bench_validated": True},
    )
    assert forbid_gov_bench.status_code == 422

    forbid_activate_failed = client.patch(
        "/api/v1/agents-and-skills/agents/agent-echec-banc/governance?persona_key=marc",
        json={"lifecycle_status": "ACTIVE"},
    )
    assert forbid_activate_failed.status_code == 422
    assert forbid_activate_failed.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"


def test_p0_3_and_p1_2_draft_agent_blocked_in_reflexive_mcp_substeps_and_validation_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify DRAFT block across reflexive, PUT /mcp/exposure, workflow sub-steps & validation."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    app = create_app()
    client = TestClient(app)

    client.post(
        "/api/v1/agents-and-skills/agents?persona_key=marc",
        json={
            "agent_id": "agent-draft-guard-2",
            "name": "Draft Guard Two",
            "role_mission": "Verify all execution entry points",
            "instructions": "Check controls.",
        },
    )

    # P1-2: whitespace prompt validation error (422) does NOT flip UNTESTED -> FAILED
    bad_prompt = client.post(
        "/api/v1/agents-and-skills/agents/agent-draft-guard-2/execute?persona_key=marc",
        json={"prompt": "   "},
    )
    assert bad_prompt.status_code == 422
    ag_after_bad = next(
        a
        for a in client.get("/api/v1/agents-and-skills").json()["agents"]
        if a["agent_id"] == "agent-draft-guard-2"
    )
    assert ag_after_bad["test_bench_status"] == "UNTESTED"

    # P0-3a: POST /api/v1/executions/reflexive rejects DRAFT actor_slug / delegate
    reflexive_resp = client.post(
        "/api/v1/executions/reflexive?persona_key=marc",
        json={
            "actor_slug": "draft-guard-2",
            "objective": "Run reflexive verification",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "initial_resources": ["workspace://docs/readme.md"],
        },
    )
    assert reflexive_resp.status_code == 422
    assert reflexive_resp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    # P0-3b: PUT /api/v1/mcp/exposure rejects DRAFT agent_slug when mcp_exposed=True
    mcp_put = client.put(
        "/api/v1/mcp/exposure?persona_key=marc",
        json={
            "workspace_slug": "global",
            "agent_slug": "draft-guard-2",
            "display_name": "Draft Guard Two",
            "mcp_exposed": True,
        },
    )
    assert mcp_put.status_code == 422
    assert mcp_put.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    # P0-3c: workflow sub_steps[].instruction_prompt_or_ref & knowledge_feedback_target_agent
    base_wf = client.get("/api/v1/workflows/v2").json()["items"][0]
    wf_sub = {
        **base_wf,
        "id": "wf-substep-draft-guard",
        "slug": "wf-substep-draft-guard",
        "knowledge_feedback_target_agent": "draft-guard-2",
    }
    wf_put = client.put(
        "/api/v1/workflows/v2/wf-substep-draft-guard?persona_key=marc",
        json={"workflow": wf_sub, "publish": False},
    )
    assert wf_put.status_code == 422
    assert wf_put.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"
