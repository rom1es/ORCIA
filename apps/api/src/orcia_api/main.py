"""FastAPI application factory for ORCIA (`apps/api`, `AD-19`)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    app: FastAPI

_LAZY_APP: FastAPI | None = None
rehydrate_bearer_subject_from_pg_if_missing: Callable[[Request], Awaitable[Any]] | None = None


def _resolve_rehydrate_bearer_fn() -> Callable[[Request], Awaitable[Any]]:
    if rehydrate_bearer_subject_from_pg_if_missing is not None:
        return rehydrate_bearer_subject_from_pg_if_missing
    from orcia_api.routers._auth_pg_helpers import (
        rehydrate_bearer_subject_from_pg_if_missing as _default_rehydrate,
    )

    return _default_rehydrate


def create_app() -> FastAPI:
    """Create and configure the ORCIA FastAPI application (OpenAPI 3.1.0, Composition Root)."""
    from orcia_api._router_registry import register_all_routers
    from orcia_api.dependencies.core_and_lifespan import app_lifespan, initialize_app_services
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
    from orcia_api.routers.auth import PROBLEM_RESPONSES
    from orcia_core import __version__
    from orcia_core.config import load_orcia_env
    from orcia_core.observability.logging import configure_logging
    from orcia_core.permissions.errors import ResourceNotFoundError

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
        # Readiness/liveness probes must stay dependency-free and sub-100ms.
        if request.url.path in ("/ready", "/api/v1/ready", "/api/v1/health"):
            return await call_next(request)
        hydrated_svc = await _resolve_rehydrate_bearer_fn()(request)
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
                            refreshed_svc = await _resolve_rehydrate_bearer_fn()(request)
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
    register_all_routers(application)
    install_openapi_bearer_security(application)
    # Pre-build ASGI middleware stack so the first /ready probe avoids cold stack assembly.
    application.middleware_stack = application.build_middleware_stack()
    return application


def __getattr__(name: str) -> Any:
    """Provide PEP 562 lazy `orcia_api.main.app` without paying `create_app()` on import."""
    global _LAZY_APP
    if name == "app":
        if _LAZY_APP is None:
            _LAZY_APP = create_app()
        globals()["app"] = _LAZY_APP
        return _LAZY_APP
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
