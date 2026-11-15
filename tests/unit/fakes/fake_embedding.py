"""Deterministic in-memory Fake Embedding Adapter for CI testing (`AD-17`, `Story 19.5`).

Produces 1024-dimensional normalized float vectors deterministically from input strings (0 $ cost).
Can also be initialized with pre-recorded cassettes.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Sequence

from orcia_core.ports.embedding import EMBEDDING_FIXED_DIMENSION, EmbeddingPort


def _deterministic_vector_1024(text: str) -> list[float]:
    """Derive a deterministic 1024-dim unit-normalized vector from text content."""
    # Seed generator with sha256
    raw_seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []

    # Expand 32 bytes into 1024 floats via chained hashes
    current = raw_seed
    while len(values) < EMBEDDING_FIXED_DIMENSION:
        current = hashlib.sha256(current).digest()
        # Extract 8 floats (32 bytes = 8 x 4-byte standard floats)
        floats = struct.unpack("8f", current)
        for f in floats:
            # Avoid nan / inf
            val = f if math.isfinite(f) else 0.0
            values.append(val)
            if len(values) == EMBEDDING_FIXED_DIMENSION:
                break

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [round(v / norm, 6) for v in values]


class FakeDeterministicEmbeddingAdapter(EmbeddingPort):
    """Test fake implementing `EmbeddingPort` with zero network overhead."""

    def __init__(self, recorded_cassette: dict[str, list[float]] | None = None) -> None:
        self._cassette: dict[str, list[float]] = dict(recorded_cassette or {})
        self.call_count: int = 0
        self.last_texts: list[str] = []

    @property
    def dimension(self) -> int:
        return EMBEDDING_FIXED_DIMENSION

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.call_count += 1
        self.last_texts = list(texts)
        results: list[list[float]] = []
        for text in texts:
            if text in self._cassette:
                vec = self._cassette[text]
            else:
                vec = _deterministic_vector_1024(text)
            results.append(vec)
        return results

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        res = await self.embed([query])
        return res[0]

    def embed_query_sync(self, query: str) -> list[float]:
        self.call_count += 1
        self.last_texts = [query]
        if query in self._cassette:
            return self._cassette[query]
        return _deterministic_vector_1024(query)


__all__ = [
    "FakeDeterministicEmbeddingAdapter",
]
