"""Unit tests for Story 19.5: EmbeddingPort, HTTPX adapters, and error contracts (`AD-24.5`)."""

from __future__ import annotations

import math
import socket
from typing import Any

import httpx
import pytest
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag.adapters.embedding_httpx import (
    HttpxGeminiNativeEmbeddingAdapter,
    HttpxOpenAiCompatibleEmbeddingAdapter,
    assert_embedding_usage_supported,
    validate_embedding_vectors_dimension,
)
from orcia_core.rag.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationFailedError,
    EmbeddingProviderUnsupportedError,
)


def test_fake_deterministic_embedding_adapter_contract() -> None:
    """Verify fake adapter satisfies EmbeddingPort and produces 1024-dim deterministic vectors."""
    adapter: EmbeddingPort = FakeDeterministicEmbeddingAdapter()
    assert adapter.dimension == 1024

    texts = ["bonjour le monde", "documentation orcia"]
    vectors = pytest.importorskip("asyncio").run(adapter.embed_texts(texts))

    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == 1024
        assert all(isinstance(val, float) and math.isfinite(val) for val in vec)

    # Determinism: same input gives identical vector
    v1_again = pytest.importorskip("asyncio").run(adapter.embed_query("bonjour le monde"))
    assert v1_again == vectors[0]


def test_validate_embedding_vectors_dimension() -> None:
    """Strict validation: exactly 1024 finite floats per vector, error otherwise."""
    valid_vector = [0.1] * 1024
    validate_embedding_vectors_dimension([valid_vector], expected_dim=1024)

    # Wrong dimension raises EmbeddingDimensionMismatchError
    with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
        validate_embedding_vectors_dimension([[0.1] * 768], expected_dim=1024)
    assert exc_info.value.error_code == "ERR_EMBEDDING_DIMENSION_MISMATCH"
    assert exc_info.value.http_status == 422

    # Non-finite float raises EmbeddingGenerationFailedError or dimension error
    with pytest.raises(EmbeddingGenerationFailedError):
        bad_vector = [0.1] * 1023 + [float("nan")]
        validate_embedding_vectors_dimension([bad_vector], expected_dim=1024)


def test_assert_embedding_usage_supported_rejects_anthropic() -> None:
    """Anthropic has no native embedding API and must be rejected for usage='embedding'."""
    assert_embedding_usage_supported(provider_slug="openai", protocol_mode="openai_compatible")
    assert_embedding_usage_supported(provider_slug="google", protocol_mode="gemini_native")
    assert_embedding_usage_supported(provider_slug="mistral", protocol_mode="openai_compatible")
    assert_embedding_usage_supported(provider_slug="ollama", protocol_mode="openai_compatible")

    with pytest.raises(EmbeddingProviderUnsupportedError) as exc_info:
        assert_embedding_usage_supported(
            provider_slug="anthropic", protocol_mode="anthropic_messages"
        )
    assert exc_info.value.error_code == "ERR_EMBEDDING_PROVIDER_UNSUPPORTED"
    assert exc_info.value.http_status == 422


