"""FastAPI application factory for ORCIA (`apps/api`)."""

from __future__ import annotations

from fastapi import FastAPI

from orcia_api.middleware.trace_and_error import (
    TraceContextMiddleware,
    register_exception_handlers,
)
from orcia_api.routers.auth import router as auth_router
from orcia_api.routers.blackboard_and_engine import router as blackboard_and_engine_router
from orcia_api.routers.bootstrap import router as bootstrap_router
from orcia_api.routers.catalog import router as catalog_router
from orcia_api.routers.health import router as health_router
from orcia_api.routers.ontology_and_rag import router as ontology_and_rag_router
from orcia_api.routers.orchestration import router as orchestration_router
from orcia_api.routers.org_and_workspaces import router as org_and_workspaces_router
from orcia_api.routers.permission_broker import router as permission_broker_router
from orcia_api.routers.shell import router as shell_router
from orcia_core import __version__
from orcia_core.bootstrap import build_default_system_bootstrap_service
from orcia_core.catalog import build_default_federated_catalog_service
from orcia_core.config import load_orcia_env
from orcia_core.observability.logging import configure_structlog
from orcia_core.orchestration import build_default_orchestration_setup_service
from orcia_core.permissions import (
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
)


def create_app() -> FastAPI:
    """Create and configure the ORCIA FastAPI application (OpenAPI 3.1.0)."""
    load_orcia_env()
    configure_structlog()
    application = FastAPI(
        title="ORCIA Platform API",
        version=__version__,
        description=(
            "Orchestration of Processes, Context, and Intelligent Agents — "
            "Hexagonal Modular Monolith API with RFC 9457 Problem Details."
        ),
    )
    auth_service = build_default_auth_and_org_service()
    catalog_service = build_default_federated_catalog_service(evaluator=auth_service.evaluator)
    permission_broker_service = build_default_permission_broker_service(
        evaluator=auth_service.evaluator, vault_cipher=auth_service.vault_cipher
    )
    application.state.auth_service = auth_service
    application.state.catalog_service = catalog_service
    application.state.permission_broker_service = permission_broker_service
    application.state.bootstrap_service = build_default_system_bootstrap_service(
        auth_service=auth_service,
        catalog_service=catalog_service,
        permission_broker_service=permission_broker_service,
    )
    application.state.orchestration_service = build_default_orchestration_setup_service(
        evaluator=auth_service.evaluator,
    )
    application.add_middleware(TraceContextMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(shell_router)
    application.include_router(auth_router)
    application.include_router(org_and_workspaces_router)
    application.include_router(catalog_router)
    application.include_router(permission_broker_router)
    application.include_router(bootstrap_router)
    application.include_router(ontology_and_rag_router)
    application.include_router(orchestration_router)
    application.include_router(blackboard_and_engine_router)
    return application


app = create_app()
