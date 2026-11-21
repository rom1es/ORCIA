"""Unit tests for idempotent `GET /api/v1/auth/session` bootstrap vs strict `POST /refresh`."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.permissions import DEFAULT_TOTP_SECRET_KARIM, TotpManager


def _login_karim(client: TestClient) -> str:
    totp_code = TotpManager.generate_code(DEFAULT_TOTP_SECRET_KARIM)
    login = client.post(
        "/api/v1/auth/login/local",
        json={
            "email": "karim.admin@orcia.io",
            "password": "OrciaAdmin!2026",  # pragma: allowlist secret
            "totp_code": totp_code,
        },
    )
    assert login.status_code == 200
    refresh_cookie = login.cookies.get("orcia_refresh_token")
    assert refresh_cookie is not None
    return refresh_cookie


@pytest.mark.asyncio
async def test_concurrent_session_bootstrap_calls_preserve_refresh_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent `GET /api/v1/auth/session` requests must never revoke each other."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    totp_code = TotpManager.generate_code(DEFAULT_TOTP_SECRET_KARIM)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        login = await async_client.post(
            "/api/v1/auth/login/local",
            json={
                "email": "karim.admin@orcia.io",
                "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                "totp_code": totp_code,
            },
        )
        assert login.status_code == 200
        raw_refresh = login.cookies.get("orcia_refresh_token")
        assert raw_refresh is not None

        res1, res2 = await asyncio.gather(
            async_client.get("/api/v1/auth/session", headers={"X-Refresh-Token": raw_refresh}),
            async_client.get("/api/v1/auth/session", headers={"X-Refresh-Token": raw_refresh}),
        )

    assert res1.status_code == 200
    assert res2.status_code == 200
    body1 = res1.json()
    body2 = res2.json()
    assert body1["authenticated"] is True
    assert body2["authenticated"] is True
    assert body1["session"]["access_token"]
    assert body2["session"]["access_token"]
    assert "Max-Age=0" not in res1.headers.get("set-cookie", "")
    assert "Max-Age=0" not in res2.headers.get("set-cookie", "")


def test_session_bootstrap_rejects_revoked_refresh_after_refresh_rotation_or_logout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict `POST /refresh` rotation and `POST /logout` revoke the token for `GET /session`."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)
    first_refresh = _login_karim(client)

    rotated = client.post("/api/v1/auth/refresh", headers={"X-Refresh-Token": first_refresh})
    assert rotated.status_code == 200
    second_refresh = rotated.cookies.get("orcia_refresh_token")
    assert second_refresh is not None
    assert second_refresh != first_refresh

    stale_session = client.get("/api/v1/auth/session", headers={"X-Refresh-Token": first_refresh})
    assert stale_session.status_code == 200
    assert stale_session.json()["authenticated"] is False
    assert stale_session.json()["session"] is None
    assert "Max-Age=0" in stale_session.headers.get("set-cookie", "")

    valid_session = client.get("/api/v1/auth/session", headers={"X-Refresh-Token": second_refresh})
    assert valid_session.status_code == 200
    assert valid_session.json()["authenticated"] is True

    logout_res = client.post("/api/v1/auth/logout", headers={"X-Refresh-Token": second_refresh})
    assert logout_res.status_code == 200

    post_logout_session = client.get(
        "/api/v1/auth/session", headers={"X-Refresh-Token": second_refresh}
    )
    assert post_logout_session.status_code == 200
    assert post_logout_session.json()["authenticated"] is False
    assert "Max-Age=0" in post_logout_session.headers.get("set-cookie", "")
