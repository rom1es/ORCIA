"""In-memory RAG Reindexing fake for isolated unit testing (`tests/unit/fakes/`, `AD-19`).

Kept exclusively under tests/unit/fakes/ according to GEMINI.md policy.
"""

from __future__ import annotations

from typing import Any

from orcia_core.rag.models import (
    RagReindexJobRecord,
    RagReindexJobStatus,
    RagReindexPendingIngestionRecord,
)


class InMemoryReindexManager:
    """In-memory reindexing state manager used for isolated unit tests without Postgres."""

    def __init__(self) -> None:
        self._current_job: RagReindexJobRecord | None = None
        self._pending_ingestions: list[RagReindexPendingIngestionRecord] = []

    def reset(self) -> None:
        """Reset in-memory state for clean test isolation."""
        self._current_job = None
        self._pending_ingestions.clear()

    def clear(self) -> None:
        """Alias for reset."""
        self.reset()

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


default_in_memory_reindex_manager = InMemoryReindexManager()
