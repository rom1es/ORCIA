"""Core Composition Root lifespan & foundational service providers (`AD-19`)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap import (
    DurableOnboardingWizardService,
    LiteLLMAdapter,
    SystemBootstrapWorkflowService,
    build_default_system_bootstrap_service,
    build_litellm_gateway_plugin,
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
from orcia_core.rag import (
    CatalogAndBlackboardContextSourceAdapter,
    ConnectorHubAndIngestionService,
    HybridRagService,
    HybridRagVectorStoreAdapter,
    TripartiteGraphAndFreshnessService,
    build_empty_rag_service,
    build_seeded_rag_service,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ports import LLMPort
from orcia_pack_sdlc import activate_sdlc_pack


def _resolve_default_llm_gateway() -> LLMPort:
    """Resolve `LiteLLMAdapter` by default (`ORCIA_USE_CASSETTE_LLM=true` for cassette)."""
    use_cassette = os.environ.get("ORCIA_USE_CASSETTE_LLM", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if use_cassette:
        return DeterministicCassetteLLM()
    mode = os.environ.get("ORCIA_LLM_GATEWAY", "").strip().lower()
    if mode == "cassette":
        return DeterministicCassetteLLM()
    if mode == "litellm_plugin":
        return build_litellm_gateway_plugin()
    return LiteLLMAdapter(
        fallback_cassette=DeterministicCassetteLLM(),
    )


def initialize_app_services(app: FastAPI) -> None:
    """Wire and attach all domain services to `app.state` (idempotent Composition Root)."""
    activate_sdlc_pack()
    if getattr(app.state, "llm_gateway", None) is None:
        app.state.llm_gateway = _resolve_default_llm_gateway()
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

    if getattr(app.state, "http_client", None) is None or getattr(
        app.state.http_client, "is_closed", False
    ):
        import httpx

        app.state.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    if (
        getattr(app.state, "session_maker", None) is None
        and os.environ.get("ORCIA_ENABLE_PG_SESSION_MAKER") == "1"
    ):
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

            from orcia_core.config import resolve_database_url

            db_engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.5})
            app.state.db_engine = db_engine
            app.state.session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
        except Exception as exc:
            from orcia_core.observability.logging import get_logger

            get_logger("orcia.api.lifespan").warning(
                "lifespan_pg_session_maker_init_skipped", error_type=type(exc).__name__
            )


def get_or_create_shared_db_engine(request: Request) -> AsyncEngine:
    """Return shared `AsyncEngine` from `request.app.state.db_engine`, creating it if absent."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from orcia_core.config import resolve_database_url

    engine: AsyncEngine | None = getattr(request.app.state, "db_engine", None)
    if engine is None:
        engine = create_async_engine(
            resolve_database_url(),
            poolclass=NullPool,
            connect_args={"timeout": 1.5},
        )
        request.app.state.db_engine = engine
    return engine


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager initializing Composition Root services (`AD-19`)."""
    initialize_app_services(app)
    try:
        yield
    finally:
        http_client = getattr(app.state, "http_client", None)
        if http_client is not None:
            with suppress(Exception):
                await http_client.aclose()
        db_engine = getattr(app.state, "db_engine", None)
        if db_engine is not None:
            with suppress(Exception):
                await db_engine.dispose()


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


def get_ontology_and_rag_services(
    request: Request, *, fixture: bool = False
) -> tuple[
    OntologyGovernanceService,
    HybridRagService,
    TripartiteGraphAndFreshnessService,
]:
    """Return either the empty runtime Ontology/RAG bundle or the deterministic test fixture."""
    if fixture:
        seeded: (
            tuple[
                OntologyGovernanceService,
                HybridRagService,
                TripartiteGraphAndFreshnessService,
            ]
            | None
        ) = getattr(request.app.state, "ontology_rag_seeded_bundle", None)
        if seeded is None:
            gov = build_seeded_ontology_service()
            rag, trip = build_seeded_rag_service()
            seeded = (gov, rag, trip)
            request.app.state.ontology_rag_seeded_bundle = seeded
        return seeded

    runtime: (
        tuple[
            OntologyGovernanceService,
            HybridRagService,
            TripartiteGraphAndFreshnessService,
        ]
        | None
    ) = getattr(request.app.state, "ontology_rag_runtime_bundle", None)
    if runtime is None:
        gov = build_empty_ontology_service()
        rag, trip = build_empty_rag_service()
        runtime = (gov, rag, trip)
        request.app.state.ontology_rag_runtime_bundle = runtime
    return runtime
