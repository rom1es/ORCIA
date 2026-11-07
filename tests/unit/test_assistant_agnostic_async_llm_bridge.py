"""Unit & Integration tests for Agnostic Async LLM Bridge, SSRF, Ontology & True SSE Streaming.

Covers all 8 architectural pillars:
1. SSRF protection (`is_safe_llm_endpoint_url`): blocks Cloud Metadata (`169.254.169.254`,
   `metadata.google.internal`, `100.100.100.200`), permits enterprise `.local`/`.internal`,
   `localhost`, and public HTTPS endpoints.
2. Agnostic Multi-Provider URL normalization (`normalize_chat_completions_url`) & headers
   (`OpenAI`, `Anthropic` `/v1/messages` with `x-api-key` + `anthropic-version: 2023-06-01`,
   `Azure OpenAI` `api-key`, `Ollama` `/v1/chat/completions` + 404 fallback to `/api/chat`).
3. Multi-language & i18n (`locale="en"` vs `"fr"`, universal instruction to reply in user's
   exact message language, multilingual adaptive thinking step detection).
4. `AssistantHarness` 5-layer prompt + `OntologyGovernanceService` (`L1–L4`) integration
   without hardcoded `humanize_hat_label_fr`.
5. Strict separation between `<think>` / `reasoning_content` / `thinking` and final `content`
   (never leaks `raw_reasoning` as final reply when `content` is empty).
6. True async HTTP SSE streaming (`resp.aiter_lines()`) via `httpx.MockTransport` preserving
   100% of multi-line Markdown code block newlines (`\n`) and 4-space indentation.
7. Multi-turn `conversation_history` continuity and `tools` JSON Schema injection in agentic mode.
8. Structured logging (`orcia.assistant.llm`) on HTTP status errors (`401`/`429`/`500`).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import orcia_core.bootstrap as bm
from orcia_api.main import app
from orcia_api.routers.assistant_llm_bridge import (
    ResolvedLiveLlmEndpoint,
    build_assistant_system_instructions,
    build_multi_turn_messages,
    build_provider_headers,
    build_provider_request_body,
    build_workspace_tools_schema,
    detect_adaptive_thinking_steps_for_question,
    extract_thinking_and_clean_content,
    is_safe_llm_endpoint_url,
    normalize_chat_completions_url,
)


def test_pillar_8_ssrf_guard_blocks_cloud_metadata_and_allows_enterprise_local() -> None:
    """Verify `is_safe_llm_endpoint_url` blocks Cloud Metadata SSRF and allows `.local`."""
    assert is_safe_llm_endpoint_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_llm_endpoint_url("http://[fe80::1]:8080/v1") is False
    assert is_safe_llm_endpoint_url("http://metadata.google.internal/computeMetadata/v1/") is False
    assert is_safe_llm_endpoint_url("http://100.100.100.200/latest/meta-data/") is False
    assert is_safe_llm_endpoint_url("https://api.example.com/v1") is False
    assert is_safe_llm_endpoint_url("ftp://api.openai.com/v1") is False
    assert is_safe_llm_endpoint_url("") is False

    assert is_safe_llm_endpoint_url("http://ollama.cluster.local:11434") is True
    assert is_safe_llm_endpoint_url("http://vllm.ai.internal:8000/v1") is True
    assert is_safe_llm_endpoint_url("http://localhost:11434/api") is True
    assert is_safe_llm_endpoint_url("https://api.openai.com") is True
    assert is_safe_llm_endpoint_url("https://api.anthropic.com/v1/messages") is True
    assert is_safe_llm_endpoint_url("https://api.mistral.ai") is True


def test_pillar_3_agnostic_url_normalization_and_provider_headers() -> None:
    """Verify URL normalization and headers for OpenAI, Anthropic, Azure, Mistral, and Ollama."""
    assert (
        normalize_chat_completions_url("https://api.openai.com", "OpenAI")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        normalize_chat_completions_url("https://api.mistral.ai/v1", "Mistral")
        == "https://api.mistral.ai/v1/chat/completions"
    )
    assert (
        normalize_chat_completions_url("https://my-gateway.internal/v1/chat/completions", "LiteLLM")
        == "https://my-gateway.internal/v1/chat/completions"
    )
    assert (
        normalize_chat_completions_url("http://localhost:11434", "Ollama")
        == "http://localhost:11434/v1/chat/completions"
    )
    assert (
        normalize_chat_completions_url("https://api.anthropic.com", "Anthropic")
        == "https://api.anthropic.com/v1/messages"
    )
    assert (
        normalize_chat_completions_url("https://api.anthropic.com/v1", "Claude")
        == "https://api.anthropic.com/v1/messages"
    )

    ep_anthropic = ResolvedLiveLlmEndpoint(
        provider="Anthropic",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com",
        auth_mode="api_key",
        api_key="sk-ant-test-key",  # pragma: allowlist secret
    )
    ant_url = normalize_chat_completions_url(ep_anthropic.endpoint_uri, ep_anthropic.provider)
    ant_headers = build_provider_headers(ep_anthropic, ant_url)
    assert ant_headers["x-api-key"] == "sk-ant-test-key"
    assert ant_headers["anthropic-version"] == "2023-06-01"
    assert "Authorization" not in ant_headers

    ant_body = build_provider_request_body(
        ep=ep_anthropic,
        target_url=ant_url,
        messages=[
            {"role": "system", "content": "System rules"},
            {"role": "user", "content": "Hello Claude"},
        ],
        stream=True,
    )
    assert ant_body["system"] == "System rules"
    assert ant_body["messages"] == [{"role": "user", "content": "Hello Claude"}]
    assert ant_body["stream"] is True

    ep_azure = ResolvedLiveLlmEndpoint(
        provider="Azure OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://my-resource.openai.azure.com/openai/deployments/gpt-4o",
        auth_mode="api_key",
        api_key="az-secret-key",  # pragma: allowlist secret
    )
    az_headers = build_provider_headers(ep_azure, ep_azure.endpoint_uri)
    assert az_headers["api-key"] == "az-secret-key"
    assert az_headers["Authorization"] == "Bearer az-secret-key"


def test_pillar_1_and_2_multilingual_locale_and_5_layers_ontology_prompt() -> None:
    """Verify multilingual step detection, user language rule, and 5-layer + Ontology prompt."""
    en_steps = detect_adaptive_thinking_steps_for_question(
        "Compare the trade-offs between PostgreSQL and DynamoDB", locale="en"
    )
    fr_steps = detect_adaptive_thinking_steps_for_question(
        "Explique le contrat d'architecture de ce dossier", locale="fr"
    )
    es_steps = detect_adaptive_thinking_steps_for_question(
        "Explica el resumen del documento", locale="es"
    )
    assert en_steps[0][0] == "Evaluation criteria"
    assert fr_steps[0][0] == "Extraction des points clés"
    assert es_steps[0][0] == "Extracción de puntos clave"

    prompt_en = build_assistant_system_instructions(
        hat="ARCHITECT",
        speed_mode="SPEED_3_DEEP_AUDIT",
        requested_tier="complex",
        thinking_effort="deep",
        assembled_5_layers_prompt="### 1. 🔒 Constitution\nImmutable rules",
        ontology_concepts_summary="- [1_ENTERPRISE] Actif Stratégique: Actif critique DORA",
        locale="en",
    )
    assert "### 1. 🔒 Constitution" in prompt_en
    assert "[ONTOLOGY_L1_L4_CONTEXT]" in prompt_en
    assert "Actif Stratégique" in prompt_en
    assert "High Thinking Effort" in prompt_en
    assert "Respond in the exact same language as the user's message" in prompt_en
    assert "Réponds toujours en français" not in prompt_en


def test_pillar_4_reasoning_channel_separation_never_leaks_draft_as_final_content() -> None:
    """Verify `<think>` and `reasoning_content` never leak into `content` when empty."""
    clean_1, think_1 = extract_thinking_and_clean_content(
        "<think>Step 1: internal chain of thought</think>\nHere is the final answer.",
        explicit_reasoning="Initial reasoning",
    )
    assert clean_1 == "Here is the final answer."
    assert "Initial reasoning" in think_1
    assert "Step 1: internal chain of thought" in think_1

    # When content is empty (e.g., max_tokens truncation during reasoning), clean_content MUST be ""
    clean_empty, think_only = extract_thinking_and_clean_content(
        "", explicit_reasoning="Internal draft reasoning that must never be shown as final reply"
    )
    assert clean_empty == ""
    assert "Internal draft reasoning" in think_only

    # Unclosed <think> tag due to max_tokens truncation
    clean_unclosed, think_unclosed = extract_thinking_and_clean_content(
        "<think>Truncated internal reasoning without closing tag"
    )
    assert clean_unclosed == ""
    assert "Truncated internal reasoning" in think_unclosed


def test_pillar_6_true_async_sse_streaming_preserves_multiline_markdown_indentation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify true async SSE streaming (`aiter_lines()`) preserves `\n` and 4-space code blocks."""
    monkeypatch.setenv("ORCIA_FORCE_LIVE_LLM_IN_TESTS", "1")

    sse_lines = [
        'data: {"choices": [{"delta": {"reasoning_content": "Analyzing factorial recursion..."}}]}',
        'data: {"choices": [{"delta": {"content": "Here is the Python code:\\n\\n```python\\n"}}]}',
        'data: {"choices": [{"delta": {"content": "def fact(n: int) -> int:\\n"}}]}',
        'data: {"choices": [{"delta": {"content": "    if n <= 1:\\n        return 1\\n"}}]}',
        'data: {"choices": [{"delta": {"content": "    return n * fact(n - 1)\\n```"}}]}',
        "data: [DONE]",
    ]
    sse_payload = "\n\n".join(sse_lines) + "\n\n"

    def _sse_mock_handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        assert body.get("stream") is True
        assert "think" not in body
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_payload.encode("utf-8"),
        )

    with TestClient(app) as client:
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_sse_mock_handler))
        app.state.platform_setup_snapshot = bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=True,
            first_admin_email="admin@orcia.io",
            first_admin_display_name="Admin",
            llm_tiers=[
                {
                    "tier": "medium",
                    "primaryModel": "deepseek-r1:14b",
                    "modelFamily": "OpenAI Compatible",
                    "endpointUrl": "https://llm.enterprise.internal",
                    "authMode": "api_key",
                    "apiKey": "sk-live-token",  # pragma: allowlist secret
                }
            ],
        )
        resp = client.post(
            "/api/v1/assistant/three-speed/stream",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Write a recursive factorial function in Python",
                "locale": "en",
            },
        )
        assert resp.status_code == 200
        token_deltas: list[str] = []
        completed_text = ""
        for block in resp.text.split("\n\n"):
            if "event: token_delta" in block:
                for line in block.splitlines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        token_deltas.append(str(data.get("delta") or ""))
            elif "event: turn_completed" in block:
                for line in block.splitlines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        completed_text = str(data.get("response_text") or "")

        reassembled = "".join(token_deltas)
        expected_code = (
            "Here is the Python code:\n\n```python\n"
            "def fact(n: int) -> int:\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * fact(n - 1)\n```"
        )
        assert reassembled == expected_code
        assert completed_text == expected_code
        assert "    return n * fact(n - 1)" in completed_text


