"""Portal, Two-Speed Search, Contextual Help & Assistant Workspace providers (`AD-19`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_core.bootstrap import ProgressiveDay0AccostageService
from orcia_core.catalog.contextual_help import ContextualHelpResolutionService
from orcia_core.orchestration import AssistantAgentService
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
