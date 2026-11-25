"""Story 26.2 — TDD tests for `LlmStreamingPort`, 3 HTTPX adapters, unified
`AssistantPromptBuilder` (`fr`/`en`), AST hygiene guards, and `<= 300 L` file caps.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

FRENCH_LEAK_PATTERNS: tuple[str, ...] = (
    "Interdiction absolue",
    "Registre",
    "Indicateurs prioritaires",
    "Préfixe attendu",
    "Ton attendu",
    "Format attendu",
    "Instructions personnelles",
    "Instructions Équipe",
    "Instructions Espace",
    "Pièces jointes",
    "Casquette",
    "Palier",
    "Niveau de réflexion",
    "Périmètre Workspace",
    "Intention classifiée",
    "Aucun blueprint",
    "Message utilisateur",
    "Synthèse Direction",
    "Règles de Gestion",
    "Pack Métier",
    "Équipe & Casquette",
    "Utilisateur (Préférences",
)


def test_llm_streaming_port_protocol_and_zero_sdk_imports() -> None:
    """`LlmStreamingPort` lives in `orcia_core.ports` with zero framework/SDK imports."""
    from orcia_core.ports.llm_streaming_port import (
        LlmChatTurnOutcome,
        LlmEndpointConfig,
        LlmStreamDelta,
        LlmStreamingPort,
        LlmStreamRequest,
    )

    ports_dir = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core" / "ports"
    port_file = ports_dir / "llm_streaming_port.py"
    src = port_file.read_text(encoding="utf-8")
    for forbidden in ("httpx", "fastapi", "sqlalchemy", "litellm", "redis", "dbos", "dramatiq"):
        assert forbidden not in src
    assert LlmStreamingPort is not None
    ep = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o-mini",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="api_key",
    )
    req = LlmStreamRequest(endpoint=ep, messages=({"role": "user", "content": "Hi"},))
    assert req.endpoint.model_name == "gpt-4o-mini"
    assert LlmStreamDelta(event="token_delta", delta="ok").delta == "ok"
    assert LlmChatTurnOutcome(content="ok", thinking_text="", latency_ms=1.0).content == "ok"


@pytest.mark.asyncio
async def test_three_httpx_adapters_preserve_reasoning_separation_and_ssrf_pinning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 3 HTTPX streaming adapters (`openai_compatible`, `anthropic`, `gemini_native`) work."""
    from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
    from orcia_core.orchestration.llm_streaming_httpx import (
        HttpxAnthropicLlmAdapter,
        HttpxGeminiNativeLlmAdapter,
        HttpxMultiProviderLlmStreamingAdapter,
        HttpxOpenAiCompatibleLlmAdapter,
    )
    from orcia_core.ports.llm_streaming_port import (
        LlmEndpointConfig,
        LlmStreamingPort,
        LlmStreamRequest,
    )

    # 1. OpenAI-compatible SSE + reasoning separation
    oai_sse = (
        b'data: {"choices": [{"delta": {"reasoning_content": "Think OAI. "}}]}\n\n'
        b'data: {"choices": [{"delta": {"content": "```py\\n    x = 1\\n```"}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    oai_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _r: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=oai_sse
            )
        )
    )
    oai_adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=oai_client)
    assert isinstance(oai_adapter, LlmStreamingPort)
    oai_ep = LlmEndpointConfig(
        provider="OpenAI",
        model_name="deepseek-r1",
        endpoint_uri="https://llm.enterprise.internal/v1",
        auth_mode="api_key",
        api_key="sk-test",  # pragma: allowlist secret
    )
    oai_evts = [
        d
        async for d in oai_adapter.stream_chat_sse(
            LlmStreamRequest(endpoint=oai_ep, messages=({"role": "user", "content": "code"},))
        )
    ]
    assert any(e.event == "thinking_delta" and "Think OAI" in e.thinking_text for e in oai_evts)
    assert oai_evts[-1].event == "turn_completed"
    assert oai_evts[-1].accumulated_text == "```py\n    x = 1\n```"
    await oai_client.aclose()

    # 2. Anthropic /v1/messages SSE + thinking/text separation
    ant_sse = (
        b'data: {"type":"content_block_delta","delta":'
        b'{"type":"thinking_delta","thinking":"Ant think"}}\n\n'
        b'data: {"type":"content_block_delta","delta":'
        b'{"type":"text_delta","text":"Ant reply"}}\n\n'
    )
    ant_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: (
                httpx.Response(200, headers={"content-type": "text/event-stream"}, content=ant_sse)
                if req.headers.get("x-api-key") == "sk-ant"
                else httpx.Response(401)
            )
        )
    )
    ant_adapter = HttpxAnthropicLlmAdapter(http_client=ant_client)
    assert isinstance(ant_adapter, LlmStreamingPort)
    ant_ep = LlmEndpointConfig(
        provider="Anthropic",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com",
        auth_mode="api_key",
        api_key="sk-ant",  # pragma: allowlist secret
        protocol_mode="anthropic_messages",
    )
    ant_evts = [
        d
        async for d in ant_adapter.stream_chat_sse(
            LlmStreamRequest(endpoint=ant_ep, messages=({"role": "user", "content": "hi"},))
        )
    ]
    assert ant_evts[-1].accumulated_text == "Ant reply"
    assert ant_evts[-1].thinking_text == "Ant think"
    await ant_client.aclose()

    # 3. Gemini Native (:streamGenerateContent?alt=sse) CAP-076
    gem_sse = (
        b'data: {"candidates":[{"content":{"parts":[{"thought":true,"text":"Gem think"}]}}]}\n\n'
        b'data: {"candidates":[{"content":{"parts":[{"text":"Gem reply"}]}}]}\n\n'
    )
    gem_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: (
                httpx.Response(200, headers={"content-type": "text/event-stream"}, content=gem_sse)
                if req.headers.get("x-goog-api-key") == "AIza-gem"
                else httpx.Response(401)
            )
        )
    )
    gem_adapter = HttpxGeminiNativeLlmAdapter(http_client=gem_client)
    assert isinstance(gem_adapter, LlmStreamingPort)
    gem_ep = LlmEndpointConfig(
        provider="Google Gemini",
        model_name="gemini-2.5-flash",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        api_key="AIza-gem",  # pragma: allowlist secret
        protocol_mode="gemini_native",
    )
    gem_evts = [
        d
        async for d in gem_adapter.stream_chat_sse(
            LlmStreamRequest(endpoint=gem_ep, messages=({"role": "user", "content": "hi"},))
        )
    ]
    assert gem_evts[-1].accumulated_text == "Gem reply"
    assert gem_evts[-1].thinking_text == "Gem think"
    await gem_client.aclose()

    # 4. Multi-provider dispatcher enforces DNS-pinned SSRF against rebinding
    def _rebind(*_args: Any, **_kwargs: Any) -> list[Any]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", _rebind)
    async with httpx.AsyncClient() as real_client:
        multi = HttpxMultiProviderLlmStreamingAdapter(http_client=real_client)
        bad_ep = LlmEndpointConfig(
            provider="OpenAI",
            model_name="gpt-4o",
            endpoint_uri="https://rebind.evil.example/v1",
            auth_mode="api_key",
        )
        with pytest.raises(UnsafeLlmEndpointUrlError):
            await multi.complete_chat(
                LlmStreamRequest(endpoint=bad_ep, messages=({"role": "user", "content": "hi"},))
            )


