"""FastAPI application factory for ORCIA (`apps/api`, `AD-19`)."""

from __future__ import annotations

from fastapi import FastAPI

from orcia_api.dependencies import app_lifespan, initialize_app_services
from orcia_api.middleware.trace_and_error import (
    TraceContextMiddleware,
    register_exception_handlers,
)
from orcia_api.routers.assistant import router as assistant_router
from orcia_api.routers.auth import router as auth_router
from orcia_api.routers.blackboard_and_engine import router as blackboard_and_engine_router
from orcia_api.routers.bootstrap import router as bootstrap_router
from orcia_api.routers.catalog import router as catalog_router
from orcia_api.routers.challenge_and_replay import router as challenge_and_replay_router
from orcia_api.routers.gates import router as gates_router
from orcia_api.routers.health import router as health_router
from orcia_api.routers.human_gates import router as human_gates_router
from orcia_api.routers.jira_and_mcp import router as jira_and_mcp_router
from orcia_api.routers.ontology_and_rag import router as ontology_and_rag_router
from orcia_api.routers.orchestration import router as orchestration_router
from orcia_api.routers.org_and_workspaces import router as org_and_workspaces_router
from orcia_api.routers.permission_broker import router as permission_broker_router
from orcia_api.routers.shell import router as shell_router
from orcia_core import __version__
from orcia_core.config import load_orcia_env
from orcia_core.observability.logging import configure_structlog


def create_app() -> FastAPI:
    """Create and configure the ORCIA FastAPI application (OpenAPI 3.1.0, Composition Root)."""
    load_orcia_env()
    configure_structlog()
    application = FastAPI(
        title="ORCIA Platform API",
        version=__version__,
        description=(
            "Orchestration of Processes, Context, and Intelligent Agents — "
            "Hexagonal Modular Monolith API with RFC 9457 Problem Details."
        ),
        lifespan=app_lifespan,
    )
    initialize_app_services(application)
    application.add_middleware(TraceContextMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(shell_router)
    application.include_router(auth_router)
    application.include_router(org_and_workspaces_router)
    application.include_router(catalog_router)
    application.include_router(permission_broker_router)
    application.include_router(gates_router)
    application.include_router(human_gates_router)
    application.include_router(jira_and_mcp_router)
    application.include_router(bootstrap_router)
    application.include_router(ontology_and_rag_router)
    application.include_router(orchestration_router)
    application.include_router(blackboard_and_engine_router)
    application.include_router(challenge_and_replay_router)
    application.include_router(assistant_router)
    return application


app = create_app()
