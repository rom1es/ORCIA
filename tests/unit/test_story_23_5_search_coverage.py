"""Story 23.5 — Unit & HTTP Contract Coverage for Two-Speed Search, SQL Loader & Portal Router."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_api.main import create_app
from orcia_core.rag._internal.sql_federated_search import (
    _map_catalog_family,
    load_federated_search_candidates_pg18,
)
from orcia_core.rag.two_speed_search import (
    FederatedSearchCandidate,
    TwoSpeedFederatedSearchService,
)


class _FakeResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeAsyncConnection:
    """Minimal stub AsyncConnection capturing SQL & bind params for isolation tests."""

    def __init__(self, table_rows: dict[str, list[tuple[Any, ...]]]) -> None:
        self._table_rows = table_rows
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = str(stmt)
        self.executed.append((sql, params))
        if "FROM pg_tables" in sql:
            return _FakeResult([(name,) for name in self._table_rows])
        if "FROM catalog_items" in sql:
            return _FakeResult(self._table_rows.get("catalog_items", []))
        if "FROM workflow_definitions_v2" in sql:
            return _FakeResult(self._table_rows.get("workflow_definitions_v2", []))
        if "FROM declarative_pack_bundles" in sql:
            return _FakeResult(self._table_rows.get("declarative_pack_bundles", []))
        if "FROM assistant_folders" in sql:
            return _FakeResult(self._table_rows.get("assistant_folders", []))
        if "FROM workspaces" in sql:
            return _FakeResult(self._table_rows.get("workspaces", []))
        return _FakeResult([])


def test_map_catalog_family_covers_all_resource_and_item_types() -> None:
    assert _map_catalog_family("template", "HELP_ARTICLE") == ("HELP_ACTIONS", "/help", "/help")
    assert _map_catalog_family("agent", "CATALOG_RESOURCE") == (
        "AGENTS_SKILLS",
        "/agents",
        "/agents",
    )
    assert _map_catalog_family("skill", "CATALOG_RESOURCE") == (
        "AGENTS_SKILLS",
        "/agents",
        "/agents",
    )
    assert _map_catalog_family("datasource", "CATALOG_RESOURCE") == (
        "SOURCES_SNIPPETS",
        "/spaces",
        "/spaces",
    )
    assert _map_catalog_family("workflow", "CATALOG_RESOURCE") == (
        "PROCESSES_EXECUTIONS",
        "/processes",
        "/processes",
    )


async def test_load_federated_search_candidates_pg18_maps_all_five_tables() -> None:
    conn = _FakeAsyncConnection(
        {
            "workspace_memberships": [],
            "assistant_folder_shares": [],
            "catalog_items": [
                (
                    "res-help",
                    "orcia://help/1",
                    "Aide Cockpit",
                    "",
                    "template",
                    "HELP_ARTICLE",
                    "GLOBAL",
                    "PUBLISHED_ORG",
                ),
                (
                    "res-agent",
                    "orcia://agents/1",
                    "Agent Archi",
                    "Analyse architecture",
                    "agent",
                    "CATALOG_RESOURCE",
                    "ws-1",
                    "SHARED_WORKSPACE",
                ),
                (
                    "res-ds",
                    "orcia://ds/1",
                    "Git Core",
                    "Dépôt principal",
                    "datasource",
                    "CATALOG_RESOURCE",
                    "ws-1",
                    "SHARED_TEAM",
                ),
                (
                    "res-wf",
                    "orcia://wf/1",
                    "Workflow Spec",
                    "Génération spec",
                    "workflow",
                    "CATALOG_RESOURCE",
                    "GLOBAL",
                    "PENDING_APPROVAL",
                ),
            ],
            "workflow_definitions_v2": [
                (
                    "wf-2",
                    "ticket-spec",
                    "orcia-pack-sdlc",
                    "Ticket to Spec",
                    "Synthèse spec",
                    "draft",
                ),
            ],
            "declarative_pack_bundles": [
                ("pack-1", "sdlc-pack", "Pack SDLC", "2.1.0"),
            ],
            "workspaces": [
                (
                    "0195f000-0000-7000-8000-000000000001",
                    "Espace Paiement",
                    "ws-paiement",
                    "STANDARD",
                ),
            ],
            "assistant_folders": [
                (
                    "0195f000-0000-7000-8000-000000000002",
                    "0195f000-0000-7000-8000-000000000001",
                    "Dossier SEPA",
                    "Résumé SEPA",
                ),
            ],
        }
    )

    candidates = await load_federated_search_candidates_pg18(  # type: ignore[arg-type]
        conn, user_id="user-a", user_role="CONTRIBUTOR", primary_org_unit_id="org-1"
    )
    by_id = {c.item_id: c for c in candidates}
    assert by_id["pg-catalog:res-help"].family == "HELP_ACTIONS"
    assert by_id["pg-catalog:res-help"].snippet == "orcia://help/1"
    assert by_id["pg-catalog:res-agent"].family == "AGENTS_SKILLS"
    assert by_id["pg-catalog:res-ds"].family == "SOURCES_SNIPPETS"
    assert by_id["pg-catalog:res-wf"].family == "PROCESSES_EXECUTIONS"
    assert by_id["pg-catalog:res-wf"].allowed_roles == ("PLATFORM_ADMIN", "BU_DIRECTOR", "BU_LEAD")
    assert by_id["pg-workflow:wf-2"].deep_link_uri == "/processes/studio/wf-2"
    assert "OBSERVER" not in by_id["pg-workflow:wf-2"].allowed_roles
    assert by_id["pg-pack:pack-1"].deep_link_uri == "/settings/packs"
    ws_cand = by_id["pg-workspace:0195f000-0000-7000-8000-000000000001"]
    assert ws_cand.family == "FOLDERS_DISCUSSIONS"
    assert by_id["pg-folder:0195f000-0000-7000-8000-000000000002"].screen_route == "/assistant"

    # Verify SQL tenant/RBAC predicates and fail-closed behavior for anonymous caller
    executed_sql = "\n".join(sql for sql, _ in conn.executed)
    assert "assistant_folder_shares" in executed_sql
    assert "workspace_memberships" in executed_sql
    assert "PRIVATE_USER" in executed_sql
    assert "f.owner_user_id::text = :uid" in executed_sql

    anon_conn = _FakeAsyncConnection(
        {
            "assistant_folders": [
                ("f-secret", "ws-1", "Dossier Privé", "Secret"),
            ]
        }
    )
    anon_cands = await load_federated_search_candidates_pg18(anon_conn, user_id="")  # type: ignore[arg-type]
    assert not any(c.item_id.startswith("pg-folder:") for c in anon_cands)


def test_speed2_cache_key_isolates_users_and_roles() -> None:
    svc = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="ws-item-1",
                family="FOLDERS_DISCUSSIONS",
                title="Note Stratégique Paiement",
                snippet="Détails confidentiels",
                workspace_id="ws-1",
                screen_route="/assistant",
                deep_link_uri="/assistant",
                allowed_roles=("PLATFORM_ADMIN", "CONTRIBUTOR"),
            ),
        )
    )
    res_user_a = svc.execute_search(
        query="paiement stratégie architecture",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        user_id="user-a",
        user_role="CONTRIBUTOR",
        include_speed2=True,
        query_embedding=(1.0, 0.0),
    )
    res_user_b = svc.execute_search(
        query="paiement stratégie architecture",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        user_id="user-b",
        user_role="CONTRIBUTOR",
        include_speed2=True,
        query_embedding=(1.0, 0.0),
    )
    assert res_user_a.speed2_redis_key != res_user_b.speed2_redis_key
    assert res_user_a.speed2_cache_hit is False
    assert res_user_b.speed2_cache_hit is False
    assert "user-a" in (res_user_a.speed2_redis_key or "")
    assert "user-b" in (res_user_b.speed2_redis_key or "")


def test_two_speed_search_deduplicates_candidates_and_handles_embeddings_and_scopes() -> None:
    svc = TwoSpeedFederatedSearchService()
    svc.register_candidate(
        FederatedSearchCandidate(
            item_id="dup-1",
            family="AGENTS_SKILLS",
            title="Agent Principal",
            snippet="Validation architecture",
            workspace_id="ws-1",
            screen_route="/agents",
            deep_link_uri="/agents",
            embedding=(1.0, 0.0, 0.0),
        )
    )
    svc.register_candidate(
        FederatedSearchCandidate(
            item_id="sem-only-2",
            family="GLOSSARY_RULES",
            title="Règle Hexa",
            snippet="Séparation ports et adaptateurs",
            workspace_id="ws-1",
            screen_route="/spaces",
            deep_link_uri="/spaces",
            embedding=(0.9, 0.1, 0.0),
        )
    )

    # Extra candidate with duplicate item_id must NOT duplicate results
    report_dup = svc.execute_search(
        query="Agent",
        scope="WORKSPACE",
        active_workspace_id="GLOBAL",
        active_screen_route="/cockpit",
        include_speed2=False,
        extra_candidates=(
            FederatedSearchCandidate(
                item_id="dup-1",
                family="AGENTS_SKILLS",
                title="Duplicate Ignored",
                snippet="Should be ignored",
                workspace_id="ws-1",
                screen_route="/agents",
                deep_link_uri="/agents",
            ),
            FederatedSearchCandidate(
                item_id="extra-screen-only",
                family="HELP_ACTIONS",
                title="Aide Agent Écran",
                snippet="Guide rapide",
                workspace_id="ws-1",
                screen_route="/agents",
                deep_link_uri="/help",
            ),
        ),
    )
    assert [h.item_id for h in report_dup.hits] == ["dup-1", "extra-screen-only"]

    # SCREEN scope filters out items from other routes
    report_screen = svc.execute_search(
        query="Agent",
        scope="SCREEN",
        active_workspace_id="ws-1",
        active_screen_route="/cockpit",
        include_speed2=False,
    )
    assert report_screen.hits == ()

    # Speed 2 without query_embedding gracefully falls back to Speed 1 only
    report_no_vec = svc.execute_search(
        query="Agent Principal architecture",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        include_speed2=True,
        query_embedding=None,
    )
    assert report_no_vec.speed2_executed is False
    assert [h.item_id for h in report_no_vec.hits] == ["dup-1"]

    # Speed 2 with vector uses cosine similarity on cand.embedding and deduplicates Speed 1 hits
    report_vec = svc.execute_search(
        query="Agent Principal architecture",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        include_speed2=True,
        query_embedding=(1.0, 0.0, 0.0),
    )
    assert report_vec.speed2_executed is True
    assert report_vec.speed2_cache_hit is False
    assert [h.item_id for h in report_vec.hits] == ["dup-1", "sem-only-2"]
    assert report_vec.hits[0].speed_tier == 1
    assert report_vec.hits[1].speed_tier == 2
    assert report_vec.hits[1].score > 0.5


def test_portal_and_help_search_scopes_global_and_contextual() -> None:
    app = create_app()
    app.state.embedding_port = FakeDeterministicEmbeddingAdapter()
    app.state.two_speed_search_service = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="pg-catalog:1",
                family="AGENTS_SKILLS",
                title="Agent Audit",
                snippet="Contrôle qualité",
                workspace_id="ws-other",
                screen_route="/agents",
                deep_link_uri="/agents",
            ),
        )
    )
    client = TestClient(app)

    r_global = client.get(
        "/api/v1/search",
        params={"q": "Audit", "scope": "GLOBAL", "workspace_id": "", "include_speed2": "false"},
    )
    assert r_global.status_code == 200
    assert r_global.json()["scope"] == "ALL_WORKSPACES"
    assert [h["item_id"] for h in r_global.json()["hits"]] == ["pg-catalog:1"]

    r_ctx = client.get(
        "/api/v1/search",
        params={"q": "Audit", "scope": "CONTEXTUAL", "workspace_id": "ws-claims-alpha"},
    )
    assert r_ctx.status_code == 200
    assert r_ctx.json()["scope"] == "WORKSPACE"
    assert r_ctx.json()["hits"] == []


async def test_load_federated_search_candidates_pg18_visibility_branches() -> None:
    conn = _FakeAsyncConnection(
        {
            "catalog_items": [
                (
                    "res-draft",
                    "orcia://draft/1",
                    "Brouillon Agent",
                    "Brouillon interne",
                    "agent",
                    "CATALOG_RESOURCE",
                    "ws-1",
                    "DRAFT",
                ),
            ],
            "workspaces": [
                ("ws-priv", "Espace Privé", "ws-priv", "PRIVATE_USER"),
                ("ws-conf", "Espace Confidentiel", "ws-conf", "CONFIDENTIAL_RESTRICTED"),
            ],
            "assistant_folders": [
                ("f-open", "ws-priv", "Dossier Ouvert", "Résumé"),
            ],
        }
    )

    candidates = await load_federated_search_candidates_pg18(  # type: ignore[arg-type]
        conn, user_id="user-b", user_role="CONTRIBUTOR"
    )
    by_id = {c.item_id: c for c in candidates}
    assert "OBSERVER" not in by_id["pg-catalog:res-draft"].allowed_roles
    assert by_id["pg-workspace:ws-priv"].allowed_roles == ("CONTRIBUTOR",)
    assert by_id["pg-workspace:ws-conf"].allowed_roles == ("CONTRIBUTOR",)
    assert by_id["pg-folder:f-open"].allowed_roles == ("CONTRIBUTOR",)

    # Non-member PLATFORM_ADMIN sees zero CONFIDENTIAL_RESTRICTED workspace candidates
    admin_no_member_conn = _FakeAsyncConnection(
        {
            "workspaces": [],
        }
    )
    admin_cands = await load_federated_search_candidates_pg18(  # type: ignore[arg-type]
        admin_no_member_conn, user_id="admin-non-member", user_role="PLATFORM_ADMIN"
    )
    assert admin_cands == ()
    ws_sqls = [sql for sql, _ in admin_no_member_conn.executed if "FROM workspaces" in sql]
    assert ws_sqls and all(":is_admin" not in sql for sql in ws_sqls)

    # Without workspaces table, assistant_folders uses fallback WORKSPACE_OPEN clause
    no_ws_conn = _FakeAsyncConnection(
        {
            "assistant_folders": [("f-only", "ws-1", "Dossier Sans WS", "")],
        }
    )
    no_ws_cands = await load_federated_search_candidates_pg18(  # type: ignore[arg-type]
        no_ws_conn, user_id="user-b", user_role="PLATFORM_ADMIN"
    )
    assert [c.item_id for c in no_ws_cands] == ["pg-folder:f-only"]
