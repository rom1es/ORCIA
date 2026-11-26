"""Unit tests for Story 30.3 HTTP routers (`workflows`, `executions_trace`) & lifespan (`AD-17`)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import (
    _init_redis_and_sse,
    _resolve_default_llm_gateway,
    should_seed_test_personas_in_memory,
)
from orcia_api.dependencies.reflexive_execution import (
    _resolve_reflexive_session_maker,
    get_assistant_reflexive_runtime_service,
    get_vsm_v2_sql_store,
    get_workflows_v2_runs_sql_store,
    get_workflows_v2_sql_store,
)
from orcia_api.main import create_app
from orcia_api.routers._workflows_pending_runs import (
    load_or_rehydrate_run_state,
    resolve_workflow_run_workspace_id,
)
from orcia_core.workflows import SqlWorkflowV2RunsStore


def test_workflows_v2_vsm_draft_whatif_runs_cold_rehydration_and_hitl_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise VSM, Studio PUT publish, What-If, PG18 pending runs, cold F5 get, & HITL signals."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")

    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/vsm").status_code == 200
        assert client.get("/api/v1/vsm/vsm-mon-compte-idea-to-prod").status_code == 200
        assert client.get("/api/v1/vsm/missing-vsm").status_code == 404
        assert client.get("/api/v1/workflows/v2/missing-wf").status_code == 404
        assert client.post("/api/v1/workflows/v2/missing-wf/what-if", json={}).status_code == 404
        assert client.post("/api/v1/workflows/v2/missing-wf/runs", json={}).status_code == 404
        assert client.get("/api/v1/runs/missing-run").status_code == 404
        assert (
            client.post(
                "/api/v1/runs/missing-run/hitl-signal",
                json={"action": "APPROVE", "actor_id": "marc"},
            ).status_code
            == 404
        )

        wf_resp = client.get("/api/v1/workflows/v2/wf-01-qualification-prd")
        assert wf_resp.status_code == 200
        wf_body = wf_resp.json()
        pub_resp = client.put(
            "/api/v1/workflows/v2/wf-01-qualification-prd",
            params={"persona_key": "marc"},
            json={"workflow": wf_body, "publish": True},
        )
        assert pub_resp.status_code == 200
        assert pub_resp.json()["forked_as_draft"] is False

        start_resp = client.post(
            "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
            params={"persona_key": "marc"},
            json={
                "inputs": {"demande_source": "MCIA-99"},
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            },
        )
        assert start_resp.status_code == 200
        run_id = start_resp.json()["run"]["run_id"]

        # Cold rehydration: clear RAM cache and fetch via GET /api/v1/runs/{run_id}
        app.state.workflow_v2_runs_store.clear()
        cold_get = client.get(f"/api/v1/runs/{run_id}")
        assert cold_get.status_code == 200
        assert cold_get.json()["run"]["run_id"] == run_id

        list_global = client.get(
            "/api/v1/workflows/v2/runs",
            params={"scope_type": "GLOBAL", "persona_key": "karim"},
        )
        assert list_global.status_code == 200
        assert any(r["run_id"] == run_id for r in list_global.json()["items"])

        ws_list = client.get(
            "/api/v1/workflows/v2/runs",
            params={"workspace_id": "0192c4e0-0000-7000-8000-000000000201", "persona_key": "marc"},
        )
        assert ws_list.status_code == 200

        for _ in range(3):
            step_sig = client.post(
                f"/api/v1/runs/{run_id}/hitl-signal",
                params={"persona_key": "marc"},
                json={"action": "APPROVE", "actor_id": "marc"},
            )
            assert step_sig.status_code == 200
            if step_sig.json()["run"]["status"] == "WAITING_FINAL_ANCHOR":
                break

        suspend = client.post(
            f"/api/v1/runs/{run_id}/hitl-signal",
            params={"persona_key": "marc"},
            json={"action": "SUSPEND_SLA", "actor_id": "marc"},
        )
        assert suspend.status_code == 200
        assert suspend.json()["run"]["status"] == "SLA_SUSPENDED"


def test_executions_trace_router_full_lifecycle_background_sse_and_write_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise POST /reflexive (sync & bg), GET, SSE stream, synthesize, cancel, approve."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/executions/missing-exec").status_code == 404
        assert client.get("/api/v1/executions/missing-exec/trace-stream").status_code == 404

        bg_resp = client.post(
            "/api/v1/executions/reflexive",
            params={"persona_key": "marc"},
            json={
                "actor_slug": "redacteur-documentation-orcia",
                "objective": "Analyse de contexte",
                "effort_mode": "approfondi",
                "run_in_background": True,
                "step_delay_ms": 50,
            },
        )
        assert bg_resp.status_code == 200
        bg_id = bg_resp.json()["execution_id"]

        assert client.get(f"/api/v1/executions/{bg_id}").status_code == 200
        synth_resp = client.post(
            f"/api/v1/executions/{bg_id}/synthesize-now",
            params={"persona_key": "marc"},
        )
        assert synth_resp.status_code == 200

        cancel_resp = client.post(
            f"/api/v1/executions/{bg_id}/cancel",
            params={"persona_key": "marc"},
        )
        assert cancel_resp.status_code == 200

        # Approve-write when NOT WAITING_WRITE_PREVIEW -> 422
        invalid_state = client.post(
            f"/api/v1/executions/{bg_id}/approve-write",
            params={"persona_key": "marc"},
            json={"preview_id": "p-1", "approved": True},
        )
        assert invalid_state.status_code == 422

        # Sync run with requested_write_preview -> WAITING_WRITE_PREVIEW
        wp_resp = client.post(
            "/api/v1/executions/reflexive",
            params={"persona_key": "marc"},
            json={
                "actor_slug": "redacteur-documentation-orcia",
                "objective": "Publier page",
                "requested_write_preview": {
                    "connector_type": "confluence",
                    "action": "publish_page",
                    "target_resource_uri": "confluence://Docs/Page",
                    "action_summary": "Publier",
                    "payload": {"title": "Doc"},
                },
            },
        )
        assert wp_resp.status_code == 200
        wp_body = wp_resp.json()
        wp_exec_id = wp_body["execution_id"]
        preview_id = wp_body["pending_write_preview"]["preview_id"]

        sse_resp = client.get(f"/api/v1/executions/{wp_exec_id}/trace-stream")
        assert sse_resp.status_code == 200
        assert "event:" in sse_resp.text

        # Mismatched preview_id -> 403
        mismatch = client.post(
            f"/api/v1/executions/{wp_exec_id}/approve-write",
            params={"persona_key": "marc"},
            json={"preview_id": "wrong-id", "approved": True},
        )
        assert mismatch.status_code == 403

        # Missing exec on approve-write -> 404
        assert (
            client.post(
                "/api/v1/executions/missing-exec/approve-write",
                params={"persona_key": "marc"},
                json={"preview_id": "p", "approved": False},
            ).status_code
            == 404
        )

        # Valid approve without explicit token (broker issues token)
        approved = client.post(
            f"/api/v1/executions/{wp_exec_id}/approve-write",
            params={"persona_key": "marc"},
            json={"preview_id": preview_id, "approved": True},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_dependencies_and_pending_runs_edge_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover gateway resolver modes, store upgrades, workspace ID normalization, & rehydration."""
    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    monkeypatch.setenv("ORCIA_LLM_GATEWAY", "cassette")
    assert getattr(_resolve_default_llm_gateway(), "is_cassette_adapter", False) is True

    monkeypatch.setenv("ORCIA_LLM_GATEWAY", "litellm_plugin")
    gw_plugin = _resolve_default_llm_gateway()
    assert gw_plugin is not None

    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    assert should_seed_test_personas_in_memory() is False
    monkeypatch.delenv("ORCIA_FORCE_REAL_RUNTIME", raising=False)
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    assert should_seed_test_personas_in_memory() is False
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_SEED_TEST_PERSONAS", "1")
    assert should_seed_test_personas_in_memory() is True

    app = FastAPI()
    app.state.sse_broker = MagicMock()
    app.state.redis_client = object()
    _init_redis_and_sse(app)
    app.state.sse_broker.set_redis_client.assert_called_once()

    fake_req = SimpleNamespace(
        app=app,
        headers={"X-Orcia-Workspace-Id": "scope-ws-0195f000-0000-7000-8000-000000000111"},
    )
    assert (
        resolve_workflow_run_workspace_id(None, fake_req)  # type: ignore[arg-type]
        == "0195f000-0000-7000-8000-000000000111"
    )
    assert (
        resolve_workflow_run_workspace_id("scope-global", fake_req)  # type: ignore[arg-type]
        is None
    )

    # Store upgrades from session_maker=None -> non-None
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    fake_engine = object()
    with patch(
        "orcia_api.dependencies.reflexive_execution.get_or_create_shared_db_engine",
        return_value=fake_engine,
    ):
        req_obj: Request = SimpleNamespace(app=app)  # type: ignore[assignment]
        app.state.workflows_v2_sql_store = MagicMock(_session_maker=None)
        app.state.vsm_v2_sql_store = MagicMock(_session_maker=None)
        app.state.workflows_v2_runs_sql_store = MagicMock(_session_maker=None)
        assert get_workflows_v2_sql_store(req_obj)._strict_sql is True
        assert get_vsm_v2_sql_store(req_obj)._strict_sql is True
        assert get_workflows_v2_runs_sql_store(req_obj)._strict_sql is True
        assert _resolve_reflexive_session_maker(req_obj) is app.state.reflexive_session_maker

        # Assistant runtime caching
        app.state.llm_gateway = _resolve_default_llm_gateway()
        app.state.surgical_explorer_service = MagicMock()
        rt1 = get_assistant_reflexive_runtime_service(req_obj)
        rt2 = get_assistant_reflexive_runtime_service(req_obj)
        assert rt1 is rt2

    # Rehydrate run with workspace_id embedded in SQL payload
    sql_runs = SqlWorkflowV2RunsStore(session_maker=None)
    await sql_runs.upsert_run(
        run_id="run-rehyd-1",
        workspace_id="0195f000-0000-7000-8000-000000000111",
        workflow_id="wf-01",
        workflow_slug="wf-01",
        workflow_title="WF 01",
        actor_slug="assistant",
        status="WAITING_FINAL_ANCHOR",
        reflexive_execution_id=None,
        state_payload={
            "run_id": "run-rehyd-1",
            "workflow_id": "wf-01",
            "workflow_slug": "wf-01",
            "workflow_version": "1.0.0",
            "execution_mode": "native_orcia",
            "status": "WAITING_FINAL_ANCHOR",
            "workspace_id": "0195f000-0000-7000-8000-000000000111",
        },
    )
    mem_runs: dict[str, Any] = {}
    restored, ws_id = await load_or_rehydrate_run_state(mem_runs, sql_runs, "run-rehyd-1")
    assert restored is not None and ws_id == "0195f000-0000-7000-8000-000000000111"
