"""PostgreSQL 18 manual sync & active embedding guard for Workspace Datasources (`Story 25.5`)."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal.sql_iam_account_helpers import (
    ensure_iam_accounts_schema,
)
from orcia_core.bootstrap._internal.sql_workspace_datasources_queries import (
    _RETURNING_COLS,
    _SELECT_DATASOURCES_SQL,
    build_datasource_record_from_conn,
    ensure_workspace_datasources_schema,
)
from orcia_core.kernel import new_uuid7_str
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.workspace_sources_governance import WorkspaceDatasourceRecord
from orcia_core.rag.errors import (
    NoActiveEmbeddingModelError,
    RagReindexInProgressError,
)


async def has_active_global_embedding_model_on_conn(conn: AsyncConnection) -> bool:
    """Return True if an active GLOBAL embedding model mapping exists in PG18."""
    table_exists = (
        await conn.execute(sa.text("SELECT to_regclass('workspace_llm_tier_mappings')"))
    ).scalar()
    if table_exists is None:
        return False
    active_model = (
        await conn.execute(
            sa.text(
                """
                SELECT id FROM workspace_llm_tier_mappings
                WHERE usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL'
                LIMIT 1;
                """
            )
        )
    ).fetchone()
    return active_model is not None


async def assert_active_global_embedding_model_for_rag_source(
    conn: AsyncConnection,
    *,
    source_nature: str,
    instance: str | None = None,
) -> None:
    """Reject non-SOURCE_CODE datasource mutations when no GLOBAL embedding model is active."""
    if source_nature == "SOURCE_CODE":
        return
    if not await has_active_global_embedding_model_on_conn(conn):
        raise NoActiveEmbeddingModelError(
            detail_override=(
                "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
                "L'ajout ou la synchronisation de sources documentaires RAG nécessite "
                "un modèle d'indexation sémantique (/settings/ai-models)."
            ),
            instance=instance,
        )


async def trigger_workspace_datasource_sync_on_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    datasource_id: str,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Trigger manual sync: update last_sync_at, freshness_status and codegraph status."""
    try:
        wid_uuid = UUID(workspace_id.strip())
        ds_uuid = UUID(datasource_id.strip())
    except (ValueError, AttributeError):
        raise ResourceNotFoundError(instance=instance) from None

    no_model_needed = False
    record: WorkspaceDatasourceRecord | None = None

    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)

        current = (
            await conn.execute(
                sa.text(
                    f"{_SELECT_DATASOURCES_SQL} "
                    "WHERE id = :ds_id AND workspace_id = :wid FOR UPDATE"
                ),
                {"ds_id": ds_uuid, "wid": wid_uuid},
            )
        ).fetchone()
        if current is None:
            raise ResourceNotFoundError(instance=instance)

        current_nature = str(current[10] or "DOCUMENT_KB")
        reindex_in_progress_job: tuple[str, int] | None = None
        if current_nature != "SOURCE_CODE":
            if not await has_active_global_embedding_model_on_conn(conn):
                await conn.execute(
                    sa.text(
                        """
                        UPDATE workspace_datasources
                        SET freshness_status = 'AWAITING_EMBEDDING_MODEL'
                        WHERE id = :ds_id AND workspace_id = :wid
                        """
                    ),
                    {"ds_id": ds_uuid, "wid": wid_uuid},
                )
                no_model_needed = True
            else:
                reindex_tbl = (
                    await conn.execute(sa.text("SELECT to_regclass('rag_reindexing_jobs')"))
                ).scalar()
                active_reindex = (
                    (
                        await conn.execute(
                            sa.text(
                                """
                                SELECT id, progress_percentage FROM rag_reindexing_jobs
                                WHERE status IN ('PENDING', 'IN_PROGRESS')
                                ORDER BY created_at DESC
                                LIMIT 1;
                                """
                            )
                        )
                    ).fetchone()
                    if reindex_tbl is not None
                    else None
                )
                if active_reindex is not None:
                    reindex_in_progress_job = (str(active_reindex[0]), int(active_reindex[1]))
                    pending_ing_id = new_uuid7_str()
                    await conn.execute(
                        sa.text(
                            """
                            INSERT INTO rag_reindexing_pending_ingestions (
                                id, workspace_id, datasource_id, job_id,
                                payload_jsonb, status, created_at
                            ) VALUES (
                                :id, :wid, :ds_id, :job_id,
                                '{"reason": "sync_during_reindex"}'::jsonb,
                                'PENDING', NOW()
                            )
                            """
                        ),
                        {
                            "id": UUID(pending_ing_id),
                            "wid": wid_uuid,
                            "ds_id": ds_uuid,
                            "job_id": UUID(active_reindex[0]),
                        },
                    )

        if reindex_in_progress_job is not None:
            job_id_str, prog_pct = reindex_in_progress_job
            raise RagReindexInProgressError(
                progress_percentage=prog_pct,
                job_id=job_id_str,
                instance=instance,
                detail_override=(
                    f"Réindexation sémantique en cours ({prog_pct}%). "
                    "Synchronisation documentaire mise en attente."
                ),
            )

        if not no_model_needed:
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        UPDATE workspace_datasources
                        SET last_sync_at = NOW(),
                            freshness_status = 'SYNCED',
                            codegraph_status = CASE
                                WHEN codegraph_enabled
                                    AND codegraph_status != 'PAUSED_REFERENT_RENEWAL_REQUIRED'
                                THEN 'READY'
                                ELSE codegraph_status
                            END,
                            codegraph_last_indexed_at = CASE
                                WHEN codegraph_enabled THEN NOW()
                                ELSE codegraph_last_indexed_at
                            END
                        WHERE id = :ds_id AND workspace_id = :wid
                        RETURNING {_RETURNING_COLS}
                        """
                    ),
                    {"ds_id": ds_uuid, "wid": wid_uuid},
                )
            ).fetchone()
            assert row is not None
            record = await build_datasource_record_from_conn(conn, row, wid_uuid)

    if no_model_needed:
        raise NoActiveEmbeddingModelError(
            detail_override=(
                "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
                "Ingestion documentaire bloquée."
            ),
            instance=instance,
        )

    assert record is not None
    return record


__all__ = [
    "assert_active_global_embedding_model_for_rag_source",
    "has_active_global_embedding_model_on_conn",
    "trigger_workspace_datasource_sync_on_postgres18",
]
