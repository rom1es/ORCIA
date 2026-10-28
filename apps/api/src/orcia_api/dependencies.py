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
    WorkflowOrchestrationSetupService,
    build_default_orchestration_setup_service,
)
from orcia_core.permissions import (
    AuthAndOrganizationService,
    PermissionBrokerService,
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
)
from orcia_core.rag import (
    HybridRagService,
    TripartiteGraphAndFreshnessService,
    build_empty_rag_service,
    build_seeded_rag_service,
)
from orcia_pack_sdlc import activate_sdlc_pack


def initialize_app_services(app: FastAPI) -> None:
    """Wire and attach all domain services to `app.state` (idempotent Composition Root)."""
    activate_sdlc_pack()
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
