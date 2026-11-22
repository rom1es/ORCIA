"""Story 23.2 (Sécurité) — Fail-closed 401/403 guards on SSE endpoints under ORCIA_ENV=e2e."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.main import create_app


@pytest.mark.asyncio
async def test_story_23_2_sse_and_reflexive_endpoints_reject_anon_and_persona_in_e2e(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under ORCIA_ENV=e2e, SSE & smoke endpoints reject anon/persona impersonation with 401."""
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-23-2-sec-jwt-0001")

    app = create_app()
    assert app.dependency_overrides == {}

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        for auth_params, auth_headers in (
            ({}, {}),
            ({"persona_key": "karim"}, {"X-Orcia-Persona": "karim"}),
        ):
            r_events = await client.get(
                "/api/v1/events/stream",
                params={"workspace_id": "0195f000-0000-7000-8000-000000000301", **auth_params},
                headers=auth_headers,
            )
            assert r_events.status_code == 401
            assert r_events.json()["error_code"] == "ERR_AUTH_REQUIRED"
            assert r_events.headers["content-type"].startswith("application/problem+json")

            r_inspect = await client.get(
                "/api/v1/sources/inspect-lines",
                params={
                    "uri": "docs/product/capabilities.yaml",
                    "start_line": 1,
                    "end_line": 10,
                    **auth_params,
                },
                headers=auth_headers,
            )
            assert r_inspect.status_code == 401
            assert r_inspect.json()["error_code"] == "ERR_AUTH_REQUIRED"

            r_reflexive = await client.post(
                "/api/v1/executions/reflexive",
                params=auth_params,
                headers=auth_headers,
                json={"actor_slug": "assistant-agent", "objective": "Security check"},
            )
            assert r_reflexive.status_code == 401
            assert r_reflexive.json()["error_code"] == "ERR_AUTH_REQUIRED"

            r_trace_sse = await client.get(
                "/api/v1/executions/0195f000-0000-7000-8000-000000009999/trace-stream",
                params=auth_params,
                headers=auth_headers,
            )
            assert r_trace_sse.status_code == 401
            assert r_trace_sse.json()["error_code"] == "ERR_AUTH_REQUIRED"

            r_assistant_sse = await client.post(
                "/api/v1/assistant/turns",
                params=auth_params,
                headers=auth_headers,
                json={
                    "workspace_id": "0195f000-0000-7000-8000-000000000301",
                    "user_prompt": "Bonjour",
                },
            )
            assert r_assistant_sse.status_code == 401
            assert r_assistant_sse.json()["error_code"] == "ERR_AUTH_REQUIRED"

            r_stream_unauth = await client.get(
                "/api/v1/assistant/turns/turn-nonexistent/stream",
                params=auth_params,
                headers=auth_headers,
            )
            assert r_stream_unauth.status_code == 401
            assert r_stream_unauth.json()["error_code"] == "ERR_AUTH_REQUIRED"
