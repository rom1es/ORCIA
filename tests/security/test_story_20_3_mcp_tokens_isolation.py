"""Story 20.3 — Security isolation tests for `/api/v1/users/me/mcp-tokens`."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import UserIdentity


def _build_security_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service

    alice = UserIdentity(
        id="u-alice-20-3",
        email="alice@orcia.ia",
        display_name="Alice",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="team-1",
        roles=("CONTRIBUTOR",),
    )
    bob = UserIdentity(
        id="u-bob-20-3",
        email="bob@orcia.ia",
        display_name="Bob",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="team-1",
        roles=("CONTRIBUTOR",),
    )
    observer = UserIdentity(
        id="u-obs-20-3",
        email="obs@orcia.ia",
        display_name="Observer",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="OBSERVER",
        primary_org_unit_id="team-1",
        roles=("OBSERVER",),
    )
    for key, u in (("alice", alice), ("bob", bob), ("obs", observer)):
        svc.register_user(u)
        svc._persona_map[key] = u.id  # noqa: SLF001

    return TestClient(app)


def test_story_20_3_mcp_tokens_cross_user_isolation_and_observer_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _build_security_client(monkeypatch) as client:
        # 1. OBSERVER cannot create a personal MCP token (403 ERR_OBSERVER_MODE_READ_ONLY)
        obs_create = client.post(
            "/api/v1/users/me/mcp-tokens",
            params={"persona_key": "obs"},
            json={
                "label": "Forbidden Observer Key",
                "expires_in_days": 30,
                "rpm_limit": 60,
                "allowed_workspace_slugs": ["ws-1"],
                "exposed_capabilities": ["ASSISTANT"],
                "target_kind": "SPACE",
                "target_slug": "ws-1",
            },
        )
        assert obs_create.status_code == 403
        assert obs_create.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 2. Alice creates a real random pat_mcp_* token
        alice_create = client.post(
            "/api/v1/users/me/mcp-tokens",
            params={"persona_key": "alice"},
            json={
                "label": "Alice Cursor Key",
                "expires_in_days": 30,
                "rpm_limit": 60,
                "allowed_workspace_slugs": ["ws-1"],
                "exposed_capabilities": ["ASSISTANT"],
                "target_kind": "SPACE",
                "target_slug": "ws-1",
            },
        )
        assert alice_create.status_code == 201
        created = alice_create.json()
        plaintext = created["plaintext_token"]
        token_id = created["record"]["token_id"]
        assert plaintext.startswith("pat_mcp_")
        assert plaintext != "pat_mcp_9a8b7c6d5e4f3a2b1c0d"

        # 3. GET /users/me/mcp-tokens NEVER leaks plaintext_token and is scoped to user_id
        alice_list = client.get("/api/v1/users/me/mcp-tokens", params={"persona_key": "alice"})
        assert alice_list.status_code == 200
        assert plaintext not in alice_list.text
        assert len(alice_list.json()["tokens"]) == 1

        bob_list = client.get("/api/v1/users/me/mcp-tokens", params={"persona_key": "bob"})
        assert bob_list.status_code == 200
        assert bob_list.json()["tokens"] == []

        # 4. Bob cannot revoke Alice's token (strict user_id isolation -> 404)
        bob_delete = client.delete(
            f"/api/v1/users/me/mcp-tokens/{token_id}",
            params={"persona_key": "bob"},
        )
        assert bob_delete.status_code == 404

        # 5. READ_ONLY_OBSERVER header cannot revoke even with non-observer persona
        header_obs_delete = client.delete(
            f"/api/v1/users/me/mcp-tokens/{token_id}",
            params={"persona_key": "alice"},
            headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
        )
        assert header_obs_delete.status_code == 403
        assert header_obs_delete.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
