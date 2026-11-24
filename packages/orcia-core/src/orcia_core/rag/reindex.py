"""RAG Reindexing Orchestration & Execution Service (`Story 19.7`, `AD-24.7`, `D9`, `D12`).

Coordinates:
- Batch calculation of embeddings with EmbeddingPort (batch_size=50)
- Progress tracking and database state transitions (PENDING -> IN_PROGRESS -> COMPLETED/FAILED)
- Guard assertion against search during active or failed reindexing
- In-memory fallback for isolated unit testing
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag._internal.sql_reindex import (
    complete_reindex_job_pg18,
    count_indexed_corpus_pg18,
    create_or_replace_reindex_job_pg18,
    fail_reindex_job_pg18,
    fetch_unindexed_chunks_batch_pg18,
    get_active_reindex_job_pg18,
    get_latest_reindex_job_pg18,
    get_reindex_job_by_id_pg18,
    queue_pending_ingestion_pg18,
    update_chunks_embedding_batch_pg18,
)
from orcia_core.rag.errors import RagReindexInProgressError
from orcia_core.rag.models import (
    RagReindexJobRecord,
)

logger = get_logger("orcia.rag.reindex")


async def check_rag_operational_on_conn(conn: AsyncConnection) -> None:
    """Raise RagReindexInProgressError if a reindex job is active or failed."""
    active_job = await get_active_reindex_job_pg18(conn)
    if active_job is not None:
        raise RagReindexInProgressError(
            progress_percentage=active_job.progress_percentage,
            job_id=active_job.id,
            detail_code="ERR_RAG_REINDEX_PROGRESS_DETAIL",
            detail_params={"progress_percentage": active_job.progress_percentage},
        )
    latest_job = await get_latest_reindex_job_pg18(conn)
    if latest_job is not None and latest_job.status == "FAILED":
        raise RagReindexInProgressError(
            progress_percentage=latest_job.progress_percentage,
            job_id=latest_job.id,
            detail_code="ERR_RAG_REINDEX_FAILED_DETAIL",
            detail_params={"error_message": latest_job.error_message or "unknown error"},
        )


async def execute_rag_reindex_job(
    *,
    engine: AsyncEngine,
    job_id: str,
    target_model_id: str,
    embedding_port: EmbeddingPort,
    batch_size: int = 50,
    trace_id: str = "00000000000000000000000000000000",
) -> RagReindexJobRecord:
    """Execute complete reindexing of all document chunks by batches of batch_size."""
    bind_trace_context(trace_id)
    logger.info("rag.reindex.start", job_id=job_id, target_model_id=target_model_id)

    try:
        while True:
            async with engine.begin() as conn:
                job = await get_reindex_job_by_id_pg18(conn, job_id)
                if job is None or job.status in ("CANCELLED", "COMPLETED"):
                    logger.info("rag.reindex.cancelled_or_completed", job_id=job_id)
                    return job or RagReindexJobRecord(
                        id=job_id,
                        target_model_id=target_model_id,
                        target_model_name="",
                        status="CANCELLED",
                    )

                batch = await fetch_unindexed_chunks_batch_pg18(
                    conn, target_model_id=target_model_id, batch_size=batch_size
                )
                if not batch:
                    # All document chunks vectorized: complete job
                    completed = await complete_reindex_job_pg18(
                        conn, job_id=job_id, target_model_id=target_model_id, trace_id=trace_id
                    )
                    logger.info("rag.reindex.completed", job_id=job_id)
                    return completed

                # Vectorize batch
                texts = [
                    f"{c['contextual_header']}\n\n{c['content_text']}".strip()
                    if c["contextual_header"]
                    else c["content_text"]
                    for c in batch
                ]
                vectors = await embedding_port.embed(texts)
                chunk_updates = [(batch[i]["id"], tuple(vectors[i])) for i in range(len(batch))]
                await update_chunks_embedding_batch_pg18(
                    conn,
                    job_id=job_id,
                    target_model_id=target_model_id,
                    chunk_updates=chunk_updates,
                )
    except Exception as exc:
        logger.error("rag.reindex.failed", job_id=job_id, error=str(exc))
        async with engine.begin() as conn:
            return await fail_reindex_job_pg18(
                conn,
                job_id=job_id,
                target_model_id=target_model_id,
                error_message=str(exc),
                trace_id=trace_id,
            )


__all__ = [
    "check_rag_operational_on_conn",
    "complete_reindex_job_pg18",
    "count_indexed_corpus_pg18",
    "create_or_replace_reindex_job_pg18",
    "execute_rag_reindex_job",
    "fail_reindex_job_pg18",
    "fetch_unindexed_chunks_batch_pg18",
    "get_active_reindex_job_pg18",
    "get_latest_reindex_job_pg18",
    "get_reindex_job_by_id_pg18",
    "queue_pending_ingestion_pg18",
    "update_chunks_embedding_batch_pg18",
]
