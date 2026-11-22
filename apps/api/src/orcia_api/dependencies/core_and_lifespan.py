"""Core Composition Root lifespan & foundational service providers (`AD-19`)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
from orcia_api.dependencies._lifespan_infra import (
    attach_pg18_repositories,
    init_pg_engine_and_uow,
    shutdown_app_resources,
    startup_declarative_packs_and_dbos,
)
from orcia_api.dependencies._lifespan_services import init_runtime_secondary_services
from orcia_core.bootstrap import (
    LiteLLMAdapter,
    build_default_system_bootstrap_service,
    build_litellm_gateway_plugin,
)
from orcia_core.catalog import build_default_federated_catalog_service
from orcia_core.gates import SqlGateEvaluationRepository
from orcia_core.orchestration import (
    ConnectorInvoker,
    RedisSseBrokerAdapter,
    build_default_orchestration_setup_service,
    register_default_step_executors,
)
from orcia_core.permissions import (
    InMemoryPlatformAuthPolicyStore,
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
    persona_impersonation_allowed,
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
    return LiteLLMAdapter(fallback_cassette=DeterministicCassetteLLM())


def should_seed_test_personas_in_memory() -> bool:
    """Return `True` only inside automated unit tests or explicit persona-seed mode."""
    if os.environ.get("ORCIA_FORCE_REAL_RUNTIME", "").strip() == "1":
        return False
    if os.environ.get("ORCIA_ENV", "").strip().lower() == "e2e":
        return False
    if os.environ.get("ORCIA_SEED_TEST_PERSONAS", "").strip() == "1":
        return True
    return bool(
        os.environ.get("PYTEST_CURRENT_TEST", "").strip()
        or os.environ.get("PYTEST_VERSION", "").strip()
    )


def _init_redis_and_sse(app: FastAPI) -> None:
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


def initialize_app_services(app: FastAPI) -> None:
    """Wire and attach all domain services to `app.state` (idempotent Composition Root)."""
    activate_sdlc_pack()
    init_pg_engine_and_uow(app)

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

    catalog_service = getattr(app.state, "catalog_service", None)
    if catalog_service is None:
        catalog_service = build_default_federated_catalog_service(evaluator=auth_service.evaluator)
        app.state.catalog_service = catalog_service

    if getattr(app.state, "contextual_help_service", None) is None:
        from orcia_core.catalog.contextual_help import ContextualHelpResolutionService

        app.state.contextual_help_service = ContextualHelpResolutionService(
            redis_client=getattr(app.state, "redis_client", None),
            engine=getattr(app.state, "db_engine", None),
        )
    permission_broker_service = getattr(app.state, "permission_broker_service", None)
    if permission_broker_service is None:
        permission_broker_service = build_default_permission_broker_service(
            evaluator=auth_service.evaluator,
            vault_cipher=auth_service.vault_cipher,
            engine=getattr(app.state, "db_engine", None),
        )
        app.state.permission_broker_service = permission_broker_service

    if getattr(app.state, "bootstrap_service", None) is None:
        app.state.bootstrap_service = build_default_system_bootstrap_service(
            auth_service=auth_service,
            catalog_service=catalog_service,
            permission_broker_service=permission_broker_service,
        )
    app.state.bootstrap_service.gate_service.agentic_service.llm_port = app.state.llm_gateway
    if (
        getattr(app.state, "db_engine", None) is not None
        and getattr(app.state.bootstrap_service.gate_service, "_repository", None) is None
    ):
        gate_repo = getattr(app.state, "gate_repository", None) or SqlGateEvaluationRepository(
            app.state.db_engine
        )
        app.state.gate_repository = gate_repo
        app.state.bootstrap_service.gate_service.set_repository(gate_repo)

    if getattr(app.state, "orchestration_service", None) is None:
        app.state.orchestration_service = build_default_orchestration_setup_service(
            evaluator=auth_service.evaluator
        )
    if getattr(app.state, "secret_provider", None) is None:
        from orcia_core.permissions.secret_manager import EnvelopeVaultSecretProvider

        app.state.secret_provider = EnvelopeVaultSecretProvider()

    _init_redis_and_sse(app)
    for attr_name in ("contextual_help_service", "two_speed_search_service"):
        svc_r = getattr(app.state, attr_name, None)
        if (
            svc_r is not None
            and getattr(svc_r, "_redis_client", None) is None
            and getattr(app.state, "redis_client", None) is not None
        ):
            if hasattr(svc_r, "set_redis_client"):
                svc_r.set_redis_client(app.state.redis_client)
            else:
                svc_r._redis_client = app.state.redis_client
    if getattr(app.state, "two_speed_search_service", None) is None:
        from orcia_core.rag import TwoSpeedFederatedSearchService

        app.state.two_speed_search_service = TwoSpeedFederatedSearchService(
            redis_client=getattr(app.state, "redis_client", None)
        )
    init_runtime_secondary_services(
        app,
        auth_service=auth_service,
        catalog_service=catalog_service,
        permission_broker_service=permission_broker_service,
    )
    for attr_name in (
        "assistant_turn_registry",
        "assistant_rate_limiter",
        "assistant_folders_and_sharing_service",
    ):
        svc_r = getattr(app.state, attr_name, None)
        if svc_r is not None and getattr(app.state, "redis_client", None) is not None:
            svc_r.set_redis_client(app.state.redis_client)
    attach_pg18_repositories(app)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager initializing Composition Root services (`AD-19`)."""
    from orcia_core.observability import configure_tracing, instrument_runtime

    initialize_app_services(app)
    await startup_declarative_packs_and_dbos(app)
    tracer_provider = configure_tracing(service_name="api")
    instrument_runtime(app=app, engine=getattr(app.state, "db_engine", None))
    sse_broker = getattr(app.state, "sse_broker", None)
    if sse_broker is not None and hasattr(sse_broker, "start_pubsub_listener"):
        await sse_broker.start_pubsub_listener()
    try:
        yield
    finally:
        await shutdown_app_resources(app, tracer_provider)
