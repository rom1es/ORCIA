"""Story 25.5 — Unit tests for AD-24 Epic 25 decoupling & RAG datasource guard.

Proves:
1. `AssistantAgentService` responds normally when `embedding_available=False` (empty RAG hits,
   `rag_active=False`, `"kb"` excluded, zero `ERR_NO_ACTIVE_EMBEDDING_MODEL`).
2. All 5 Assistant FastAPI endpoints (`/chat`, `/chat/stream`, `/three-speed/turn`,
   `/three-speed/stream`, `/threads/{thread_id}/turns`) and `GET /api/v1/search` succeed (`200`)
   even when `get_embedding_port` raises `NoActiveEmbeddingModelError` or
   `RagReindexInProgressError`.
3. In live LLM mode (non-cassette), `0` active `chat` model (including when
   only an `embedding` model exists) raises HTTP `422 ERR_TIER_MODEL_NOT_CONFIGURED`.
4. `create_workspace_datasource_on_postgres18` and
   `assert_active_global_embedding_model_for_rag_source` reject `DOCUMENT_KB`, `WORK_TRACKER`,
   and `RELATIONAL_SCHEMA` with `422 ERR_NO_ACTIVE_EMBEDDING_MODEL` BEFORE any SQL `INSERT`,
   while permitting `SOURCE_CODE`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies import get_embedding_port
from orcia_api.main import create_app
from orcia_core.bootstrap._internal._sql_workspace_datasources_sync import (
    assert_active_global_embedding_model_for_rag_source,
)
from orcia_core.bootstrap._internal.sql_workspace_datasources_mutations import (
    create_workspace_datasource_on_postgres18,
)
from orcia_core.orchestration.assistant_agent import AssistantAgentService
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag import HybridRagService
from orcia_core.rag.context_adapters import (
    CatalogAndBlackboardContextSourceAdapter,
    HybridRagVectorStoreAdapter,
)
from orcia_core.rag.errors import NoActiveEmbeddingModelError, RagReindexInProgressError

_WS_TEST = "0195f000-0000-7000-8000-000000000301"


def test_assistant_agent_service_responds_without_embedding_and_skips_rag_citations() -> None:
    """AssistantAgentService runs cleanly with `embedding_available=False` and empty RAG hits."""
    auth_svc = build_default_auth_and_org_service()
    setup_svc = build_default_orchestration_setup_service(evaluator=auth_svc.evaluator)
    rag_no_emb = HybridRagService(embedding_port=None)
    vector_store = HybridRagVectorStoreAdapter(rag_no_emb, embedding_port=None)
    context_source = CatalogAndBlackboardContextSourceAdapter(
        rag_service=rag_no_emb,
        catalog_items_provider=lambda _ws: tuple(setup_svc.workflows),
        blackboard_snapshots_provider=lambda _ws: (),
        permission_policies_provider=lambda _ws: (),
    )
    from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

    service = AssistantAgentService(
        context_source=context_source,
        vector_store=vector_store,
        llm_gateway=DeterministicCassetteLLM(),
        orchestration_setup=setup_svc,
        workflow_engine=setup_svc.engine,
    )

    result = service.run_conversation_turn(
        workspace_id=_WS_TEST,
        user_prompt="Explique l'état de mes workflows sans modèle sémantique.",
        human_profile_archetype="ARCHITECT",
        embedding_available=False,
    )
    assert result.response_text.strip() != ""
    fan_out = next(t for t in result.node_traces if t.node_id == "3_PARALLEL_FAN_OUT")
    assert fan_out.output_metadata["rag_active"] is False
    assert fan_out.output_metadata["vector_hit_count"] == 0
    assert "RAG" not in fan_out.output_metadata["sources_queried"]
    assert not any(u.startswith("confluence://") for u in result.assembled_prompt.cited_uris)


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda: NoActiveEmbeddingModelError(
            detail_override="Aucun modèle d'embedding actif configuré au niveau GLOBAL."
        ),
        lambda: RagReindexInProgressError(progress_percentage=65, job_id="job-25-5"),
    ],
)
def test_all_assistant_routes_and_federated_search_succeed_without_embedding(
    error_factory: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 5 Assistant routes and GET /search stay 200 when embedding is missing or reindexing."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/tmp/orcia-unit-none.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    app = create_app()

    def _raise_rag_unavailable() -> EmbeddingPort:
        raise error_factory()

    app.dependency_overrides[get_embedding_port] = _raise_rag_unavailable
    with TestClient(app) as client:
        ws_seeded = "0192c4e0-0000-7000-8000-000000000201"
        r_turns = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={
                "workspace_id": ws_seeded,
                "user_prompt": "Bonjour",
                "requested_speed": "SPEED_1_FAST",
            },
        )
        assert r_turns.status_code == 202, r_turns.text
        r_turns_stream = client.get(r_turns.json()["stream_url"], params={"persona_key": "marc"})
        assert r_turns_stream.status_code == 200
        assert "event: turn_completed" in r_turns_stream.text

        # Create folder + thread, then post turn without embedding model
        r_folder = client.post(
            "/api/v1/assistant/folders",
            params={"persona_key": "marc"},
            json={"workspace_id": ws_seeded, "title": "Dossier Sans Embedding"},
        )
        assert r_folder.status_code == 200
        folder_id = r_folder.json()["folder_id"]

        r_thread = client.post(
            "/api/v1/assistant/threads",
            params={"persona_key": "marc"},
            json={"workspace_id": ws_seeded, "folder_id": folder_id, "title": "Fil Test"},
        )
        assert r_thread.status_code == 200
        thread_id = r_thread.json()["thread_id"]

        r_thread_turn = client.post(
            f"/api/v1/assistant/threads/{thread_id}/turns",
            params={"persona_key": "marc"},
            json={"workspace_id": ws_seeded, "message_text": "Synthèse du dossier"},
        )
        assert r_thread_turn.status_code == 200

        r_search = client.get(
            "/api/v1/search",
            params={"q": "dossier sans embedding", "workspace_id": ws_seeded},
        )
        assert r_search.status_code == 200
        assert r_search.json()["speed2_executed"] is False


def test_live_assistant_rejects_422_when_zero_active_chat_model_even_if_embedding_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In live mode, 0 active chat model (with only an embedding model) returns 422."""
    from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter
    from tests.unit.fakes.in_memory_reindex import InMemoryReindexManager

    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/tmp/orcia-unit-none.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    import orcia_core.bootstrap as bm

    app = create_app()
    app.state.reindex_manager = InMemoryReindexManager()
    app.state.embedding_port = FakeDeterministicEmbeddingAdapter()
    with TestClient(app) as client:
        # Only an embedding model is configured -> chat resolution MUST reject with 422
        app.state.db_engine = None
        app.state.platform_setup_snapshot = bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=True,
            first_admin_email="admin@orcia.io",
            first_admin_display_name="Admin",
            llm_tiers=[
                {
                    "tier": "simple",
                    "usage": "embedding",
                    "primaryModel": "text-embedding-3-small",
                    "modelFamily": "OpenAI",
                    "endpointUrl": "https://api.openai.com/v1",
                    "authMode": "api_key",
                    "apiKey": "sk-emb-only",  # pragma: allowlist secret
                }
            ],
        )

        resp_turn = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={"workspace_id": "0192c4e0-0000-7000-8000-000000000201", "user_prompt": "Bonjour"},
        )
        assert resp_turn.status_code == 422
        assert resp_turn.json()["error_code"] == "ERR_TIER_MODEL_NOT_CONFIGURED"
        assert resp_turn.headers.get("content-type") == "application/problem+json"


