"""SQL operations for RAG reindexing jobs and outbox events (`Story 19.7`, `AD-24.7`)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.kernel.events import (
    EmbeddingReindexCompleted,
    EmbeddingReindexStarted,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.rag.models import RagReindexJobRecord


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _row_to_job(row: Any) -> RagReindexJobRecord:
    return RagReindexJobRecord(
        id=str(row.id),
        target_model_id=str(row.target_model_id),
        target_model_name=str(row.target_model_name),
        status=str(row.status),  # type: ignore[arg-type]
        total_chunks=int(row.total_chunks),
        processed_chunks=int(row.processed_chunks),
        progress_percentage=int(row.progress_percentage),
        error_message=str(row.error_message) if row.error_message is not None else None,
        created_at=row.created_at.isoformat() if row.created_at is not None else None,
        started_at=row.started_at.isoformat() if row.started_at is not None else None,
        completed_at=row.completed_at.isoformat() if row.completed_at is not None else None,
        updated_at=row.updated_at.isoformat() if row.updated_at is not None else None,
        created_by=str(row.created_by),
        cancelled_by_job_id=(
            str(row.cancelled_by_job_id) if row.cancelled_by_job_id is not None else None
        ),
    )


async def get_active_reindex_job_pg18(conn: AsyncConnection) -> RagReindexJobRecord | None:
    """Return the currently active (PENDING or IN_PROGRESS) reindex job, if any."""
    stmt = sa.text(
        """
        SELECT id, target_model_id, target_model_name, status,
               total_chunks, processed_chunks, progress_percentage,
               error_message, created_at, started_at, completed_at,
               updated_at, created_by, cancelled_by_job_id
        FROM rag_reindexing_jobs
        WHERE status IN ('PENDING', 'IN_PROGRESS')
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    row = (await conn.execute(stmt)).fetchone()
    if row is None:
        return None
    return _row_to_job(row)


async def get_latest_reindex_job_pg18(conn: AsyncConnection) -> RagReindexJobRecord | None:
    """Return the most recently created reindex job (any status)."""
    stmt = sa.text(
        """
        SELECT id, target_model_id, target_model_name, status,
               total_chunks, processed_chunks, progress_percentage,
               error_message, created_at, started_at, completed_at,
               updated_at, created_by, cancelled_by_job_id
        FROM rag_reindexing_jobs
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    row = (await conn.execute(stmt)).fetchone()
    if row is None:
        return None
    return _row_to_job(row)


async def get_reindex_job_by_id_pg18(
    conn: AsyncConnection, job_id: str
) -> RagReindexJobRecord | None:
    """Fetch a specific reindex job by ID."""
    stmt = sa.text(
        """
        SELECT id, target_model_id, target_model_name, status,
               total_chunks, processed_chunks, progress_percentage,
               error_message, created_at, started_at, completed_at,
               updated_at, created_by, cancelled_by_job_id
        FROM rag_reindexing_jobs
        WHERE id = :id
        """
    )
    row = (await conn.execute(stmt, {"id": UUID(job_id)})).fetchone()
    if row is None:
        return None
    return _row_to_job(row)


async def create_or_replace_reindex_job_pg18(
    conn: AsyncConnection,
    *,
    target_model_id: str,
    target_model_name: str,
    actor_id: str = "system",
    trace_id: str = "00000000000000000000000000000000",
) -> RagReindexJobRecord:
    """Cancel existing active job and create a new PENDING reindexing job."""
    new_job_id = new_uuid7_str()

    # Cancel any active job
    await conn.execute(
        sa.text(
            """
            UPDATE rag_reindexing_jobs
            SET status = 'CANCELLED',
                cancelled_by_job_id = :new_job_id,
                error_message = 'Cancelled by newer reindexing job',
                updated_at = NOW()
            WHERE status IN ('PENDING', 'IN_PROGRESS')
            """
        ),
        {"new_job_id": UUID(new_job_id)},
    )

    # Count document chunks requiring vector recalculation
    total_chunks_row = (
        await conn.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM kb_chunks
                WHERE chunk_role != 'AST_SYMBOL'
                """
            )
        )
    ).fetchone()
    total_chunks = int(total_chunks_row[0]) if total_chunks_row is not None else 0

    if total_chunks == 0:
        # Zero document chunks to reindex (e.g. Day-0 reset): complete immediately without blocking
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
        stmt_empty = sa.text(
            """
            INSERT INTO rag_reindexing_jobs (
                id, target_model_id, target_model_name, status,
                total_chunks, processed_chunks, progress_percentage,
                created_at, started_at, completed_at, updated_at, created_by
            ) VALUES (
                :id, :target_model_id, :target_model_name, 'COMPLETED',
                0, 0, 100,
                NOW(), NOW(), NOW(), NOW(), :created_by
            )
            RETURNING id, target_model_id, target_model_name, status,
                      total_chunks, processed_chunks, progress_percentage,
                      error_message, created_at, started_at, completed_at,
                      updated_at, created_by, cancelled_by_job_id
            """
        )
        row_empty = (
            await conn.execute(
                stmt_empty,
                {
                    "id": UUID(new_job_id),
                    "target_model_id": UUID(target_model_id),
                    "target_model_name": target_model_name,
                    "created_by": actor_id,
                },
            )
        ).fetchone()
        assert row_empty is not None

        ev_start = EmbeddingReindexStarted.create(
            job_id=new_job_id,
            target_model_id=target_model_id,
            target_model_name=target_model_name,
            total_chunks=0,
            trace_id=trace_id,
        )
        ev_comp = EmbeddingReindexCompleted.create(
            job_id=new_job_id,
            target_model_id=target_model_id,
            total_chunks=0,
            processed_chunks=0,
            trace_id=trace_id,
        )
        for ev in (ev_start, ev_comp):
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
        return _row_to_job(row_empty)

    # Insert new job for non-zero corpus
    stmt = sa.text(
        """
        INSERT INTO rag_reindexing_jobs (
            id, target_model_id, target_model_name, status,
            total_chunks, processed_chunks, progress_percentage,
            created_at, updated_at, created_by
        ) VALUES (
            :id, :target_model_id, :target_model_name, 'PENDING',
            :total_chunks, 0, 0,
            NOW(), NOW(), :created_by
        )
        RETURNING id, target_model_id, target_model_name, status,
                  total_chunks, processed_chunks, progress_percentage,
                  error_message, created_at, started_at, completed_at,
                  updated_at, created_by, cancelled_by_job_id
        """
    )
    row = (
        await conn.execute(
            stmt,
            {
                "id": UUID(new_job_id),
                "target_model_id": UUID(target_model_id),
                "target_model_name": target_model_name,
                "total_chunks": total_chunks,
                "created_by": actor_id,
            },
        )
    ).fetchone()
    assert row is not None

    # Emit Outbox event
    ev = EmbeddingReindexStarted.create(
        job_id=new_job_id,
        target_model_id=target_model_id,
        target_model_name=target_model_name,
        total_chunks=total_chunks,
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
