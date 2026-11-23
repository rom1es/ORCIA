"""Unit tests for request locale resolution, FR/EN prompt rules, and tool-loop localization."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from orcia_api.routers._assistant_prompt_sanitization import resolve_request_locale
from orcia_api.routers._assistant_turn_locale_messages import (
    build_budget_reached_prompt,
    build_synthesize_now_prompt,
    format_governed_tool_round_summary,
    format_zero_tokens_error_detail,
)
from orcia_api.routers._assistant_turn_producer import execute_turn_producer_task
from orcia_api.routers._assistant_turn_producer_tool_loop import run_streaming_tool_loop
from orcia_core.orchestration.assistant_prompt_locales import PROMPT_LOCALES
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamRequest,
)


def _make_request(accept_language: str | None) -> Any:
    headers = {"accept-language": accept_language} if accept_language is not None else {}
    return SimpleNamespace(headers=headers)


def test_resolve_request_locale_respects_primary_accept_language_tag() -> None:
    assert resolve_request_locale(_make_request("fr-FR,fr;q=0.9,en-US;q=0.8")) == "fr"
    assert resolve_request_locale(_make_request("en-US,en;q=0.9,fr;q=0.8")) == "en"
    assert resolve_request_locale(_make_request("es-ES,es;q=0.9,en;q=0.8")) == "es"
    assert resolve_request_locale(_make_request("fr-FR,fr;q=0.9"), explicit_locale="en") == "en"
    assert resolve_request_locale(None, None) == "fr"


def test_prompt_locales_fr_language_rule_defaults_to_french() -> None:
    fr_rule = PROMPT_LOCALES["fr"].language_rule
    assert "RÈGLE DE LANGUE IMPÉRATIVE" in fr_rule
    assert "français" in fr_rule
    assert "fichiers" in fr_rule and "artefacts" in fr_rule
    assert "CRITICAL LANGUAGE RULE" in PROMPT_LOCALES["en"].language_rule


def test_turn_locale_messages_fr_and_en() -> None:
    assert "Synthèse anticipée" in build_synthesize_now_prompt("fr")
    assert "Early synthesis requested" in build_synthesize_now_prompt("en")
    assert "Budget d'exécution atteint" in build_budget_reached_prompt("fr")
    assert "Execution budget reached" in build_budget_reached_prompt("en")
    assert format_governed_tool_round_summary(2, "fr") == "2 appels d'outil gouvernés exécutés"
    assert format_governed_tool_round_summary(2, "en") == "Executed 2 governed tool call(s)"
    assert "n'a renvoyé aucun jeton" in format_zero_tokens_error_detail(
        "gemini-2.5-flash", "https://example.test", "fr"
    )
    assert "returned zero tokens" in format_zero_tokens_error_detail(
        "gemini-2.5-flash", "https://example.test", "en"
    )


@pytest.mark.asyncio
async def test_run_streaming_tool_loop_injects_localized_synthesize_now_prompt() -> None:
    seen_requests: list[LlmStreamRequest] = []

    class _MockLlmPort:
        async def stream_chat_sse(self, req: LlmStreamRequest) -> AsyncIterator[Any]:
            seen_requests.append(req)
            yield LlmStreamDelta(
                event="turn_completed",
                accumulated_text="Réponse finale.",
                thinking_text="",
                input_tokens=5,
                output_tokens=4,
            )

    registry = SimpleNamespace(
        is_synthesize_now_requested=AsyncMock(return_value=True),
        append_event=AsyncMock(),
    )
    ep = LlmEndpointConfig(
        provider="google",
        model_name="gemini-2.5-flash",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        supports_tools=True,
    )
    record = AssistantTurnRecord(
        turn_id="turn-fr-1",
        workspace_id="ws-1",
        user_id="user-1",
        status="RUNNING",
        user_prompt="Bonjour",
        assembled_system_prompt="System",
        trace_id="trace-1",
    )

    out = await run_streaming_tool_loop(
        active_port=_MockLlmPort(),  # type: ignore[arg-type]
        stream_ep=ep,
        initial_messages=[{"role": "user", "content": "Bonjour"}],
        tools=(),
        tool_catalog=(),
        tool_router=None,
        registry=registry,  # type: ignore[arg-type]
        record=record,
        user_email="u@example.test",
        user_display_name="User",
        locale="fr",
        t0=0.0,
    )
    assert out["streamed_text"] == "Réponse finale."
    assert len(seen_requests) == 1
    assert "Synthèse anticipée demandée" in seen_requests[0].messages[-1]["content"]


@pytest.mark.asyncio
async def test_execute_turn_producer_task_localizes_zero_tokens_error() -> None:
    appended_events: list[tuple[str, dict[str, Any]]] = []

    class _ZeroTokenLlmPort:
        async def stream_chat_sse(self, req: LlmStreamRequest) -> AsyncIterator[Any]:
            yield LlmStreamDelta(
                event="turn_completed",
                accumulated_text="",
                thinking_text="",
                input_tokens=2,
                output_tokens=0,
            )

    async def _append_event(_tid: str, *, event: str, data: dict[str, Any], **_kw: Any) -> None:
        appended_events.append((event, data))

    registry = SimpleNamespace(
        is_synthesize_now_requested=AsyncMock(return_value=False),
        is_stop_requested=AsyncMock(return_value=None),
        refresh_liveness=AsyncMock(),
        append_event=_append_event,
        update_turn=AsyncMock(),
        clear_liveness=AsyncMock(),
        set_stream_ttl=AsyncMock(),
    )
    rate_limiter = SimpleNamespace(release_concurrency_slot=AsyncMock())
    ep = LlmEndpointConfig(
        provider="google",
        model_name="gemini-2.5-flash",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        supports_tools=False,
    )
    record = AssistantTurnRecord(
        turn_id="turn-zero-fr",
        workspace_id="ws-1",
        user_id="user-1",
        status="RUNNING",
        user_prompt="Bonjour",
        assembled_system_prompt="System",
        trace_id="trace-fr",
    )

    await execute_turn_producer_task(
        registry=registry,  # type: ignore[arg-type]
        rate_limiter=rate_limiter,  # type: ignore[arg-type]
        initial_record=record,
        lease_token="lease-1",
        liveness_ttl_s=15,
        t0=0.0,
        default_thinking="",
        fallback_response_text=None,
        ep=ep,
        http_client_getter=lambda: None,  # type: ignore[arg-type, return-value]
        messages_builder=lambda: [{"role": "user", "content": "Bonjour"}],
        tools_builder=list,
        conversation_history_count=0,
        folder_pinned_notes=None,
        llm_port=_ZeroTokenLlmPort(),  # type: ignore[arg-type]
        user_email="u@example.test",
        user_display_name="User",
        audit_ledger_sink=None,
        locale="fr",
        instance="/api/v1/assistant/turns",
    )
    err_evt = next(d for ev, d in appended_events if ev == "stream_error")
    assert "n'a renvoyé aucun jeton" in str(err_evt.get("detail") or err_evt.get("message") or "")
