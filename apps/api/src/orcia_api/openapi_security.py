"""OpenAPI 3.1 Bearer JWT security scheme and operation-level enforcement."""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

_HTTP_METHODS: frozenset[str] = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
)

_PUBLIC_EXACT_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/health"),
        ("GET", "/ready"),
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/ready"),
        ("GET", "/api/v1/auth/public-config"),
        ("GET", "/api/v1/auth/session"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/login/local"),
        ("POST", "/api/v1/auth/login/oidc"),
        ("POST", "/api/v1/auth/login/verify-2fa"),
        ("POST", "/api/v1/auth/login/resend-2fa"),
        ("GET", "/api/v1/auth/oidc/authorize"),
        ("POST", "/api/v1/auth/oidc/callback"),
        ("GET", "/api/v1/bootstrap/accostage-status"),
        ("GET", "/api/v1/bootstrap/platform-setup-state"),
        ("POST", "/api/v1/bootstrap/welcome-setup/first-admin"),
        ("POST", "/api/v1/triggers/alerts"),
        ("POST", "/api/v1/webhooks/jira/issue-updated"),
        ("POST", "/api/v1/_e2e/evict-memory-caches"),
        ("GET", "/showcase"),
    }
)

_PUBLIC_REGEX_OPERATIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("POST", re.compile(r"^/api/v1/webhooks/datasources/[^/]+$")),
    ("POST", re.compile(r"^/api/v1/webhooks/triggers/[^/]+$")),
    ("POST", re.compile(r"^/api/v1/workspaces/[^/]+/datasources/[^/]+/webhook$")),
)


def is_public_openapi_operation(path: str, method: str) -> bool:
    """Return True if `(method, path)` matches an explicit anonymous or HMAC POST route."""
    normalized_method = method.upper()
    if (normalized_method, path) in _PUBLIC_EXACT_OPERATIONS:
        return True
    return any(
        allowed_method == normalized_method and pattern.match(path) is not None
        for allowed_method, pattern in _PUBLIC_REGEX_OPERATIONS
    )


def install_openapi_bearer_security(application: FastAPI) -> None:
    """Register `BearerAuth` securityScheme and apply `security` to all protected routes."""

    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        for path, path_item in schema.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                    continue
                if is_public_openapi_operation(path, method):
                    operation.pop("security", None)
                else:
                    operation["security"] = [{"BearerAuth": []}]
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]
