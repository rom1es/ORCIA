"""Secondary Runtime Services Initialization Helpers extracted from `core_and_lifespan.py`."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI

from orcia_core.bootstrap import SqlWizardSessionRepository
from orcia_core.orchestration import (
    AssistantAgentService,
    CognitiveModelRouterService,
    ControlCenterOverviewService,
    ResourceLeaseService,
    UnifiedNotificationAndClaimService,
    WorkflowStudioAndPackService,
)
from orcia_core.permissions import (
    AuthAndOrganizationService,
    HierarchicalRbacService,
    IamAccountsGovernanceService,
    PlatformSettingsService,
    RolePermissionGrant,
)
from orcia_core.rag import (
    CatalogAndBlackboardContextSourceAdapter,
    ConnectorHubAndIngestionService,
    HybridRagVectorStoreAdapter,
    build_seeded_rag_service,
)


def init_runtime_secondary_services(
    app: FastAPI,
    *,
    auth_service: AuthAndOrganizationService,
    catalog_service: object,
    permission_broker_service: object,
) -> None:
    """Attach notification, RBAC, FinOps, assistant agent, HTTPX, and log sink services."""
    from orcia_core.audit_finops import BudgetGuardService, SqlAuditLedgerService
    from orcia_core.bootstrap import DurableOnboardingWizardService
    from orcia_core.catalog import FederatedCatalogService
    from orcia_core.permissions import PermissionBrokerService

    db_engine = getattr(app.state, "db_engine", None)
    cat_svc: FederatedCatalogService = catalog_service  # type: ignore[assignment]
    perm_svc: PermissionBrokerService = permission_broker_service  # type: ignore[assignment]

    if getattr(app.state, "notification_service", None) is None:
        app.state.notification_service = UnifiedNotificationAndClaimService(
            sse_broker=app.state.sse_broker, engine=db_engine
        )
    if getattr(app.state, "resource_lease_service", None) is None:
        app.state.resource_lease_service = ResourceLeaseService(engine=db_engine)
    if getattr(app.state, "control_center_service", None) is None:
        app.state.control_center_service = ControlCenterOverviewService(
            evaluator=auth_service.evaluator, notification_service=app.state.notification_service
        )
    if getattr(app.state, "hierarchical_rbac_service", None) is None:
        alpha = "org/orcia/bu/claims/team/alpha"
        verbs: tuple[Literal["grant", "read", "execute", "update"], ...] = (
            "grant",
            "read",
            "execute",
            "update",
        )
        app.state.hierarchical_rbac_service = HierarchicalRbacService(
            initial_grants=tuple(
                RolePermissionGrant(
                    id=f"0195f000-0000-7000-8000-00000000810{idx}",
                    subject_type="ROLE",
                    subject_id="TEAM_LEAD",
                    scope_path=alpha,
                    verb=verb,
                )
                for idx, verb in enumerate(verbs, start=1)
            )
        )
    if getattr(app.state, "iam_accounts_service", None) is None:
        app.state.iam_accounts_service = IamAccountsGovernanceService()
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
            llm_gateway=app.state.llm_gateway,
            external_budget_guard_port=BudgetGuardService(engine=db_engine) if db_engine else None,
        )
    if getattr(app.state, "connector_hub_service", None) is None:
        app.state.connector_hub_service = ConnectorHubAndIngestionService()
    if getattr(app.state, "studio_and_pack_service", None) is None:
        app.state.studio_and_pack_service = WorkflowStudioAndPackService()
    if getattr(app.state, "durable_wizard_service", None) is None:
        app.state.durable_wizard_service = DurableOnboardingWizardService(
            repository=SqlWizardSessionRepository(db_engine) if db_engine is not None else None
        )
    if getattr(app.state, "audit_ledger_service", None) is None:
        app.state.audit_ledger_service = SqlAuditLedgerService(engine=db_engine)
    if getattr(app.state, "assistant_service", None) is None:
        seeded_rag, _ = build_seeded_rag_service()
        app.state.assistant_service = AssistantAgentService(
            context_source=CatalogAndBlackboardContextSourceAdapter(
                rag_service=seeded_rag,
                catalog_items_provider=lambda _ws: cat_svc.workflows,
                blackboard_snapshots_provider=lambda _ws: (),
                permission_policies_provider=lambda _ws: perm_svc.list_policies(),
            ),
            vector_store=HybridRagVectorStoreAdapter(seeded_rag),
            llm_gateway=app.state.llm_gateway,
            orchestration_setup=app.state.orchestration_service,
            workflow_engine=app.state.orchestration_service.engine,
            cognitive_router=app.state.cognitive_router_service,
        )
    if getattr(app.state, "http_client", None) is None or getattr(
        app.state.http_client, "is_closed", False
    ):
        import httpx

        app.state.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    if getattr(app.state, "log_sink", None) is None:
        from orcia_core.observability import build_log_sink_from_env

        app.state.log_sink = build_log_sink_from_env(
            http_client=app.state.http_client,
            secret_provider=getattr(app.state, "secret_provider", None),
        )
