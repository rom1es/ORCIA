"""SQL operations for RAG reindexing chunks and pending ingestions (`Story 19.7`, `AD-24.7`)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.rag.models import RagReindexPendingIngestionRecord


def _format_halfvec(vec: tuple[float, ...]) -> str:
    return f"[{','.join(f'{x:.6f}' for x in vec)}]"


async def fetch_unindexed_chunks_batch_pg18(
    conn: AsyncConnection,
    target_model_id: str,
    *,
    batch_size: int = 50,
) -> list[dict[str, Any]]:
    """Fetch next batch of chunks that are not yet vectorized with target_model_id."""
    stmt = sa.text(
        """
        SELECT id, chunk_key, contextual_header, content_text
        FROM kb_chunks
        WHERE chunk_role != 'AST_SYMBOL'
          AND (embedding_model_id IS NULL OR embedding_model_id != :target_model_id)
        ORDER BY id
        LIMIT :batch_size
        """
    )
    res = await conn.execute(
        stmt,
        {"target_model_id": UUID(target_model_id), "batch_size": batch_size},
    )
    rows = res.fetchall()
    return [
        {
            "id": str(r.id),
            "chunk_key": str(r.chunk_key),
            "contextual_header": str(r.contextual_header or ""),
            "content_text": str(r.content_text or ""),
        }
        for r in rows
    ]


async def update_chunks_embedding_batch_pg18(
    conn: AsyncConnection,
    *,
    job_id: str,
    target_model_id: str,
    chunk_updates: list[tuple[str, tuple[float, ...]]],
) -> int:
    """Update vectors for a batch of chunks and advance job progress percentage."""
    if not chunk_updates:
        return 0

    for chunk_id, vec in chunk_updates:
        vec_literal = _format_halfvec(vec)
        await conn.execute(
            sa.text(
                """
                UPDATE kb_chunks
                SET embedding = CAST(:vec_lit AS halfvec(1024)),
                    embedding_model_id = :target_model_id,
                    embedding_generated_at = NOW()
                WHERE id = :chunk_id
                """
            ),
            {
                "vec_lit": vec_literal,
                "target_model_id": UUID(target_model_id),
                "chunk_id": UUID(chunk_id),
            },
        )

    # Advance job processed_chunks
    batch_count = len(chunk_updates)
    await conn.execute(
        sa.text(
            """
            UPDATE rag_reindexing_jobs
            SET status = 'IN_PROGRESS',
                started_at = COALESCE(started_at, NOW()),
                processed_chunks = processed_chunks + :batch_count,
                progress_percentage = CASE
                    WHEN total_chunks > 0 THEN LEAST(
                        100,
                        CAST((processed_chunks + :batch_count) * 100 / total_chunks AS integer)
                    )
                    ELSE 100
                END,
                updated_at = NOW()
            WHERE id = :job_id
            """
        ),
        {"batch_count": batch_count, "job_id": UUID(job_id)},
    )
    return batch_count


async def queue_pending_ingestion_pg18(
    conn: AsyncConnection,
    *,
    workspace_id: str,
    datasource_id: str,
    job_id: str | None,
    payload: dict[str, Any],
) -> RagReindexPendingIngestionRecord:
    """Queue a pending datasource ingestion deferred during an active reindex job."""
    ing_id = new_uuid7_str()
    stmt = sa.text(
        """
        INSERT INTO rag_reindexing_pending_ingestions (
            id, workspace_id, datasource_id, job_id, payload_jsonb,
            status, created_at
        ) VALUES (
            :id, :workspace_id, :datasource_id, :job_id, :payload_jsonb,
            'PENDING', NOW()
        )
        RETURNING id, workspace_id, datasource_id, job_id, payload_jsonb,
                  status, created_at, processed_at
        """
    )
    row = (
        await conn.execute(
            stmt,
            {
                "id": UUID(ing_id),
                "workspace_id": UUID(workspace_id),
                "datasource_id": UUID(datasource_id),
                "job_id": UUID(job_id) if job_id else None,
                "payload_jsonb": json.dumps(payload),
            },
        )
    ).fetchone()
    assert row is not None
    return RagReindexPendingIngestionRecord(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        datasource_id=str(row.datasource_id),
        job_id=str(row.job_id) if row.job_id is not None else None,
        payload_jsonb=dict(row.payload_jsonb),
        status=str(row.status),  # type: ignore[arg-type]
        created_at=row.created_at.isoformat() if row.created_at is not None else None,
        processed_at=row.processed_at.isoformat() if row.processed_at is not None else None,
    )
