"""FastAPI RAG & EmbeddingPort Availability Guards (`AD-24`, `Story 25.5`)."""

from __future__ import annotations

import inspect
from typing import cast
from urllib.parse import urlparse

from fastapi import Request

from orcia_api.dependencies._llm_streaming_providers import (
    get_or_create_async_http_client,
    is_cassette_llm_enabled,
)
from orcia_core.orchestration import (
    get_active_global_embedding_model_pg18,
    unpack_encrypted_api_key,
)
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag.adapters.embedding_httpx import (
    HttpxGeminiNativeEmbeddingAdapter,
    HttpxOpenAiCompatibleEmbeddingAdapter,
)
from orcia_core.rag.errors import (
    NoActiveEmbeddingModelError,
    RagReindexInProgressError,
)
from orcia_core.rag.reindex import check_rag_operational_on_conn


async def get_embedding_port(request: Request) -> EmbeddingPort:
    """FastAPI `Depends` provider resolving the active global EmbeddingPort."""
    from orcia_api.dependencies.core_and_lifespan import (
        get_or_create_shared_db_engine,
        initialize_app_services,
    )

    test_reindex_mgr = getattr(request.app.state, "reindex_manager", None)
    if test_reindex_mgr is not None:
        active_mem = test_reindex_mgr.get_active_job()
        if active_mem is not None:
            raise RagReindexInProgressError(
                progress_percentage=active_mem.progress_percentage,
                job_id=active_mem.id,
                detail_override=(
                    f"Réindexation sémantique en cours ({active_mem.progress_percentage}%). "
                    "La recherche documentaire et l'ingestion RAG sont temporairement "
                    "indisponibles."
                ),
            )
        latest_mem = test_reindex_mgr.get_latest_job()
        if latest_mem is not None and latest_mem.status == "FAILED":
            raise RagReindexInProgressError(
                progress_percentage=latest_mem.progress_percentage,
                job_id=latest_mem.id,
                detail_override=(
                    f"La réindexation sémantique a échoué "
                    f"({latest_mem.error_message or 'erreur inconnue'}). "
                    "Veuillez relancer la réindexation dans /settings/ai-models."
                ),
            )

    engine = getattr(request.app.state, "db_engine", None)
    if engine is None and test_reindex_mgr is None:
        engine = get_or_create_shared_db_engine(request)

    if engine is not None:
        async with engine.connect() as conn:
            await check_rag_operational_on_conn(conn)

    explicit_port = getattr(request.app.state, "embedding_port", None)
    if explicit_port is not None:
        return cast(EmbeddingPort, explicit_port)

    http_client = get_or_create_async_http_client(request)

    auth_svc = getattr(request.app.state, "auth_service", None)
    if auth_svc is None:
        initialize_app_services(request.app)
        auth_svc = request.app.state.auth_service

    if engine is not None:
        async with engine.connect() as conn:
            resolved = await get_active_global_embedding_model_pg18(
                conn, cipher=auth_svc.vault_cipher
            )
            if resolved is None:
                raise NoActiveEmbeddingModelError(
                    detail_override=(
                        "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
                        "Veuillez en configurer un dans /settings/ai-models."
                    )
                )
            rec, api_key = resolved
    else:
        from orcia_api.dependencies.orchestration_and_settings import (
            get_ai_models_hub_service,
        )

        hub_svc = get_ai_models_hub_service(request)
        active_rec = hub_svc.get_active_embedding_mapping()
        if active_rec is None:
            raise NoActiveEmbeddingModelError(
                detail_override=(
                    "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
                    "Veuillez en configurer un dans /settings/ai-models."
                )
            )
        rec = active_rec
        api_key = None
        if rec.encrypted_api_key:
            host = urlparse(rec.endpoint_uri).netloc or "default"
            api_key = unpack_encrypted_api_key(
                auth_svc.vault_cipher,
                mapping_id=rec.id,
                packed=rec.encrypted_api_key,
                target_host=host,
            )

    if is_cassette_llm_enabled():
        from orcia_core.testing.cassette_llm import DeterministicCassetteEmbedding

        return DeterministicCassetteEmbedding()

    if rec.protocol_mode == "gemini_native":
        return HttpxGeminiNativeEmbeddingAdapter(
            http_client=http_client,
            endpoint_uri=rec.endpoint_uri,
            model_name=rec.model_name,
            api_key=api_key,
        )
    return HttpxOpenAiCompatibleEmbeddingAdapter(
        http_client=http_client,
        endpoint_uri=rec.endpoint_uri,
        model_name=rec.model_name,
        api_key=api_key,
    )


async def get_optional_embedding_port(request: Request) -> EmbeddingPort | None:
    """Resolve active EmbeddingPort or return `None` when RAG is unavailable (`Story 25.5`)."""
    try:
        override = request.app.dependency_overrides.get(get_embedding_port)
        if override is not None:
            result = override()
            if inspect.isawaitable(result):
                result = await result
            return cast(EmbeddingPort | None, result)
        return await get_embedding_port(request)
    except (NoActiveEmbeddingModelError, RagReindexInProgressError):
        return None


async def require_rag_available(request: Request) -> EmbeddingPort:
    """FastAPI `Depends` provider asserting an active global embedding model and no reindex job."""
    return await get_embedding_port(request)


__all__ = [
    "get_embedding_port",
    "get_optional_embedding_port",
    "require_rag_available",
]
