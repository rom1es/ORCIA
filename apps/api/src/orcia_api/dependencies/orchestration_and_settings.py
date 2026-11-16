"""Orchestration, Inbox, Leases, RBAC, Settings, Cognitive Router & Studio providers (`AD-19`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from orcia_core.audit_finops import ProvenanceExporterService, SqlAuditLedgerService

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_core.bootstrap import DurableOnboardingWizardService
from orcia_core.orchestration import (
    AiModelsHubService,
    CognitiveModelRouterService,
    ControlCenterOverviewService,
    ResourceLeaseService,
    UnifiedNotificationAndClaimService,
    WorkflowOrchestrationSetupService,
    WorkflowStudioAndPackService,
)
from orcia_core.permissions import (
    HierarchicalRbacService,
    IamAccountsGovernanceService,
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


def get_iam_accounts_service(request: Request) -> IamAccountsGovernanceService:
    """FastAPI `Depends` provider returning `IamAccountsGovernanceService` (`Story 17.3`)."""
    svc: IamAccountsGovernanceService | None = getattr(
        request.app.state, "iam_accounts_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.iam_accounts_service
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


def get_ai_models_hub_service(request: Request) -> AiModelsHubService:
    """FastAPI `Depends` provider returning `AiModelsHubService` (`Story 17.5`)."""
    svc: AiModelsHubService | None = getattr(request.app.state, "ai_models_hub_service", None)
    if svc is None:
        initialize_app_services(request.app)
        auth = request.app.state.auth_service
        svc = AiModelsHubService(vault_cipher=auth.vault_cipher)
        request.app.state.ai_models_hub_service = svc
    return svc


def get_audit_ledger_service(request: Request) -> SqlAuditLedgerService:
    """FastAPI `Depends` provider returning `SqlAuditLedgerService` (`Story 6.1`)."""
    from orcia_core.audit_finops import SqlAuditLedgerService

    svc: SqlAuditLedgerService | None = getattr(request.app.state, "audit_ledger_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = getattr(request.app.state, "audit_ledger_service", None)
        if svc is None:
            engine = getattr(request.app.state, "db_engine", None)
            svc = SqlAuditLedgerService(engine=engine)
            request.app.state.audit_ledger_service = svc
    assert svc is not None
    return svc


def get_provenance_exporter_service(request: Request) -> ProvenanceExporterService:
    """FastAPI `Depends` provider returning `ProvenanceExporterService` (`Story 6.1`)."""
    from orcia_core.audit_finops import ProvenanceExporterService

    ledger_svc = get_audit_ledger_service(request)
    return ProvenanceExporterService(ledger_svc)
