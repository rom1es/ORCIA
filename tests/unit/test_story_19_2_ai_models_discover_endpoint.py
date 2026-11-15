"""Unit tests for AI Models Discovery endpoints (`Story 19.2`, `AD-24.2`)."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration import (
    AiModelsHubService,
)
from orcia_core.permissions import PassthroughVaultCipher


@pytest.fixture
def mock_provider_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "api.openai.com" in url_str and request.url.path == "/v1/models":
            if request.headers.get("Authorization") == "Bearer sk-invalid":
                return httpx.Response(401, json={"error": "Invalid token"})
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "gpt-4o", "owned_by": "system"},
                        {"id": "gpt-4o-mini", "owned_by": "system"},
                    ]
                },
            )
        if "api.anthropic.com" in url_str and request.url.path == "/v1/models":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "claude-3-5-sonnet-20241022", "display_name": "Claude 3.5 Sonnet"}
                    ]
                },
            )
        if "localhost:11434" in url_str:
            if request.url.path == "/v1/models":
                return httpx.Response(404, text="Not Found")
            if request.url.path == "/api/tags":
                return httpx.Response(
                    200,
                    json={
                        "models": [
                            {"name": "llama3.2:latest"},
                            {"name": "nomic-embed-text:latest"},
                        ]
                    },
                )
        if "nonexistent.example.org" in url_str:
            return httpx.Response(404, text="Not found")
        if "timeout.example.org" in url_str:
            raise httpx.ConnectTimeout("Network timed out")
        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


@pytest.fixture
def test_app(monkeypatch: pytest.MonkeyPatch, mock_provider_transport: httpx.MockTransport):
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    # Mock shared http_client
    app.state.http_client = httpx.AsyncClient(transport=mock_provider_transport)
    return app


def test_discover_models_post_success(test_app) -> None:
    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "https://api.openai.com/v1",
            "protocol_mode": "openai_compatible",
            "provider_slug": "openai",
            "api_key": "sk-valid-key",  # pragma: allowlist secret
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_count"] == 2
    assert [m["id"] for m in data["models"]] == ["gpt-4o", "gpt-4o-mini"]
    assert all(m["usage_hint"] == "unknown" for m in data["models"])


def test_discover_models_post_anthropic_success(test_app) -> None:
    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "https://api.anthropic.com/v1",
            "protocol_mode": "anthropic_messages",
            "provider_slug": "anthropic",
            "api_key": "sk-ant-valid",  # pragma: allowlist secret
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["models"][0]["id"] == "claude-3-5-sonnet-20241022"
    assert data["models"][0]["usage_hint"] == "chat"


def test_discover_models_get_success(test_app) -> None:
    client = TestClient(test_app)
    resp = client.get(
        "/api/v1/settings/ai-models/discover?base_url=http://localhost:11434&provider=ollama"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_count"] == 2
    assert [m["id"] for m in data["models"]] == ["llama3.2:latest", "nomic-embed-text:latest"]


def test_discover_models_with_existing_mapping_id(test_app) -> None:
    # Seed an existing mapping in hub_svc
    hub_svc: AiModelsHubService = getattr(test_app.state, "ai_models_hub_service", None)
    if hub_svc is None:
        cipher = PassthroughVaultCipher(master_key=b"0" * 32)
        hub_svc = AiModelsHubService(vault_cipher=cipher)
        test_app.state.ai_models_hub_service = hub_svc

    rec = hub_svc.create_mapping(
        scope_level="GLOBAL",
        scope_id="01932900-0001-7000-8000-000000000001",
        display_name="Stored OpenAI",
        inference_tier="medium",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="api_key",
        protocol_mode="openai_compatible",
        secret_input=None,
    )

    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "https://api.openai.com/v1",
            "protocol_mode": "openai_compatible",
            "mapping_id": rec.id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2


def test_discover_models_rejects_read_only_observer(test_app) -> None:
    client = TestClient(test_app)
    resp_post = client.post(
        "/api/v1/settings/ai-models/discover",
        headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"},
        json={
            "endpoint_uri": "https://api.openai.com/v1",
            "protocol_mode": "openai_compatible",
        },
    )
    assert resp_post.status_code == 403
    payload = resp_post.json()
    assert payload["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    resp_get = client.get(
        "/api/v1/settings/ai-models/discover?base_url=https://api.openai.com/v1",
        headers={"x-orcia-observer": "true"},
    )
    assert resp_get.status_code == 403
    assert resp_get.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"


def test_discover_models_rejects_ssrf_url(test_app) -> None:
    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "http://169.254.169.254/latest",
            "protocol_mode": "openai_compatible",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "ERR_UNSAFE_LLM_ENDPOINT_URL"


def test_discover_models_auth_failure_rfc9457(test_app) -> None:
    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "https://api.openai.com/v1",
            "protocol_mode": "openai_compatible",
            "api_key": "sk-invalid",  # pragma: allowlist secret
        },
    )
    assert resp.status_code == 401
    payload = resp.json()
    assert payload["error_code"] == "ERR_MODEL_DISCOVERY_AUTH_FAILED"
    assert "Authentification" in payload["title"] or "authentication" in payload["title"].lower()


def test_discover_models_404_not_supported_rfc9457(test_app) -> None:
    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "https://nonexistent.example.org/v1",
            "protocol_mode": "openai_compatible",
            "provider_slug": "custom",
        },
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["error_code"] == "ERR_MODEL_DISCOVERY_NOT_SUPPORTED"


def test_discover_models_network_timeout_rfc9457(test_app) -> None:
    client = TestClient(test_app)
    resp = client.post(
        "/api/v1/settings/ai-models/discover",
        json={
            "endpoint_uri": "https://timeout.example.org/v1",
            "protocol_mode": "openai_compatible",
        },
    )
    assert resp.status_code == 502
    payload = resp.json()
    assert payload["error_code"] == "ERR_MODEL_DISCOVERY_NETWORK_ERROR"
