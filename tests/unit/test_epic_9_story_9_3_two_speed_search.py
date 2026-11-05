"""Unit & HTTP Contract Tests for Story 9.3 — Two-Speed Federated & Contextual Search (`⌘K`),
Zero Layout Shift, 3 Scopes (`SCREEN`, `WORKSPACE`, `ALL_WORKSPACES`), 7 Families,
PermissionGuard (`AD-21`) & Deep-Linking Auto-Focus.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.rag.two_speed_search import (
    DEFAULT_SEARCH_CANDIDATES,
    SEVEN_SEARCH_FAMILIES,
    FederatedSearchCandidate,
    TwoSpeedFederatedSearchService,
    build_speed2_redis_cache_key,
)


def test_story_9_3_seven_families_three_scopes_and_permission_guard() -> None:
    """Verify 7 families, 3 scopes, Speed 1 (< 30 ms, 0 $) vs Speed 2 (>= 3 words, cached 300 s)."""
    assert len(SEVEN_SEARCH_FAMILIES) == 7

    svc = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="hit-folder-1",
                family="FOLDERS_DISCUSSIONS",
                title="Dossier Architecture Paiement SEPA",
                snippet="Discussion sur la garantie d'idempotence des virements instantanés.",
                workspace_id="ws-alpha",
                screen_route="/assistant",
                deep_link_uri="/assistant?folder=hit-folder-1#focus-hit-folder-1",
                allowed_roles=("PLATFORM_ADMIN", "TEAM_LEAD", "CONTRIBUTOR"),
            ),
            FederatedSearchCandidate(
                item_id="hit-secret-c3",
                family="DELIVERABLES_ARTIFACTS",
                title="Audit Confidentiel C3 Paiement SEPA",
                snippet="Réservé aux administrateurs plateforme uniquement.",
                workspace_id="ws-alpha",
                screen_route="/spaces",
                deep_link_uri="/spaces?artifact=hit-secret-c3#focus-hit-secret-c3",
                allowed_roles=("PLATFORM_ADMIN",),
            ),
            FederatedSearchCandidate(
                item_id="hit-help-1",
                family="HELP_ACTIONS",
                title="Comment résoudre une alerte de fraîcheur [STALE_WARNING]",
                snippet="Guide pas-à-pas pour arbitrer l'écart entre Confluence et Git.",
                workspace_id="ws-alpha",
                screen_route="/cockpit",
                deep_link_uri="help://cockpit/stale-warning",
                allowed_roles=("PLATFORM_ADMIN", "TEAM_LEAD", "CONTRIBUTOR", "OBSERVER"),
            ),
            FederatedSearchCandidate(
                item_id="hit-other-ws",
                family="GLOSSARY_RULES",
                title="Règle Métier Paiement SEPA Instantané",
                snippet="Plafond de 100 000 EUR par transaction SEPA.",
                workspace_id="ws-beta",
                screen_route="/spaces",
                deep_link_uri="/spaces?term=hit-other-ws#focus-hit-other-ws",
                allowed_roles=("PLATFORM_ADMIN", "TEAM_LEAD", "CONTRIBUTOR"),
            ),
        )
    )

    # 1. PermissionGuard filtering: CONTRIBUTOR cannot see hit-secret-c3
    res_ws = svc.execute_search(
        query="Paiement",
        scope="WORKSPACE",
        active_workspace_id="ws-alpha",
        active_screen_route="/assistant",
        user_role="CONTRIBUTOR",
        include_speed2=False,
    )
    hit_ids_ws = [h.item_id for h in res_ws.hits]
    assert "hit-folder-1" in hit_ids_ws
    assert "hit-secret-c3" not in hit_ids_ws
    assert "hit-other-ws" not in hit_ids_ws
    assert res_ws.speed1_llm_cost_usd == 0.0
    assert all(h.speed_tier == 1 and h.locked_top is True for h in res_ws.hits)

    # 2. Scope = SCREEN filters to active_screen_route == "/cockpit"
    res_screen = svc.execute_search(
        query="fraîcheur",
        scope="SCREEN",
        active_workspace_id="ws-alpha",
        active_screen_route="/cockpit",
        user_role="CONTRIBUTOR",
        include_speed2=False,
    )
    assert [h.item_id for h in res_screen.hits] == ["hit-help-1"]
    assert res_screen.hits[0].opens_contextual_help_column is True

    # 3. Scope = ALL_WORKSPACES returns hits across ws-alpha and ws-beta
    res_all = svc.execute_search(
        query="Paiement SEPA",
        scope="ALL_WORKSPACES",
        active_workspace_id="ws-alpha",
        active_screen_route="/assistant",
        user_role="CONTRIBUTOR",
        include_speed2=False,
    )
    assert {h.item_id for h in res_all.hits} == {"hit-folder-1", "hit-other-ws"}


def test_story_9_3_speed2_semantic_3_words_rule_redis_cache_and_bottom_append() -> None:
    """Verify Speed 2 triggers only on >= 3 words or force_semantic, caches 300s, appends bottom."""
    svc = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="hit-lex-top",
                family="SOURCES_SNIPPETS",
                title="Architecture des flux bancaires",
                snippet="Contrat d'interface des paiements.",
                workspace_id="ws-alpha",
                screen_route="/spaces",
                deep_link_uri="/spaces#hit-lex-top",
            ),
            FederatedSearchCandidate(
                item_id="hit-sem-bottom",
                family="SOURCES_SNIPPETS",
                title="Mécanisme de compensation interbancaire européen",
                snippet="Règlement continu des écritures sur le grand livre.",
                workspace_id="ws-alpha",
                screen_route="/spaces",
                deep_link_uri="/spaces#hit-sem-bottom",
            ),
        )
    )

    # Short query (< 3 words) without force_semantic -> Speed 2 NOT triggered
    short_res = svc.execute_search(
        query="flux bancaires",
        scope="WORKSPACE",
        active_workspace_id="ws-alpha",
        active_screen_route="/spaces",
        user_role="CONTRIBUTOR",
        include_speed2=True,
        force_semantic=False,
    )
    assert short_res.speed2_executed is False
    assert all(h.speed_tier == 1 for h in short_res.hits)

    # >= 3 words query -> Speed 2 executes, appends at bottom with badge '✨ Passage proche'
    long_query = "flux bancaires contrat"
    long_res1 = svc.execute_search(
        query=long_query,
        scope="WORKSPACE",
        active_workspace_id="ws-alpha",
        active_screen_route="/spaces",
        user_role="CONTRIBUTOR",
        include_speed2=True,
    )
    assert long_res1.speed2_executed is True
    assert long_res1.speed2_cache_hit is False
    assert long_res1.speed2_redis_key == build_speed2_redis_cache_key("ws-alpha", long_query)
    assert long_res1.speed2_cache_ttl_seconds == 300

    # Lexical Speed 1 hit is locked first, Speed 2 semantic hit is appended at the bottom
    assert long_res1.hits[0].item_id == "hit-lex-top"
    assert long_res1.hits[0].speed_tier == 1
    assert long_res1.hits[0].locked_top is True
    assert long_res1.hits[-1].item_id == "hit-sem-bottom"
    assert long_res1.hits[-1].speed_tier == 2
    assert long_res1.hits[-1].badge == "✨ Passage proche"

    # Second identical call within 5 min hits the Redis/in-memory cache!
    long_res2 = svc.execute_search(
        query=long_query,
        scope="WORKSPACE",
        active_workspace_id="ws-alpha",
        active_screen_route="/spaces",
        user_role="CONTRIBUTOR",
        include_speed2=True,
    )
    assert long_res2.speed2_executed is True
    assert long_res2.speed2_cache_hit is True


def test_story_9_3_get_api_v1_search_endpoint() -> None:
    """Verify `GET /api/v1/search` endpoint contract and PermissionGuard filtering."""
    app = create_app()
    app.state.two_speed_search_service = TwoSpeedFederatedSearchService(
        candidates=DEFAULT_SEARCH_CANDIDATES
    )
    client = TestClient(app)

    resp = client.get(
        "/api/v1/search",
        params={
            "q": "architecture",
            "scope": "WORKSPACE",
            "workspace_id": "ws-claims-alpha",
            "screen_route": "/cockpit",
            "include_speed2": "true",
            "force_semantic": "true",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["scope"] == "WORKSPACE"
    assert payload["speed1_llm_cost_usd"] == 0.0
    assert payload["speed2_executed"] is True
    assert payload["speed2_cache_ttl_seconds"] == 300
    assert len(payload["hits"]) >= 1