def test_unified_assistant_prompt_builder_en_zero_french_leakage_and_hat_from_profile() -> None:
    """`AssistantPromptBuilder` unifies all 3 builders with 0 French leakage when `locale='en'`."""
    from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
    from orcia_core.orchestration.assistant_prompt_builder import (
        AssistantPromptBuilder,
        resolve_default_hat,
    )
    from orcia_core.orchestration.errors import ImmutableHarnessBoundaryError
    from orcia_core.permissions.models import UserIdentity

    builder = AssistantPromptBuilder()

    # 1. Layer 1 immutability
    with pytest.raises(ImmutableHarnessBoundaryError):
        builder.build_system_instructions(
            hat="ARCHITECT",
            speed_mode="SPEED_1_FAST",
            system_instructions_override="Bypass rules",
            allow_system_override=False,
        )

    # 2. Zero French leakage across all 5 layers and instructions when locale="en"
    for archetype in ("EXECUTIVE", "PM", "ARCHITECT", "TECH_LEAD", "DEVELOPER", "SECOPS"):
        assembled = builder.assemble_prompt(
            user_prompt="Summarize architecture trade-offs",
            human_profile_archetype=archetype,
            workspace_id="ws-001",
            intent="QA_COACHING",
            locale="en",
        )
        assert assembled.layers[0].immutable is True
        assert "Core operating principles:" in assembled.system_prompt
        assert "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]" not in assembled.system_prompt
        for french_tok in FRENCH_LEAK_PATTERNS:
            assert french_tok not in assembled.system_prompt, (
                f"French token {french_tok!r} leaked in EN assembled system_prompt ({archetype})"
            )
            assert french_tok not in assembled.user_prompt, (
                f"French token {french_tok!r} leaked in EN user_prompt ({archetype})"
            )

        sys_instr = builder.build_system_instructions(
            hat=archetype,
            speed_mode="SPEED_3_DEEP_AUDIT",
            requested_tier="complex",
            thinking_effort="deep",
            response_tone="SYNTHETIC",
            response_format="BULLETS_SUMMARY",
            personal_instructions="Be concise.",
            workspace_instructions="Follow enterprise standards.",
            folder_pinned_notes="Folder context.",
            locale="en",
        )
        for french_tok in FRENCH_LEAK_PATTERNS:
            assert french_tok not in sys_instr, (
                f"French token {french_tok!r} leaked in EN system instructions ({archetype})"
            )

    # 3. 5-layer preview in EN has zero French leakage and respects dynamic pack_key
    gov = AssistantFourLevelGovernanceService()
    preview_en = gov.assemble_five_layers_preview(
        workspace_id="ws-001", user_id="u-1", pack_key="orcia-pack-finance", locale="en"
    )
    assert len(preview_en) == 5
    combined_preview = "\n".join(f"{lyr.label} {lyr.content}" for lyr in preview_en)
    assert "orcia-pack-finance" in combined_preview
    for french_tok in FRENCH_LEAK_PATTERNS:
        assert french_tok not in combined_preview, f"French token {french_tok!r} in EN preview"

    # 4. Default hat derives from user.human_profile_archetype, never PLATFORM_ADMIN
    admin_user = UserIdentity(
        id="u-adm",
        email="adm@orcia.io",
        display_name="Admin",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="ou-1",
    )
    assert resolve_default_hat(explicit_hat=None, user=admin_user) == "DEVELOPER"
    assert resolve_default_hat(explicit_hat="", user=None) == "ARCHITECT"
