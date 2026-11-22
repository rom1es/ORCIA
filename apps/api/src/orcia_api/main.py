"""FastAPI application factory for ORCIA (`apps/api`, `AD-19`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from orcia_api.dependencies import app_lifespan, initialize_app_services
from orcia_api.errors.registry import OrciaDomainError, resolve_domain_error_mapping
from orcia_api.middleware.trace_and_error import (
    TraceContextMiddleware,
    build_problem_response,
    register_exception_handlers,
)
from orcia_api.openapi_security import (
    install_openapi_bearer_security,
    is_public_openapi_operation,
)
from orcia_api.routers._auth_pg_helpers import (
    rehydrate_bearer_subject_from_pg_if_missing,
)
from orcia_api.routers.agents_and_skills import router as agents_and_skills_router
from orcia_api.routers.ai_models_hub import router as ai_models_hub_router
from orcia_api.routers.assistant import router as assistant_router
from orcia_api.routers.assistant_turns import router as assistant_turns_router
from orcia_api.routers.audit_ledger import router as audit_ledger_router
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.routers.auth import router as auth_router
from orcia_api.routers.auth_settings import router as auth_settings_router
from orcia_api.routers.autonomous_supervision import router as autonomous_supervision_router
from orcia_api.routers.autonomy_contracts import router as autonomy_contracts_router
from orcia_api.routers.blackboard_and_engine import router as blackboard_and_engine_router
from orcia_api.routers.bootstrap import router as bootstrap_router
from orcia_api.routers.catalog import router as catalog_router
from orcia_api.routers.challenge_and_replay import router as challenge_and_replay_router
from orcia_api.routers.codegraph_mcp import router as codegraph_mcp_router
from orcia_api.routers.control_center import router as control_center_router
from orcia_api.routers.datasource_webhooks import (
    router as datasource_webhooks_router,
)
from orcia_api.routers.dna_and_glossary import (
    router as dna_and_glossary_router,
)
from orcia_api.routers.e2e_test_hooks import router as e2e_test_hooks_router
from orcia_api.routers.enterprise_connectors import (
    router as enterprise_connectors_router,
)
from orcia_api.routers.executions_trace import router as executions_trace_router
from orcia_api.routers.finops import router as finops_router
from orcia_api.routers.gates import router as gates_router
from orcia_api.routers.health import probe_router as health_probe_router
from orcia_api.routers.health import router as health_router
from orcia_api.routers.human_gates import router as human_gates_router
from orcia_api.routers.iam_accounts import router as iam_accounts_router
from orcia_api.routers.inbox_and_leases import router as inbox_and_leases_router
from orcia_api.routers.jira_and_mcp import router as jira_and_mcp_router
from orcia_api.routers.mcp_and_test_bench import (
    router as mcp_and_test_bench_router,
)
from orcia_api.routers.ontology_and_rag import router as ontology_and_rag_router
from orcia_api.routers.ontology_promotions import router as ontology_promotions_router
from orcia_api.routers.orchestration import router as orchestration_router
from orcia_api.routers.org_and_workspaces import router as org_and_workspaces_router
from orcia_api.routers.pack_builder import (
    router as pack_builder_router,
)
from orcia_api.routers.packs import router as packs_router
from orcia_api.routers.permission_broker import router as permission_broker_router
from orcia_api.routers.portal_and_help import router as portal_and_help_router
from orcia_api.routers.settings_and_studio import router as settings_and_studio_router
from orcia_api.routers.shell import router as shell_router
from orcia_api.routers.sources_surgical import router as sources_surgical_router
from orcia_api.routers.studio_and_wizards import router as studio_and_wizards_router
from orcia_api.routers.user_account_settings import router as user_account_settings_router
from orcia_api.routers.user_profile import router as user_profile_router
from orcia_api.routers.workflow_triggers import router as workflow_triggers_router
from orcia_api.routers.workflows import router as workflows_v2_router
from orcia_api.routers.workspace_datasources import (
    router as workspace_datasources_router,
)
from orcia_api.routers.workspace_governance import (
    router as workspace_governance_router,
)
from orcia_core import __version__
from orcia_core.config import load_orcia_env
from orcia_core.observability.logging import configure_logging
from orcia_core.permissions.errors import ResourceNotFoundError


def create_app() -> FastAPI:
    """Create and configure the ORCIA FastAPI application (OpenAPI 3.1.0, Composition Root)."""
    load_orcia_env()
    configure_logging(service="api")
    application = FastAPI(
        title="ORCIA Platform API",
        version=__version__,
        description=(
            "Orchestration of Processes, Context, and Intelligent Agents — "
            "Hexagonal Modular Monolith API with RFC 9457 Problem Details."
        ),
        lifespan=app_lifespan,
        responses={
            **PROBLEM_RESPONSES,
            409: PROBLEM_RESPONSES[422],
            412: PROBLEM_RESPONSES[422],
            428: PROBLEM_RESPONSES[422],
        },
    )
    initialize_app_services(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3100",
            "http://127.0.0.1:3100",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def bearer_auth_rehydration_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        hydrated_svc = await rehydrate_bearer_subject_from_pg_if_missing(request)
        if (
            request.method.upper() != "OPTIONS"
            and request.url.path.startswith("/api/")
            and not is_public_openapi_operation(request.url.path, request.method)
        ):
            auth_svc = getattr(request.app.state, "auth_service", None) or hydrated_svc
            auth_hdr = request.headers.get("Authorization")
            if auth_svc is not None and (
                auth_hdr is not None or not auth_svc.allow_persona_impersonation
            ):
                try:
                    if auth_hdr is not None:
                        raw_token = auth_hdr.strip()
                        if raw_token.lower().startswith("bearer "):
                            raw_token = raw_token[7:].strip()
                        else:
                            raw_token = ""
                        try:
                            resolved_user = auth_svc.authenticate_access_token(raw_token)
                        except ResourceNotFoundError:
                            # Concurrent cache eviction may swap `app.state.auth_service`
                            # between initial rehydration and bearer verification.
                            refreshed_svc = await rehydrate_bearer_subject_from_pg_if_missing(
                                request
                            )
                            active_svc = (
                                getattr(request.app.state, "auth_service", None)
                                or refreshed_svc
                                or auth_svc
                            )
                            resolved_user = active_svc.authenticate_access_token(raw_token)
                        request.state.resolved_bearer_user = resolved_user
                    else:
                        auth_svc.resolve_user(bearer_token=None)
                except OrciaDomainError as exc:
                    mapping = resolve_domain_error_mapping(exc)
                    return build_problem_response(
                        request,
                        status_code=mapping.http_status,
                        error_code=mapping.error_code,
                        type_uri=mapping.type_uri,
                        detail_override=exc.detail_override,
                        instance_override=exc.instance or str(request.url.path),
                    )
        return await call_next(request)

    application.add_middleware(TraceContextMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(health_probe_router)
    application.include_router(shell_router)
    application.include_router(auth_router)
    application.include_router(org_and_workspaces_router)
    application.include_router(catalog_router)
    application.include_router(permission_broker_router)
    application.include_router(gates_router)
    application.include_router(human_gates_router)
    application.include_router(inbox_and_leases_router)
    application.include_router(control_center_router)
    application.include_router(iam_accounts_router)
    application.include_router(auth_settings_router)
    application.include_router(enterprise_connectors_router)
    application.include_router(ai_models_hub_router)
    application.include_router(settings_and_studio_router)
    application.include_router(studio_and_wizards_router)
    application.include_router(jira_and_mcp_router)
    application.include_router(bootstrap_router)
    application.include_router(ontology_and_rag_router)
    application.include_router(ontology_promotions_router)
    application.include_router(orchestration_router)
    application.include_router(blackboard_and_engine_router)
    application.include_router(challenge_and_replay_router)
    application.include_router(assistant_router)
    application.include_router(portal_and_help_router)
    application.include_router(user_account_settings_router)
    application.include_router(user_profile_router)
    application.include_router(assistant_turns_router)
    application.include_router(workspace_governance_router)
    application.include_router(workspace_datasources_router)
    application.include_router(codegraph_mcp_router)
    application.include_router(datasource_webhooks_router)
    application.include_router(dna_and_glossary_router)
    application.include_router(mcp_and_test_bench_router)
    application.include_router(pack_builder_router)
    application.include_router(agents_and_skills_router)
    application.include_router(packs_router)
    application.include_router(workflows_v2_router)
    application.include_router(audit_ledger_router)
    application.include_router(finops_router)
    application.include_router(autonomy_contracts_router)
    application.include_router(autonomous_supervision_router)
    application.include_router(workflow_triggers_router)
    application.include_router(sources_surgical_router)
    application.include_router(executions_trace_router)
    application.include_router(e2e_test_hooks_router)
    install_openapi_bearer_security(application)
    return application


app = create_app()