class _FakeResult:
    def __init__(self, scalar_val: Any = None, row_val: Any = None) -> None:
        self._scalar = scalar_val
        self._row = row_val

    def scalar(self) -> Any:
        return self._scalar

    def fetchone(self) -> Any:
        return self._row

    def fetchall(self) -> list[Any]:
        return []


class _RecordingAsyncConnection:
    def __init__(self, *, has_active_embedding: bool) -> None:
        self.has_active_embedding = has_active_embedding
        self.executed_sql: list[str] = []

    async def execute(self, statement: Any, _params: Any = None) -> _FakeResult:
        sql = str(statement)
        self.executed_sql.append(sql)
        if "SELECT to_regclass('workspace_llm_tier_mappings')" in sql:
            return _FakeResult(scalar_val="workspace_llm_tier_mappings")
        if "FROM workspace_llm_tier_mappings" in sql:
            return _FakeResult(row_val=("mod-emb-1",) if self.has_active_embedding else None)
        if "SELECT id FROM workspaces WHERE id" in sql:
            return _FakeResult(scalar_val=_WS_TEST)
        if "INSERT INTO workspace_datasources" in sql:
            return _FakeResult(
                row_val=(
                    "0195f000-0000-7000-8000-000000000999",
                    _WS_TEST,
                    "Repo Code",
                    "git",
                    "https://gitlab.internal/org/repo.git",
                    None,
                    "SERVICE_ACCOUNT",
                    None,
                    None,
                    None,
                    "SOURCE_CODE",
                    "POLLING_24H",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "PENDING_INITIAL_SYNC",
                    False,
                    "SERVICE_ACCOUNT",
                    None,
                    "DISABLED",
                    None,
                    None,
                )
            )
        return _FakeResult()