def test_pillar_5_and_8_multi_turn_history_tools_and_structured_error_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-turn `conversation_history`, `tools` in Speed 2, and structured HTTP logs."""
    monkeypatch.setenv("ORCIA_FORCE_LIVE_LLM_IN_TESTS", "1")

    msgs = build_multi_turn_messages(
        system_msg="Sys",
        user_prompt="Et pour le second point ?",
        conversation_history=[
            {"role": "user", "content": "Voici deux points A et B."},
            {"role": "assistant", "content": "Le point A concerne l'architecture."},
        ],
    )
    assert len(msgs) == 4
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    assert msgs[3]["content"] == "Et pour le second point ?"

    tools_s1 = build_workspace_tools_schema(None, "SPEED_1_FAST")
    tools_s2 = build_workspace_tools_schema(None, "SPEED_2_AGENT_TOOLS")
    assert tools_s1 == []
    assert len(tools_s2) >= 1
    assert tools_s2[0]["function"]["name"] == "query_workspace_knowledge_and_glossary"

    captured_payloads: list[dict[str, Any]] = []
    logged_warnings: list[tuple[str, dict[str, Any]]] = []

    from orcia_api.routers import assistant_llm_providers

    orig_log_err = assistant_llm_providers._log_provider_error

    def _spy_log_err(
        event: str,
        exc: Exception,
        ep: ResolvedLiveLlmEndpoint,
        target_url: str,
        t0: float,
    ) -> None:
        status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        logged_warnings.append((event, {"status_code": status_code, "endpoint": target_url}))
        orig_log_err(event, exc, ep, target_url, t0)

    monkeypatch.setattr(assistant_llm_providers, "_log_provider_error", _spy_log_err)

    call_count = 0

    def _handler(req: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        body = json.loads(req.content.decode("utf-8"))
        captured_payloads.append(body)
        if call_count == 1:
            return httpx.Response(429, json={"error": "rate_limit_exceeded"})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Synthèse du second point B avec outils.",
                        }
                    }
                ]
            },
        )

    with TestClient(app) as client:
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        app.state.platform_setup_snapshot = bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=True,
            first_admin_email="admin@orcia.io",
            first_admin_display_name="Admin",
            llm_tiers=[
                {
                    "tier": "medium",
                    "primaryModel": "gpt-4o",
                    "modelFamily": "OpenAI",
                    "endpointUrl": "https://api.openai.com",
                    "authMode": "api_key",
                    "apiKey": "sk-test-key",  # pragma: allowlist secret
                }
            ],
        )
        # 1st call returns HTTP 429 -> logged with status_code=429 and falls back gracefully
        r_err = client.post(
            "/api/v1/assistant/three-speed/turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Vérifie avec @jira-triage le point B",
                "conversation_history": [
                    {"role": "user", "content": "Question initiale A et B"},
                    {"role": "assistant", "content": "Réponse sur A"},
                ],
            },
        )
        assert r_err.status_code == 200
        assert any(
            evt == "llm_provider_http_status_error" and kw.get("status_code") == 429
            for evt, kw in logged_warnings
        )
        assert len(captured_payloads[0]["messages"]) == 4
        assert "tools" in captured_payloads[0]

        # 2nd call succeeds with live LLM
        r_ok = client.post(
            "/api/v1/assistant/three-speed/turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Vérifie avec @jira-triage le point B",
                "conversation_history": [
                    {"role": "user", "content": "Question initiale A et B"},
                    {"role": "assistant", "content": "Réponse sur A"},
                ],
            },
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["response_text"] == "Synthèse du second point B avec outils."


@pytest.mark.asyncio
async def test_anthropic_blocks_legacy_404_fallback_and_tool_call_followup() -> None:
    """Cover Anthropic content blocks, 404 `/api/chat` fallback, and `<think>` stream tags."""
    from orcia_api.routers.assistant_llm_providers import (
        _extract_stream_chunk_deltas,
        _parse_non_stream_json,
        invoke_provider_chat_async,
        stream_provider_chat_sse_async,
    )

    clean, think, t_calls = _parse_non_stream_json(
        {
            "content": [
                {"type": "thinking", "thinking": "Anthropic extended thinking"},
                {"type": "text", "text": "Anthropic final response"},
                {"type": "tool_use", "id": "tu_1", "name": "search_kb", "input": {"q": "SLA"}},
            ]
        }
    )
    assert clean == "Anthropic final response"
    assert think == "Anthropic extended thinking"
    assert len(t_calls) == 1 and t_calls[0]["name"] == "search_kb"

    c_d, r_d = _extract_stream_chunk_deltas(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}
    )
    assert c_d == "Hello" and r_d == ""
    c_d2, r_d2 = _extract_stream_chunk_deltas(
        {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "Hmm"}}
    )
    assert c_d2 == "" and r_d2 == "Hmm"

    ep_local = ResolvedLiveLlmEndpoint(
        provider="Local",
        model_name="qwen2.5:7b",
        endpoint_uri="http://localhost:11434",
        auth_mode="none",
    )

    def _fallback_handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(404)
        return httpx.Response(
            200,
            json={"message": {"content": "<think>Local thought</think>Local fallback reply"}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fallback_handler)) as client:
        res = await invoke_provider_chat_async(
            client, ep=ep_local, messages=[{"role": "user", "content": "Hi"}]
        )
        assert res is not None
        assert res.content == "Local fallback reply"
        assert res.thinking_text == "Local thought"

    sse_think = (
        'data: {"choices": [{"delta": {"content": "<think>Tag thinking"}}]}\n\n'
        'data: {"choices": [{"delta": {"content": " end</think>Final text"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, content=sse_think.encode("utf-8"))
        )
    ) as s_client:
        evts = [
            e
            async for e in stream_provider_chat_sse_async(
                s_client, ep=ep_local, messages=[{"role": "user", "content": "Hi"}]
            )
        ]
        assert any(e["event"] == "thinking_delta" for e in evts)
        assert evts[-1]["data"]["response_text"] == "Final text"
        assert "Tag thinking" in evts[-1]["data"]["thinking_text"]
