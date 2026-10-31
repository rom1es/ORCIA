"""Orchestration, Inbox, Leases, RBAC, Settings, Cognitive Router & Studio providers (`AD-19`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_core.bootstrap import DurableOnboardingWizardService
from orcia_core.orchestration import (
    CognitiveModelRouterService,
    ControlCenterOverviewService,
    ResourceLeaseService,
    UnifiedNotificationAndClaimService,
    WorkflowOrchestrationSetupService,
    WorkflowStudioAndPackService,
)
from orcia_core.permissions import (
    HierarchicalRbacService,
    PlatformSettingsService,
)
from orcia_core.rag import ConnectorHubAndIngestionService


def get_orchestration_service(request: Request) -> WorkflowOrchestrationSetupService:
    """FastAPI `Depends` provider returning `WorkflowOrchestrationSetupService` from `app.state`."""
    svc: WorkflowOrchestrationSetupService | None = getattr(
        request.app.state, "orchestration_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.orchestration_service
    assert svc is not None
    return svc


def get_notification_service(request: Request) -> UnifiedNotificationAndClaimService:
    """FastAPI `Depends` provider returning `UnifiedNotificationAndClaimService`."""
    svc: UnifiedNotificationAndClaimService | None = getattr(
        request.app.state, "notification_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.notification_service
    assert svc is not None
    return svc


def get_resource_lease_service(request: Request) -> ResourceLeaseService:
    """FastAPI `Depends` provider returning `ResourceLeaseService` (`DEC-CONC-01`)."""
    svc: ResourceLeaseService | None = getattr(request.app.state, "resource_lease_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.resource_lease_service
    assert svc is not None
    return svc


def get_control_center_service(request: Request) -> ControlCenterOverviewService:
    """FastAPI `Depends` provider returning `ControlCenterOverviewService`."""
    svc: ControlCenterOverviewService | None = getattr(
        request.app.state, "control_center_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.control_center_service
    assert svc is not None
    return svc


def get_hierarchical_rbac_service(request: Request) -> HierarchicalRbacService:
    """FastAPI `Depends` provider returning `HierarchicalRbacService`."""
    svc: HierarchicalRbacService | None = getattr(
        request.app.state, "hierarchical_rbac_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.hierarchical_rbac_service
    assert svc is not None
    return svc


def get_platform_settings_service(request: Request) -> PlatformSettingsService:
    """FastAPI `Depends` provider returning `PlatformSettingsService`."""
    svc: PlatformSettingsService | None = getattr(
        request.app.state, "platform_settings_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.platform_settings_service
    assert svc is not None
    return svc


def get_cognitive_router_service(request: Request) -> CognitiveModelRouterService:
    """FastAPI `Depends` provider returning `CognitiveModelRouterService`."""
    svc: CognitiveModelRouterService | None = getattr(
        request.app.state, "cognitive_router_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.cognitive_router_service
    assert svc is not None
    return svc


def get_connector_hub_service(request: Request) -> ConnectorHubAndIngestionService:
    """FastAPI `Depends` provider returning `ConnectorHubAndIngestionService`."""
    svc: ConnectorHubAndIngestionService | None = getattr(
        request.app.state, "connector_hub_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.connector_hub_service
    assert svc is not None
    return svc


def get_studio_and_pack_service(request: Request) -> WorkflowStudioAndPackService:
    """FastAPI `Depends` provider returning `WorkflowStudioAndPackService`."""
    svc: WorkflowStudioAndPackService | None = getattr(
        request.app.state, "studio_and_pack_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.studio_and_pack_service
    assert svc is not None
    return svc


def get_durable_wizard_service(request: Request) -> DurableOnboardingWizardService:
    """FastAPI `Depends` provider returning `DurableOnboardingWizardService`."""
    svc: DurableOnboardingWizardService | None = getattr(
        request.app.state, "durable_wizard_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.durable_wizard_service
    assert svc is not None
    return svc
