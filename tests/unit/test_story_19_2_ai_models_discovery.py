"""Unit tests for AI Models Discovery client (`Story 19.2`, `AD-24.2`)."""

from __future__ import annotations

import httpx
import pytest

from orcia_core.orchestration.ai_models_discovery import (
    discover_models_from_provider,
)
from orcia_core.orchestration.ai_models_errors import (
    ModelDiscoveryAuthFailedError,
    ModelDiscoveryEndpointNotFoundError,
    ModelDiscoveryNetworkError,
    UnsafeLlmEndpointUrlError,
)


@pytest.mark.asyncio
async def test_discover_openai_compatible_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers.get("Authorization") == "Bearer sk-test-openai"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
                    {"id": "text-embedding-3-small", "object": "model", "owned_by": "openai"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1",
            protocol_mode="openai_compatible",
            provider_slug="openai",
            api_key="sk-test-openai",  # pragma: allowlist secret
        )

    assert len(models) == 2
    assert models[0].id == "gpt-4o"
    assert models[0].usage_hint == "unknown"
    assert models[0].owned_by == "openai"
    assert models[1].id == "text-embedding-3-small"
    assert models[1].usage_hint == "unknown"


@pytest.mark.asyncio
async def test_discover_ollama_v1_models_format() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "llama3.2:latest"},
                    {"name": "nomic-embed-text:latest"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="http://localhost:11434/v1",
            protocol_mode="openai_compatible",
            provider_slug="ollama",
        )

    assert len(models) == 2
    assert [m.id for m in models] == ["llama3.2:latest", "nomic-embed-text:latest"]
    assert all(m.usage_hint == "unknown" for m in models)


@pytest.mark.asyncio
async def test_discover_ollama_fallback_to_api_tags() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(404, text="Not Found")
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "qwen2.5-coder:7b"},
                        {"name": "bge-m3:latest"},
                    ]
                },
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="http://localhost:11434",
            protocol_mode="openai_compatible",
            provider_slug="ollama",
        )

    assert len(models) == 2
    assert [m.id for m in models] == ["bge-m3:latest", "qwen2.5-coder:7b"]


@pytest.mark.asyncio
async def test_discover_openai_compatible_404_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ModelDiscoveryEndpointNotFoundError) as exc_info:
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://custom-proxy.internal/v1",
                protocol_mode="openai_compatible",
                provider_slug="custom",
            )
        assert exc_info.value.http_status == 404
        assert exc_info.value.error_code == "ERR_MODEL_DISCOVERY_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_discover_anthropic_messages_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers.get("x-api-key") == "sk-ant-test"
        assert request.headers.get("anthropic-version") == "2023-06-01"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "claude-3-5-sonnet-20241022",
                        "display_name": "Claude 3.5 Sonnet",
                        "type": "model",
                    },
                    {
                        "id": "claude-3-5-haiku-20241022",
                        "display_name": "Claude 3.5 Haiku",
                        "type": "model",
                    },
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="https://api.anthropic.com/v1",
            protocol_mode="anthropic_messages",
            provider_slug="anthropic",
            api_key="sk-ant-test",  # pragma: allowlist secret
        )

    assert len(models) == 2
    assert models[0].id == "claude-3-5-haiku-20241022"
    assert models[0].usage_hint == "chat"
    assert models[1].id == "claude-3-5-sonnet-20241022"
    assert models[1].usage_hint == "chat"


@pytest.mark.asyncio
async def test_discover_gemini_native_success_with_pagination_and_usage_hints() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/models"
        assert request.headers.get("x-goog-api-key") == "gemini-api-key-test"
        page_token = request.url.params.get("pageToken")
        if not page_token:
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "displayName": "Gemini 1.5 Pro",
                            "description": "Mid-size multimodal model",
                            "supportedGenerationMethods": ["generateContent", "countTokens"],
                        },
                        {
                            "name": "models/text-embedding-004",
                            "displayName": "Text Embedding 004",
                            "description": "Embedding model",
                            "supportedGenerationMethods": ["embedContent", "batchEmbedContents"],
                        },
                    ],
                    "nextPageToken": "token-page-2",
                },
            )
        elif page_token == "token-page-2":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-1.5-flash",
                            "displayName": "Gemini 1.5 Flash",
                            "supportedGenerationMethods": ["generateContent"],
                        },
                        {
                            "name": "models/custom-hybrid",
                            "displayName": "Custom Hybrid",
                            "supportedGenerationMethods": ["generateContent", "embedContent"],
                        },
                    ]
                },
            )
        return httpx.Response(400)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com",
            protocol_mode="gemini_native",
            provider_slug="google",
            api_key="gemini-api-key-test",  # pragma: allowlist secret
        )

    assert len(models) == 4
    by_id = {m.id: m for m in models}
    assert by_id["gemini-1.5-pro"].usage_hint == "chat"
    assert by_id["gemini-1.5-flash"].usage_hint == "chat"
    assert by_id["text-embedding-004"].usage_hint == "embedding"
    assert by_id["custom-hybrid"].usage_hint == "unknown"


