"""Idempotent Dramatiq actor `rag_reindexer` for vector corpus reindexing (`Story 19.7`).

Conventions (AGENTS.md, ARCHITECTURE-SPINE.md):
- Dramatiq workers retry on transient failures — jobs are idempotent and safe to resume
- Chunks already vectorized with target_model_id are skipped without duplicate API calls
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

import dramatiq
import httpx
from sqlalchemy.ext.asyncio import create_async_engine

from orcia_core.config import resolve_database_url
from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_core.orchestration._internal.sql_ai_model_mappings import (
    get_ai_model_mapping_pg18,
)
from orcia_core.orchestration.ai_models_crypto import unpack_encrypted_api_key
from orcia_core.permissions import PassthroughVaultCipher
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag.adapters.embedding_httpx import (
    HttpxGeminiNativeEmbeddingAdapter,
    HttpxOpenAiCompatibleEmbeddingAdapter,
)
from orcia_core.rag.models import RagReindexJobRecord
from orcia_core.rag.reindex import execute_rag_reindex_job

logger = get_logger("orcia.worker.rag_reindexer")


@dataclass(frozen=True, slots=True)
class RagReindexExecutionResult:
    """Result of a `rag_reindexer_actor` run."""

    job_id: str
    status: str
    processed_chunks: int
    total_chunks: int
    trace_id: str


async def execute_rag_reindex_worker_job_async(
    *,
    job_id: str,
    target_model_id: str,
    trace_id: str,
    embedding_port: EmbeddingPort | None = None,
    database_url: str | None = None,
) -> RagReindexJobRecord:
    """Async execution of reindexing job, resolving DB engine and EmbeddingPort if needed."""
    ctx = bind_trace_context(trace_id)
    db_url = database_url or resolve_database_url()
    engine = create_async_engine(db_url, echo=False)
    cipher = PassthroughVaultCipher(master_key=b"0" * 32)

    eff_port = embedding_port
    if eff_port is None:
        async with engine.begin() as conn:
            mapping = await get_ai_model_mapping_pg18(conn, target_model_id)

        host = urlparse(mapping.endpoint_uri).netloc or "default"
        api_key: str | None = None
        if mapping.encrypted_api_key:
            api_key = unpack_encrypted_api_key(
                cipher,
                mapping_id=mapping.id,
                packed=mapping.encrypted_api_key,
                target_host=host,
            )

        http_client = httpx.AsyncClient()
        if mapping.protocol_mode == "gemini_native":
            eff_port = HttpxGeminiNativeEmbeddingAdapter(
                http_client=http_client,
                endpoint_uri=mapping.endpoint_uri,
                model_name=mapping.model_name,
                api_key=api_key,
            )
        else:
            eff_port = HttpxOpenAiCompatibleEmbeddingAdapter(
                http_client=http_client,
                endpoint_uri=mapping.endpoint_uri,
                model_name=mapping.model_name,
                api_key=api_key,
            )

    try:
        rec = await execute_rag_reindex_job(
            engine=engine,
            job_id=job_id,
            target_model_id=target_model_id,
            embedding_port=eff_port,
            batch_size=50,
            trace_id=ctx.trace_id,
        )
        return rec
    finally:
        await engine.dispose()


def execute_rag_reindex_worker_job(
    *,
    job_id: str,
    target_model_id: str,
    trace_id: str,
    embedding_port: EmbeddingPort | None = None,
    database_url: str | None = None,
) -> RagReindexExecutionResult:
    """Synchronous facade running the async reindex job."""
    rec = asyncio.run(
        execute_rag_reindex_worker_job_async(
            job_id=job_id,
            target_model_id=target_model_id,
            trace_id=trace_id,
            embedding_port=embedding_port,
            database_url=database_url,
        )
    )
    return RagReindexExecutionResult(
        job_id=rec.id,
        status=rec.status,
        processed_chunks=rec.processed_chunks,
        total_chunks=rec.total_chunks,
        trace_id=trace_id,
    )


@dramatiq.actor(actor_name="rag_reindexer", max_retries=2)
def rag_reindex_actor(job_id: str, target_model_id: str, trace_id: str) -> None:
    """Idempotent Dramatiq actor executing background vector corpus reindexing."""
    execute_rag_reindex_worker_job(
        job_id=job_id,
        target_model_id=target_model_id,
        trace_id=trace_id,
    )