@pytest.mark.asyncio
async def test_httpx_openai_compatible_embedding_adapter_success() -> None:
    """Verify openai_compatible adapter formats payload and parses 1024-dim response."""
    test_key = "sk-test-secret-canary"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path in ("/v1/embeddings", "/embeddings")
        assert request.headers.get("authorization") == f"Bearer {test_key}"
        # Response with 1024-dim vector
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [0.05] * 1024},
                    {"index": 1, "embedding": [-0.05] * 1024},
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1",
            model_name="text-embedding-3-large",
            api_key=test_key,
        )
        assert adapter.dimension == 1024
        vectors = await adapter.embed_texts(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 1024
        assert len(vectors[1]) == 1024


@pytest.mark.asyncio
async def test_httpx_openai_compatible_embedding_ollama_embed_endpoint() -> None:
    """Verify native Ollama /api/embed endpoint formatting."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        return httpx.Response(
            200,
            json={
                "embeddings": [
                    [0.01] * 1024,
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="http://localhost:11434/api/embed",
            model_name="bge-m3",
        )
        vectors = await adapter.embed(["test doc"])
        assert len(vectors) == 1
        assert len(vectors[0]) == 1024


@pytest.mark.asyncio
async def test_httpx_gemini_native_embedding_adapter_success() -> None:
    """Verify gemini_native adapter calls :batchEmbedContents with outputDimensionality=1024."""
    test_key = "gemini-secret-canary"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert ":batchEmbedContents" in request.url.path
        assert request.headers.get("x-goog-api-key") == test_key
        return httpx.Response(
            200,
            json={
                "embeddings": [
                    {"values": [0.02] * 1024},
                    {"values": [-0.02] * 1024},
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HttpxGeminiNativeEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com",
            model_name="text-embedding-004",
            api_key=test_key,
        )
        assert adapter.dimension == 1024
        vectors = await adapter.embed_texts(["doc A", "doc B"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 1024


@pytest.mark.asyncio
async def test_httpx_embedding_adapters_dimension_mismatch_and_http_errors() -> None:
    """Check proper RFC 9457 exceptions on 768-dim output and HTTP 500 error."""

    # 1. Dimension mismatch
    def mock_768_dim(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1] * 768}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_768_dim)) as client:
        adapter = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1",
            model_name="small-model",
        )
        with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
            await adapter.embed_texts(["test"])
        assert "768" in str(exc_info.value)

    # 2. HTTP error 401
    def mock_401(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API Key"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_401)) as client:
        adapter = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1",
            model_name="model",
            api_key="bad-key",  # pragma: allowlist secret
        )
        with pytest.raises(EmbeddingGenerationFailedError) as exc_info:
            await adapter.embed_texts(["test"])
        assert exc_info.value.http_status == 502


@pytest.mark.asyncio
async def test_httpx_embedding_adapters_edge_cases_and_network_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test empty input, embed_query, URL variations, 400 dimension fallback, and network errors."""

    def _fake_getaddrinfo(host: str, port: Any, *_args: Any, **_kwargs: Any) -> list[Any]:
        if host == "down-host.local":
            raise socket.gaierror(-2, "Name or service not known")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", int(port or 443)))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    # 1. Empty input
    async with httpx.AsyncClient() as client:
        oa = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1/embeddings",
            model_name="text-embedding-3-large",
        )
        assert await oa.embed([]) == []

        gem = HttpxGeminiNativeEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            model_name="models/text-embedding-004",
        )
        assert await gem.embed([]) == []

    # 2. embed_query and URL formatting
    def mock_oa(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/v1/embeddings")
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.5] * 1024}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_oa)) as client:
        # endpoint without /v1
        oa = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://custom-llm.corp",
            model_name="custom-embed",
        )
        q_vec = await oa.embed_query("search query")
        assert len(q_vec) == 1024

    # 3. OpenAI 400 dimensions fallback
    call_count = 0

    def mock_dimensions_reject(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        body = request.read().decode("utf-8")
        if "dimensions" in body:
            return httpx.Response(400, json={"error": "dimensions param not supported"})
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.2] * 1024}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_dimensions_reject)) as client:
        oa = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://api.openai.com/v1",
            model_name="local-tei",
        )
        res = await oa.embed(["text"])
        assert len(res) == 1
        assert len(res[0]) == 1024
        assert call_count == 2

    # 4. Network error on OpenAI
    def mock_network_err(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_network_err)) as client:
        oa = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://down-host.local",
            model_name="model",
        )
        with pytest.raises(EmbeddingGenerationFailedError) as exc_oa:
            await oa.embed(["text"])
        assert "Network error" in str(exc_oa.value)

        gem = HttpxGeminiNativeEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://down-host.local",
            model_name="text-embedding-004",
        )
        with pytest.raises(EmbeddingGenerationFailedError) as exc_gem:
            await gem.embed(["text"])
        assert "Network error" in str(exc_gem.value)

    # 5. Gemini full url endpoint + embed_query + HTTP 500 error
    def mock_gemini_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Gemini Error with key SECRET_AI_KEY")

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_gemini_500)) as client:
        gem = HttpxGeminiNativeEmbeddingAdapter(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents",
            model_name="text-embedding-004",
            api_key="SECRET_AI_KEY",  # pragma: allowlist secret
        )
        with pytest.raises(EmbeddingGenerationFailedError) as exc_gem:
            await gem.embed_query("query")
        # Ensure secret API key is redacted from error details
        assert "SECRET_AI_KEY" not in str(exc_gem.value)
        assert "[REDACTED]" in str(exc_gem.value)
