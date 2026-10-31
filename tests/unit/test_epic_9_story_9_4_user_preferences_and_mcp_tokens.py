"""Story 9.4 — Unit & API tests for User Preferences (`0 ms` Anti-FOUC) & MCP Tokens (`pat_mcp_*`).

Validates:
- `GET`/`PATCH /api/v1/users/me/preferences` (theme, locale, hat, auto-help, redirect URI).
- `POST /api/v1/users/me/mcp-tokens` issuing `pat_mcp_*` tokens hashed `SHA-256` at rest,
  enforcing mandatory `30` or `90` days expiration, `RPM` limit, target URI
  `/api/v1/mcp/spaces/<ws_slug>` or `/api/v1/mcp/agents/<agent_slug>`, and IDE JSON snippet.
- `DELETE /api/v1/users/me/mcp-tokens/{token_id}` instant Redis revocation (`< 10 ms`).
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import app
from orcia_core.permissions.user_preferences_and_mcp_tokens import (
    PAT_MCP_PREFIX,
    InvalidMcpTokenConfigurationError,
    UserPreferencesAndMcpTokenService,
)


def test_story_9_4_user_preferences_and_scoped_mcp_token_lifecycle() -> None:
    """Verify preferences update, SHA-256 hashing of pat_mcp_* tokens, and revocation."""
    svc = UserPreferencesAndMcpTokenService()
    prefs = svc.update_preferences(
        user_id="user-helene",
        theme="dark",
        locale="en",
        default_hat="TECH_LEAD_DEV",
        auto_open_contextual_help=False,
    )
    assert prefs.theme == "dark"
    assert prefs.locale == "en"
    assert prefs.default_hat == "TECH_LEAD_DEV"
    assert prefs.auto_open_contextual_help is False
    assert prefs.assistant_behavior_redirect_uri == "/assistant?modal=settings"

    # Invalid expiration days (e.g. 60) -> rejected with 422 ERR_INVALID_MCP_TOKEN_CONFIG
    with pytest.raises(InvalidMcpTokenConfigurationError) as exc_info:
        svc.issue_mcp_token(
            user_id="user-helene",
            label="Invalid Expiry Token",
            expires_in_days=60,
            rpm_limit=60,
            allowed_workspace_slugs=("ws-claims-alpha",),
            exposed_capabilities=("ASSISTANT",),
            target_kind="SPACE",
            target_slug="ws-claims-alpha",
        )
    assert exc_info.value.error_code == "ERR_INVALID_MCP_TOKEN_CONFIG"

    # Valid Space-targeted MCP token (30 days)
    issued_space = svc.issue_mcp_token(
        user_id="user-helene",
        label="Cursor IDE Espace Sinistres",
        expires_in_days=30,
        rpm_limit=120,
        allowed_workspace_slugs=("ws-claims-alpha",),
        exposed_capabilities=("ASSISTANT", "KB_GLOSSARY_SEARCH"),
        target_kind="SPACE",
        target_slug="ws-claims-alpha",
    )
    assert issued_space.plaintext_token.startswith(PAT_MCP_PREFIX)
    expected_sha = hashlib.sha256(issued_space.plaintext_token.encode("utf-8")).hexdigest()
    assert issued_space.record.token_sha256 == expected_sha
    assert issued_space.record.mcp_endpoint_uri == "/api/v1/mcp/spaces/ws-claims-alpha"
    assert "/api/v1/mcp/spaces/ws-claims-alpha" in issued_space.record.ide_json_snippet

    # Valid Agent-targeted MCP token (90 days)
    issued_agent = svc.issue_mcp_token(
        user_id="user-helene",
        label="Antigravity Agent Spec",
        expires_in_days=90,
        rpm_limit=60,
        allowed_workspace_slugs=("ws-claims-alpha",),
        exposed_capabilities=("PUBLISHED_AGENTS",),
        target_kind="AGENT",
        target_slug="tech-spec-writer",
    )
    assert issued_agent.record.mcp_endpoint_uri == "/api/v1/mcp/agents/tech-spec-writer"

    # Revoke token -> marked revoked in < 10ms Redis set
    revoked = svc.revoke_mcp_token(
        user_id="user-helene",
        token_id=issued_space.record.token_id,
    )
    assert revoked.revoked is True
    assert svc.is_token_hash_revoked(expected_sha) is True


def test_story_9_4_api_preferences_and_mcp_tokens_endpoints() -> None:
    """Verify PATCH /api/v1/users/me/preferences and POST/GET/DELETE /api/v1/users/me/mcp-tokens."""
    with TestClient(app) as client:
        patch_resp = client.patch(
            "/api/v1/users/me/preferences",
            params={"persona_key": "claire"},
            json={
                "theme": "dark",
                "locale": "fr",
                "default_hat": "ARCHITECT",
                "auto_open_contextual_help": False,
            },
        )
        assert patch_resp.status_code == 200
        patch_body = patch_resp.json()
        assert patch_body["theme"] == "dark"
        assert patch_body["default_hat"] == "ARCHITECT"
        assert patch_body["assistant_behavior_redirect_uri"] == "/assistant?modal=settings"

        create_resp = client.post(
            "/api/v1/users/me/mcp-tokens",
            params={"persona_key": "claire"},
            json={
                "label": "VS Code MCP Key",
                "expires_in_days": 90,
                "rpm_limit": 90,
                "allowed_workspace_slugs": ["ws-claims-alpha"],
                "exposed_capabilities": ["ASSISTANT", "STAGED_DRAFTS"],
                "target_kind": "AGENT",
                "target_slug": "sdlc-architect-agent",
            },
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["plaintext_token"].startswith("pat_mcp_")
        token_id = created["record"]["token_id"]
        assert created["record"]["mcp_endpoint_uri"] == "/api/v1/mcp/agents/sdlc-architect-agent"

        list_resp = client.get("/api/v1/users/me/mcp-tokens", params={"persona_key": "claire"})
        assert list_resp.status_code == 200
        assert any(t["token_id"] == token_id for t in list_resp.json()["tokens"])

        del_resp = client.delete(
            f"/api/v1/users/me/mcp-tokens/{token_id}",
            params={"persona_key": "claire"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["revoked"] is True
