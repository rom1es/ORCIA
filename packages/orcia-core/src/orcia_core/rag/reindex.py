"""RAG Reindexing Orchestration & Execution Service (`Story 19.7`, `AD-24.7`, `D9`, `D12`).

Coordinates:
- Batch calculation of embeddings with EmbeddingPort (batch_size=50)
- Progress tracking and database state transitions (PENDING -> IN_PROGRESS -> COMPLETED/FAILED)
- Guard assertion against search during active or failed reindexing
- In-memory fallback for isolated unit testing
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag._internal.sql_reindex import (
    complete_reindex_job_pg18,
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
    RagReindexJobStatus,
    RagReindexPendingIngestionRecord,
)

logger = get_logger("orcia.rag.reindex")


class InMemoryReindexManager:
    """In-memory reindexing state manager used for isolated unit tests without Postgres."""

    def __init__(self) -> None:
        self._current_job: RagReindexJobRecord | None = None
        self._pending_ingestions: list[RagReindexPendingIngestionRecord] = []

    def reset(self) -> None:
        """Reset in-memory state for clean test isolation."""
        self._current_job = None
        self._pending_ingestions.clear()

    def get_active_job(self) -> RagReindexJobRecord | None:
        if self._current_job is not None and self._current_job.status in (
            "PENDING",
            "IN_PROGRESS",
        ):
            return self._current_job
        return None

    def get_latest_job(self) -> RagReindexJobRecord | None:
        return self._current_job

    def create_or_replace_job(
        self,
        *,
        target_model_id: str,
        target_model_name: str,
        total_chunks: int = 0,
        actor_id: str = "system",
    ) -> RagReindexJobRecord:
        status: RagReindexJobStatus = "COMPLETED" if total_chunks == 0 else "PENDING"
        progress_percentage = 100 if total_chunks == 0 else 0
        job = RagReindexJobRecord(
            id=f"mem-job-{target_model_id}",
            target_model_id=target_model_id,
            target_model_name=target_model_name,
            status=status,
            total_chunks=total_chunks,
            processed_chunks=0,
            progress_percentage=progress_percentage,
            created_by=actor_id,
        )
        self._current_job = job
        return job

    def advance_progress(self, processed_count: int) -> RagReindexJobRecord:
        assert self._current_job is not None
        tot = self._current_job.total_chunks
        processed = self._current_job.processed_chunks + processed_count
        pct = int(processed * 100 / tot) if tot > 0 else 100
        self._current_job = RagReindexJobRecord(
            id=self._current_job.id,
            target_model_id=self._current_job.target_model_id,
            target_model_name=self._current_job.target_model_name,
            status="IN_PROGRESS",
            total_chunks=tot,
            processed_chunks=processed,
            progress_percentage=min(100, pct),
            created_by=self._current_job.created_by,
        )
        return self._current_job

    def complete_job(self) -> RagReindexJobRecord:
        assert self._current_job is not None
        self._current_job = RagReindexJobRecord(
            id=self._current_job.id,
            target_model_id=self._current_job.target_model_id,
            target_model_name=self._current_job.target_model_name,
            status="COMPLETED",
            total_chunks=self._current_job.total_chunks,
            processed_chunks=self._current_job.total_chunks,
            progress_percentage=100,
            created_by=self._current_job.created_by,
        )
        return self._current_job

    def fail_job(self, error_message: str) -> RagReindexJobRecord:
        assert self._current_job is not None
        self._current_job = RagReindexJobRecord(
            id=self._current_job.id,
            target_model_id=self._current_job.target_model_id,
            target_model_name=self._current_job.target_model_name,
            status="FAILED",
            total_chunks=self._current_job.total_chunks,
            processed_chunks=self._current_job.processed_chunks,
            progress_percentage=self._current_job.progress_percentage,
            error_message=error_message,
            created_by=self._current_job.created_by,
        )
        return self._current_job

    def queue_ingestion(
        self,
        *,
        workspace_id: str,
        datasource_id: str,
        payload: dict[str, Any],
    ) -> RagReindexPendingIngestionRecord:
        rec = RagReindexPendingIngestionRecord(
            id=f"mem-ing-{datasource_id}",
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            job_id=self._current_job.id if self._current_job else None,
            payload_jsonb=payload,
            status="PENDING",
        )
        self._pending_ingestions.append(rec)
        return rec

    def clear(self) -> None:
        self._current_job = None
        self._pending_ingestions.clear()


default_in_memory_reindex_manager = InMemoryReindexManager()


async def check_rag_operational_on_conn(conn: AsyncConnection) -> None:
    """Raise RagReindexInProgressError if a reindex job is active or failed."""
    active_job = await get_active_reindex_job_pg18(conn)
    if active_job is not None:
        raise RagReindexInProgressError(
            progress_percentage=active_job.progress_percentage,
            job_id=active_job.id,
            detail_override=(
                f"Réindexation sémantique en cours ({active_job.progress_percentage}%). "
                "La recherche documentaire et Mon Assistant sont temporairement indisponibles."
            ),
        )
    latest_job = await get_latest_reindex_job_pg18(conn)
    if latest_job is not None and latest_job.status == "FAILED":
        raise RagReindexInProgressError(
            progress_percentage=latest_job.progress_percentage,
            job_id=latest_job.id,
            detail_override=(
                f"La réindexation sémantique a échoué "
                f"({latest_job.error_message or 'erreur inconnue'}). "
                "Veuillez relancer la réindexation dans /settings/ai-models."
            ),
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
    "InMemoryReindexManager",
    "check_rag_operational_on_conn",
    "complete_reindex_job_pg18",
    "create_or_replace_reindex_job_pg18",
    "default_in_memory_reindex_manager",
    "execute_rag_reindex_job",
    "fail_reindex_job_pg18",
    "fetch_unindexed_chunks_batch_pg18",
    "get_active_reindex_job_pg18",
    "get_latest_reindex_job_pg18",
    "get_reindex_job_by_id_pg18",
    "queue_pending_ingestion_pg18",
    "update_chunks_embedding_batch_pg18",
]
