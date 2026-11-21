"""Story 26.2 — TDD tests for `LlmStreamingPort`, 3 HTTPX adapters, unified
`AssistantPromptBuilder` (`fr`/`en`), AST hygiene guards, and `<= 300 L` file caps.
"""

from __future__ import annotations

import ast
import json
import re
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
        assert "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]" in assembled.system_prompt
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


def test_no_synthetic_latencies_in_three_speed_or_citations() -> None:
    """Story 26.2 / H-30 P2: real `perf_counter()` timings, zero hardcoded 14.5/380/520/1460."""
    files_to_check = (
        REPO_ROOT
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "orchestration"
        / "assistant_three_speed_router.py",
        REPO_ROOT
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "orchestration"
        / "assistant_three_speed_steps.py",
        REPO_ROOT
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "orchestration"
        / "assistant_citations_and_v5_guard.py",
    )
    synthetic_nums = re.compile(r"\b(?:14\.5|380\.0|410\.0|490\.0|520\.0|640\.0|820\.0|1460\.0)\b")
    for p in files_to_check:
        content = p.read_text(encoding="utf-8")
        assert not synthetic_nums.search(content), f"Synthetic latency literal in {p.name}"
        assert "min((time.perf_counter()" not in content, f"Synthetic min(..., cap) in {p.name}"


