"""Orchestration, Inbox, Leases, RBAC, Settings, Cognitive Router & Studio providers (`AD-19`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.dependencies.finops_and_triggers import (
    get_audit_ledger_service as get_audit_ledger_service,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_autonomy_contract_service as get_autonomy_contract_service,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_cognitive_impact_service as get_cognitive_impact_service,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_connector_quota_guard_service as get_connector_quota_guard_service,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_finops_accounting_service as get_finops_accounting_service,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_log_sink_port as get_log_sink_port,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_provenance_exporter_service as get_provenance_exporter_service,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_remote_usage_sanitizer as get_remote_usage_sanitizer,
)
from orcia_api.dependencies.finops_and_triggers import (
    get_trigger_dispatcher_service as get_trigger_dispatcher_service,
)
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
from orcia_core.orchestration.assistant_process_launcher import AssistantProcessLauncherService
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
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    svc: UnifiedNotificationAndClaimService | None = getattr(
        request.app.state, "notification_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.notification_service
    assert svc is not None
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc.set_engine(engine)
    return svc


def get_resource_lease_service(request: Request) -> ResourceLeaseService:
    """FastAPI `Depends` provider returning `ResourceLeaseService` (`DEC-CONC-01`)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    svc: ResourceLeaseService | None = getattr(request.app.state, "resource_lease_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.resource_lease_service
    assert svc is not None
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc.set_engine(engine)
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
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_core.bootstrap import SqlWizardSessionRepository

    engine = get_configured_db_engine(request)
    svc: DurableOnboardingWizardService | None = getattr(
        request.app.state, "durable_wizard_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.durable_wizard_service
    assert svc is not None
    if engine is not None and getattr(svc, "_repository", None) is None:
        svc.set_repository(SqlWizardSessionRepository(engine))
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


def get_assistant_process_launcher_service(request: Request) -> AssistantProcessLauncherService:
    """FastAPI `Depends` provider returning `AssistantProcessLauncherService` (`Story 26.8`)."""
    launcher: AssistantProcessLauncherService | None = getattr(
        request.app.state, "assistant_process_launcher_service", None
    )
    if launcher is None:
        setup_svc = get_orchestration_service(request)
        engine = setup_svc.engine
        request.app.state.orchestration_engine = engine
        launcher = AssistantProcessLauncherService(setup_service=setup_svc, engine=engine)
        request.app.state.assistant_process_launcher_service = launcher
    return launcher
