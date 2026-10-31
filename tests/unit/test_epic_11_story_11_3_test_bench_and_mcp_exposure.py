"""Unit & API contract tests for Story 11.3 (4-Step Test Bench & 7-Lock Governed MCP Server)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
)
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)


def test_four_step_test_bench_anti_ssrf_and_passthrough_non_blocking() -> None:
    """Verify Anti-SSRF blocking, non-blocking Passthrough step 2, and Dry-Run limits."""
    svc = RemoteServiceTestBenchAndGovernedMcpService()

    # Step 1 blocks private / metadata IP (169.254.169.254)
    ssrf_res = svc.test_and_discover_remote_service(
        actor_role="PLATFORM_ADMIN",
        protocol="MCP_STREAMABLE_HTTP_SSE",
        endpoint_url="http://169.254.169.254/latest/meta-data",
        identity_mode="PASSTHROUGH",
    )
    assert ssrf_res.steps[0].status == "FAIL"
    assert ssrf_res.can_activate is False

    # Passthrough without personal token: Step 2 is WAITING_USER_PASSTHROUGH_TOKEN, can_activate
    pass_res = svc.test_and_discover_remote_service(
        actor_role="PLATFORM_ADMIN",
        protocol="MCP_STREAMABLE_HTTP_SSE",
        endpoint_url="https://mcp.partner.io/sse",
        identity_mode="PASSTHROUGH",
        has_user_personal_token=False,
        raw_tool_names=["get_customer", "update_ticket"],
    )
    assert pass_res.steps[0].status == "PASS"
    assert pass_res.steps[1].status == "WAITING_USER_PASSTHROUGH_TOKEN"
    assert pass_res.steps[2].status == "PASS"
    assert pass_res.can_activate is True
    assert pass_res.discovered_capabilities[0].qualification == "READ_ONLY"
    assert pass_res.discovered_capabilities[1].qualification == "WRITE_STAGED_REQUIRED"
    assert pass_res.dry_run_audit_actor_type == "ADMIN_CONNECTION_TEST"

    # Dry-run timeout > 5000 ms fails Step 4
    timeout_res = svc.test_and_discover_remote_service(
        actor_role="PLATFORM_ADMIN",
        protocol="OPENAPI_3_1_REST",
        endpoint_url="https://api.partner.io/openapi.json",
        identity_mode="SECRET_REF",
        secret_ref_valid=True,
        simulated_dry_run_elapsed_ms=6200.0,
    )
    assert timeout_res.steps[3].status == "FAIL"
    assert timeout_res.can_activate is False


def test_governed_mcp_seven_hardware_security_locks() -> None:
    """Verify the 7 Hardware Security Locks on `/api/v1/mcp` (`execute != read`, `AD-3`, `AD-6`)."""
    svc = RemoteServiceTestBenchAndGovernedMcpService()
    pat = "pat_mcp_ide_token_001"  # pragma: allowlist secret
    svc.register_pat_mcp_token(raw_pat_token=pat, allowed_workspace_slugs={"claims-ws"})

    svc.configure_agent_mcp_exposure(
        actor_role="TEAM_LEAD",
        workspace_slug="claims-ws",
        agent_slug="triage-agent",
        display_name="Agent Triage Sinistre",
        mcp_exposed=True,
        regime="GOVERNED_STAGED_COPILOT",
        system_prompt_layers_1_to_4="CONFIDENTIAL_SYSTEM_PROMPT_L1_L4",
    )

    tools = svc.list_governed_mcp_tools(
        workspace_slug="claims-ws",
        caller_verbs={"execute"},
    )
    assert "assistant.ask" in tools
    assert "agent.triage-agent" in tools

    # Caller with `execute` but WITHOUT `read` cannot read system_prompt or restricted snippets
    res_no_read = svc.invoke_governed_mcp_tool(
        raw_pat_token=pat,
        workspace_slug="claims-ws",
        agent_slug="triage-agent",
        caller_role="CONTRIBUTOR",
        caller_verbs={"execute"},
        passthrough_identity="oidc:yanis@orcia.io",
        prompt_text="Analyse IBAN_SECRET du dossier",
        requested_write_target_uri="jira://CLAIMS-42",
    )
    assert res_no_read.system_prompt_exposed is None
    assert res_no_read.secret_refs_exposed == ()
    assert "[REDACTED_PII]" in res_no_read.sanitized_response_text
    assert "[S1 · 🔒 Source restreinte]" in res_no_read.sanitized_response_text
    assert res_no_read.staged_actions == ("STAGED_WRITE:jira://CLAIMS-42",)
    assert res_no_read.audit_actor_type == "MCP_IDE_CLIENT"
    assert res_no_read.history_badge_fr == "💻 Appelé via MCP (IDE)"

    # Lock 5: Human Anchor required raises HumanAnchorRequiredError (HTTP 422)
    svc.configure_agent_mcp_exposure(
        actor_role="TEAM_LEAD",
        workspace_slug="claims-ws",
        agent_slug="anchor-agent",
        display_name="Agent Décision Critique",
        mcp_exposed=True,
        regime="GOVERNED_STAGED_COPILOT",
        human_authored_required=True,
    )
    with pytest.raises(HumanAnchorRequiredError):
        svc.invoke_governed_mcp_tool(
            raw_pat_token=pat,
            workspace_slug="claims-ws",
            agent_slug="anchor-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="oidc:yanis@orcia.io",
            prompt_text="Valider l'indemnisation",
        )

    # Lock 5: READ_ONLY_OBSERVER rejected with HTTP 403
    with pytest.raises(ObserverModeReadOnlyError):
        svc.invoke_governed_mcp_tool(
            raw_pat_token=pat,
            workspace_slug="claims-ws",
            agent_slug="triage-agent",
            caller_role="READ_ONLY_OBSERVER",
            caller_verbs={"execute"},
            passthrough_identity="oidc:obs@orcia.io",
            prompt_text="Test",
        )

    # Lock 1: Out-of-scope workspace rejected
    with pytest.raises(ScopeAccessDeniedError):
        svc.invoke_governed_mcp_tool(
            raw_pat_token=pat,
            workspace_slug="other-ws",
            agent_slug="triage-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="oidc:yanis@orcia.io",
            prompt_text="Test",
        )


def test_story_11_3_fastapi_endpoints() -> None:
    """Verify Story 11.3 FastAPI endpoints (`/test-and-discover` & `/api/v1/mcp/*`)."""
    client = TestClient(create_app())

    resp_bench = client.post(
        "/api/v1/settings/connectors/test-and-discover",
        params={"persona_key": "karim"},
        json={
            "protocol": "MCP_STREAMABLE_HTTP_SSE",
            "endpoint_url": "https://mcp.orcia.io/sse",
            "identity_mode": "PASSTHROUGH",
            "has_user_personal_token": False,
        },
    )
    assert resp_bench.status_code == 200
    assert resp_bench.json()["can_activate"] is True
    assert resp_bench.json()["steps"][1]["status"] == "WAITING_USER_PASSTHROUGH_TOKEN"

    resp_expose = client.put(
        "/api/v1/mcp/exposure",
        params={"persona_key": "claire"},
        json={
            "workspace_slug": "claims-core",
            "agent_slug": "spec-reviewer",
            "display_name": "Agent Relecteur Spec",
            "mcp_exposed": True,
            "regime": "GOVERNED_STAGED_COPILOT",
            "pat_token_to_register": "pat_mcp_test_client_01",
        },
    )
    assert resp_expose.status_code == 200
    assert "agent.spec-reviewer" in resp_expose.json()["exposed_tools"]

    resp_invoke = client.post(
        "/api/v1/mcp/spaces/claims-core/invoke",
        params={"persona_key": "claire"},
        json={
            "raw_pat_token": "pat_mcp_test_client_01",
            "agent_slug": "spec-reviewer",
            "caller_verbs": ["execute"],
            "passthrough_identity": "oidc:claire@orcia.io",
            "prompt_text": "Relis la section 2",
        },
    )
    assert resp_invoke.status_code == 200
    assert resp_invoke.json()["audit_actor_type"] == "MCP_IDE_CLIENT"
    assert resp_invoke.json()["system_prompt_exposed"] is None
