"""Sécurité — Authentification obligatoire hors environnement local / test (BUG-E2E-04).

Invariants vérifiés :
- Hors `ORCIA_ENV` ∈ {`local`, `test`}, toute requête sans `Authorization: Bearer` est rejetée en
  `401 ERR_AUTH_REQUIRED` (RFC 9457), même avec un `persona_key` (aucune usurpation).
- Un jeton Bearer valide reste accepté hors environnement local.
- Au démarrage, la plateforme ne sème aucune notification fictive (zéro donnée fictive).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from orcia_core.permissions import persona_impersonation_allowed


def _build_client(monkeypatch: pytest.MonkeyPatch, orcia_env: str) -> TestClient:
    monkeypatch.setenv("ORCIA_ENV", orcia_env)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.delenv("ORCIA_E2E_SEED_FIXTURES", raising=False)
    from orcia_api.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture
def production_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    with _build_client(monkeypatch, "production") as client:
        yield client


@pytest.fixture
def local_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    with _build_client(monkeypatch, "local") as client:
        yield client


@pytest.mark.parametrize(
    ("orcia_env", "allowed"),
    [
        ("local", True),
        ("test", True),
        (" LOCAL ", True),
        ("", True),
        ("staging", False),
        ("production", False),
        ("prod", False),
    ],
)
def test_persona_impersonation_is_only_allowed_in_local_and_test(
    orcia_env: str, allowed: bool
) -> None:
    assert persona_impersonation_allowed(orcia_env) is allowed


def test_missing_bearer_is_rejected_outside_local(production_client: TestClient) -> None:
    res = production_client.get("/api/v1/inbox/notifications")
    assert res.status_code == 401, res.text
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["error_code"] == "ERR_AUTH_REQUIRED"
    assert len(body["trace_id"]) == 32


def test_persona_key_cannot_impersonate_admin_outside_local(
    production_client: TestClient,
) -> None:
    res = production_client.get("/api/v1/inbox/notifications?persona_key=karim")
    assert res.status_code == 401, res.text
    assert res.json()["error_code"] == "ERR_AUTH_REQUIRED"


def test_valid_bearer_is_accepted_outside_local(production_client: TestClient) -> None:
    auth_service = production_client.app.state.auth_service  # type: ignore[attr-defined]
    marc = auth_service.get_user_by_id("0192c4e0-0000-7000-8000-000000000603")
    tokens = auth_service._issue_for_user(marc, "LOCAL", None)
    res = production_client.get(
        "/api/v1/inbox/notifications",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert res.status_code == 200, res.text


def test_local_dev_mode_still_allows_persona_selection(local_client: TestClient) -> None:
    res = local_client.get("/api/v1/inbox/notifications?persona_key=nadia")
    assert res.status_code == 200, res.text


def test_startup_seeds_no_fictional_notifications(local_client: TestClient) -> None:
    res = local_client.get("/api/v1/inbox/notifications?persona_key=marc")
    assert res.status_code == 200, res.text
    assert res.json()["items"] == []
