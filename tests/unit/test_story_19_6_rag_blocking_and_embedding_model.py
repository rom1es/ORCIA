"""Unit tests for Story 19.6: EmbeddingPort wiring, SHA-256 eradication, and Day-0 blocking.

Verifies:
- Confluence/Jira/DDL indexing blocked without active embedding model (NoActiveEmbeddingModelError).
- Codegraph / Git AST indexing remains non-blocking with chunks embedding=None.
- HybridRagService raises NoActiveEmbeddingModelError when queried without embedding port/vector.
- HybridRagService tolerates chunks with embedding=None without ValueError/TypeError.
- TwoSpeedFederatedSearchService degrades gracefully with speed2_executed=False when no model.
- FastAPI endpoints /ontology-rag/rag/search and /assistant/three-speed/turn return HTTP 422
  ERR_NO_ACTIVE_EMBEDDING_MODEL when no active global embedding model is configured.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_api.dependencies.portal_and_assistant import get_embedding_port
from orcia_api.main import create_app
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag.errors import NoActiveEmbeddingModelError
from orcia_core.rag.hybrid_rag_service import HybridRagService
from orcia_core.rag.indexer_and_rrf import DifferentiatedIncrementalIndexer
from orcia_core.rag.models import (
    KbChunkEntity,
    KbDocumentEntity,
)
from orcia_core.rag.two_speed_search import TwoSpeedFederatedSearchService


@pytest.mark.asyncio
async def test_confluence_indexing_blocked_without_embedding_model() -> None:
    """Document ingestion for Confluence must raise NoActiveEmbeddingModelError without model."""
    with pytest.raises(NoActiveEmbeddingModelError) as exc_info:
        await DifferentiatedIncrementalIndexer.index_confluence_parent_child(
            workspace_id="ws-test",
            datasource_id="ds-conf-1",
            datasource_alias="confluence_main",
            source_uri="confluence://SPACE/page-1",
            title="Architecture Spec",
            hierarchy_path="SPACE > Architecture",
            markdown_sections=("Section 1 Content", "Section 2 Content"),
            revision_tag="rev-1",
            embedding_port=None,
        )
    assert exc_info.value.error_code == "ERR_NO_ACTIVE_EMBEDDING_MODEL"


@pytest.mark.asyncio
async def test_jira_and_ddl_indexing_blocked_without_embedding_model() -> None:
    """Document ingestion for Jira & DDL must raise NoActiveEmbeddingModelError without model."""
    with pytest.raises(NoActiveEmbeddingModelError):
        await DifferentiatedIncrementalIndexer.index_jira_reference_issue(
            workspace_id="ws-test",
            datasource_id="ds-jira-1",
            datasource_alias="jira_main",
            issue_key="PROJ-101",
            issue_type="Story",
            title="Critical Bug",
            body_text="Details of the bug",
            updated_tag="v1",
            embedding_port=None,
        )

    with pytest.raises(NoActiveEmbeddingModelError):
        await DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
            workspace_id="ws-test",
            datasource_id="ds-db-1",
            datasource_alias="db_main",
            db_uri="db://postgres/prod",
            ddl_sql="CREATE TABLE accounts (id UUID PRIMARY KEY);",
            schema_version="v1",
            embedding_port=None,
        )


def test_codegraph_git_ast_indexing_remains_non_blocking_without_embedding_model() -> None:
    """Codegraph / Git AST indexing continues with embedding=None (Epic 18 out-of-scope)."""
    doc, chunks, edges = DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph(
        workspace_id="ws-test",
        datasource_id="ds-git-1",
        datasource_alias="git_repo",
        repo_uri="git://repo/main",
        file_path="src/engine.py",
        python_source="def process_claim(x: int) -> int:\n    return x * 2\n",
        commit_sha="git-sha1",
    )
    assert doc is not None
    assert doc.indexing_regime == "CODE_AST_GRAPH"
    assert len(chunks) == 1
    assert chunks[0].embedding is None
    assert chunks[0].embedding_model_id is None
    assert len(edges) >= 1


def test_hybrid_rag_service_memory_search_requires_embedding_port() -> None:
    """HybridRagService memory fallback raises NoActiveEmbeddingModelError without port."""
    rag = HybridRagService(embedding_port=None)
    with pytest.raises(NoActiveEmbeddingModelError) as exc_info:
        rag.search_hybrid_rrf(
            workspace_id="ws-test",
            query_text="search query",
            query_embedding=None,
        )
    assert exc_info.value.error_code == "ERR_NO_ACTIVE_EMBEDDING_MODEL"


def test_hybrid_rag_service_memory_search_tolerates_null_embeddings() -> None:
    """Chunks with embedding=None (e.g. CodeGraph) must not crash hybrid cosine/RRF ranking."""
    fake_emb = FakeDeterministicEmbeddingAdapter()
    rag = HybridRagService(embedding_port=fake_emb)

    doc = KbDocumentEntity(
        id="doc-1",
        doc_key="doc-1-key",
        workspace_id="ws-test",
        datasource_id="ds-test",
        datasource_alias="ds_alias",
        source_uri="confluence://p1",
        source_scheme="confluence",
        indexing_regime="DOC_PARENT_CHILD",
        title="Doc 1",
        revision_tag="v1",
        content_sha256="hash-1",
    )
    # Chunk 1: has embedding
    c1 = KbChunkEntity(
        id="c1",
        chunk_key="k1",
        document_id="doc-1",
        workspace_id="ws-test",
        datasource_alias="ds_alias",
        parent_chunk_id=None,
        chunk_role="CHILD",
        contextual_header="[ds : H1]",
        content_text="Payment processing validation rule PAY-142",
        token_count=10,
        embedding=fake_emb.embed_query_sync("Payment processing validation rule PAY-142"),
        embedding_model_id="mod-1",
    )
    # Chunk 2: CodeGraph chunk without embedding
    c2 = KbChunkEntity(
        id="c2",
        chunk_key="k2",
        document_id="doc-1",
        workspace_id="ws-test",
        datasource_alias="ds_alias",
        parent_chunk_id=None,
        chunk_role="CHILD",
        contextual_header="[ds : H2]",
        content_text="def validate_payment(amount): return amount > 0",
        token_count=10,
        embedding=None,
        embedding_model_id=None,
    )
    rag.upsert_indexed_bundle(document=doc, chunks=(c1, c2))

    # Query with query_embedding provided
    q_vec = fake_emb.embed_query_sync("validation rule PAY-142")
    hits = rag.search_hybrid_rrf(
        workspace_id="ws-test",
        query_text="validation rule PAY-142",
        query_embedding=q_vec,
        top_k=5,
    )
    assert len(hits) >= 1
    # Both chunks may match text or vector, no TypeError/ValueError raised
    assert all(h.chunk_key in ("k1", "k2") for h in hits)


def test_two_speed_search_service_degrades_gracefully_without_model() -> None:
    """TwoSpeedFederatedSearchService returns speed2_executed=False when embedding port is None."""
    svc = TwoSpeedFederatedSearchService(embedding_port=None)
    result = svc.execute_search(
        active_workspace_id="ws-test",
        query="test search",
    )
    assert result.speed1_llm_cost_usd == 0.0
    assert result.speed2_executed is False


def test_api_rag_search_returns_422_when_no_active_embedding_model() -> None:
    """POST /api/v1/ontology-rag/rag/search returns HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL."""
    app = create_app()

    def _raise_no_model() -> EmbeddingPort:
        raise NoActiveEmbeddingModelError(
            detail_override="Aucun modèle d'embedding actif configuré au niveau GLOBAL."
        )

    app.dependency_overrides[get_embedding_port] = _raise_no_model
    client = TestClient(app)

    resp = client.post(
        "/api/v1/ontology-rag/rag/search",
        json={
            "workspace_id": "ws-test",
            "query_text": "how to configure claims",
            "top_k": 3,
        },
    )
    assert resp.status_code == 422
    data = resp.json()
    assert data["error_code"] == "ERR_NO_ACTIVE_EMBEDDING_MODEL"
    assert "detail" in data
    assert resp.headers.get("content-type") == "application/problem+json"


def test_api_assistant_and_federated_search_succeed_when_no_active_embedding_model() -> None:
    """AD-24 Epic 25: Assistant and GET /search stay unlocked (200) without embedding model."""
    app = create_app()

    def _raise_no_model() -> EmbeddingPort:
        raise NoActiveEmbeddingModelError(
            detail_override="Aucun modèle d'embedding actif configuré au niveau GLOBAL."
        )

    app.dependency_overrides[get_embedding_port] = _raise_no_model
    client = TestClient(app)

    resp_turn = client.post(
        "/api/v1/assistant/three-speed/turn",
        params={"persona_key": "marc"},
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "user_prompt": "Hello assistant without embedding",
            "requested_speed": "SPEED_1_FAST",
        },
    )
    assert resp_turn.status_code == 200
    assert resp_turn.json()["response_text"]

    resp_search = client.get(
        "/api/v1/search",
        params={"q": "claims validation rule", "workspace_id": "ws-test"},
    )
    assert resp_search.status_code == 200
    assert resp_search.json()["speed2_executed"] is False
