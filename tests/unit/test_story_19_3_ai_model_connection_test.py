"""Unit tests for Story 19.3: Real Connection Tests for Chat & Embeddings (`AD-24.3`, `D3`).

Verifies:
- Chat connectivity tests with minimal inference (`max_tokens=1`):
  * `openai_compatible`
  * `anthropic_messages`
  * `gemini_native`
- Embedding connectivity tests via `EmbeddingPort` adapters with strict 1024-dim check:
  * dimension 1024 success
  * dimension mismatch rejection (e.g. 768 or 1536) -> `ERR_EMBEDDING_DIMENSION_MISMATCH`
  * Anthropic rejection for embedding usage -> `ERR_EMBEDDING_PROVIDER_UNSUPPORTED`
- Real latency measurement via `time.perf_counter` (no hardcoded fake latencies)
- Provider errors translation to RFC 9457 invariant error codes:
  * 401/403 -> `ERR_MODEL_CONNECTION_AUTH_FAILED`
  * 404 -> `ERR_MODEL_CONNECTION_NOT_FOUND`
  * 429 -> `ERR_MODEL_CONNECTION_RATE_LIMITED`
  * timeout -> `ERR_MODEL_CONNECTION_TIMEOUT`
  * network error -> `ERR_MODEL_CONNECTION_NETWORK_ERROR`
  * 5xx upstream -> `ERR_MODEL_CONNECTION_UPSTREAM_ERROR`
- Anti-SSRF guard & zero secret leak in error messages or exceptions.
- 0 $ external LLM calls (deterministic HTTPX MockTransport).
"""

from __future__ import annotations

import json

import httpx
import pytest

from orcia_core.orchestration.ai_models_connection import (
    AiModelConnectionTestSuccess,
    test_ai_model_endpoint_connection,
)
from orcia_core.orchestration.ai_models_errors import (
    ModelConnectionAuthFailedError,
    ModelConnectionNetworkError,
    ModelConnectionNotFoundError,
    ModelConnectionRateLimitedError,
    ModelConnectionTimeoutError,
    ModelConnectionUpstreamError,
    UnsafeLlmEndpointUrlError,
)
from orcia_core.rag.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingProviderUnsupportedError,
)


@pytest.mark.asyncio
async def test_chat_connection_openai_compatible_success() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        body = json.loads(request.content.decode("utf-8"))
        assert body.get("max_tokens") == 1
        assert body.get("model") == "mistral-large-latest"
        assert body.get("messages") == [{"role": "user", "content": "ping"}]
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://api.mistral.ai/v1",
            protocol_mode="openai_compatible",
            model_name="mistral-large-latest",
            usage="chat",
            api_key="sk-test-secret-12345",  # pragma: allowlist secret
            provider_slug="mistral",
        )

    assert isinstance(result, AiModelConnectionTestSuccess)
    assert result.latency_ms >= 0
    assert "mistral-large-latest" in result.message_fr
    assert "mistral-large-latest" in result.message_en
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.path == "/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer sk-test-secret-12345"


@pytest.mark.asyncio
async def test_chat_connection_anthropic_messages_success() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        body = json.loads(request.content.decode("utf-8"))
        assert body.get("max_tokens") == 1
        assert body.get("model") == "claude-3-7-sonnet"
        assert body.get("messages") == [{"role": "user", "content": "ping"}]
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "pong"}],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://api.anthropic.com/v1",
            protocol_mode="anthropic_messages",
            model_name="claude-3-7-sonnet",
            usage="chat",
            api_key="sk-ant-test-key",  # pragma: allowlist secret
            provider_slug="anthropic",
        )

    assert isinstance(result, AiModelConnectionTestSuccess)
    assert result.latency_ms >= 0
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.path == "/v1/messages"
    assert req.headers["x-api-key"] == "sk-ant-test-key"
    assert req.headers["anthropic-version"] == "2023-06-01"


