"""W3C OpenTelemetry `trace_id` middleware and localized RFC 9457 exception handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from orcia_core.domain.exceptions import (
    OrciaDomainError,
    get_localized_error_text,
    resolve_locale,
)
from orcia_core.observability.logging import (
    bind_trace_context,
    clear_trace_context,
    get_logger,
    resolve_or_create_trace_id,
)
from orcia_core.schemas.problem_details import ProblemDetails

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"
logger = get_logger("orcia.api")


def _extract_request_trace_id(request: Request) -> str:
    state_trace: str | None = getattr(request.state, "trace_id", None)
    if state_trace:
        return state_trace
    traceparent = request.headers.get("traceparent")
    x_trace_id = request.headers.get("x-trace-id")
    resolved = resolve_or_create_trace_id(traceparent=traceparent, x_trace_id=x_trace_id)
    request.state.trace_id = resolved
    return resolved


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Propagate W3C `traceparent` / `X-Trace-Id` into `request.state`, `structlog`, and headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = _extract_request_trace_id(request)
        workspace_id = request.headers.get("x-workspace-id")
        bind_trace_context(trace_id, workspace_id=workspace_id)
        try:
            response = await call_next(request)
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            clear_trace_context()


def build_problem_response(
    request: Request,
    *,
    status_code: int,
    error_code: str,
    type_uri: str,
    detail_override: str | None = None,
    instance_override: str | None = None,
    permission_broker_hint: str | None = None,
) -> JSONResponse:
    """Construct a localized RFC 9457 `application/problem+json` response."""
    trace_id = _extract_request_trace_id(request)
    locale = resolve_locale(request.headers.get("accept-language"))
    copy = get_localized_error_text(error_code, locale=locale, detail_override=detail_override)
    problem = ProblemDetails(
        type=type_uri,
        title=copy.title,
        status=status_code,
        detail=copy.detail,
        instance=instance_override or str(request.url.path),
        error_code=error_code,
        trace_id=trace_id,
        permission_broker_hint=permission_broker_hint,
    )
    logger.warning(
        "api.problem_details",
        error_code=error_code,
        status=status_code,
        path=str(request.url.path),
        locale=locale,
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
        headers={
            "X-Trace-Id": trace_id,
            "Content-Language": locale,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global RFC 9457 Problem Details exception handlers to `app`."""

    @app.exception_handler(OrciaDomainError)
    async def handle_domain_error(request: Request, exc: OrciaDomainError) -> JSONResponse:
        return build_problem_response(
            request,
            status_code=exc.http_status,
            error_code=exc.error_code,
            type_uri=exc.type_uri,
            detail_override=exc.detail_override,
            instance_override=exc.instance,
            permission_broker_hint=exc.permission_broker_hint,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail_override: str | None = None
        if exc.status_code == 404:
            error_code = "ERR_RESOURCE_NOT_FOUND"
            type_uri = "https://orcia.io/problems/resource-not-found"
        elif exc.status_code == 403:
            error_code = "ERR_OBSERVER_MODE_READ_ONLY"
            type_uri = "https://orcia.io/problems/observer-mode-read-only"
        elif exc.status_code < 500:
            error_code = "ERR_VALIDATION_FAILED"
            type_uri = "https://orcia.io/problems/validation-failed"
            if isinstance(exc.detail, str) and exc.detail.strip():
                detail_override = exc.detail
        else:
            error_code = "ERR_INTERNAL_SERVER_ERROR"
            type_uri = "https://orcia.io/problems/http-error"
        return build_problem_response(
            request,
            status_code=exc.status_code,
            error_code=error_code,
            type_uri=type_uri,
            detail_override=detail_override,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return build_problem_response(
            request,
            status_code=422,
            error_code="ERR_VALIDATION_FAILED",
            type_uri="https://orcia.io/problems/validation-failed",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        trace_id = _extract_request_trace_id(request)
        bind_trace_context(trace_id)
        logger.error(
            "api.unhandled_exception",
            exc_type=type(_exc).__name__,
            detail=str(_exc),
            trace_id=trace_id,
        )
        return build_problem_response(
            request,
            status_code=500,
            error_code="ERR_INTERNAL_SERVER_ERROR",
            type_uri="https://orcia.io/problems/internal-server-error",
        )
