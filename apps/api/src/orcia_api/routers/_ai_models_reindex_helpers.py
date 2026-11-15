"""Helpers for RAG vector reindexing triggers, status retrieval, and Dramatiq dispatch.

Story 19.7 (`AD-24.7`, `D9`, `D12`).
"""

from __future__ import annotations

from fastapi import Request

from orcia_api.routers._ai_models_helpers import assert_ai_models_write_allowed
from orcia_api.schemas.ai_models_hub import (
    RagReindexStatusResponse,
    RagReindexTriggerResponse,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    AiModelMappingRecord,
    AiModelsHubService,
)
from orcia_core.orchestration._internal.sql_ai_model_mappings import (
    ensure_ai_model_mappings_schema_on_postgres18,
    get_active_global_embedding_model_pg18,
)
from orcia_core.permissions import AuthAndOrganizationService
from orcia_core.rag.errors import NoActiveEmbeddingModelError
from orcia_core.rag.models import RagReindexJobRecord
from orcia_core.rag.reindex import (
    create_or_replace_reindex_job_pg18,
    default_in_memory_reindex_manager,
    get_latest_reindex_job_pg18,
)

logger = get_logger("orcia.api.ai_models_reindex")


def _row_to_status_response(job: RagReindexJobRecord | None) -> RagReindexStatusResponse:
    if job is None:
        return RagReindexStatusResponse(status="IDLE")
    return RagReindexStatusResponse(
        job_id=job.id,
        status=job.status,
        target_model_id=job.target_model_id,
        target_model_name=job.target_model_name,
        total_chunks=job.total_chunks,
        processed_chunks=job.processed_chunks,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        updated_at=job.updated_at,
    )


async def trigger_global_reindexing_job(
    request: Request,
    mapping: AiModelMappingRecord,
    actor_id: str,
) -> RagReindexJobRecord:
    """Create a persistent reindex job and dispatch background actor."""
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            job = await create_or_replace_reindex_job_pg18(
                conn,
                target_model_id=mapping.id,
                target_model_name=mapping.model_name,
                actor_id=actor_id,
                trace_id=trace_id,
            )
        if job.status != "COMPLETED":
            try:
                import dramatiq

                broker = dramatiq.get_broker()
                actor = broker.get_actor("rag_reindexer")
                if actor is not None:
                    actor.send(job.id, mapping.id, trace_id)
                else:
                    broker.enqueue(
                        dramatiq.Message(
                            queue_name="default",
                            actor_name="rag_reindexer",
                            args=(job.id, mapping.id, trace_id),
                            kwargs={},
                            options={},
                        )
                    )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "ai_models_hub.dramatiq_dispatch_failed",
                    job_id=job.id,
                    error=str(exc),
                )
        return job

    mem_job = default_in_memory_reindex_manager.create_or_replace_job(
        target_model_id=mapping.id,
        target_model_name=mapping.model_name,
        total_chunks=0,
        actor_id=actor_id,
    )
    return mem_job


async def fetch_reindex_status_response(request: Request) -> RagReindexStatusResponse:
    """Fetch status of latest vector corpus reindexing job."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            # Ensure schema if needed
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            job = await get_latest_reindex_job_pg18(conn)
            return _row_to_status_response(job)

    mem_job = default_in_memory_reindex_manager.get_latest_job()
    return _row_to_status_response(mem_job)


async def trigger_manual_reindex_embeddings(
    request: Request,
    auth_svc: AuthAndOrganizationService,
    hub_svc: AiModelsHubService,
    actor_persona: str | None,
) -> RagReindexTriggerResponse:
    """Admin-triggered reindexing of the vector corpus on active global embedding model."""
    assert_ai_models_write_allowed(request, actor_persona)
    actor_id = actor_persona or "system"

    engine = getattr(request.app.state, "db_engine", None)
    active_mapping: AiModelMappingRecord | None = None
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            resolved = await get_active_global_embedding_model_pg18(
                conn, cipher=auth_svc.vault_cipher
            )
            if resolved is not None:
                active_mapping, _ = resolved
    else:
        active_mapping = hub_svc.get_active_embedding_mapping()

    if active_mapping is None:
        raise NoActiveEmbeddingModelError(
            detail_override=(
                "Impossible de lancer la réindexation : aucun modèle d'embedding actif "
                "configuré au niveau GLOBAL. Activez un modèle dans /settings/ai-models."
            )
        )

    job = await trigger_global_reindexing_job(
        request,
        active_mapping,
        actor_id=actor_id,
    )
    return RagReindexTriggerResponse(
        job_id=job.id,
        status=job.status,
        target_model_id=active_mapping.id,
        target_model_name=active_mapping.model_name,
        message="Réindexation globale du corpus vectoriel initiée avec succès.",
    )