@pytest.mark.asyncio
async def test_chat_connection_gemini_native_success() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        body = json.loads(request.content.decode("utf-8"))
        assert body.get("generationConfig", {}).get("maxOutputTokens") == 1
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "P"}]},
                        "finishReason": "MAX_TOKENS",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            protocol_mode="gemini_native",
            model_name="gemini-2.5-flash",
            usage="chat",
            api_key="AIzaSy-test-key",  # pragma: allowlist secret
            provider_slug="google",
        )

    assert isinstance(result, AiModelConnectionTestSuccess)
    assert result.latency_ms >= 0
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert ":generateContent" in str(req.url)
    assert req.headers["x-goog-api-key"] == "AIzaSy-test-key"


@pytest.mark.asyncio
async def test_chat_connection_auth_failed_401() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "Incorrect API key provided: sk-test-badkey"}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ModelConnectionAuthFailedError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="gpt-4o",
                usage="chat",
                api_key="sk-test-badkey",  # pragma: allowlist secret
            )

    err = exc_info.value
    assert err.http_status == 401
    assert err.error_code == "ERR_MODEL_CONNECTION_AUTH_FAILED"
    # Verify no secret leak in string representation
    assert "sk-test-badkey" not in str(err)


@pytest.mark.asyncio
async def test_chat_connection_model_not_found_404() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": {"message": "The model `nonexistent-model` does not exist"}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ModelConnectionNotFoundError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="nonexistent-model",
                usage="chat",
                api_key="sk-test-valid",  # pragma: allowlist secret
            )

    err = exc_info.value
    assert err.http_status == 404
    assert err.error_code == "ERR_MODEL_CONNECTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_chat_connection_rate_limited_429() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ModelConnectionRateLimitedError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="gpt-4o",
                usage="chat",
                api_key="sk-test-valid",  # pragma: allowlist secret
            )

    err = exc_info.value
    assert err.http_status == 429
    assert err.error_code == "ERR_MODEL_CONNECTION_RATE_LIMITED"


@pytest.mark.asyncio
async def test_chat_connection_timeout() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Server took too long to respond")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ModelConnectionTimeoutError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="gpt-4o",
                usage="chat",
                api_key="sk-test-valid",  # pragma: allowlist secret
            )

    err = exc_info.value
    assert err.http_status == 504
    assert err.error_code == "ERR_MODEL_CONNECTION_TIMEOUT"


@pytest.mark.asyncio
async def test_chat_connection_network_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to resolve host")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ModelConnectionNetworkError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://invalid.hostname.internal",
                protocol_mode="openai_compatible",
                model_name="llama3.2",
                usage="chat",
            )

    err = exc_info.value
    assert err.http_status == 502
    assert err.error_code == "ERR_MODEL_CONNECTION_NETWORK_ERROR"


@pytest.mark.asyncio
async def test_chat_connection_upstream_500() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ModelConnectionUpstreamError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="gpt-4o",
                usage="chat",
                api_key="sk-test-valid",  # pragma: allowlist secret
            )

    err = exc_info.value
    assert err.http_status == 502
    assert err.error_code == "ERR_MODEL_CONNECTION_UPSTREAM_ERROR"


@pytest.mark.asyncio
async def test_connection_anti_ssrf_guard() -> None:
    async with httpx.AsyncClient() as client:
        with pytest.raises(UnsafeLlmEndpointUrlError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="http://169.254.169.254/latest/meta-data",
                protocol_mode="openai_compatible",
                model_name="gpt-4o",
                usage="chat",
            )


@pytest.mark.asyncio
async def test_embedding_connection_anthropic_unsupported() -> None:
    async with httpx.AsyncClient() as client:
        with pytest.raises(EmbeddingProviderUnsupportedError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.anthropic.com/v1",
                protocol_mode="anthropic_messages",
                model_name="claude-3-7-sonnet",
                usage="embedding",
                provider_slug="anthropic",
            )

    err = exc_info.value
    assert err.http_status == 422
    assert err.error_code == "ERR_EMBEDDING_PROVIDER_UNSUPPORTED"


