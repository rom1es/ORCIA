"""Story 10.2 — Live LLM bridge, tier selection, effort & prompt locale tests."""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

import orcia_core.bootstrap as bm
from orcia_api.main import app
from orcia_api.routers.assistant_llm_bridge import (
    _extract_tier_endpoint_from_dict,
    _select_endpoint_from_tiers,
    build_assistant_system_instructions,
    detect_adaptive_thinking_steps_for_question,
    normalize_chat_completions_url,
)


def test_story_10_2_live_llm_bridge_agnostic_provider_and_url_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify agnostic LLM bridge resolves configured tier and normalizes URLs properly."""
    assert (
        normalize_chat_completions_url(
            "http://localhost:11434/api", "Ollama Local", model_name="llama3.2"
        )
        == "http://localhost:11434/v1/chat/completions"
    )
    assert (
        normalize_chat_completions_url("https://api.openai.com", "OpenAI", model_name="gpt-4o")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        normalize_chat_completions_url(
            "https://api.anthropic.com", "Anthropic", model_name="claude-3-7-sonnet"
        )
        == "https://api.anthropic.com/v1/messages"
    )

    resolved = _extract_tier_endpoint_from_dict(
        {
            "tier": "medium",
            "primaryModel": "gemma4:12b",
            "modelFamily": "Ollama Local",
            "endpointUrl": "http://localhost:11434/api",
            "authMode": "none_local",
        }
    )
    assert resolved is not None
    assert resolved.model_name == "gemma4:12b"

    def _mock_handler(req: httpx.Request) -> httpx.Response:
        assert str(req.url) == "http://localhost:11434/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                "Bonjour, je suis votre Assistant ORCIA propulsé par gemma4:12b."
                            ),
                        }
                    }
                ]
            },
        )

    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with TestClient(app) as client:
        app.state.embedding_port = FakeDeterministicEmbeddingAdapter()
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
        app.state.platform_setup_snapshot = bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=True,
            first_admin_email="admin@orcia.io",
            first_admin_display_name="Admin",
            llm_tiers=[
                {
                    "tier": "medium",
                    "primaryModel": "gemma4:12b",
                    "modelFamily": "Ollama Local",
                    "endpointUrl": "http://localhost:11434/api",
                    "authMode": "none_local",
                }
            ],
        )

        def _sse_stream_mock(req: httpx.Request) -> httpx.Response:
            json_body = json.loads(req.content.decode("utf-8"))
            model = str(json_body.get("model", ""))
            sse_body = (
                f'data: {{"choices":[{{"delta":{{"content":"Réponse live via {model}."}}}}]}}\n\n'
                "data: [DONE]\n\n"
            )
            return httpx.Response(200, text=sse_body, headers={"content-type": "text/event-stream"})

        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_sse_stream_mock))
        r_live = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "user_prompt": "Bonjour",
            },
        )
        assert r_live.status_code == 202
        s_live = client.get(r_live.json()["stream_url"], params={"persona_key": "marc"})
        assert s_live.status_code == 200
        assert "gemma4:12b" in s_live.text


def test_story_10_2_live_llm_bridge_tier_selection_and_thinking_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `requested_tier`, `thinking_effort`, 5-layer prompt & multilingual steps."""
    code_steps_fr = detect_adaptive_thinking_steps_for_question(
        "code la fonction factorielle en python", locale="fr"
    )
    code_steps_en = detect_adaptive_thinking_steps_for_question(
        "implement a python function for factorial", locale="en"
    )
    assert len(code_steps_fr) == 3
    assert code_steps_fr[0][0] == "Spécification et cas limites"
    assert code_steps_en[0][0] == "Specification & edge cases"

    tiers_cfg = [
        {
            "tier": "simple",
            "primaryModel": "gemma4:4b-fast",
            "modelFamily": "Ollama Local",
            "endpointUrl": "http://localhost:11434/api",
            "authMode": "none_local",
        },
        {
            "tier": "medium",
            "primaryModel": "gemma4:12b",
            "modelFamily": "Ollama Local",
            "endpointUrl": "http://localhost:11434/api",
            "authMode": "none_local",
        },
        {
            "tier": "complex",
            "primaryModel": "gemma4:27b-pro",
            "modelFamily": "Ollama Local",
            "endpointUrl": "http://localhost:11434/v1",
            "authMode": "none_local",
        },
    ]

    ep_simple = _select_endpoint_from_tiers(tiers_cfg, "simple")
    ep_medium = _select_endpoint_from_tiers(tiers_cfg, "medium")
    ep_complex = _select_endpoint_from_tiers(tiers_cfg, "complex")
    assert ep_simple is not None and ep_simple.model_name == "gemma4:4b-fast"
    assert ep_simple.supports_tools is False
    assert ep_medium is not None and ep_medium.model_name == "gemma4:12b"
    assert ep_complex is not None and ep_complex.model_name == "gemma4:27b-pro"
    assert ep_complex.supports_tools is True

    sys_fast = build_assistant_system_instructions(
        hat="ARCHITECT",
        speed_mode="SPEED_1_FAST",
        requested_tier="simple",
        thinking_effort="fast",
    )
    sys_deep = build_assistant_system_instructions(
        hat="PM",
        speed_mode="SPEED_3_DEEP_AUDIT",
        requested_tier="complex",
        thinking_effort="deep",
    )
    assert "Palier Rapide" in sys_fast
    assert "Niveau de réflexion Bas" in sys_fast
    assert "Principes de comportement fondamentaux" in sys_fast
    assert "CONSTITUTIONAL_IMMUTABLE_LAYER_1" not in sys_fast
    assert "RÈGLE DE LANGUE IMPÉRATIVE" in sys_fast
    assert "Réponds en français" in sys_fast
    assert "Palier Raisonnement avancé" in sys_deep
    assert "Niveau de réflexion Élevé" in sys_deep
    assert "Règles de Gestion" in sys_deep

    captured_models: list[str] = []
    captured_sys_prompts: list[str] = []

    def _mock_handler(req: httpx.Request) -> httpx.Response:
        json_body = json.loads(req.content.decode("utf-8"))
        model = str(json_body.get("model", ""))
        msgs = json_body.get("messages", [])
        captured_models.append(model)
        if msgs:
            captured_sys_prompts.append(str(msgs[0].get("content", "")))
        sse_body = (
            f'data: {{"choices":[{{"delta":{{"content":"Réponse générée par {model}."}}}}]}}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(200, text=sse_body, headers={"content-type": "text/event-stream"})

    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/tmp/orcia-unit-none.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with TestClient(app) as client:
        app.state.embedding_port = FakeDeterministicEmbeddingAdapter()
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
        app.state.platform_setup_snapshot = bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=True,
            first_admin_email="admin@orcia.io",
            first_admin_display_name="Admin",
            llm_tiers=tiers_cfg,
        )
        r_non_v1_reject = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "user_prompt": "Vérifie avec @jira-triage",
                "requested_tier": "simple",
                "requested_speed": "SPEED_2_AGENT_TOOLS",
            },
        )
        assert r_non_v1_reject.status_code == 422
        assert r_non_v1_reject.json()["error_code"] == "ERR_MODEL_TOOLS_UNSUPPORTED"

        r_complex_deep = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "user_prompt": "Analyse critique complète du dossier",
                "requested_tier": "complex",
                "thinking_effort": "deep",
            },
        )
        assert r_complex_deep.status_code == 202
        d_complex = r_complex_deep.json()
        assert d_complex["speed_mode"] == "SPEED_3_DEEP_AUDIT"
        s_complex = client.get(d_complex["stream_url"], params={"persona_key": "marc"})
        assert s_complex.status_code == 200
        assert "gemma4:27b-pro" in s_complex.text
        assert captured_models[-1] == "gemma4:27b-pro"
        assert "Niveau de réflexion Élevé" in captured_sys_prompts[-1]
        assert "Principes de comportement fondamentaux" in captured_sys_prompts[-1]
        assert "1. 🔒 Constitution (AssistantHarness Socle)" not in captured_sys_prompts[-1]
