"""Core FastAPI `Depends` providers extracted from `core_and_lifespan.py` (`MINOR-01`)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from fastapi import Request

from orcia_core.bootstrap import SystemBootstrapWorkflowService
from orcia_core.catalog import FederatedCatalogService
from orcia_core.ontology import (
    OntologyGovernanceService,
    build_empty_ontology_service,
    build_seeded_ontology_service,
)
from orcia_core.permissions import (
    AuthAndOrganizationService,
    PermissionBrokerService,
)
from orcia_core.rag import (
    HybridRagService,
    TripartiteGraphAndFreshnessService,
    build_empty_rag_service,
    build_seeded_rag_service,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def should_auto_init_infra(env_var: str) -> bool:
    """Return True when PG18 or Redis should auto-initialize in Composition Root."""
    if os.environ.get("ORCIA_ENABLE_PG_SESSION_MAKER") == "1":
        return True
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION"):
        return bool(os.environ.get(env_var, "").strip())
    return True


def is_pg_runtime_active(request: Request | None = None) -> bool:
    """Return True when PostgreSQL 18 is active (always True outside unit tests without DB)."""
    if request is not None and getattr(request.app.state, "db_engine", None) is not None:
        return True
    return should_auto_init_infra("DATABASE_URL")


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


def get_configured_db_engine(request: Request) -> AsyncEngine | None:
    """Return `db_engine` when auto-init is enabled, creating it lazily if missing."""
    engine: AsyncEngine | None = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        return engine
    if should_auto_init_infra("DATABASE_URL"):
        return get_or_create_shared_db_engine(request)
    return None


def get_auth_service(request: Request) -> AuthAndOrganizationService:
    """FastAPI `Depends` provider returning `AuthAndOrganizationService` from `app.state`."""
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services

    svc: AuthAndOrganizationService | None = getattr(request.app.state, "auth_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.auth_service
    assert svc is not None
    return svc


def get_catalog_service(request: Request) -> FederatedCatalogService:
    """FastAPI `Depends` provider returning `FederatedCatalogService` from `app.state`."""
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services

    svc: FederatedCatalogService | None = getattr(request.app.state, "catalog_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.catalog_service
    assert svc is not None
    return svc


def get_permission_broker_service(request: Request) -> PermissionBrokerService:
    """FastAPI `Depends` provider returning `PermissionBrokerService` from `app.state`."""
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services

    engine = get_configured_db_engine(request)
    svc: PermissionBrokerService | None = getattr(
        request.app.state, "permission_broker_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.permission_broker_service
    assert svc is not None
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc.set_engine(engine)
    return svc


def get_bootstrap_service(request: Request) -> SystemBootstrapWorkflowService:
    """FastAPI `Depends` provider returning `SystemBootstrapWorkflowService` from `app.state`."""
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_core.gates import SqlGateEvaluationRepository

    svc: SystemBootstrapWorkflowService | None = getattr(
        request.app.state, "bootstrap_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.bootstrap_service
    assert svc is not None
    engine = get_configured_db_engine(request)
    if engine is not None and getattr(svc.gate_service, "_repository", None) is None:
        repo = getattr(request.app.state, "gate_repository", None)
        if repo is None:
            repo = SqlGateEvaluationRepository(engine)
            request.app.state.gate_repository = repo
        svc.gate_service.set_repository(repo)
    return svc


_OntologyRagBundle = tuple[
    OntologyGovernanceService, HybridRagService, TripartiteGraphAndFreshnessService
]


def get_ontology_and_rag_services(
    request: Request, *, fixture: bool = False, embedding_port: Any = None
) -> _OntologyRagBundle:
    """Return either the empty runtime Ontology/RAG bundle or the deterministic test fixture."""
    if fixture:
        seeded: _OntologyRagBundle | None = getattr(
            request.app.state, "ontology_rag_seeded_bundle", None
        )
        if seeded is None:
            gov = build_seeded_ontology_service()
            emb_port = embedding_port
            if emb_port is None:
                from orcia_api.dependencies.portal_and_assistant import get_embedding_port

                override = request.app.dependency_overrides.get(get_embedding_port)
                if override is not None:
                    emb_port = override()
            rag, trip = build_seeded_rag_service(embedding_port=emb_port)
            seeded = (gov, rag, trip)
            request.app.state.ontology_rag_seeded_bundle = seeded
        return seeded

    runtime: _OntologyRagBundle | None = getattr(
        request.app.state, "ontology_rag_runtime_bundle", None
    )
    if runtime is None:
        gov = build_empty_ontology_service()
        emb_port = embedding_port
        if emb_port is None:
            from orcia_api.dependencies.portal_and_assistant import get_embedding_port

            override = request.app.dependency_overrides.get(get_embedding_port)
            if override is not None:
                emb_port = override()
        rag, trip = build_empty_rag_service(embedding_port=emb_port)
        runtime = (gov, rag, trip)
        request.app.state.ontology_rag_runtime_bundle = runtime
    return runtime
