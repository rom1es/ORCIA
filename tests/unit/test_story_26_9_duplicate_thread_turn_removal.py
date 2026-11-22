"""Story 26.9 — TDD Unit Tests: Duplicate Thread Turn Route Removal & Canonical Turn/History API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app


def _seed_ws_and_thread(client: TestClient) -> tuple[str, str]:
    ws_resp = client.post(
        "/api/v1/workspaces",
        params={"persona_key": "karim"},
        json={
            "name": "Story 26.9 Workspace",
            "slug": "ws-story-26-9",
            "owner_org_unit_id": "0192c4e0-0000-7000-8000-000000000103",
        },
    )
    assert ws_resp.status_code in (200, 201), ws_resp.text
    ws_id = str(ws_resp.json()["id"])

    thread_resp = client.post(
        "/api/v1/assistant/threads",
        params={"persona_key": "karim"},
        json={"workspace_id": ws_id, "title": "Story 26.9 Thread"},
    )
    assert thread_resp.status_code == 200, thread_resp.text
    return ws_id, str(thread_resp.json()["thread_id"])


def test_duplicate_threads_turns_route_is_deleted_and_canonical_turns_messages_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`POST /threads/{id}/turns` must return 404/405 while `POST /turns` & `GET /messages` work."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    with TestClient(app) as client:
        ws_id, thread_id = _seed_ws_and_thread(client)

        legacy_res = client.post(
            f"/api/v1/assistant/threads/{thread_id}/turns",
            params={"persona_key": "karim"},
            json={"workspace_id": ws_id, "message_text": "Should fail"},
        )
        assert legacy_res.status_code in (404, 405), legacy_res.text

        turn1 = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "karim"},
            json={
                "workspace_id": ws_id,
                "thread_id": thread_id,
                "user_prompt": "First speed 1 prompt",
                "requested_speed": "SPEED_1_FAST",
            },
        )
        assert turn1.status_code == 202, turn1.text
        t1_id = str(turn1.json()["turn_id"])

        stream1 = client.get(turn1.json()["stream_url"], params={"persona_key": "karim"})
        assert stream1.status_code == 200
        assert "event: turn_completed" in stream1.text

        deepen = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "karim"},
            json={
                "workspace_id": ws_id,
                "thread_id": thread_id,
                "parent_turn_id": t1_id,
                "user_prompt": "First speed 1 prompt",
                "requested_speed": "SPEED_2_AGENT_TOOLS",
            },
        )
        assert deepen.status_code == 202, deepen.text
        assert deepen.json()["parent_turn_id"] == t1_id

        stream2 = client.get(deepen.json()["stream_url"], params={"persona_key": "karim"})
        assert stream2.status_code == 200
        assert "event: turn_completed" in stream2.text

        msgs = client.get(
            f"/api/v1/assistant/threads/{thread_id}/messages",
            params={"persona_key": "karim", "workspace_id": ws_id},
        )
        assert msgs.status_code == 200, msgs.text
        assert msgs.json()["thread_id"] == thread_id


def test_send_collaborative_thread_turn_schemas_and_openapi_path_removed() -> None:
    """Removed route and schemas must not remain in `orcia_api.schemas` or FastAPI OpenAPI."""
    import orcia_api.schemas.assistant_citations_and_folders as folder_schemas

    assert not hasattr(folder_schemas, "SendCollaborativeThreadTurnRequest")
    assert not hasattr(folder_schemas, "SendCollaborativeThreadTurnResponse")
    app = create_app()
    schema = app.openapi()
    assert "/api/v1/assistant/threads/{thread_id}/turns" not in schema.get("paths", {})
