"""Unit tests for Dramatiq worker `rag_reindexer` cipher and HTTP client lifecycle (`Story 19.7`).

Verifies:
1. Worker job decrypts API keys encrypted with `ORCIA_PASSTHROUGH_MASTER_KEY`.
2. Dedicated `PassthroughVaultCipher` master key resolution from environment.
3. Proper closure of `httpx.AsyncClient` in finally block (zero connection leaks).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orcia_core.orchestration import AiModelMappingRecord
from orcia_core.orchestration.ai_models_crypto import pack_encrypted_api_key
from orcia_core.permissions import PassthroughVaultCipher
from orcia_core.rag.models import RagReindexJobRecord
from orcia_worker.rag_reindexer import execute_rag_reindex_worker_job_async

CUSTOM_MASTER_KEY = "orcia-test-vault-secret-key-4321-custom"


@pytest.mark.asyncio
async def test_worker_decrypts_api_key_with_configured_master_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify background worker uses ORCIA_PASSTHROUGH_MASTER_KEY to unpack encrypted API key."""
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", CUSTOM_MASTER_KEY)

    # 1. Encrypt API key with the custom master key
    cipher = PassthroughVaultCipher(master_key=CUSTOM_MASTER_KEY)
    encrypted_blob = pack_encrypted_api_key(
        cipher,
        mapping_id="0195f000-0000-7000-8000-000000000888",
        plaintext_key="sk-live-secret-test-key-5555",
        target_host="api.openai.com",
    )

    fake_mapping = AiModelMappingRecord(
        id="0195f000-0000-7000-8000-000000000888",
        scope_level="GLOBAL",
        scope_id="global",
        display_name="Test Embedder",
        inference_tier="simple",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="bearer_token",
        protocol_mode="openai_compatible",
        encrypted_api_key=encrypted_blob,
        fallback_order=1,
        is_active=True,
        draining=False,
        usage="embedding",
        created_at="2026-11-15T20:00:00Z",
        updated_at="2026-11-15T20:00:00Z",
    )

    fake_job_rec = RagReindexJobRecord(
        id="job-888",
        target_model_id=fake_mapping.id,
        target_model_name=fake_mapping.model_name,
        status="COMPLETED",
        total_chunks=10,
        processed_chunks=10,
        progress_percentage=100,
        created_by="system",
    )

    created_adapter_holder: list[object] = []

    async def _mock_execute_job(*args: object, **kwargs: object) -> RagReindexJobRecord:
        port = kwargs.get("embedding_port")
        created_adapter_holder.append(port)
        return fake_job_rec

    with (
        patch(
            "orcia_worker.rag_reindexer.get_ai_model_mapping_pg18",
            new_callable=AsyncMock,
            return_value=fake_mapping,
        ),
        patch(
            "orcia_worker.rag_reindexer.execute_rag_reindex_job",
            side_effect=_mock_execute_job,
        ),
        patch("orcia_worker.rag_reindexer.create_async_engine") as mock_engine_factory,
    ):
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_conn = AsyncMock()
        mock_begin = AsyncMock()
        mock_begin.__aenter__.return_value = mock_conn
        mock_begin.__aexit__.return_value = None
        mock_engine.begin.return_value = mock_begin
        mock_engine_factory.return_value = mock_engine

        result = await execute_rag_reindex_worker_job_async(
            job_id="job-888",
            target_model_id=fake_mapping.id,
            trace_id="00000000000000000000000000000888",
            database_url="postgresql+asyncpg://mock/db",
        )

        assert result.status == "COMPLETED"
        assert len(created_adapter_holder) == 1
        adapter = created_adapter_holder[0]
        # Verify the decrypted API key matches raw key
        assert getattr(adapter, "_api_key", None) == "sk-live-secret-test-key-5555"
        # Verify engine was disposed
        assert mock_engine.dispose.await_count == 1


@pytest.mark.asyncio
async def test_worker_http_client_closed_in_finally_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify owned httpx.AsyncClient is closed in finally block even when job execution fails."""
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", CUSTOM_MASTER_KEY)

    fake_mapping = AiModelMappingRecord(
        id="0195f000-0000-7000-8000-000000000999",
        scope_level="GLOBAL",
        scope_id="global",
        display_name="Test Embedder 2",
        inference_tier="simple",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none_local",
        protocol_mode="openai_compatible",
        encrypted_api_key=None,
        fallback_order=1,
        is_active=True,
        draining=False,
        usage="embedding",
        created_at="2026-11-15T20:00:00Z",
        updated_at="2026-11-15T20:00:00Z",
    )

    created_adapter_holder: list[object] = []

    async def _failing_execute_job(*args: object, **kwargs: object) -> RagReindexJobRecord:
        port = kwargs.get("embedding_port")
        created_adapter_holder.append(port)
        raise RuntimeError("Transient provider outage")

    with (
        patch(
            "orcia_worker.rag_reindexer.get_ai_model_mapping_pg18",
            new_callable=AsyncMock,
            return_value=fake_mapping,
        ),
        patch(
            "orcia_worker.rag_reindexer.execute_rag_reindex_job",
            side_effect=_failing_execute_job,
        ),
        patch("orcia_worker.rag_reindexer.create_async_engine") as mock_engine_factory,
    ):
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_conn = AsyncMock()
        mock_begin = AsyncMock()
        mock_begin.__aenter__.return_value = mock_conn
        mock_begin.__aexit__.return_value = None
        mock_engine.begin.return_value = mock_begin
        mock_engine_factory.return_value = mock_engine

        with pytest.raises(RuntimeError, match="Transient provider outage"):
            await execute_rag_reindex_worker_job_async(
                job_id="job-999",
                target_model_id=fake_mapping.id,
                trace_id="00000000000000000000000000000999",
                database_url="postgresql+asyncpg://mock/db",
            )

        assert len(created_adapter_holder) == 1
        adapter = created_adapter_holder[0]
        http_cli = getattr(adapter, "_client", None)
        assert http_cli is not None
        assert http_cli.is_closed is True
        assert mock_engine.dispose.await_count == 1
