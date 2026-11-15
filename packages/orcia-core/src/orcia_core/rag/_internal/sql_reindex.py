"""SQL operations facade for RAG reindexing jobs, chunks, and ingestions (`Story 19.7`, `AD-24.7`).

Modularized into `sql_reindex_jobs.py` (< 350 lines) and `sql_reindex_chunks.py` (< 150 lines).
"""

from __future__ import annotations

from orcia_core.rag._internal.sql_reindex_chunks import (
    fetch_unindexed_chunks_batch_pg18,
    queue_pending_ingestion_pg18,
    update_chunks_embedding_batch_pg18,
)
from orcia_core.rag._internal.sql_reindex_jobs import (
    create_or_replace_reindex_job_pg18,
    get_active_reindex_job_pg18,
    get_latest_reindex_job_pg18,
    get_reindex_job_by_id_pg18,
)
from orcia_core.rag._internal.sql_reindex_lifecycle import (
    complete_reindex_job_pg18,
    fail_reindex_job_pg18,
)

__all__ = [
    "complete_reindex_job_pg18",
    "create_or_replace_reindex_job_pg18",
    "fail_reindex_job_pg18",
    "fetch_unindexed_chunks_batch_pg18",
    "get_active_reindex_job_pg18",
    "get_latest_reindex_job_pg18",
    "get_reindex_job_by_id_pg18",
    "queue_pending_ingestion_pg18",
    "update_chunks_embedding_batch_pg18",
]
