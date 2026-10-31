"""Single Composition Root & FastAPI `Depends` providers for `apps/api` (`AD-19`, `Story 3.2a`).

All domain services and adapters are wired here and attached to `app.state` during application
initialization / `lifespan`. Zero `_DEFAULT_*_SERVICE` singletons are instantiated at module
import time inside router modules.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from orcia_core.bootstrap import (
    DurableOnboardingWizardService,
    ProgressiveDay0AccostageService,
    SystemBootstrapWorkflowService,
    build_default_system_bootstrap_service,
)
from orcia_core.catalog import (
    FederatedCatalogService,
    build_default_federated_catalog_service,
)
from orcia_core.ontology import (
    OntologyGovernanceService,
    build_empty_ontology_service,
    build_seeded_ontology_service,
)
from orcia_core.orchestration import (
    AssistantAgentService,
    CognitiveModelRouterService,
    ConnectorInvoker,
    ControlCenterOverviewService,
    ResourceLeaseService,
    UnifiedNotificationAndClaimService,
    WorkflowOrchestrationSetupService,
    WorkflowStudioAndPackService,
    build_default_orchestration_setup_service,
    register_default_step_executors,
)
from orcia_core.permissions import (
    AuthAndOrganizationService,
    HierarchicalRbacService,
    PermissionBrokerService,
    PlatformSettingsService,
    RolePermissionGrant,
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
)
from orcia_core.permissions.user_preferences_and_mcp_tokens import (
    UserPreferencesAndMcpTokenService,
)
from orcia_core.rag import (
    CatalogAndBlackboardContextSourceAdapter,
    ConnectorHubAndIngestionService,
    HybridRagService,
    HybridRagVectorStoreAdapter,
    TripartiteGraphAndFreshnessService,
    TwoSpeedFederatedSearchService,
    build_empty_rag_service,
    build_seeded_rag_service,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_pack_sdlc import activate_sdlc_pack


def initialize_app_services(app: FastAPI) -> None:
    """Wire and attach all domain services to `app.state` (idempotent Composition Root)."""
    activate_sdlc_pack()
    if getattr(app.state, "llm_gateway", None) is None:
        app.state.llm_gateway = DeterministicCassetteLLM()
    if getattr(app.state, "connector_invoker", None) is None:
        app.state.connector_invoker = ConnectorInvoker()
    register_default_step_executors(
        llm_gateway=app.state.llm_gateway,
        connector_invoker=app.state.connector_invoker,
    )

    if getattr(app.state, "auth_service", None) is None:
        auth_service = build_default_auth_and_org_service()
        app.state.auth_service = auth_service
    else:
        auth_service = app.state.auth_service

    if getattr(app.state, "catalog_service", None) is None:
        catalog_service = build_default_federated_catalog_service(evaluator=auth_service.evaluator)
        app.state.catalog_service = catalog_service
    else:
        catalog_service = app.state.catalog_service

    if getattr(app.state, "permission_broker_service", None) is None:
        permission_broker_service = build_default_permission_broker_service(
            evaluator=auth_service.evaluator, vault_cipher=auth_service.vault_cipher
        )
        app.state.permission_broker_service = permission_broker_service
    else:
        permission_broker_service = app.state.permission_broker_service

    if getattr(app.state, "bootstrap_service", None) is None:
        app.state.bootstrap_service = build_default_system_bootstrap_service(
            auth_service=auth_service,
            catalog_service=catalog_service,
            permission_broker_service=permission_broker_service,
        )

    if getattr(app.state, "orchestration_service", None) is None:
        app.state.orchestration_service = build_default_orchestration_setup_service(
            evaluator=auth_service.evaluator,
        )

    if getattr(app.state, "notification_service", None) is None:
        notif_svc = UnifiedNotificationAndClaimService()
        notif_svc.seed_default_notifications(
            workspace_id="0195f000-0000-7000-8000-000000000301",
            team_id="0195f000-0000-7000-8000-000000000103",
            user_id="0195f000-0000-7000-8000-000000000203",
            run_id="0195f000-0000-7000-8000-000000000701",
            step_execution_id="0195f000-0000-7000-8000-000000000801",
        )
        app.state.notification_service = notif_svc

    if getattr(app.state, "resource_lease_service", None) is None:
        app.state.resource_lease_service = ResourceLeaseService()

    if getattr(app.state, "control_center_service", None) is None:
        app.state.control_center_service = ControlCenterOverviewService(
            evaluator=auth_service.evaluator,
            notification_service=app.state.notification_service,
        )

    if getattr(app.state, "hierarchical_rbac_service", None) is None:
        app.state.hierarchical_rbac_service = HierarchicalRbacService(
            initial_grants=(
                RolePermissionGrant(
                    id="0195f000-0000-7000-8000-000000008101",
                    subject_type="ROLE",
                    subject_id="TEAM_LEAD",
                    scope_path="org/orcia/bu/claims/team/alpha",
                    verb="grant",
                ),
                RolePermissionGrant(
                    id="0195f000-0000-7000-8000-000000008102",
                    subject_type="ROLE",
                    subject_id="TEAM_LEAD",
                    scope_path="org/orcia/bu/claims/team/alpha",
                    verb="read",
                ),
                RolePermissionGrant(
                    id="0195f000-0000-7000-8000-000000008103",
                    subject_type="ROLE",
                    subject_id="TEAM_LEAD",
                    scope_path="org/orcia/bu/claims/team/alpha",
                    verb="execute",
                ),
                RolePermissionGrant(
                    id="0195f000-0000-7000-8000-000000008104",
                    subject_type="ROLE",
                    subject_id="TEAM_LEAD",
                    scope_path="org/orcia/bu/claims/team/alpha",
                    verb="update",
                ),
            )
        )

    if getattr(app.state, "platform_settings_service", None) is None:
        settings_svc = PlatformSettingsService()
        settings_svc.upsert_initial_setting(
            scope_level="WORKSPACE",
            scope_id="0195f000-0000-7000-8000-000000000301",
            category="ai-models",
            key="default_routing_policy",
            value_jsonb={"default_tier": "medium", "default_effort": "balanced"},
        )
        app.state.platform_settings_service = settings_svc

    if getattr(app.state, "cognitive_router_service", None) is None:
        app.state.cognitive_router_service = CognitiveModelRouterService(
            llm_gateway=app.state.llm_gateway
        )

    if getattr(app.state, "connector_hub_service", None) is None:
        app.state.connector_hub_service = ConnectorHubAndIngestionService()

    if getattr(app.state, "studio_and_pack_service", None) is None:
        app.state.studio_and_pack_service = WorkflowStudioAndPackService()

    if getattr(app.state, "durable_wizard_service", None) is None:
        app.state.durable_wizard_service = DurableOnboardingWizardService()

    if getattr(app.state, "assistant_service", None) is None:
        seeded_rag, _ = build_seeded_rag_service()
        context_source = CatalogAndBlackboardContextSourceAdapter(
            rag_service=seeded_rag,
            catalog_items_provider=lambda _ws: catalog_service.workflows,
            blackboard_snapshots_provider=lambda _ws: (),
            permission_policies_provider=lambda _ws: permission_broker_service.list_policies(),
        )
        vector_store = HybridRagVectorStoreAdapter(seeded_rag)
        app.state.assistant_service = AssistantAgentService(
            context_source=context_source,
            vector_store=vector_store,
            llm_gateway=app.state.llm_gateway,
            orchestration_setup=app.state.orchestration_service,
            workflow_engine=app.state.orchestration_service.engine,
        )


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager initializing Composition Root services (`AD-19`)."""
    initialize_app_services(app)
    yield


