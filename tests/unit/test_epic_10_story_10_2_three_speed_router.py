"""Story 10.2 — Unit & API tests for Redis 5-Layer Prompt Cache (`TTL 300s`) & 3-Speed Router.

Validates:
- `assistant:prompt:<workspace_id>:<user_id>:<hat>` cache (`TTL = 300s`, `< 5 ms` read)
  with MISS -> HIT and deterministic invalidation on:
  1. `SETTINGS_CHANGED` Outbox event,
  2. `OVERRIDE_UPDATED` (`workspace_customization_overrides`),
  3. `GLOSSARY_PROMOTED`.
- 3-Speed Conversational Routing:
  - `SPEED_1_FAST` (`⚡ Rapide`, default): Nodes 1–4 `< 80 ms` deterministic (`0` intermediate LLM
    calls) + `1` single SSE streaming LLM call (`TTFT < 1200 ms`).
  - `SPEED_2_AGENT_TOOLS` (`@Agent` / `/Skill`): triggered by `@jira-triage` or `/audit-adn`,
    streams `🔍 Interrogation de Jira...` (`TTFT < 2500 ms`).
  - `SPEED_3_DEEP_AUDIT` (`🧠 Approfondi`): triggered by `deep_audit_pill_active=True`, runs
    intermediate LLM planning and multi-lens `AD-10` verification (`intermediate_llm_calls = 2`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import app
from orcia_core.orchestration.assistant_three_speed_router import (
    MAX_NODES_1_TO_4_DETERMINISTIC_MS,
    PROMPT_CACHE_TTL_SECONDS,
    SPEED_1_TTFT_SLO_MS,
    SPEED_2_TTFT_SLO_MS,
    AssistantThreeSpeedRouterService,
    build_assistant_prompt_cache_key,
)
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import PlatformRole, UserIdentity


def _make_user(
    *,
    user_id: str = "u-claire-01",
    role: PlatformRole = "CONTRIBUTOR",
    archetype: str = "PM",
) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.local",
        display_name=user_id,
        auth_mode="LOCAL",
        human_profile_archetype=archetype,
        platform_role=role,
        primary_org_unit_id="org-unit-alpha",
    )


def test_story_10_2_prompt_cache_hit_miss_and_three_invalidation_triggers() -> None:
    """Verify `assistant:prompt:<ws>:<user>:<hat>` cache (< 5 ms) and all 3 invalidation reasons."""
    svc = AssistantThreeSpeedRouterService()
    key = build_assistant_prompt_cache_key("ws-claims-alpha", "u-claire-01", "PM")
    assert key == "assistant:prompt:ws-claims-alpha:u-claire-01:PM"

    # 1st lookup: MISS -> populates cache with TTL = 300s
    first = svc.get_or_assemble_cached_prompt(
        workspace_id="ws-claims-alpha",
        user_id="u-claire-01",
        hat="PM",
    )
    assert first.cache_hit is False
    assert first.ttl_seconds == PROMPT_CACHE_TTL_SECONDS
    assert first.lookup_latency_ms < 5.0
    assert len(first.layers) == 5

    # 2nd lookup: HIT (< 5 ms)
    second = svc.get_or_assemble_cached_prompt(
        workspace_id="ws-claims-alpha",
        user_id="u-claire-01",
        hat="PM",
    )
    assert second.cache_hit is True
    assert second.lookup_latency_ms < 5.0
    assert second.layers_sha256 == first.layers_sha256

    # Invalidation #1: SETTINGS_CHANGED
    inv1 = svc.invalidate_prompt_cache(
        workspace_id="ws-claims-alpha",
        reason="SETTINGS_CHANGED",
    )
    assert inv1.invalidated_keys_count == 1
    after_inv1 = svc.get_or_assemble_cached_prompt(
        workspace_id="ws-claims-alpha",
        user_id="u-claire-01",
        hat="PM",
    )
    assert after_inv1.cache_hit is False

    # Invalidation #2: OVERRIDE_UPDATED (user-scoped)
    inv2 = svc.invalidate_prompt_cache(
        workspace_id="ws-claims-alpha",
        reason="OVERRIDE_UPDATED",
        user_id="u-claire-01",
    )
    assert inv2.invalidated_keys_count == 1

    # Repopulate then Invalidation #3: GLOSSARY_PROMOTED
    svc.get_or_assemble_cached_prompt(
        workspace_id="ws-claims-alpha",
        user_id="u-claire-01",
        hat="PM",
    )
    inv3 = svc.invalidate_prompt_cache(
        workspace_id="ws-claims-alpha",
        reason="GLOSSARY_PROMOTED",
    )
    assert inv3.invalidated_keys_count == 1


def test_story_10_2_three_speeds_routing_and_slos() -> None:
    """Verify Speed 1 (`< 80 ms` + `< 1.2s`), Speed 2 (`@Agent` `< 2.5s`), and Speed 3 (`🧠`)."""
    svc = AssistantThreeSpeedRouterService()
    claire = _make_user(user_id="u-claire-01", role="CONTRIBUTOR", archetype="PM")
    observer = _make_user(user_id="u-obs", role="OBSERVER", archetype="PM")

    with pytest.raises(ObserverModeReadOnlyError):
        svc.execute_three_speed_turn(
            observer,
            workspace_id="ws-claims-alpha",
            user_prompt="Bonjour",
        )

    # Speed 1 (Fast, default): Nodes 1-4 < 80 ms, 0 intermediate LLM calls, TTFT < 1200 ms
    turn_s1 = svc.execute_three_speed_turn(
        claire,
        workspace_id="ws-claims-alpha",
        user_prompt="Quelles sont les règles d'arbitrage sur le dossier sinistre ?",
    )
    assert turn_s1.speed_mode == "SPEED_1_FAST"
    assert turn_s1.nodes_1_to_4_deterministic_ms < MAX_NODES_1_TO_4_DETERMINISTIC_MS
    assert turn_s1.intermediate_llm_calls == 0
    assert turn_s1.ttft_ms < SPEED_1_TTFT_SLO_MS

    # Speed 2 (@Agent or /Skill): streams `🔍 Interrogation de Jira...`, TTFT < 2500 ms
    turn_s2 = svc.execute_three_speed_turn(
        claire,
        workspace_id="ws-claims-alpha",
        user_prompt="Vérifie avec @jira-triage et /audit-adn l'état du sprint",
    )
    assert turn_s2.speed_mode == "SPEED_2_AGENT_TOOLS"
    assert turn_s2.invoked_targets == ("@jira-triage", "/audit-adn")
    assert turn_s2.ttft_ms < SPEED_2_TTFT_SLO_MS
    assert any("🔍 Interrogation de Jira..." in st.label for st in turn_s2.step_progress)

    # Speed 3 (🧠 Approfondi): intermediate planning + multi-lens AD-10 verification
    turn_s3 = svc.execute_three_speed_turn(
        claire,
        workspace_id="ws-claims-alpha",
        user_prompt="Analyse contradictoire complète de la conformité N1–N3",
        deep_audit_pill_active=True,
    )
    assert turn_s3.speed_mode == "SPEED_3_DEEP_AUDIT"
    assert turn_s3.intermediate_llm_calls == 2
    assert "ARCHITECTURE_CONSISTENCY" in turn_s3.deep_audit_lenses
    assert len(turn_s3.step_progress) == 4


def test_story_10_2_api_endpoints_turn_stream_and_invalidation() -> None:
    """Verify `/api/v1/assistant/three-speed/*` endpoints (`Story 10.2`)."""
    with TestClient(app) as client:
        # 1st turn (MISS -> populates cache)
        r1 = client.post(
            "/api/v1/assistant/three-speed/turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Synthèse rapide des règles de gestion",
            },
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["speed_mode"] == "SPEED_1_FAST"
        assert d1["ttft_ms"] < 1200.0

        # 2nd turn (HIT)
        r2 = client.post(
            "/api/v1/assistant/three-speed/turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Interroge @jira-triage sur l'épic 10",
            },
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["cache_hit"] is True
        assert d2["speed_mode"] == "SPEED_2_AGENT_TOOLS"

        # SSE stream endpoint
        stream_resp = client.post(
            "/api/v1/assistant/three-speed/stream",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Audit approfondi",
                "deep_audit_pill_active": True,
            },
        )
        assert stream_resp.status_code == 200
        assert "event: cache_status" in stream_resp.text
        assert "event: step_progress" in stream_resp.text
        assert "SPEED_3_DEEP_AUDIT" in stream_resp.text

        # Invalidate cache on GLOSSARY_PROMOTED
        inv_resp = client.post(
            "/api/v1/assistant/three-speed/invalidate-cache",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "ws-claims-alpha",
                "reason": "GLOSSARY_PROMOTED",
            },
        )
        assert inv_resp.status_code == 200
        assert inv_resp.json()["invalidated_keys_count"] >= 1


def test_story_10_2_live_llm_bridge_ollama_and_openai_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify live LLM bridge resolves configured tier (`Ollama Local` `/api` or `/v1`)."""
    from typing import Any

    import httpx

    import orcia_core.bootstrap as bm
    from orcia_api.routers.assistant_llm_bridge import (
        _build_ollama_root_url,
        _extract_tier_endpoint_from_dict,
    )

    assert _build_ollama_root_url("http://localhost:11434/api") == "http://localhost:11434"
    assert _build_ollama_root_url("http://localhost:11434/v1") == "http://localhost:11434"

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

    class _FakeHttpResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "message": {
                    "role": "assistant",
                    "content": "Bonjour, je suis votre Assistant ORCIA propulsé par gemma4:12b.",
                }
            }

    class _FakeHttpClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> _FakeHttpClient:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def post(self, url: str, **kwargs: Any) -> _FakeHttpResponse:
            assert url == "http://localhost:11434/api/chat"
            return _FakeHttpResponse()

    monkeypatch.setenv("ORCIA_FORCE_LIVE_LLM_IN_TESTS", "1")
    monkeypatch.setattr(httpx, "Client", _FakeHttpClient)

    with TestClient(app) as client:
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
        r_live = client.post(
            "/api/v1/assistant/three-speed/turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Bonjour",
            },
        )
        assert r_live.status_code == 200
        data_live = r_live.json()
        assert "gemma4:12b" in data_live["response_text"]
        assert any("gemma4:12b" in st["label"] for st in data_live["step_progress"])


