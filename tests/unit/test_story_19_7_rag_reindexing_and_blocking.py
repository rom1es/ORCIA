"""Unit tests for Story 19.7: RAG Reindexing jobs, 503 blocking, and Assistant lockout.

Verifies:
- InMemoryReindexManager state transitions (PENDING -> IN_PROGRESS -> COMPLETED / FAILED).
- Superseded job cancellation on new active model reindexing trigger.
- ProblemDetails carries progress_percentage on RagReindexInProgressError.
- GET /api/v1/settings/ai-models/reindex-status returns job status and percentage.
- POST /api/v1/settings/ai-models/reindex-embeddings triggers job on active model (or 422 if none).
- POST /api/v1/ontology-rag/rag/search returns HTTP 503 ERR_RAG_REINDEX_IN_PROGRESS during job.
- POST /api/v1/assistant/three-speed/turn returns HTTP 503 ERR_RAG_REINDEX_IN_PROGRESS during job.
- Outbox events: EmbeddingReindexStarted, EmbeddingReindexCompleted, EmbeddingReindexFailed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter
from tests.unit.fakes.in_memory_reindex import (
    InMemoryReindexManager,
    default_in_memory_reindex_manager,
)

from orcia_api.main import create_app
from orcia_core.kernel.events import (
    EmbeddingReindexCompleted,
    EmbeddingReindexFailed,
    EmbeddingReindexStarted,
)
from orcia_core.orchestration import AiModelsHubService


@pytest.fixture(autouse=True)
def _reset_reindex_manager() -> None:
    default_in_memory_reindex_manager.clear()


def test_reindex_manager_state_machine_and_cancellation() -> None:
    """Verify in-memory reindexing lifecycle and replacement of superseded jobs."""
    mgr = InMemoryReindexManager()
    assert mgr.get_active_job() is None
    assert mgr.get_latest_job() is None

    # 1. Create first job
    job1 = mgr.create_or_replace_job(
        target_model_id="mod-1", target_model_name="text-embedding-3-small", total_chunks=100
    )
    assert job1.status == "PENDING"
    assert job1.progress_percentage == 0
    assert mgr.get_active_job() == job1

    # 2. Advance progress
    job1_in_prog = mgr.advance_progress(50)
    assert job1_in_prog.status == "IN_PROGRESS"
    assert job1_in_prog.processed_chunks == 50
    assert job1_in_prog.progress_percentage == 50

    # 3. Supersede with a newer job
    job2 = mgr.create_or_replace_job(
        target_model_id="mod-2", target_model_name="mistral-embed", total_chunks=80
    )
    assert job2.status == "PENDING"
    assert job2.target_model_id == "mod-2"
    assert mgr.get_active_job() == job2

    # 4. Complete job2
    job2_completed = mgr.complete_job()
    assert job2_completed.status == "COMPLETED"
    assert job2_completed.progress_percentage == 100
    assert mgr.get_active_job() is None
    assert mgr.get_latest_job() == job2_completed


def test_reindex_manager_failure_state() -> None:
    """Verify failure state recording on in-memory manager."""
    mgr = InMemoryReindexManager()
    mgr.create_or_replace_job(
        target_model_id="mod-fail", target_model_name="failing-model", total_chunks=20
    )
    failed_job = mgr.fail_job("Connection refused by embedding provider")
    assert failed_job.status == "FAILED"
    assert failed_job.error_message == "Connection refused by embedding provider"
    assert mgr.get_active_job() is None
    assert mgr.get_latest_job() == failed_job


def test_domain_events_outbox_constructors() -> None:
    """Verify outbox events creation with required fields."""
    ev_start = EmbeddingReindexStarted.create(
        job_id="job-100",
        target_model_id="mod-alpha",
        target_model_name="text-embedding-3-small",
        total_chunks=150,
    )
    assert ev_start.event_type == "EmbeddingReindexStarted"
    assert ev_start.payload["total_chunks"] == 150

    ev_done = EmbeddingReindexCompleted.create(
        job_id="job-100",
        target_model_id="mod-alpha",
        total_chunks=150,
        processed_chunks=150,
    )
    assert ev_done.event_type == "EmbeddingReindexCompleted"
    assert ev_done.payload["processed_chunks"] == 150

    ev_fail = EmbeddingReindexFailed.create(
        job_id="job-100",
        target_model_id="mod-alpha",
        error_message="HTTP 500 from provider",
        processed_chunks=50,
    )
    assert ev_fail.event_type == "EmbeddingReindexFailed"
    assert ev_fail.payload["error_message"] == "HTTP 500 from provider"


def test_fastapi_reindex_status_and_trigger_endpoints() -> None:
    """Verify GET /reindex-status and POST /reindex-embeddings on FastAPI router."""
    app = create_app()
    app.state.reindex_manager = default_in_memory_reindex_manager
    client = TestClient(app)

    # Initially IDLE
    res_idle = client.get("/api/v1/settings/ai-models/reindex-status")
    assert res_idle.status_code == 200
    body_idle = res_idle.json()
    assert body_idle["status"] == "IDLE"

    # Trigger reindex without active model -> 422 ERR_NO_ACTIVE_EMBEDDING_MODEL
    res_trigger_no_model = client.post(
        "/api/v1/settings/ai-models/reindex-embeddings",
        headers={"X-Orcia-Persona": "karim"},
    )
    assert res_trigger_no_model.status_code == 422
    assert res_trigger_no_model.json()["error_code"] == "ERR_NO_ACTIVE_EMBEDDING_MODEL"

    # Create active embedding model in hub_svc
    hub_svc: AiModelsHubService = app.state.ai_models_hub_service
    rec = hub_svc.create_mapping(
        scope_level="GLOBAL",
        scope_id="global",
        display_name="OpenAI Embeddings",
        inference_tier="simple",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none_local",
        usage="embedding",
        actor_id="admin-test",
    )
    assert rec.is_active is True

    # Trigger reindex with active model -> 200 OK (in-memory with 0 chunks: immediately COMPLETED)
    res_trigger = client.post(
        "/api/v1/settings/ai-models/reindex-embeddings",
        headers={"X-Orcia-Persona": "karim"},
    )
    assert res_trigger.status_code == 200
    trigger_data = res_trigger.json()
    assert trigger_data["status"] == "COMPLETED"
    assert trigger_data["target_model_id"] == rec.id

    # Check status returns COMPLETED
    res_status = client.get("/api/v1/settings/ai-models/reindex-status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "COMPLETED"


def test_fastapi_rag_blocked_503_while_assistant_and_search_stay_unlocked_during_reindex() -> None:
    """Verify pure RAG returns 503 during reindexing while Assistant & GET /search stay 200."""
    app = create_app()
    app.state.reindex_manager = default_in_memory_reindex_manager
    fake_adapter = FakeDeterministicEmbeddingAdapter()
    app.state.embedding_port = fake_adapter

    client = TestClient(app)

    # 1. Put reindexing in progress (42%)
    default_in_memory_reindex_manager.create_or_replace_job(
        target_model_id="mod-1", target_model_name="text-embedding-3-small", total_chunks=100
    )
    default_in_memory_reindex_manager.advance_progress(42)

    # 2. Pure RAG search -> HTTP 503 ERR_RAG_REINDEX_IN_PROGRESS
    rag_payload = {
        "workspace_id": "0195f000-0000-7000-8000-000000000301",
        "query_text": "Comment fonctionne l'orchestration ?",
        "top_k": 5,
    }
    res_search = client.post("/api/v1/ontology-rag/rag/search", json=rag_payload)
    assert res_search.status_code == 503
    problem_search = res_search.json()
    assert problem_search["error_code"] == "ERR_RAG_REINDEX_IN_PROGRESS"
    assert problem_search["progress_percentage"] == 42
    assert "42%" in problem_search["detail"]

    # 3. Assistant turn & GET /search remain unlocked (HTTP 200, AD-24 Epic 25)
    assistant_payload = {
        "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        "user_prompt": "Bonjour assistant",
    }
    res_assistant = client.post(
        "/api/v1/assistant/three-speed/turn",
        params={"persona_key": "marc"},
        json=assistant_payload,
    )
    assert res_assistant.status_code == 200

    res_fed_search = client.get(
        "/api/v1/search",
        params={"q": "orchestration", "workspace_id": "0195f000-0000-7000-8000-000000000301"},
    )
    assert res_fed_search.status_code == 200
    assert res_fed_search.json()["speed2_executed"] is False

    # 4. Complete reindexing -> 503 unlocked on pure RAG search
    default_in_memory_reindex_manager.complete_job()
    res_search_unlocked = client.post("/api/v1/ontology-rag/rag/search", json=rag_payload)
    assert res_search_unlocked.status_code == 200


def test_empty_corpus_reindex_immediately_completed_without_blocking() -> None:
    """When corpus has 0 document chunks (Day-0 reset), reindexing passes directly to COMPLETED."""
    app = create_app()
    app.state.reindex_manager = default_in_memory_reindex_manager
    app.state.embedding_port = FakeDeterministicEmbeddingAdapter()
    client = TestClient(app)

    default_in_memory_reindex_manager.reset()
    job = default_in_memory_reindex_manager.create_or_replace_job(
        target_model_id="0195f000-0000-7000-8000-000000000301",
        target_model_name="text-embedding-3-small",
        total_chunks=0,
    )
    assert job.status == "COMPLETED"
    assert job.progress_percentage == 100
    assert default_in_memory_reindex_manager.get_active_job() is None

    # Status endpoint returns COMPLETED
    res_status = client.get("/api/v1/settings/ai-models/reindex-status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "COMPLETED"
    assert res_status.json()["progress_percentage"] == 100

    # RAG search does NOT return 503
    rag_payload = {
        "workspace_id": "0195f000-0000-7000-8000-000000000301",
        "query_text": "Comment fonctionne l'architecture ?",
        "top_k": 5,
    }
    res_search = client.post("/api/v1/ontology-rag/rag/search", json=rag_payload)
    assert res_search.status_code == 200
