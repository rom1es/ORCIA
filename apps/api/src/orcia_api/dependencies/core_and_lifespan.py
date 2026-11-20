"""Core Composition Root lifespan & foundational service providers (`AD-19`)."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, Literal

from fastapi import FastAPI

if TYPE_CHECKING:
    pass

from orcia_api.dependencies._core_providers import (
    get_auth_service as get_auth_service,
)
from orcia_api.dependencies._core_providers import (
    get_bootstrap_service as get_bootstrap_service,
)
from orcia_api.dependencies._core_providers import (
    get_catalog_service as get_catalog_service,
)
from orcia_api.dependencies._core_providers import (
    get_ontology_and_rag_services as get_ontology_and_rag_services,
)
from orcia_api.dependencies._core_providers import (
    get_or_create_shared_db_engine as get_or_create_shared_db_engine,
)
from orcia_api.dependencies._core_providers import (
    get_permission_broker_service as get_permission_broker_service,
)
from orcia_api.dependencies._core_providers import should_auto_init_infra
from orcia_core.bootstrap import (
    DurableOnboardingWizardService,
    LiteLLMAdapter,
    SqlWizardSessionRepository,
    build_default_system_bootstrap_service,
    build_litellm_gateway_plugin,
    upsert_declarative_pack_bundles_sql,
)
from orcia_core.catalog import (
    build_default_federated_catalog_service,
)
from orcia_core.orchestration import (
    AssistantAgentService,
    CognitiveModelRouterService,
    ConnectorInvoker,
    ControlCenterOverviewService,
    RedisSseBrokerAdapter,
    ResourceLeaseService,
    UnifiedNotificationAndClaimService,
    WorkflowStudioAndPackService,
    build_default_orchestration_setup_service,
    register_default_step_executors,
)
from orcia_core.permissions import (
    HierarchicalRbacService,
    IamAccountsGovernanceService,
    InMemoryPlatformAuthPolicyStore,
    PlatformSettingsService,
    RolePermissionGrant,
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
    persona_impersonation_allowed,
)
from orcia_core.rag import (
    CatalogAndBlackboardContextSourceAdapter,
    ConnectorHubAndIngestionService,
    HybridRagVectorStoreAdapter,
    build_seeded_rag_service,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_core.workflows import upsert_vsm_definitions_v2_sql
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


def should_seed_test_personas_in_memory() -> bool:
    """Return `True` only inside automated unit tests or explicit persona-seed mode.

    A real server process (`uvicorn`) or isolated E2E stack (`ORCIA_ENV=e2e`) starts with
    zero in-memory mock personas (`Marc`, `Karim`, `Claire`) so authentication operates
    strictly against PostgreSQL 18.
    """
    if os.environ.get("ORCIA_FORCE_REAL_RUNTIME", "").strip() == "1":
        return False
    if os.environ.get("ORCIA_ENV", "").strip().lower() == "e2e":
        return False
    if os.environ.get("ORCIA_SEED_TEST_PERSONAS", "").strip() == "1":
        return True
    return bool(
        os.environ.get("PYTEST_CURRENT_TEST", "").strip()
        or os.environ.get("PYTEST_VERSION", "").strip()
        or "pytest" in sys.modules
    )


def initialize_app_services(app: FastAPI) -> None:
    """Wire and attach all domain services to `app.state` (idempotent Composition Root)."""
    activate_sdlc_pack()
    if getattr(app.state, "session_maker", None) is None and should_auto_init_infra("DATABASE_URL"):
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
            from sqlalchemy.pool import NullPool

            from orcia_core.config import resolve_database_url
            from orcia_core.orchestration import DbosSqlAlchemyUnitOfWork

            engine_kwargs: dict[str, object] = {"connect_args": {"timeout": 1.5}}
            if "pytest" in sys.modules:
                engine_kwargs["poolclass"] = NullPool
            db_engine = getattr(app.state, "db_engine", None)
            if db_engine is None:
                db_engine = create_async_engine(resolve_database_url(), **engine_kwargs)
                app.state.db_engine = db_engine
            app.state.session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
            if getattr(app.state, "dbos_uow", None) is None:
                app.state.dbos_uow = DbosSqlAlchemyUnitOfWork.from_engine(
                    db_engine, session_factory=app.state.session_maker
                )
        except Exception as exc:
            from orcia_core.observability.logging import get_logger

            get_logger("orcia.api.lifespan").warning(
                "lifespan_pg_session_maker_init_skipped", error_type=type(exc).__name__
            )

    if getattr(app.state, "llm_gateway", None) is None:
        app.state.llm_gateway = _resolve_default_llm_gateway()
    if getattr(app.state, "finops_sanitizer", None) is None:
        from orcia_core.audit_finops import RemoteUsageSanitizer

        app.state.finops_sanitizer = RemoteUsageSanitizer()
    if getattr(app.state, "connector_quota_guard_service", None) is None:
        from orcia_core.audit_finops import SqlConnectorQuotaGuardService

        app.state.connector_quota_guard_service = SqlConnectorQuotaGuardService(
            engine=getattr(app.state, "db_engine", None)
        )
    if getattr(app.state, "connector_invoker", None) is None:
        app.state.connector_invoker = ConnectorInvoker(
            quota_guard=app.state.connector_quota_guard_service,
            usage_sanitizer=app.state.finops_sanitizer,
        )
    if not hasattr(app.state, "otp_email_sink"):
        app.state.otp_email_sink = None
    register_default_step_executors(
        llm_gateway=app.state.llm_gateway,
        connector_invoker=app.state.connector_invoker,
    )

    if getattr(app.state, "auth_service", None) is None:
        seed_personas = should_seed_test_personas_in_memory()
        auth_service = build_default_auth_and_org_service(
            allow_persona_impersonation=(
                seed_personas
                and persona_impersonation_allowed(os.environ.get("ORCIA_ENV", "local"))
            ),
            seed_reference_personas=seed_personas,
        )
        app.state.auth_service = auth_service
    else:
        auth_service = app.state.auth_service

    if (
        getattr(app.state, "auth_policy_store", None) is None
        and getattr(app.state, "db_engine", None) is None
        and not should_auto_init_infra("DATABASE_URL")
    ):
        app.state.auth_policy_store = InMemoryPlatformAuthPolicyStore(
            cipher=auth_service.vault_cipher
        )

    if getattr(app.state, "catalog_service", None) is None:
        catalog_service = build_default_federated_catalog_service(evaluator=auth_service.evaluator)
        app.state.catalog_service = catalog_service
    else:
        catalog_service = app.state.catalog_service

    if getattr(app.state, "contextual_help_service", None) is None:
        from orcia_core.catalog.contextual_help import ContextualHelpResolutionService

        app.state.contextual_help_service = ContextualHelpResolutionService(
            redis_client=getattr(app.state, "redis_client", None),
            engine=getattr(app.state, "db_engine", None),
        )
    else:
        help_svc = app.state.contextual_help_service
        if (
            getattr(help_svc, "_engine", None) is None
            and getattr(app.state, "db_engine", None) is not None
        ):
            help_svc._engine = app.state.db_engine
        if (
            getattr(help_svc, "_redis_client", None) is None
            and getattr(app.state, "redis_client", None) is not None
        ):
            help_svc._redis_client = app.state.redis_client

    if getattr(app.state, "permission_broker_service", None) is None:
        permission_broker_service = build_default_permission_broker_service(
            evaluator=auth_service.evaluator,
            vault_cipher=auth_service.vault_cipher,
            engine=getattr(app.state, "db_engine", None),
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
    if (
        getattr(app.state, "db_engine", None) is not None
        and getattr(app.state.bootstrap_service.gate_service, "_repository", None) is None
    ):
        from orcia_core.gates import SqlGateEvaluationRepository

        gate_repo = getattr(app.state, "gate_repository", None) or SqlGateEvaluationRepository(
            app.state.db_engine
        )
        app.state.gate_repository = gate_repo
        app.state.bootstrap_service.gate_service.set_repository(gate_repo)

    if getattr(app.state, "orchestration_service", None) is None:
        app.state.orchestration_service = build_default_orchestration_setup_service(
            evaluator=auth_service.evaluator,
        )

    if getattr(app.state, "secret_provider", None) is None:
        from orcia_core.permissions.secret_manager import EnvelopeVaultSecretProvider

        app.state.secret_provider = EnvelopeVaultSecretProvider()

    if getattr(app.state, "redis_client", None) is None and should_auto_init_infra("REDIS_URL"):
        try:
            import redis.asyncio as aioredis

            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0").strip()
            if redis_url:
                app.state.redis_client = aioredis.from_url(redis_url, decode_responses=False)
        except Exception as exc:
            from orcia_core.observability.logging import get_logger

            get_logger("orcia.api.lifespan").warning(
                "lifespan_redis_init_skipped", error_type=type(exc).__name__
            )

    if getattr(app.state, "sse_broker", None) is None:
        app.state.sse_broker = RedisSseBrokerAdapter(
            redis_client=getattr(app.state, "redis_client", None)
        )
    elif getattr(app.state, "redis_client", None) is not None and hasattr(
        app.state.sse_broker, "set_redis_client"
    ):
        app.state.sse_broker.set_redis_client(app.state.redis_client)

    help_svc_after_redis = getattr(app.state, "contextual_help_service", None)
    if (
        help_svc_after_redis is not None
        and getattr(help_svc_after_redis, "_redis_client", None) is None
        and getattr(app.state, "redis_client", None) is not None
    ):
        help_svc_after_redis._redis_client = app.state.redis_client

    if getattr(app.state, "notification_service", None) is None:
        notif_svc = UnifiedNotificationAndClaimService(
            sse_broker=app.state.sse_broker,
            engine=getattr(app.state, "db_engine", None),
        )
        app.state.notification_service = notif_svc

    if getattr(app.state, "resource_lease_service", None) is None:
        app.state.resource_lease_service = ResourceLeaseService(
            engine=getattr(app.state, "db_engine", None)
        )

    if getattr(app.state, "control_center_service", None) is None:
        app.state.control_center_service = ControlCenterOverviewService(
            evaluator=auth_service.evaluator,
            notification_service=app.state.notification_service,
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
        from orcia_core.audit_finops import BudgetGuardService

        db_engine = getattr(app.state, "db_engine", None)
        budget_guard_port = BudgetGuardService(engine=db_engine) if db_engine is not None else None
        app.state.cognitive_router_service = CognitiveModelRouterService(
            llm_gateway=app.state.llm_gateway,
            external_budget_guard_port=budget_guard_port,
        )

    if getattr(app.state, "connector_hub_service", None) is None:
        app.state.connector_hub_service = ConnectorHubAndIngestionService()

    if getattr(app.state, "studio_and_pack_service", None) is None:
        app.state.studio_and_pack_service = WorkflowStudioAndPackService()

    if getattr(app.state, "durable_wizard_service", None) is None:
        wiz_engine = getattr(app.state, "db_engine", None)
        wiz_repo = SqlWizardSessionRepository(wiz_engine) if wiz_engine is not None else None
        app.state.durable_wizard_service = DurableOnboardingWizardService(repository=wiz_repo)

    if getattr(app.state, "audit_ledger_service", None) is None:
        from orcia_core.audit_finops import SqlAuditLedgerService

        db_engine = getattr(app.state, "db_engine", None)
        app.state.audit_ledger_service = SqlAuditLedgerService(engine=db_engine)

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

    active_db_engine = getattr(app.state, "db_engine", None)
    if active_db_engine is not None:
        if getattr(app.state, "gate_repository", None) is None:
            from orcia_core.gates import SqlGateEvaluationRepository

            gate_repo = SqlGateEvaluationRepository(active_db_engine)
            app.state.gate_repository = gate_repo
            if getattr(app.state, "bootstrap_service", None) is not None:
                app.state.bootstrap_service.gate_service.set_repository(gate_repo)
        wiz_svc = getattr(app.state, "durable_wizard_service", None)
        if wiz_svc is not None and getattr(wiz_svc, "_repository", None) is None:
            wiz_svc.set_repository(SqlWizardSessionRepository(active_db_engine))
        if getattr(app.state, "jira_staged_action_service", None) is None:
            from orcia_connectors._internal.sql_jira_staged_actions import (
                SqlJiraStagedActionsRepository,
            )
            from orcia_connectors.jira_actions import MultiProjectJiraStagedActionService

            app.state.jira_staged_action_service = MultiProjectJiraStagedActionService(
                repository=SqlJiraStagedActionsRepository(active_db_engine),
                strict_sql=True,
            )
        if getattr(app.state, "mcp_server_service", None) is None:
            from orcia_core.orchestration._internal.sql_mcp_proposals import (
                SqlMcpProposalsRepository,
            )
            from orcia_core.orchestration.mcp_server import GovernedMcpServerService

            app.state.mcp_server_service = GovernedMcpServerService(
                proposals_repository=SqlMcpProposalsRepository(
                    session_maker=getattr(app.state, "session_maker", None),
                    engine=active_db_engine,
                ),
                strict_sql=True,
            )
        for attr_name in (
            "audit_ledger_service",
            "connector_quota_guard_service",
            "finops_accounting_service",
            "cognitive_impact_service",
            "post_hoc_audit_service",
            "autonomous_supervision_service",
            "contextual_help_service",
            "notification_service",
            "resource_lease_service",
            "permission_broker_service",
            "assistant_folders_and_sharing_service",
        ):
            svc_inst = getattr(app.state, attr_name, None)
            if svc_inst is not None and getattr(svc_inst, "_engine", None) is None:
                if hasattr(svc_inst, "set_engine"):
                    svc_inst.set_engine(active_db_engine)
                else:
                    svc_inst._engine = active_db_engine


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager initializing Composition Root services (`AD-19`)."""
    from orcia_core.observability import configure_tracing, instrument_runtime, shutdown_tracing

    initialize_app_services(app)
    db_engine = getattr(app.state, "db_engine", None)
    if db_engine is not None:
        try:
            from orcia_core.packs.loader import DeclarativePackLoader, resolve_default_packs_root

            pack_bundles = DeclarativePackLoader(resolve_default_packs_root()).load_all_packs()
            app.state.declarative_pack_bundles = pack_bundles
            await upsert_declarative_pack_bundles_sql(db_engine, pack_bundles)
            await upsert_vsm_definitions_v2_sql(db_engine, pack_bundles)
            help_svc = getattr(app.state, "contextual_help_service", None)
            if help_svc is not None and hasattr(help_svc, "ensure_seeded_in_postgres18_async"):
                await help_svc.ensure_seeded_in_postgres18_async()
        except Exception as exc:
            from orcia_core.observability.logging import get_logger

            get_logger("orcia.api.lifespan").warning(
                "lifespan_declarative_packs_pg_sync_skipped",
                error_type=type(exc).__name__,
            )
    if db_engine is not None and getattr(app.state, "dbos_datasource", None) is None:
        try:
            from orcia_core.config import resolve_database_url
            from orcia_core.orchestration import DbosSqlAlchemyUnitOfWork

            uow = await DbosSqlAlchemyUnitOfWork.create(
                resolve_database_url(),
                engine=db_engine,
                schema="dbos",
                run_migrations=True,
            )
            app.state.dbos_datasource = uow.datasource
            app.state.dbos_uow = uow
        except Exception as exc:
            from orcia_core.observability.logging import get_logger

            get_logger("orcia.api.lifespan").warning(
                "lifespan_dbos_datasource_fallback_engine", error_type=type(exc).__name__
            )
    tracer_provider = configure_tracing(service_name="api")
    instrument_runtime(app=app, engine=getattr(app.state, "db_engine", None))
    sse_broker = getattr(app.state, "sse_broker", None)
    if sse_broker is not None and hasattr(sse_broker, "start_pubsub_listener"):
        await sse_broker.start_pubsub_listener()
    try:
        yield
    finally:
        if sse_broker is not None and hasattr(sse_broker, "stop_pubsub_listener"):
            with suppress(Exception):
                await sse_broker.stop_pubsub_listener()
        shutdown_tracing(tracer_provider)
        http_client = getattr(app.state, "http_client", None)
        if http_client is not None:
            with suppress(Exception):
                await http_client.aclose()
        redis_client = getattr(app.state, "redis_client", None)
        if redis_client is not None:
            with suppress(Exception):
                await redis_client.aclose()
        db_engine = getattr(app.state, "db_engine", None)
        if db_engine is not None:
            with suppress(Exception):
                await db_engine.dispose()