class _FakeAsyncEngine:
    def __init__(self, conn: _RecordingAsyncConnection) -> None:
        self.conn = conn

    @asynccontextmanager
    async def begin(self) -> Any:
        yield self.conn


@pytest.mark.asyncio
@pytest.mark.parametrize("rag_nature", ["DOCUMENT_KB", "WORK_TRACKER", "RELATIONAL_SCHEMA"])
async def test_create_workspace_datasource_rejects_rag_natures_before_insert_without_embedding(
    rag_nature: str,
) -> None:
    """RAG source_nature != SOURCE_CODE must fail 422 before any INSERT when 0 embedding."""
    conn = _RecordingAsyncConnection(has_active_embedding=False)
    engine = _FakeAsyncEngine(conn)

    with pytest.raises(NoActiveEmbeddingModelError) as exc_info:
        await create_workspace_datasource_on_postgres18(
            engine,  # type: ignore[arg-type]
            workspace_id=_WS_TEST,
            alias="Confluence Test",
            scheme="confluence",
            uri="https://confluence.internal/spaces/ENG",
            source_nature=rag_nature,  # type: ignore[arg-type]
            instance=f"/api/v1/workspaces/{_WS_TEST}/datasources",
        )
    assert exc_info.value.http_status == 422
    assert exc_info.value.error_code == "ERR_NO_ACTIVE_EMBEDDING_MODEL"
    assert not any("INSERT INTO workspace_datasources" in s for s in conn.executed_sql)


@pytest.mark.asyncio
async def test_create_workspace_datasource_allows_source_code_without_embedding() -> None:
    """SOURCE_CODE bypasses embedding guard and proceeds to INSERT."""
    conn = _RecordingAsyncConnection(has_active_embedding=False)
    engine = _FakeAsyncEngine(conn)

    await assert_active_global_embedding_model_for_rag_source(
        conn,  # type: ignore[arg-type]
        source_nature="SOURCE_CODE",
    )
    assert conn.executed_sql == []

    rec = await create_workspace_datasource_on_postgres18(
        engine,  # type: ignore[arg-type]
        workspace_id=_WS_TEST,
        alias="Repo Code",
        scheme="git",
        uri="https://gitlab.internal/org/repo.git",
        source_nature="SOURCE_CODE",
    )
    assert rec.source_nature == "SOURCE_CODE"
    assert any("INSERT INTO workspace_datasources" in s for s in conn.executed_sql)


