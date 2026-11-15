"""HTTPX-based pure asynchronous adapters for EmbeddingPort (`AD-24.5`, `Story 19.5`).

Supports:
- openai_compatible: OpenAI, Mistral, vLLM, TEI, Ollama (/v1/embeddings or /api/embed)
- gemini_native: Google Gemini (:batchEmbedContents with outputDimensionality=1024)
Strict validation of 1024 finite floats. Zero third-party SDK dependencies.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse

import httpx

from orcia_core.ports.embedding import EMBEDDING_FIXED_DIMENSION, EmbeddingPort
from orcia_core.rag.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationFailedError,
    EmbeddingProviderUnsupportedError,
)

_BATCH_SIZE_MAX: int = 64


def validate_embedding_vectors_dimension(
    vectors: Sequence[Sequence[float]],
    expected_dim: int = EMBEDDING_FIXED_DIMENSION,
) -> None:
    """Validate that every vector has exactly `expected_dim` finite floating-point numbers."""
    for idx, vec in enumerate(vectors):
        if len(vec) != expected_dim:
            raise EmbeddingDimensionMismatchError(
                detail_override=(
                    f"Embedding dimension mismatch at index {idx}: expected {expected_dim}, "
                    f"received {len(vec)}."
                )
            )
        for val_idx, val in enumerate(vec):
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise EmbeddingGenerationFailedError(
                    detail_override=(
                        f"Non-finite float detected at vector[{idx}][{val_idx}]: {val!r}."
                    )
                )


def assert_embedding_usage_supported(
    *,
    provider_slug: str,
    protocol_mode: str,
) -> None:
    """Refuse providers that do not have native embedding endpoints (e.g. Anthropic)."""
    p_slug = provider_slug.strip().lower()
    p_mode = protocol_mode.strip().lower()
    if p_slug == "anthropic" or p_mode == "anthropic_messages":
        raise EmbeddingProviderUnsupportedError(
            detail_override=(
                "Le fournisseur Anthropic ne propose aucune API native d'embeddings sémantiques. "
                "Sélectionnez un fournisseur compatible (OpenAI, Mistral, Gemini, Ollama, vLLM)."
            )
        )


class HttpxOpenAiCompatibleEmbeddingAdapter(EmbeddingPort):
    """Adapter for OpenAI-compatible embedding APIs (`POST /v1/embeddings` or `/api/embed`)."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        endpoint_uri: str,
        model_name: str,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._client = http_client
        self._raw_endpoint = endpoint_uri.strip().rstrip("/")
        self._model_name = model_name.strip()
        self._api_key = api_key.strip() if api_key else None
        self._timeout = timeout_seconds

    @property
    def dimension(self) -> int:
        return EMBEDDING_FIXED_DIMENSION

    def _resolve_url_and_is_ollama_native(self) -> tuple[str, bool]:
        parsed = urlparse(self._raw_endpoint)
        path = parsed.path.rstrip("/")
        if path.endswith("/api/embed"):
            return self._raw_endpoint, True
        if path.endswith("/v1/embeddings") or path.endswith("/embeddings"):
            return self._raw_endpoint, False
        if path.endswith("/v1"):
            return f"{self._raw_endpoint}/embeddings", False
        return f"{self._raw_endpoint}/v1/embeddings", False

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        url, is_ollama_native = self._resolve_url_and_is_ollama_native()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        if is_ollama_native:
            payload: dict[str, Any] = {
                "model": self._model_name,
                "input": batch,
            }
        else:
            payload = {
                "model": self._model_name,
                "input": batch,
                "dimensions": EMBEDDING_FIXED_DIMENSION,
            }

        try:
            resp = await self._client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.RequestError as exc:
            raise EmbeddingGenerationFailedError(
                detail_override=(
                    f"Network error calling embedding endpoint '{url}': {type(exc).__name__}."
                )
            ) from exc

        if resp.status_code == 400 and "dimensions" in payload:
            fallback_payload = {"model": self._model_name, "input": batch}
            try:
                fallback_resp = await self._client.post(
                    url,
                    json=fallback_payload,
                    headers=headers,
                    timeout=self._timeout,
                )
                if fallback_resp.status_code == 200:
                    resp = fallback_resp
            except httpx.RequestError:
                pass

        if resp.status_code != 200:
            clean_status = resp.status_code
            error_snippet = resp.text[:250].replace(self._api_key or "___N_O_N_E___", "[REDACTED]")
            raise EmbeddingGenerationFailedError(
                detail_override=(
                    f"Embedding provider responded with HTTP {clean_status}: {error_snippet}"
                )
            )

        data = resp.json()
        raw_vectors: list[list[float]] = []

        if is_ollama_native:
            embeddings_list = data.get("embeddings", [])
            for item in embeddings_list:
                raw_vectors.append([float(x) for x in item])
        else:
            items = data.get("data", [])
            sorted_items = sorted(items, key=lambda x: x.get("index", 0))
            for item in sorted_items:
                raw_vectors.append([float(x) for x in item.get("embedding", [])])

        validate_embedding_vectors_dimension(raw_vectors, EMBEDDING_FIXED_DIMENSION)
        return raw_vectors

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        all_results: list[list[float]] = []
        text_list = list(texts)
        for i in range(0, len(text_list), _BATCH_SIZE_MAX):
            batch = text_list[i : i + _BATCH_SIZE_MAX]
            vectors = await self._embed_batch(batch)
            all_results.extend(vectors)
        return all_results

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        res = await self.embed([query])
        return res[0]