def get_auth_service(request: Request) -> AuthAndOrganizationService:
    """FastAPI `Depends` provider returning `AuthAndOrganizationService` from `app.state`."""
    svc: AuthAndOrganizationService | None = getattr(request.app.state, "auth_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.auth_service
    assert svc is not None
    return svc


def get_catalog_service(request: Request) -> FederatedCatalogService:
    """FastAPI `Depends` provider returning `FederatedCatalogService` from `app.state`."""
    svc: FederatedCatalogService | None = getattr(request.app.state, "catalog_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.catalog_service
    assert svc is not None
    return svc


def get_permission_broker_service(request: Request) -> PermissionBrokerService:
    """FastAPI `Depends` provider returning `PermissionBrokerService` from `app.state`."""
    svc: PermissionBrokerService | None = getattr(
        request.app.state, "permission_broker_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.permission_broker_service
    assert svc is not None
    return svc


def get_bootstrap_service(request: Request) -> SystemBootstrapWorkflowService:
    """FastAPI `Depends` provider returning `SystemBootstrapWorkflowService` from `app.state`."""
    svc: SystemBootstrapWorkflowService | None = getattr(
        request.app.state, "bootstrap_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.bootstrap_service
    assert svc is not None
    return svc


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
    """FastAPI `Depends` provider returning `UnifiedNotificationAndClaimService` (`Story 5.1`)."""
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
    """FastAPI `Depends` provider returning `ControlCenterOverviewService` (`Story 5.2`)."""
    svc: ControlCenterOverviewService | None = getattr(
        request.app.state, "control_center_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.control_center_service
    assert svc is not None
    return svc


def get_assistant_service(request: Request) -> AssistantAgentService:
    """FastAPI `Depends` provider returning `AssistantAgentService` (`Story 3.3`)."""
    svc: AssistantAgentService | None = getattr(request.app.state, "assistant_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.assistant_service
    assert svc is not None
    return svc


def get_epic2_services(
    request: Request, *, fixture: bool = False
) -> tuple[
    OntologyGovernanceService,
    HybridRagService,
    TripartiteGraphAndFreshnessService,
]:
    """Return either the empty runtime Epic 2 bundle or the deterministic test fixture bundle."""
    if fixture:
        seeded: (
            tuple[
                OntologyGovernanceService,
                HybridRagService,
                TripartiteGraphAndFreshnessService,
            ]
            | None
        ) = getattr(request.app.state, "epic2_seeded_bundle", None)
        if seeded is None:
            gov = build_seeded_ontology_service()
            rag, trip = build_seeded_rag_service()
            seeded = (gov, rag, trip)
            request.app.state.epic2_seeded_bundle = seeded
        return seeded

    runtime: (
        tuple[
            OntologyGovernanceService,
            HybridRagService,
            TripartiteGraphAndFreshnessService,
        ]
        | None
    ) = getattr(request.app.state, "epic2_runtime_bundle", None)
    if runtime is None:
        gov = build_empty_ontology_service()
        rag, trip = build_empty_rag_service()
        runtime = (gov, rag, trip)
        request.app.state.epic2_runtime_bundle = runtime
    return runtime


def get_hierarchical_rbac_service(request: Request) -> HierarchicalRbacService:
    """FastAPI `Depends` provider returning `HierarchicalRbacService` (`Story 8.1`)."""
    svc: HierarchicalRbacService | None = getattr(
        request.app.state, "hierarchical_rbac_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.hierarchical_rbac_service
    assert svc is not None
    return svc


def get_platform_settings_service(request: Request) -> PlatformSettingsService:
    """FastAPI `Depends` provider returning `PlatformSettingsService` (`Story 8.3`)."""
    svc: PlatformSettingsService | None = getattr(
        request.app.state, "platform_settings_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.platform_settings_service
    assert svc is not None
    return svc


def get_cognitive_router_service(request: Request) -> CognitiveModelRouterService:
    """FastAPI `Depends` provider returning `CognitiveModelRouterService` (`Story 8.2`)."""
    svc: CognitiveModelRouterService | None = getattr(
        request.app.state, "cognitive_router_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.cognitive_router_service
    assert svc is not None
    return svc


def get_connector_hub_service(request: Request) -> ConnectorHubAndIngestionService:
    """FastAPI `Depends` provider returning `ConnectorHubAndIngestionService` (`Story 8.4`)."""
    svc: ConnectorHubAndIngestionService | None = getattr(
        request.app.state, "connector_hub_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.connector_hub_service
    assert svc is not None
    return svc


def get_studio_and_pack_service(request: Request) -> WorkflowStudioAndPackService:
    """FastAPI `Depends` provider returning `WorkflowStudioAndPackService` (`Story 8.5`)."""
    svc: WorkflowStudioAndPackService | None = getattr(
        request.app.state, "studio_and_pack_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.studio_and_pack_service
    assert svc is not None
    return svc


def get_durable_wizard_service(request: Request) -> DurableOnboardingWizardService:
    """FastAPI `Depends` provider returning `DurableOnboardingWizardService` (`Story 8.6`)."""
    svc: DurableOnboardingWizardService | None = getattr(
        request.app.state, "durable_wizard_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.durable_wizard_service
    assert svc is not None
    return svc


def get_accostage_service(request: Request) -> ProgressiveDay0AccostageService:
    """FastAPI `Depends` provider returning `ProgressiveDay0AccostageService` (`Story 9.2`)."""
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
    """FastAPI `Depends` provider returning `TwoSpeedFederatedSearchService` (`Story 9.3`)."""
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
    """FastAPI `Depends` provider returning `UserPreferencesAndMcpTokenService` (`Story 9.4`)."""
    svc: UserPreferencesAndMcpTokenService | None = getattr(
        request.app.state, "user_preferences_and_mcp_token_service", None
    )
    if svc is None:
        svc = UserPreferencesAndMcpTokenService()
        request.app.state.user_preferences_and_mcp_token_service = svc
    return svc
