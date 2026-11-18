"""Story 20.3 — Unit tests for User Preferences & Personal IDE/MCP Tokens (coverage >= 90%)."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap._internal.sql_user_preferences import SqlUserPreferencesAndMcpService
from orcia_core.permissions.user_preferences_and_mcp_tokens import (
    PAT_MCP_PREFIX,
    InvalidMcpTokenConfigurationError,
    UserPreferencesAndMcpTokenService,
    build_ide_mcp_json_snippet,
    build_mcp_target_uri,
    decode_mcp_scopes_list,
    encode_mcp_scopes_list,
)
from orcia_kernel.errors import ResourceNotFoundError


def test_story_20_3_domain_preferences_personalization_and_mcp_helpers() -> None:
    svc = UserPreferencesAndMcpTokenService()
    defaults = svc.get_preferences("u-martin")
    assert defaults.theme == "light"
    assert defaults.locale == "fr"
    assert defaults.default_assistant_hat == "ANALYST_PM_PO"
    assert defaults.assistant_tone == "balanced"
    assert defaults.personal_instructions == ""

    updated = svc.update_preferences(
        user_id="u-martin",
        theme="dark",
        locale="en",
        default_assistant_hat="ARCHITECT",
        assistant_tone="concise",
        personal_instructions="Toujours citer les ADR.",
        auto_open_contextual_help=False,
        notifications_enabled=False,
    )
    assert updated.theme == "dark"
    assert updated.locale == "en"
    assert updated.default_hat == "ARCHITECT"
    assert updated.default_assistant_hat == "ARCHITECT"
    assert updated.assistant_tone == "concise"
    assert updated.personal_instructions == "Toujours citer les ADR."
    assert updated.auto_open_contextual_help is False
    assert updated.notifications_enabled is False

    # Validate MCP scope encoding/decoding and helper errors
    encoded = encode_mcp_scopes_list(("ws-a", "ws-b"), ("ASSISTANT", "STAGED_DRAFTS"))
    ws, caps = decode_mcp_scopes_list(encoded)
    assert ws == ("ws-a", "ws-b")
    assert caps == ("ASSISTANT", "STAGED_DRAFTS")
    assert build_mcp_target_uri("SPACE", "/ws-a/") == "/api/v1/mcp/spaces/ws-a"
    assert build_mcp_target_uri("AGENT", "spec-agent") == "/api/v1/mcp/agents/spec-agent"
    assert "orcia-test" in build_ide_mcp_json_snippet(
        server_key="orcia-test", mcp_endpoint_uri="/api/v1/mcp/spaces/ws-a"
    )

    with pytest.raises(InvalidMcpTokenConfigurationError):
        build_mcp_target_uri("SPACE", "   ")
    with pytest.raises(InvalidMcpTokenConfigurationError):
        svc.issue_mcp_token(
            user_id="u-martin",
            label="Bad RPM",
            expires_in_days=30,
            rpm_limit=0,
            allowed_workspace_slugs=("ws-a",),
            exposed_capabilities=("ASSISTANT",),
            target_kind="SPACE",
            target_slug="ws-a",
        )
    with pytest.raises(InvalidMcpTokenConfigurationError):
        svc.issue_mcp_token(
            user_id="u-martin",
            label="No WS",
            expires_in_days=30,
            rpm_limit=60,
            allowed_workspace_slugs=(),
            exposed_capabilities=("ASSISTANT",),
            target_kind="SPACE",
            target_slug="ws-a",
        )
    with pytest.raises(InvalidMcpTokenConfigurationError):
        svc.issue_mcp_token(
            user_id="u-martin",
            label="No Cap",
            expires_in_days=30,
            rpm_limit=60,
            allowed_workspace_slugs=("ws-a",),
            exposed_capabilities=(),
            target_kind="SPACE",
            target_slug="ws-a",
        )

    issued = svc.issue_mcp_token(
        user_id="u-martin",
        label="Cursor IDE",
        expires_in_days=30,
        rpm_limit=120,
        allowed_workspace_slugs=("ws-a",),
        exposed_capabilities=("ASSISTANT",),
        target_kind="SPACE",
        target_slug="ws-a",
    )
    assert issued.plaintext_token.startswith(PAT_MCP_PREFIX)
    assert issued.plaintext_token != "pat_mcp_9a8b7c6d5e4f3a2b1c0d"
    assert len(issued.record.token_prefix) <= 24
    expected_sha = hashlib.sha256(issued.plaintext_token.encode("utf-8")).hexdigest()
    assert issued.record.token_sha256 == expected_sha
    assert len(svc.list_user_mcp_tokens("u-martin")) == 1
    assert svc.list_user_mcp_tokens("u-other") == ()

    with pytest.raises(ResourceNotFoundError):
        svc.revoke_mcp_token(user_id="u-other", token_id=issued.record.token_id)

    revoked = svc.revoke_mcp_token(user_id="u-martin", token_id=issued.record.token_id)
    assert revoked.revoked is True
    assert svc.is_token_hash_revoked(expected_sha) is True


@pytest.mark.asyncio
async def test_story_20_3_sql_service_fallback_mode_without_engine() -> None:
    sql_svc = SqlUserPreferencesAndMcpService(engine=None)
    prefs = await sql_svc.get_preferences("u-fallback")
    assert prefs.theme == "light"
    updated = await sql_svc.update_preferences(
        user_id="u-fallback",
        theme="system",
        default_assistant_hat="TECH_LEAD_DEV",
        assistant_tone="detailed",
        personal_instructions="Réponses techniques détaillées.",
    )
    assert updated.theme == "system"
    assert updated.default_assistant_hat == "TECH_LEAD_DEV"
    assert updated.assistant_tone == "detailed"

    issued = await sql_svc.issue_mcp_token(
        user_id="u-fallback",
        label="Claude Code",
        expires_in_days=90,
        rpm_limit=90,
        allowed_workspace_slugs=("ws-alpha",),
        exposed_capabilities=("ASSISTANT", "KB_GLOSSARY_SEARCH"),
        target_kind="AGENT",
        target_slug="arch-agent",
    )
    listed = await sql_svc.list_user_mcp_tokens("u-fallback")
    assert len(listed) == 1
    revoked = await sql_svc.revoke_mcp_token(user_id="u-fallback", token_id=issued.record.token_id)
    assert revoked.revoked is True


def test_story_20_3_api_router_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    with TestClient(app) as client:
        get_resp = client.get("/api/v1/users/me/preferences", params={"persona_key": "claire"})
        assert get_resp.status_code == 200
        assert get_resp.json()["default_assistant_hat"] == "ANALYST_PM_PO"

        patch_resp = client.patch(
            "/api/v1/users/me/preferences",
            params={"persona_key": "claire"},
            json={
                "theme": "dark",
                "locale": "en",
                "default_assistant_hat": "SECURITY_COMPLIANCE",
                "assistant_tone": "concise",
                "personal_instructions": "Focus sur RGPD et sécurité.",
                "notifications_enabled": False,
            },
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["theme"] == "dark"
        assert body["locale"] == "en"
        assert body["default_assistant_hat"] == "SECURITY_COMPLIANCE"
        assert body["assistant_tone"] == "concise"
        assert body["personal_instructions"] == "Focus sur RGPD et sécurité."
        assert body["notifications_enabled"] is False