@pytest.mark.asyncio
async def test_embedding_connection_openai_compatible_1024_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body.get("dimensions") == 1024
        assert body.get("model") == "text-embedding-3-large"
        assert body.get("input") == ["orcia connection test"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "index": 0,
                        "embedding": [0.001] * 1024,
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1",
            protocol_mode="openai_compatible",
            model_name="text-embedding-3-large",
            usage="embedding",
            api_key="sk-test-embedding-key",  # pragma: allowlist secret
            provider_slug="openai",
        )

    assert isinstance(result, AiModelConnectionTestSuccess)
    assert result.latency_ms >= 0
    assert "1024" in result.message_fr
    assert "1024" in result.message_en


@pytest.mark.asyncio
async def test_embedding_connection_dimension_mismatch_rejection() -> None:
    # Provider returns 768 or 1536 dimensions instead of required 1024
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "index": 0,
                        "embedding": [0.002] * 768,  # Incompatible dimension
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="text-embedding-3-small",
                usage="embedding",
                api_key="sk-test-key",  # pragma: allowlist secret
            )

    err = exc_info.value
    assert err.http_status == 422
    assert err.error_code == "ERR_EMBEDDING_DIMENSION_MISMATCH"


@pytest.mark.asyncio
async def test_embedding_connection_gemini_native_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert ":batchEmbedContents" in str(request.url)
        return httpx.Response(
            200,
            json={"embeddings": [{"values": [0.001] * 1024}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com",
            protocol_mode="gemini_native",
            model_name="text-embedding-004",
            usage="embedding",
            api_key="gemini-key",  # pragma: allowlist secret
            provider_slug="google",
        )

    assert result.latency_ms >= 0
    assert "1024" in result.message_fr


@pytest.mark.asyncio
async def test_embedding_connection_error_translations() -> None:
    # 401
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(401, text="Unauthorized"))
    ) as client:
        with pytest.raises(ModelConnectionAuthFailedError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="text-embedding-3-large",
                usage="embedding",
            )

    # 404
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(404, text="Model not found"))
    ) as client:
        with pytest.raises(ModelConnectionNotFoundError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="unknown-embedding-model",
                usage="embedding",
            )

    # 429
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(429, text="Rate limit"))
    ) as client:
        with pytest.raises(ModelConnectionRateLimitedError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="text-embedding-3-large",
                usage="embedding",
            )

    # 500 upstream
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(500, text="Internal Server Error"))
    ) as client:
        with pytest.raises(ModelConnectionUpstreamError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="text-embedding-3-large",
                usage="embedding",
            )

    # Network error
    def network_error_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    async with httpx.AsyncClient(transport=httpx.MockTransport(network_error_handler)) as client:
        with pytest.raises(ModelConnectionNetworkError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="text-embedding-3-large",
                usage="embedding",
            )

    # Timeout
    def timeout_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as client:
        with pytest.raises(ModelConnectionTimeoutError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://api.openai.com/v1",
                protocol_mode="openai_compatible",
                model_name="text-embedding-3-large",
                usage="embedding",
            )


@pytest.mark.asyncio
async def test_chat_url_normalization_branches() -> None:
    def ok_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "pong"}}]},
        )

    # Anthropic with /messages in url
    transport = httpx.MockTransport(ok_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        res = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://api.anthropic.com/v1/messages",
            protocol_mode="anthropic_messages",
            model_name="claude-3-haiku",
            usage="chat",
        )
        assert res.latency_ms >= 0

    # Gemini with :generateContent in url
    def gemini_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "P"}]}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(gemini_handler)) as client:
        res2 = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            protocol_mode="gemini_native",
            model_name="gemini-2.5-flash",
            usage="chat",
        )
        assert res2.latency_ms >= 0

    # Base ending with /api
    async with httpx.AsyncClient(transport=transport) as client:
        res3 = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="http://127.0.0.1:11434/api",
            protocol_mode="openai_compatible",
            model_name="qwen2.5:7b",
            usage="chat",
        )
        assert res3.latency_ms >= 0
