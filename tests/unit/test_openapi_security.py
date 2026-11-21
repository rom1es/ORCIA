"""Layer 1a unit tests for `orcia_api.openapi_security` (Story 23.6a)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_api.openapi_security import (
    install_openapi_bearer_security,
    is_public_openapi_operation,
)

EXPECTED_PUBLIC_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
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
        ("POST", "/api/v1/webhooks/datasources/{datasource_id}"),
        ("POST", "/api/v1/webhooks/jira/issue-updated"),
        ("POST", "/api/v1/webhooks/triggers/{trigger_id}"),
        ("POST", "/api/v1/_e2e/evict-memory-caches"),
    }
)

_HTTP_METHODS: frozenset[str] = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
)


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("get", "/health", True),
        ("GET", "/ready", True),
        ("get", "/api/v1/health", True),
        ("GET", "/api/v1/ready", True),
        ("post", "/api/v1/auth/login/local", True),
        ("POST", "/api/v1/auth/login/oidc", True),
        ("POST", "/api/v1/auth/login/verify-2fa", True),
        ("POST", "/api/v1/auth/login/resend-2fa", True),
        ("POST", "/api/v1/auth/refresh", True),
        ("GET", "/api/v1/auth/session", True),
        ("POST", "/api/v1/auth/logout", True),
        ("GET", "/api/v1/bootstrap/accostage-status", True),
        ("POST", "/api/v1/bootstrap/welcome-setup/first-admin", True),
        ("POST", "/api/v1/webhooks/triggers/trg-1", True),
        ("POST", "/api/v1/workspaces/ws-1/datasources/ds-1/webhook", True),
        ("POST", "/api/v1/_e2e/evict-memory-caches", True),
        ("GET", "/showcase", True),
        ("GET", "/api/v1/workspaces", False),
        ("POST", "/api/v1/workspaces", False),
        ("GET", "/api/v1/settings/authentication", False),
        ("PUT", "/api/v1/settings/authentication", False),
        ("POST", "/api/v1/bootstrap/accostage-status", False),
        ("DELETE", "/api/v1/auth/session", False),
        ("GET", "/api/v1/finops/budgets", False),
        ("GET", "/api/v1/auth/policy", False),
        ("POST", "/api/v1/auth/policy/default", False),
        ("GET", "/api/v1/workspaces/ws-1/datasources/ds-1/webhook", False),
        ("PUT", "/api/v1/workspaces/ws-1/datasources/ds-1/webhook", False),
        ("DELETE", "/api/v1/workspaces/ws-1/datasources/ds-1/webhook", False),
        ("GET", "/api/v1/webhooks/datasources/ds-1", False),
        ("DELETE", "/api/v1/webhooks/triggers/trg-1", False),
        ("POST", "/api/v1/showcase", False),
        ("GET", "/api/v1/_e2e/evict-memory-caches", False),
    ],
)
def test_is_public_openapi_operation_classification(
    method: str,
    path: str,
    expected: bool,
) -> None:
    assert is_public_openapi_operation(path, method) is expected


def test_install_openapi_bearer_security_on_synthetic_app_and_cache_reuse() -> None:
    mini_app = FastAPI(title="Mini", version="0.1.0")

    @mini_app.get("/health")
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    @mini_app.get("/api/v1/protected-items")
    def _protected() -> list[str]:
        return []

    install_openapi_bearer_security(mini_app)
    first_schema = mini_app.openapi()
    assert first_schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert "security" not in first_schema["paths"]["/health"]["get"]
    assert first_schema["paths"]["/api/v1/protected-items"]["get"]["security"] == [
        {"BearerAuth": []}
    ]

    # Calling .openapi() again must return the cached schema object directly.
    second_schema = mini_app.openapi()
    assert second_schema is first_schema


def test_install_openapi_bearer_security_skips_non_dict_path_items_and_non_http_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mini_app = FastAPI(title="Edge", version="0.1.0")

    def _fake_get_openapi(**_kwargs: object) -> dict[str, object]:
        return {
            "paths": {
                "/broken": "not-a-dict",
                "/api/v1/health": {
                    "parameters": [{"name": "x-trace", "in": "header"}],
                    "get": {"security": [{"LegacyAuth": []}]},
                },
                "/api/v1/workspaces": {
                    "parameters": [],
                    "get": {},
                },
            }
        }

    monkeypatch.setattr("orcia_api.openapi_security.get_openapi", _fake_get_openapi)
    install_openapi_bearer_security(mini_app)
    schema = mini_app.openapi()

    assert "security" not in schema["paths"]["/api/v1/health"]["get"]
    assert schema["paths"]["/api/v1/workspaces"]["get"]["security"] == [{"BearerAuth": []}]


def test_real_create_app_openapi_enforces_bearer_auth_on_all_protected_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)

    app = create_app()
    spec = app.openapi()

    assert spec["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    observed_public: set[tuple[str, str]] = set()
    protected_count = 0

    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            op_key = (method.upper(), path)
            if op_key in EXPECTED_PUBLIC_OPERATIONS:
                assert "security" not in operation, f"Public route {op_key} must not require Bearer"
                observed_public.add(op_key)
            else:
                assert operation.get("security") == [{"BearerAuth": []}], (
                    f"Protected route {op_key} missing BearerAuth security requirement"
                )
                protected_count += 1

    assert observed_public == EXPECTED_PUBLIC_OPERATIONS
    assert protected_count >= 250


def test_runtime_middleware_rejects_invalid_and_missing_bearer_on_protected_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")

    app = create_app()
    client = TestClient(app)

    for protected_path in (
        "/api/v1/settings/connectors",
        "/api/v1/settings/iam/role-matrix",
        "/api/v1/packs",
    ):
        missing_resp = client.get(protected_path)
        assert missing_resp.status_code == 401
        assert missing_resp.headers["content-type"].startswith("application/problem+json")
        assert missing_resp.json()["error_code"] == "ERR_AUTH_REQUIRED"

        bad_resp = client.get(
            protected_path,
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert bad_resp.status_code == 401
        assert bad_resp.headers["content-type"].startswith("application/problem+json")
        assert bad_resp.json()["error_code"] == "ERR_AUTH_INVALID_CREDENTIALS"

    # Public routes remain accessible without Bearer even when ORCIA_ENV=e2e
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/auth/public-config").status_code == 200
