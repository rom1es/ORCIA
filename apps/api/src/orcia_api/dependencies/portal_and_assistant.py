"""Portal, Two-Speed Search, Contextual Help & Assistant Workspace providers (`AD-19`)."""

from __future__ import annotations

import os

from fastapi import Request

from orcia_api.dependencies._llm_streaming_providers import (
    get_llm_streaming_port as get_llm_streaming_port,
)
from orcia_api.dependencies._llm_streaming_providers import (
    get_or_create_async_http_client as get_or_create_async_http_client,
)
from orcia_api.dependencies._rag_availability_guards import (
    get_embedding_port as get_embedding_port,
)
from orcia_api.dependencies._rag_availability_guards import (
    get_optional_embedding_port as get_optional_embedding_port,
)
from orcia_api.dependencies._rag_availability_guards import (
    require_rag_available as require_rag_available,
)
from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_core.bootstrap import (
    ProgressiveDay0AccostageService,
    SqlUserPreferencesAndMcpService,
)
from orcia_core.catalog.contextual_help import ContextualHelpResolutionService
from orcia_core.orchestration import AssistantAgentService
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.assistant_feedback import (
    SqlAssistantFeedbackRepository,
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
from orcia_core.rag import TwoSpeedFederatedSearchService


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
        raw_env = getattr(request.app.state, "orcia_env", None) or os.environ.get(
            "ORCIA_ENV", "local"
        )
        orcia_env = str(raw_env).strip().lower() or "local"
        app_token = getattr(request.app.state, "bootstrap_token", None)
        env_token = os.environ.get("ORCIA_BOOTSTRAP_TOKEN", "").strip()
        if app_token is not None:
            bootstrap_token: str | None = str(app_token).strip() or None
        elif env_token:
            bootstrap_token = env_token
        elif orcia_env in ("local", "test"):
            bootstrap_token = "orcia-day0-bootstrap-token"
        else:
            bootstrap_token = None
        svc = ProgressiveDay0AccostageService(
            orcia_env=orcia_env,
            expected_bootstrap_token=bootstrap_token,
        )
        request.app.state.accostage_service = svc
    return svc


def get_two_speed_search_service(request: Request) -> TwoSpeedFederatedSearchService:
    """FastAPI `Depends` provider returning `TwoSpeedFederatedSearchService` wired to Redis."""
    from orcia_api.dependencies._core_providers import should_auto_init_infra

    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is None and should_auto_init_infra("REDIS_URL"):
        initialize_app_services(request.app)
        redis_client = getattr(request.app.state, "redis_client", None)
    svc: TwoSpeedFederatedSearchService | None = getattr(
        request.app.state, "two_speed_search_service", None
    )
    if svc is None:
        svc = TwoSpeedFederatedSearchService(redis_client=redis_client)
        request.app.state.two_speed_search_service = svc
    elif getattr(svc, "_redis_client", None) is None and redis_client is not None:
        svc.set_redis_client(redis_client)
    return svc


def get_user_preferences_and_mcp_token_service(
    request: Request,
) -> SqlUserPreferencesAndMcpService:
    """FastAPI `Depends` provider returning `SqlUserPreferencesAndMcpService` (PG18)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    svc: SqlUserPreferencesAndMcpService | None = getattr(
        request.app.state, "user_preferences_and_mcp_token_service", None
    )
    if svc is None:
        svc = SqlUserPreferencesAndMcpService(engine=engine)
        request.app.state.user_preferences_and_mcp_token_service = svc
    elif getattr(svc, "_engine", None) is None and engine is not None:
        svc._engine = engine
    return svc


def get_contextual_help_service(request: Request) -> ContextualHelpResolutionService:
    """FastAPI `Depends` provider returning `ContextualHelpResolutionService`."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    redis_client = getattr(request.app.state, "redis_client", None)
    svc: ContextualHelpResolutionService | None = getattr(
        request.app.state, "contextual_help_service", None
    )
    if svc is None:
        svc = ContextualHelpResolutionService(redis_client=redis_client, engine=engine)
        request.app.state.contextual_help_service = svc
    else:
        if getattr(svc, "_engine", None) is None and engine is not None:
            svc._engine = engine
        if getattr(svc, "_redis_client", None) is None and redis_client is not None:
            svc._redis_client = redis_client
    return svc


def get_assistant_governance_service(
    request: Request,
) -> AssistantFourLevelGovernanceService:
    """FastAPI `Depends` provider returning `AssistantFourLevelGovernanceService` (PG18)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    svc: AssistantFourLevelGovernanceService | None = getattr(
        request.app.state, "assistant_governance_service", None
    )
    if svc is None:
        svc = AssistantFourLevelGovernanceService(engine=engine)
        request.app.state.assistant_governance_service = svc
    elif getattr(svc, "_engine", None) is None and engine is not None:
        svc.set_engine(engine)
    return svc


def get_assistant_three_speed_router_service(
    request: Request,
) -> AssistantThreeSpeedRouterService:
    """FastAPI `Depends` provider returning `AssistantThreeSpeedRouterService`."""
    gov = get_assistant_governance_service(request)
    svc: AssistantThreeSpeedRouterService | None = getattr(
        request.app.state, "assistant_three_speed_router_service", None
    )
    if svc is None:
        svc = AssistantThreeSpeedRouterService(governance_service=gov)
        request.app.state.assistant_three_speed_router_service = svc
    return svc


def get_assistant_citation_and_v5_guard_service(
    request: Request,
) -> AssistantCitationAndV5GuardService:
    """FastAPI `Depends` provider returning `AssistantCitationAndV5GuardService` (PG18 ledger)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_core.audit_finops import SqlAuditLedgerService

    engine = get_configured_db_engine(request)
    ledger_sink = getattr(request.app.state, "audit_ledger_service", None)
    if ledger_sink is None and engine is not None:
        ledger_sink = SqlAuditLedgerService(engine=engine)
        request.app.state.audit_ledger_service = ledger_sink
    svc: AssistantCitationAndV5GuardService | None = getattr(
        request.app.state, "assistant_citation_and_v5_guard_service", None
    )
    if svc is None:
        svc = AssistantCitationAndV5GuardService(audit_ledger_sink=ledger_sink)
        request.app.state.assistant_citation_and_v5_guard_service = svc
    elif getattr(svc, "_audit_ledger_sink", None) is None and ledger_sink is not None:
        svc.set_audit_ledger_sink(ledger_sink)
    return svc


def get_assistant_feedback_repository(
    request: Request,
) -> SqlAssistantFeedbackRepository:
    """FastAPI `Depends` provider returning `SqlAssistantFeedbackRepository` (PG18)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    repo: SqlAssistantFeedbackRepository | None = getattr(
        request.app.state, "assistant_feedback_repository", None
    )
    if repo is None:
        repo = SqlAssistantFeedbackRepository(engine=engine)
        request.app.state.assistant_feedback_repository = repo
    elif getattr(repo, "_engine", None) is None and engine is not None:
        repo.set_engine(engine)
    return repo


def get_assistant_folders_and_sharing_service(
    request: Request,
) -> AssistantFoldersAndSharingService:
    """FastAPI `Depends` provider returning `AssistantFoldersAndSharingService` (PG18 & Redis)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    redis_client = getattr(request.app.state, "redis_client", None)
    svc: AssistantFoldersAndSharingService | None = getattr(
        request.app.state, "assistant_folders_and_sharing_service", None
    )
    if svc is None:
        svc = AssistantFoldersAndSharingService(engine=engine, redis_client=redis_client)
        request.app.state.assistant_folders_and_sharing_service = svc
    else:
        if getattr(svc, "_engine", None) is None and engine is not None:
            svc.set_engine(engine)
        if getattr(svc, "_redis_client", None) is None and redis_client is not None:
            svc.set_redis_client(redis_client)
    return svc