@pytest.mark.asyncio
async def test_rag_guards_and_llm_resolver_branches_without_pg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover FAILED reindex guard, hub embedding adapters, sync overrides, and LLM tier resolver."""
    from types import SimpleNamespace

    from orcia_api.dependencies._rag_availability_guards import (
        get_embedding_port,
        get_optional_embedding_port,
        require_rag_available,
    )
    from orcia_api.dependencies.orchestration_and_settings import get_ai_models_hub_service
    from orcia_api.routers.assistant_llm_resolver import (
        extract_tier_endpoint_from_dict,
        resolve_configured_llm_endpoint,
        select_endpoint_from_tiers,
    )
    from orcia_core.permissions.secret_hint import SecretInputSpec
    from orcia_core.rag.adapters.embedding_httpx import (
        HttpxGeminiNativeEmbeddingAdapter,
        HttpxOpenAiCompatibleEmbeddingAdapter,
    )

    app = create_app()
    fake_request = SimpleNamespace(app=app)

    # 1. Sync dependency override on get_embedding_port works via get_optional_embedding_port
    app.dependency_overrides[get_embedding_port] = lambda: "sync-emb-port"
    assert await get_optional_embedding_port(fake_request) == "sync-emb-port"  # type: ignore[arg-type]
    app.dependency_overrides.clear()

    # 2. Failed reindex job raises RagReindexInProgressError on require_rag_available
    class _FakeReindexMgr:
        def __init__(self, status: str = "NONE") -> None:
            self._status = status

        def get_active_job(self) -> Any:
            return None

        def get_latest_job(self) -> Any:
            if self._status == "FAILED":
                return SimpleNamespace(
                    id="job-fail-1",
                    progress_percentage=42,
                    error_message="boom",
                    status="FAILED",
                )
            return None

    app.state.reindex_manager = _FakeReindexMgr(status="FAILED")
    with pytest.raises(RagReindexInProgressError):
        await require_rag_available(fake_request)  # type: ignore[arg-type]

    # 3. Clear FAILED job -> no active embedding mapping raises NoActiveEmbeddingModelError
    app.state.reindex_manager = _FakeReindexMgr(status="NONE")
    app.state.db_engine = None
    app.state.embedding_port = None
    app.state.http_client = None
    app.state.auth_service = None
    with pytest.raises(NoActiveEmbeddingModelError):
        await require_rag_available(fake_request)  # type: ignore[arg-type]

    # 4. Hub embedding mapping (openai_compatible + secret_input & gemini_native)
    hub_svc = get_ai_models_hub_service(fake_request)  # type: ignore[arg-type]
    hub_svc.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Embed OAI",
        inference_tier="medium",
        effort="default",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        endpoint_uri="https://llm.internal:11434/v1",
        protocol_mode="openai_compatible",
        usage="embedding",
        secret_input=SecretInputSpec(action="set", plaintext_value="sk-emb-secret"),
    )
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "0")
    port_oai = await get_embedding_port(fake_request)  # type: ignore[arg-type]
    assert isinstance(port_oai, HttpxOpenAiCompatibleEmbeddingAdapter)

    hub_svc.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Embed Gemini",
        inference_tier="medium",
        effort="default",
        provider_slug="google",
        model_family="Google",
        model_name="text-embedding-004",
        endpoint_uri="https://generativelanguage.googleapis.com",
        protocol_mode="gemini_native",
        usage="embedding",
    )
    port_gem = await get_embedding_port(fake_request)  # type: ignore[arg-type]
    assert isinstance(port_gem, HttpxGeminiNativeEmbeddingAdapter)

    # 5. LLM endpoint resolver unit branches (cassette, snapshot tiers, hub fallback, SSRF block)
    assert extract_tier_endpoint_from_dict({"primaryModel": "", "endpointUrl": "https://x"}) is None
    assert (
        extract_tier_endpoint_from_dict(
            {"primaryModel": "gpt", "endpointUrl": "http://169.254.169.254/latest"}
        )
        is None
    )
    tiers = [
        {"tier": "small", "primaryModel": "m-small", "endpointUrl": "https://llm.internal/v1"},
        {"tier": "large", "primaryModel": "m-large", "endpointUrl": "https://llm.internal/v1"},
    ]
    assert select_endpoint_from_tiers(tiers, "large") is not None
    assert select_endpoint_from_tiers(tiers, "nonexistent") is not None

    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    assert await resolve_configured_llm_endpoint(fake_request) is None  # type: ignore[arg-type]

    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "0")
    app.state.platform_setup_snapshot = None
    app.state.ai_models_hub_service = hub_svc
    hub_svc.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Chat Live",
        inference_tier="medium",
        effort="default",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="gpt-4o-mini",
        endpoint_uri="https://llm.internal/v1",
        protocol_mode="openai_compatible",
        usage="chat",
    )
    resolved_chat = await resolve_configured_llm_endpoint(fake_request, requested_tier="medium")  # type: ignore[arg-type]
    assert resolved_chat is not None
    assert resolved_chat.model_name == "gpt-4o-mini"

    app.state.platform_setup_snapshot = SimpleNamespace(llm_tiers=tiers)
    resolved_snap = await resolve_configured_llm_endpoint(fake_request, requested_tier="large")  # type: ignore[arg-type]
    assert resolved_snap is not None
    assert resolved_snap.model_name == "m-large"
    await app.state.http_client.aclose() if getattr(app.state, "http_client", None) else None


@pytest.mark.asyncio
async def test_datasource_mutations_validation_and_llm_resolver_pg_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover remaining mutation error branches and PG18 LLM tier resolution fallback."""
    from types import SimpleNamespace

    import orcia_core.bootstrap as bstrap
    import orcia_core.orchestration._internal.sql_ai_model_mappings as bm
    from orcia_api.routers.assistant_llm_resolver import resolve_configured_llm_endpoint
    from orcia_core.bootstrap._internal.sql_workspace_datasources_mutations import (
        delete_workspace_datasource_on_postgres18,
        update_workspace_datasource_on_postgres18,
    )
    from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError

    conn = _RecordingAsyncConnection(has_active_embedding=False)
    engine = _FakeAsyncEngine(conn)

    # Validation & NotFound branches on datasource mutations
    with pytest.raises(ResourceNotFoundError):
        await create_workspace_datasource_on_postgres18(
            engine,  # type: ignore[arg-type]
            workspace_id="not-a-uuid",
            alias="A",
            scheme="git",
            uri="https://gitlab.internal/a.git",
        )
    with pytest.raises(ValidationDomainError):
        await create_workspace_datasource_on_postgres18(
            engine,  # type: ignore[arg-type]
            workspace_id=_WS_TEST,
            alias=" ",
            scheme="git",
            uri="https://gitlab.internal/a.git",
        )

    class _MissingWsConn(_RecordingAsyncConnection):
        async def execute(self, statement: Any, _params: Any = None) -> _FakeResult:
            if "SELECT id FROM workspaces WHERE id" in str(statement):
                return _FakeResult(scalar_val=None)
            return await super().execute(statement, _params)

    with pytest.raises(ResourceNotFoundError):
        await create_workspace_datasource_on_postgres18(
            _FakeAsyncEngine(_MissingWsConn(has_active_embedding=False)),  # type: ignore[arg-type]
            workspace_id=_WS_TEST,
            alias="A",
            scheme="git",
            uri="https://gitlab.internal/a.git",
            source_nature="SOURCE_CODE",
        )

    with pytest.raises(ResourceNotFoundError):
        await update_workspace_datasource_on_postgres18(
            engine,  # type: ignore[arg-type]
            workspace_id=_WS_TEST,
            datasource_id="0195f000-0000-7000-8000-000000000999",
            alias="New",
        )
    with pytest.raises(ResourceNotFoundError):
        await delete_workspace_datasource_on_postgres18(
            engine,  # type: ignore[arg-type]
            workspace_id=_WS_TEST,
            datasource_id="0195f000-0000-7000-8000-000000000999",
        )

    # Switching SOURCE_CODE -> DOCUMENT_KB without active embedding must fail 422 before UPDATE
    class _ExistingSourceConn(_RecordingAsyncConnection):
        async def execute(self, statement: Any, _params: Any = None) -> _FakeResult:
            sql = str(statement)
            if "FOR UPDATE" in sql:
                return _FakeResult(
                    row_val=(
                        "0195f000-0000-7000-8000-000000000999",
                        _WS_TEST,
                        "Repo Code",
                        "git",
                        "https://gitlab.internal/org/repo.git",
                        None,
                        "SERVICE_ACCOUNT",
                        None,
                        None,
                        None,
                        "SOURCE_CODE",
                        "POLLING_24H",
                        None,
                        None,
                        None,
                        None,
                        None,
                        "PENDING_INITIAL_SYNC",
                        False,
                        "SERVICE_ACCOUNT",
                        None,
                        "DISABLED",
                        None,
                        None,
                    )
                )
            return await super().execute(statement, _params)

    upd_conn = _ExistingSourceConn(has_active_embedding=False)
    upd_engine = _FakeAsyncEngine(upd_conn)
    with pytest.raises(NoActiveEmbeddingModelError):
        await update_workspace_datasource_on_postgres18(
            upd_engine,  # type: ignore[arg-type]
            workspace_id=_WS_TEST,
            datasource_id="0195f000-0000-7000-8000-000000000999",
            source_nature="DOCUMENT_KB",
        )
    assert not any("UPDATE workspace_datasources" in s for s in upd_conn.executed_sql)

    # PG18 LLM resolver branches (mapping found, fallback to platform setup snapshot, exception log)
    app = create_app()
    fake_request = SimpleNamespace(app=app)
    app.state.db_engine = engine
    app.state.platform_setup_snapshot = None
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "0")

    async def _resolve_mapping(_conn: Any, **_kwargs: Any) -> Any:
        return (
            SimpleNamespace(
                provider_slug="openai",
                model_name="gpt-4o",
                endpoint_uri="https://llm.internal/v1",
                auth_mode="api_key",
                inference_tier="medium",
            ),
            "sk-pg-secret",
        )

    monkeypatch.setattr(bm, "resolve_decrypted_ai_model_for_tier_pg18", _resolve_mapping)
    pg_ep = await resolve_configured_llm_endpoint(fake_request, requested_tier="medium")  # type: ignore[arg-type]
    assert pg_ep is not None and pg_ep.api_key == "sk-pg-secret"  # pragma: allowlist secret

    async def _resolve_none(_conn: Any, **_kwargs: Any) -> Any:
        return None

    async def _load_snap(_engine: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(
            llm_tiers=[
                {"tier": "small", "primaryModel": "m-pg", "endpointUrl": "https://llm.internal/v1"}
            ]
        )

    monkeypatch.setattr(bm, "resolve_decrypted_ai_model_for_tier_pg18", _resolve_none)
    monkeypatch.setattr(bstrap, "load_platform_setup_state_from_postgres18", _load_snap)
    snap_ep = await resolve_configured_llm_endpoint(fake_request, requested_tier="small")  # type: ignore[arg-type]
    assert snap_ep is not None and snap_ep.model_name == "m-pg"

    app.state.platform_setup_snapshot = None

    async def _boom(_conn: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("pg boom")

    monkeypatch.setattr(bm, "resolve_decrypted_ai_model_for_tier_pg18", _boom)
    assert await resolve_configured_llm_endpoint(fake_request, requested_tier="small") is None  # type: ignore[arg-type]
