"""Deterministic in-memory fake for `PackCasStoragePort` (`tests/unit/fakes` only)."""

from __future__ import annotations

import hashlib

from orcia_core.packs._internal.seaweedfs_pack_cas import build_pack_cas_key
from orcia_core.packs.ports import PackCasStoragePort


class InMemoryPackCasStorage(PackCasStoragePort):
    """In-memory CAS store for Story 31.2 unit tests."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_archive_zip(
        self,
        *,
        slug: str,
        version: str,
        archive_sha256: str,
        zip_bytes: bytes,
    ) -> str:
        computed = hashlib.sha256(zip_bytes).hexdigest()
        expected = archive_sha256.strip().lower()
        if computed != expected:
            raise ValueError(f"SHA-256 mismatch: expected {expected}, got {computed}")
        key = build_pack_cas_key(slug=slug, version=version, archive_sha256=expected)
        self.objects[key] = zip_bytes
        return key

    async def get_archive_zip(self, cas_key: str) -> bytes | None:
        return self.objects.get(cas_key)

    async def head_archive_zip(self, cas_key: str) -> bool:
        return cas_key in self.objects


__all__ = ["InMemoryPackCasStorage"]
