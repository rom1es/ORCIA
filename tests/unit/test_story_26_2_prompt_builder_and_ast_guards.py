"""Story 26.2 — AST hygiene, file-size caps, localization, and DI wiring guards."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    locales_dir = REPO_ROOT / "apps" / "web" / "src" / "i18n" / "locales"
    en_locale = locales_dir / "feature_inbox_assistant_labels_en.ts"
    fr_locale = locales_dir / "feature_inbox_assistant_labels_fr.ts"
    src = helper.read_text(encoding="utf-8")
    assert "flowCopy.attachmentHeader" in src
    assert "resolveDictionaryForFlag" in src
    assert "User-supplied attachments" in en_locale.read_text(encoding="utf-8")
    assert "Pièces jointes" in fr_locale.read_text(encoding="utf-8")


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