@pytest.mark.asyncio
async def test_discover_auth_failures_401_and_403() -> None:
    def handler_401(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid API key"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_401)) as client:
        with pytest.raises(ModelDiscoveryAuthFailedError) as exc_info:
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                api_key="bad-key",  # pragma: allowlist secret
            )
        assert exc_info.value.http_status == 401
        assert exc_info.value.error_code == "ERR_MODEL_DISCOVERY_AUTH_FAILED"

    def handler_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "Forbidden"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_403)) as client:
        with pytest.raises(ModelDiscoveryAuthFailedError) as exc_info:
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.anthropic.com/v1",
                protocol_mode="anthropic_messages",
                api_key="restricted-key",  # pragma: allowlist secret
            )
        assert exc_info.value.http_status == 401


@pytest.mark.asyncio
async def test_discover_network_timeout_and_error() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as client:
        with pytest.raises(ModelDiscoveryNetworkError) as exc_info:
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.mistral.ai/v1",
                protocol_mode="openai_compatible",
                api_key="key",  # pragma: allowlist secret
            )
        assert exc_info.value.http_status == 502
        assert exc_info.value.error_code == "ERR_MODEL_DISCOVERY_NETWORK_ERROR"


@pytest.mark.asyncio
async def test_discover_ssrf_guard_blocks_cloud_metadata() -> None:
    async with httpx.AsyncClient() as client:
        with pytest.raises(UnsafeLlmEndpointUrlError) as exc_info:
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="http://169.254.169.254/latest/meta-data",
                protocol_mode="openai_compatible",
            )
        assert exc_info.value.http_status == 422
        assert exc_info.value.error_code == "ERR_UNSAFE_LLM_ENDPOINT_URL"


@pytest.mark.asyncio
async def test_discover_gemini_errors_and_timeouts() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Gemini timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://generativelanguage.googleapis.com",
                protocol_mode="gemini_native",
            )

    def net_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Gemini connect failed")

    async with httpx.AsyncClient(transport=httpx.MockTransport(net_error_handler)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://generativelanguage.googleapis.com",
                protocol_mode="gemini_native",
            )

    def h404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(h404)) as client:
        with pytest.raises(ModelDiscoveryEndpointNotFoundError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://generativelanguage.googleapis.com",
                protocol_mode="gemini_native",
            )

    def h500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Server error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(h500)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://generativelanguage.googleapis.com",
                protocol_mode="gemini_native",
            )


@pytest.mark.asyncio
async def test_discover_anthropic_errors_and_timeouts() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Anthropic timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.anthropic.com",
                protocol_mode="anthropic_messages",
            )

    def net_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Anthropic connect failed")

    async with httpx.AsyncClient(transport=httpx.MockTransport(net_error_handler)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.anthropic.com",
                protocol_mode="anthropic_messages",
            )

    def h404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(h404)) as client:
        with pytest.raises(ModelDiscoveryEndpointNotFoundError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.anthropic.com",
                protocol_mode="anthropic_messages",
            )

    def h500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Internal error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(h500)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.anthropic.com",
                protocol_mode="anthropic_messages",
            )


@pytest.mark.asyncio
async def test_discover_openai_errors_and_ollama_fallback_failure() -> None:
    def net_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connect error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(net_error_handler)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.mistral.ai",
                protocol_mode="openai_compatible",
            )

    def h500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Server error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(h500)) as client:
        with pytest.raises(ModelDiscoveryNetworkError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="https://api.mistral.ai",
                protocol_mode="openai_compatible",
            )

    # 404 on /v1/models with ollama provider slug, and /api/tags also fails
    def ollama_fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(ollama_fail_handler)) as client:
        with pytest.raises(ModelDiscoveryEndpointNotFoundError):
            await discover_models_from_provider(
                http_client=client,
                endpoint_uri="http://localhost:11434/v1",
                protocol_mode="openai_compatible",
                provider_slug="local-ollama",
            )