def test_ast_hygiene_zero_test_branches_internal_imports_cassette_or_oversized_files() -> None:
    """Enforce Story 26.2 AST guards: H-24, H-25, H-34, and agents_and_skills DI port."""
    src_roots = (
        REPO_ROOT / "packages" / "orcia-core" / "src",
        REPO_ROOT / "packages" / "orcia-connectors" / "src",
        REPO_ROOT / "apps" / "api" / "src",
        REPO_ROOT / "apps" / "worker" / "src",
    )
    banned_test_patterns = (
        'client_host == "testclient"',
        'client_host != "testclient"',
        '"pytest" in sys.modules',
        "'pytest' in sys.modules",
        '"pytest" not in sys.modules',
        "ORCIA_FORCE_LIVE_LLM_IN_TESTS",
    )
    test_branch_hits: list[str] = []
    for root in src_roots:
        for py in root.rglob("*.py"):
            txt = py.read_text(encoding="utf-8")
            for pat in banned_test_patterns:
                if pat in txt:
                    test_branch_hits.append(f"{py.relative_to(REPO_ROOT)}:{pat}")
    assert test_branch_hits == [], f"Test branches in prod src: {test_branch_hits}"

    # Zero `_internal` imports in apps/api/src
    internal_hits: list[str] = []
    for py in (REPO_ROOT / "apps" / "api" / "src").rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "._internal" in node.module:
                internal_hits.append(f"{py.relative_to(REPO_ROOT)}:{node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "._internal" in alias.name:
                        internal_hits.append(f"{py.relative_to(REPO_ROOT)}:{alias.name}")
    assert internal_hits == [], f"`_internal` imports in apps/api/src: {internal_hits}"

    # Zero `testing.cassette_llm` imports inside orcia_core domain packages
    core_domains = (
        "orchestration",
        "agents",
        "rag",
        "catalog",
        "permissions",
        "ontology",
        "blackboard",
        "gates",
        "audit_finops",
        "bootstrap",
    )
    cassette_hits: list[str] = []
    for dom in core_domains:
        dom_dir = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core" / dom
        for py in dom_dir.rglob("*.py"):
            if "testing.cassette_llm" in py.read_text(encoding="utf-8"):
                cassette_hits.append(str(py.relative_to(REPO_ROOT)))
    assert cassette_hits == [], (
        f"`testing.cassette_llm` imports in orcia_core domains: {cassette_hits}"
    )

    # agents_and_skills must not import assistant_llm_bridge
    for ag_path in (
        REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers" / "agents_and_skills.py",
        REPO_ROOT
        / "apps"
        / "api"
        / "src"
        / "orcia_api"
        / "routers"
        / "_agents_and_skills_skills_routes.py",
    ):
        assert "assistant_llm_bridge" not in ag_path.read_text(encoding="utf-8")

    # Every Story 26.2 harness/dependency/web file <= 300 lines
    api_routers = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers"
    core_orch = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core" / "orchestration"
    api_schemas = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "schemas"
    capped_files: list[Path] = [
        *sorted(api_routers.glob("*assistant*.py")),
        *sorted(api_routers.glob("*agents_and_skills*.py")),
        *sorted((REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "dependencies").glob("*.py")),
        *sorted(api_schemas.glob("assistant*.py")),
        *sorted(core_orch.glob("*assistant*.py")),
        *sorted(core_orch.glob("llm_*.py")),
        REPO_ROOT
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "ports"
        / "llm_streaming_port.py",
        REPO_ROOT
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "agents"
        / "reflexive_runtime.py",
        REPO_ROOT / "apps" / "web" / "src" / "features" / "inbox" / "useAssistantStreamingTurn.ts",
    ]
    oversized = [
        f"{p.relative_to(REPO_ROOT)} ({len(p.read_text(encoding='utf-8').splitlines())} L)"
        for p in capped_files
        if p.exists() and len(p.read_text(encoding="utf-8").splitlines()) > 300
    ]
    assert oversized == [], f"Files exceeding 300 lines: {oversized}"


def test_frontend_attachment_label_is_localized() -> None:
    """`H-31`: `assistantTurnPayloadHelper.ts` localizes `[User-supplied attachments]` for EN."""
    helper = (
        REPO_ROOT / "apps" / "web" / "src" / "features" / "inbox" / "assistantTurnPayloadHelper.ts"
    )
    src = helper.read_text(encoding="utf-8")
    assert "User-supplied attachments" in src
    assert json.dumps("Pièces jointes") not in src or "isFr" in src


def test_composition_root_get_llm_streaming_port_and_agents_skills_di(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `get_llm_streaming_port` switches Cassette/HTTPX and `/agents-and-skills` uses DI."""
    from fastapi.testclient import TestClient

    from orcia_api.dependencies import get_llm_streaming_port
    from orcia_api.main import create_app
    from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
    from orcia_core.ports.llm_streaming_port import (
        LlmChatTurnOutcome,
        LlmStreamDelta,
        LlmStreamingPort,
        LlmStreamRequest,
    )

    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    isolated_app = create_app()
    with TestClient(isolated_app) as client:
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        req_dummy = type("Req", (), {"app": isolated_app})()
        cassette_port = get_llm_streaming_port(req_dummy)  # type: ignore[arg-type]
        assert getattr(cassette_port, "is_cassette_adapter", False) is True

        monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
        live_port = get_llm_streaming_port(req_dummy)  # type: ignore[arg-type]
        assert isinstance(live_port, HttpxMultiProviderLlmStreamingAdapter)

        up_res = client.post(
            "/api/v1/agents-and-skills/agents",
            params={"persona_key": "marc"},
            json={
                "agent_id": "agent-spy-di",
                "name": "Spy DI Agent",
                "role_mission": "Verify LlmStreamingPort injection",
                "instructions": "Respond concisely.",
                "thinking_level": "simple",
            },
        )
        assert up_res.status_code == 200

        calls: list[str] = []

        class _SpyLlmPort(LlmStreamingPort):
            async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
                calls.append(request.messages[-1]["content"])
                return LlmChatTurnOutcome(
                    content="SPY_DI_AGENT_OK", thinking_text="spy", latency_ms=1.0
                )

            async def stream_chat_sse(self, request: LlmStreamRequest):
                yield LlmStreamDelta(event="turn_completed", accumulated_text="SPY_DI_AGENT_OK")

        isolated_app.state.llm_streaming_port = _SpyLlmPort()
        try:
            res = client.post(
                "/api/v1/agents-and-skills/agents/agent-spy-di/execute",
                params={"persona_key": "marc"},
                json={"prompt": "Inspect Jira sprint health"},
            )
            assert res.status_code == 200
            assert "SPY_DI_AGENT_OK" in res.json()["response_text"]
            assert calls == ["Inspect Jira sprint health"]
        finally:
            isolated_app.state.llm_streaming_port = None