class HttpxGeminiNativeEmbeddingAdapter(EmbeddingPort):
    """Adapter for Google Gemini native `:batchEmbedContents` API."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        endpoint_uri: str,
        model_name: str,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._client = http_client
        self._raw_endpoint = endpoint_uri.strip().rstrip("/")
        self._model_name = model_name.strip()
        self._api_key = api_key.strip() if api_key else None
        self._timeout = timeout_seconds

    @property
    def dimension(self) -> int:
        return EMBEDDING_FIXED_DIMENSION

    def _resolve_url_and_model_path(self) -> tuple[str, str]:
        model_path = (
            self._model_name
            if self._model_name.startswith("models/")
            else f"models/{self._model_name}"
        )
        if ":batchEmbedContents" in self._raw_endpoint:
            return self._raw_endpoint, model_path
        if "/v1beta" in self._raw_endpoint:
            base = self._raw_endpoint
        else:
            base = f"{self._raw_endpoint}/v1beta"
        return f"{base}/{model_path}:batchEmbedContents", model_path

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        url, model_path = self._resolve_url_and_model_path()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["x-goog-api-key"] = self._api_key

        requests_payload = [
            {
                "model": model_path,
                "content": {"parts": [{"text": t}]},
                "outputDimensionality": EMBEDDING_FIXED_DIMENSION,
            }
            for t in batch
        ]
        payload = {"requests": requests_payload}

        try:
            resp = await self._client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.RequestError as exc:
            raise EmbeddingGenerationFailedError(
                detail_override=(
                    f"Network error calling Gemini embedding endpoint: {type(exc).__name__}."
                )
            ) from exc

        if resp.status_code != 200:
            clean_status = resp.status_code
            error_snippet = resp.text[:250].replace(self._api_key or "___N_O_N_E___", "[REDACTED]")
            raise EmbeddingGenerationFailedError(
                detail_override=(
                    f"Gemini embedding API responded with HTTP {clean_status}: {error_snippet}"
                )
            )

        data = resp.json()
        embeddings_items = data.get("embeddings", [])
        raw_vectors: list[list[float]] = []
        for item in embeddings_items:
            values = item.get("values", [])
            raw_vectors.append([float(v) for v in values])

        validate_embedding_vectors_dimension(raw_vectors, EMBEDDING_FIXED_DIMENSION)
        return raw_vectors

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        all_results: list[list[float]] = []
        text_list = list(texts)
        for i in range(0, len(text_list), _BATCH_SIZE_MAX):
            batch = text_list[i : i + _BATCH_SIZE_MAX]
            vectors = await self._embed_batch(batch)
            all_results.extend(vectors)
        return all_results

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        res = await self.embed([query])
        return res[0]


__all__ = [
    "HttpxGeminiNativeEmbeddingAdapter",
    "HttpxOpenAiCompatibleEmbeddingAdapter",
    "assert_embedding_usage_supported",
    "validate_embedding_vectors_dimension",
]
