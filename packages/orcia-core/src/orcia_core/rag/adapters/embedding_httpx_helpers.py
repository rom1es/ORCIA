"""Shared HTTPX Pinned Posting & Vector Validation Helpers for Embedding Adapters."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import httpx

from orcia_core.permissions.pinned_http import prepare_pinned_http_request
from orcia_core.ports.embedding import EMBEDDING_FIXED_DIMENSION
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
        raise EmbeddingProviderUnsupportedError(detail_code="ERR_EMBEDDING_ANTHROPIC_UNSUPPORTED")


async def post_pinned_embedding_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> httpx.Response:
    """Execute pinned JSON POST protecting embedding adapters against DNS rebinding."""
    p_url, p_hdrs, p_ext = await prepare_pinned_http_request(client, url, headers)
    if p_ext:
        return await client.post(
            p_url, json=payload, headers=p_hdrs, timeout=timeout, extensions=p_ext
        )
    return await client.post(p_url, json=payload, headers=p_hdrs, timeout=timeout)