def test_story_10_2_live_llm_bridge_tier_selection_and_thinking_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `requested_tier` and `thinking_effort` routing in `assistant_llm_bridge`."""
    from typing import Any

    import httpx

    import orcia_core.bootstrap as bm
    from orcia_api.routers.assistant_llm_bridge import (
        _select_endpoint_from_tiers,
        build_assistant_system_instructions,
    )

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
            "endpointUrl": "http://localhost:11434/api",
            "authMode": "none_local",
        },
    ]

    ep_simple = _select_endpoint_from_tiers(tiers_cfg, "simple")
    ep_medium = _select_endpoint_from_tiers(tiers_cfg, "medium")
    ep_complex = _select_endpoint_from_tiers(tiers_cfg, "complex")
    assert ep_simple is not None and ep_simple.model_name == "gemma4:4b-fast"
    assert ep_medium is not None and ep_medium.model_name == "gemma4:12b"
    assert ep_complex is not None and ep_complex.model_name == "gemma4:27b-pro"

    sys_fast = build_assistant_system_instructions(
        hat="PM",
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
    assert "Palier Raisonnement avancé" in sys_deep
    assert "Niveau de réflexion Élevé" in sys_deep

    captured_models: list[str] = []
    captured_sys_prompts: list[str] = []

    class _FakeHttpResponse:
        def __init__(self, model: str) -> None:
            self._model = model

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "message": {
                    "role": "assistant",
                    "content": f"Réponse générée par {self._model}.",
                }
            }

    class _FakeHttpClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> _FakeHttpClient:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def post(self, url: str, **kwargs: Any) -> _FakeHttpResponse:
            json_body = kwargs.get("json", {})
            model = str(json_body.get("model", ""))
            msgs = json_body.get("messages", [])
            captured_models.append(model)
            if msgs:
                captured_sys_prompts.append(str(msgs[0].get("content", "")))
            return _FakeHttpResponse(model)

    monkeypatch.setenv("ORCIA_FORCE_LIVE_LLM_IN_TESTS", "1")
    monkeypatch.setattr(httpx, "Client", _FakeHttpClient)

    with TestClient(app) as client:
        app.state.platform_setup_snapshot = bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=True,
            first_admin_email="admin@orcia.io",
            first_admin_display_name="Admin",
            llm_tiers=tiers_cfg,
        )
        r_complex_deep = client.post(
            "/api/v1/assistant/three-speed/turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "user_prompt": "Analyse critique complète du dossier",
                "requested_tier": "complex",
                "thinking_effort": "deep",
            },
        )
        assert r_complex_deep.status_code == 200
        d_complex = r_complex_deep.json()
        assert d_complex["speed_mode"] == "SPEED_3_DEEP_AUDIT"
        assert "gemma4:27b-pro" in d_complex["response_text"]
        assert captured_models[-1] == "gemma4:27b-pro"
        assert "Niveau de réflexion Élevé" in captured_sys_prompts[-1]
        assert any("Réflexion Élevée" in st["label"] for st in d_complex["step_progress"])
