"""SQL operations for RAG reindexing job completion and failure lifecycle (`Story 19.7`)."""

from __future__ import annotations

import json
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.kernel.events import (
    EmbeddingReindexCompleted,
    EmbeddingReindexFailed,
)
from orcia_core.rag._internal.sql_reindex_jobs import _row_to_job
from orcia_core.rag.models import RagReindexJobRecord


async def complete_reindex_job_pg18(
    conn: AsyncConnection,
    *,
    job_id: str,
    target_model_id: str,
    trace_id: str = "00000000000000000000000000000000",
) -> RagReindexJobRecord:
    """Mark reindex job COMPLETED, unblock document datasources, and process queued ingestions."""
    row = (
        await conn.execute(
            sa.text(
                """
                UPDATE rag_reindexing_jobs
                SET status = 'COMPLETED',
                    progress_percentage = 100,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :job_id
                RETURNING id, target_model_id, target_model_name, status,
                          total_chunks, processed_chunks, progress_percentage,
                          error_message, created_at, started_at, completed_at,
                          updated_at, created_by, cancelled_by_job_id
                """
            ),
            {"job_id": UUID(job_id)},
        )
    ).fetchone()
    assert row is not None

    # Unblock document datasources
    await conn.execute(
        sa.text(
            """
            UPDATE workspace_datasources
            SET freshness_status = 'SYNCED',
                last_sync_at = NOW()
            WHERE freshness_status = 'AWAITING_EMBEDDING_MODEL'
              AND source_nature != 'SOURCE_CODE'
            """
        )
    )

    # Process pending queue
    await conn.execute(
        sa.text(
            """
            UPDATE rag_reindexing_pending_ingestions
            SET status = 'PROCESSED',
                processed_at = NOW()
            WHERE job_id = :job_id OR status = 'PENDING'
            """
        ),
        {"job_id": UUID(job_id)},
    )

    # Outbox event
    ev = EmbeddingReindexCompleted.create(
        job_id=job_id,
        target_model_id=target_model_id,
        total_chunks=int(row.total_chunks),
        processed_chunks=int(row.processed_chunks),
        trace_id=trace_id,
    )
    await conn.execute(
        sa.text(
            """
            INSERT INTO domain_events_outbox (
                event_id, event_type, aggregate_type, aggregate_id,
                payload_jsonb, trace_id, status, created_at
            ) VALUES (
                :event_id, :event_type, :aggregate_type, :aggregate_id,
                :payload_jsonb, :trace_id, 'PENDING', NOW()
            )
            """
        ),
        {
            "event_id": UUID(ev.event_id),
            "event_type": ev.event_type,
            "aggregate_type": ev.aggregate_type,
            "aggregate_id": str(ev.aggregate_id),
            "payload_jsonb": json.dumps(ev.payload),
            "trace_id": ev.trace_id,
        },
    )

    return _row_to_job(row)


async def fail_reindex_job_pg18(
    conn: AsyncConnection,
    *,
    job_id: str,
    target_model_id: str,
    error_message: str,
    trace_id: str = "00000000000000000000000000000000",
) -> RagReindexJobRecord:
    """Mark reindex job as FAILED with an explicit error message."""
    row = (
        await conn.execute(
            sa.text(
                """
                UPDATE rag_reindexing_jobs
                SET status = 'FAILED',
                    error_message = :error_message,
                    updated_at = NOW()
                WHERE id = :job_id
                RETURNING id, target_model_id, target_model_name, status,
                          total_chunks, processed_chunks, progress_percentage,
                          error_message, created_at, started_at, completed_at,
                          updated_at, created_by, cancelled_by_job_id
                """
            ),
            {"job_id": UUID(job_id), "error_message": error_message},
        )
    ).fetchone()
    assert row is not None

    ev = EmbeddingReindexFailed.create(
        job_id=job_id,
        target_model_id=target_model_id,
        error_message=error_message,
        processed_chunks=int(row.processed_chunks),
        trace_id=trace_id,
    )
    await conn.execute(
        sa.text(
            """
            INSERT INTO domain_events_outbox (
                event_id, event_type, aggregate_type, aggregate_id,
                payload_jsonb, trace_id, status, created_at
            ) VALUES (
                :event_id, :event_type, :aggregate_type, :aggregate_id,
                :payload_jsonb, :trace_id, 'PENDING', NOW()
            )
            """
        ),
        {
            "event_id": UUID(ev.event_id),
            "event_type": ev.event_type,
            "aggregate_type": ev.aggregate_type,
            "aggregate_id": str(ev.aggregate_id),
            "payload_jsonb": json.dumps(ev.payload),
            "trace_id": ev.trace_id,
        },
    )

    return _row_to_job(row)
