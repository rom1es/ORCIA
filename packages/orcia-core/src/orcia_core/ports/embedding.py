"""Hexagonal Embedding Port interface (`AD-19`, `AD-24.5`, `Story 19.5`).

Strictly pure protocol: zero external framework, SDK or HTTP transport imports.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

EMBEDDING_FIXED_DIMENSION: int = 1024


@runtime_checkable
class EmbeddingPort(Protocol):
    """Hexagonal contract for semantic text embeddings generation (1024-dim)."""

    @property
    def dimension(self) -> int:
        """Fixed dimensionality of generated vectors (strictly 1024)."""
        ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate 1024-dimensional normalized float vectors for input texts."""
        ...

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Alias for `embed` complying with common semantic indexing pipelines."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Generate a single 1024-dimensional vector for a user or retrieval query."""
        ...


__all__ = [
    "EMBEDDING_FIXED_DIMENSION",
    "EmbeddingPort",
]
