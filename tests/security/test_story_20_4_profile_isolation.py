"""Story 20.4 — Security tests for `/api/v1/users/me/profile-summary`."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import UserIdentity


def _build_client(monkeypatch: pytest.MonkeyPatch, *, orcia_env: str) -> TestClient:
    monkeypatch.setenv("ORCIA_ENV", orcia_env)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service
    alice = UserIdentity(
        id="0195f000-0000-7000-8000-000000002401",
        email="alice.20.4@orcia.ia",
        display_name="Alice Profile",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="team-1",
        roles=("CONTRIBUTOR",),
    )
    bob = UserIdentity(
        id="0195f000-0000-7000-8000-000000002402",
        email="bob.20.4@orcia.ia",
        display_name="Bob Profile",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="BU_LEAD",
        primary_org_unit_id="team-2",
        roles=("BU_LEAD",),
    )
    for key, user in (("alice204", alice), ("bob204", bob)):
        svc.register_user(user)
        svc._persona_map[key] = user.id  # noqa: SLF001
    return TestClient(app, raise_server_exceptions=False)


def test_profile_summary_rejects_unauthenticated_outside_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _build_client(monkeypatch, orcia_env="production") as client:
        unauth = client.get("/api/v1/users/me/profile-summary")
        assert unauth.status_code == 401
        assert unauth.headers["content-type"].startswith("application/problem+json")
        assert unauth.json()["error_code"] == "ERR_AUTH_REQUIRED"

        # Persona impersonation blocked outside local/test
        impersonate = client.get("/api/v1/users/me/profile-summary?persona_key=bob204")
        assert impersonate.status_code == 401


def test_profile_summary_ignores_client_user_id_anti_idor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _build_client(monkeypatch, orcia_env="production") as client:
        svc = client.app.state.auth_service  # type: ignore[attr-defined]
        alice = svc.get_user_by_id("0195f000-0000-7000-8000-000000002401")
        tokens = svc._issue_for_user(alice, "LOCAL", None)  # noqa: SLF001

        # Even if attacker passes ?user_id=<bob_id>, endpoint strictly returns Alice's profile
        res = client.get(
            "/api/v1/users/me/profile-summary",
            params={"user_id": "0195f000-0000-7000-8000-000000002402"},
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["user_id"] == alice.id
        assert body["email"] == alice.email
        assert body["display_name"] == "Alice Profile"
        assert body["roles"] == ["CONTRIBUTOR"]
