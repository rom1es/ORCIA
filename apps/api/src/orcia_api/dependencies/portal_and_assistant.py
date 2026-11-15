"""Portal, Two-Speed Search, Contextual Help & Assistant Workspace providers (`AD-19`)."""

from __future__ import annotations

from typing import cast
from urllib.parse import urlparse

import httpx
from fastapi import Request

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_core.bootstrap import ProgressiveDay0AccostageService
from orcia_core.catalog.contextual_help import ContextualHelpResolutionService
from orcia_core.orchestration import AssistantAgentService
from orcia_core.orchestration._internal.sql_ai_model_mappings import (
    ensure_ai_model_mappings_schema_on_postgres18,
    get_active_global_embedding_model_pg18,
)
from orcia_core.orchestration.ai_models_crypto import unpack_encrypted_api_key
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.assistant_folders_and_sharing import (
    AssistantFoldersAndSharingService,
)
from orcia_core.orchestration.assistant_governance import (
    AssistantFourLevelGovernanceService,
)
from orcia_core.orchestration.assistant_three_speed_router import (
    AssistantThreeSpeedRouterService,
)
from orcia_core.permissions.user_preferences_and_mcp_tokens import (
    UserPreferencesAndMcpTokenService,
)
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag import TwoSpeedFederatedSearchService
from orcia_core.rag.adapters.embedding_httpx import (
    HttpxGeminiNativeEmbeddingAdapter,
    HttpxOpenAiCompatibleEmbeddingAdapter,
)
from orcia_core.rag.errors import (
    NoActiveEmbeddingModelError,
    RagReindexInProgressError,
)
from orcia_core.rag.reindex import (
    check_rag_operational_on_conn,
    default_in_memory_reindex_manager,
)


def get_assistant_service(request: Request) -> AssistantAgentService:
    """FastAPI `Depends` provider returning `AssistantAgentService`."""
    svc: AssistantAgentService | None = getattr(request.app.state, "assistant_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.assistant_service
    assert svc is not None
    return svc


def get_accostage_service(request: Request) -> ProgressiveDay0AccostageService:
    """FastAPI `Depends` provider returning `ProgressiveDay0AccostageService`."""
    svc: ProgressiveDay0AccostageService | None = getattr(
        request.app.state, "accostage_service", None
    )
    if svc is None:
        svc = ProgressiveDay0AccostageService(
            orcia_env="local",
            expected_bootstrap_token="orcia-day0-bootstrap-token",
        )
        request.app.state.accostage_service = svc
    return svc


def get_two_speed_search_service(request: Request) -> TwoSpeedFederatedSearchService:
    """FastAPI `Depends` provider returning `TwoSpeedFederatedSearchService`."""
    svc: TwoSpeedFederatedSearchService | None = getattr(
        request.app.state, "two_speed_search_service", None
    )
    if svc is None:
        svc = TwoSpeedFederatedSearchService()
        request.app.state.two_speed_search_service = svc
    return svc


def get_user_preferences_and_mcp_token_service(
    request: Request,
) -> UserPreferencesAndMcpTokenService:
    """FastAPI `Depends` provider returning `UserPreferencesAndMcpTokenService`."""
    svc: UserPreferencesAndMcpTokenService | None = getattr(
        request.app.state, "user_preferences_and_mcp_token_service", None
    )
    if svc is None:
        svc = UserPreferencesAndMcpTokenService()
        request.app.state.user_preferences_and_mcp_token_service = svc
    return svc


def get_contextual_help_service(request: Request) -> ContextualHelpResolutionService:
    """FastAPI `Depends` provider returning `ContextualHelpResolutionService`."""
    svc: ContextualHelpResolutionService | None = getattr(
        request.app.state, "contextual_help_service", None
    )
    if svc is None:
        svc = ContextualHelpResolutionService()
        request.app.state.contextual_help_service = svc
    return svc


def get_assistant_governance_service(
    request: Request,
) -> AssistantFourLevelGovernanceService:
    """FastAPI `Depends` provider returning `AssistantFourLevelGovernanceService`."""
    svc: AssistantFourLevelGovernanceService | None = getattr(
        request.app.state, "assistant_governance_service", None
    )
    if svc is None:
        svc = AssistantFourLevelGovernanceService()
        request.app.state.assistant_governance_service = svc
    return svc


def get_assistant_three_speed_router_service(
    request: Request,
) -> AssistantThreeSpeedRouterService:
    """FastAPI `Depends` provider returning `AssistantThreeSpeedRouterService`."""
    svc: AssistantThreeSpeedRouterService | None = getattr(
        request.app.state, "assistant_three_speed_router_service", None
    )
    if svc is None:
        gov = get_assistant_governance_service(request)
        svc = AssistantThreeSpeedRouterService(governance_service=gov)
        request.app.state.assistant_three_speed_router_service = svc
    return svc


def get_assistant_citation_and_v5_guard_service(
    request: Request,
) -> AssistantCitationAndV5GuardService:
    """FastAPI `Depends` provider returning `AssistantCitationAndV5GuardService`."""
    svc: AssistantCitationAndV5GuardService | None = getattr(
        request.app.state, "assistant_citation_and_v5_guard_service", None
    )
    if svc is None:
        svc = AssistantCitationAndV5GuardService()
        request.app.state.assistant_citation_and_v5_guard_service = svc
    return svc


def get_assistant_folders_and_sharing_service(
    request: Request,
) -> AssistantFoldersAndSharingService:
    """FastAPI `Depends` provider returning `AssistantFoldersAndSharingService`."""
    svc: AssistantFoldersAndSharingService | None = getattr(
        request.app.state, "assistant_folders_and_sharing_service", None
    )
    if svc is None:
        svc = AssistantFoldersAndSharingService()
        request.app.state.assistant_folders_and_sharing_service = svc
    return svc


async def get_embedding_port(request: Request) -> EmbeddingPort:
    """FastAPI `Depends` provider resolving the active global EmbeddingPort."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await check_rag_operational_on_conn(conn)
    else:
        active_mem = default_in_memory_reindex_manager.get_active_job()
        if active_mem is not None:
            raise RagReindexInProgressError(
                progress_percentage=active_mem.progress_percentage,
                job_id=active_mem.id,
                detail_override=(
                    f"Réindexation sémantique en cours ({active_mem.progress_percentage}%). "
                    "La recherche documentaire et Mon Assistant sont temporairement indisponibles."
                ),
            )
        latest_mem = default_in_memory_reindex_manager.get_latest_job()
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

    explicit_port = getattr(request.app.state, "embedding_port", None)
    if explicit_port is not None:
        return cast(EmbeddingPort, explicit_port)

    http_client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if http_client is None:
        http_client = httpx.AsyncClient()

    auth_svc = getattr(request.app.state, "auth_service", None)
    if auth_svc is None:
        initialize_app_services(request.app)
        auth_svc = request.app.state.auth_service

    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
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
