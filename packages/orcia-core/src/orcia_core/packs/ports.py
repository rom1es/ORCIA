"""Pure hexagonal ports for declarative APM packs v2 (`AD-19`, `Story 31.1`).

Zero framework or database driver imports.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from orcia_core.packs.models import LoadedPackBundleV2, PackManifestV2, PackScopeType


@runtime_checkable
class PackCodecPort(Protocol):
    """Port for decoding/encoding deterministic APM-Superset & legacy pack archives."""

    def decode_directory(self, pack_dir: Path) -> LoadedPackBundleV2:
        """Decode and validate an on-disk pack directory."""
        ...

    def decode_zip_bytes(self, zip_bytes: bytes) -> LoadedPackBundleV2:
        """Decode and validate an in-memory `.zip` pack archive."""
        ...

    def encode_zip_bytes(self, bundle: LoadedPackBundleV2) -> bytes:
        """Encode a pack bundle into deterministic reproducible `.zip` bytes."""
        ...


@runtime_checkable
class PackBundleRepositoryPort(Protocol):
    """Persistence port for v2 `declarative_pack_bundles` rows in PostgreSQL 18."""

    async def upsert_bundle_v2(
        self,
        bundle: LoadedPackBundleV2,
        *,
        cas_object_key: str | None = None,
    ) -> PackManifestV2:
        """Idempotently persist a validated v2 bundle into `declarative_pack_bundles`."""
        ...

    async def list_bundles_v2(
        self,
        *,
        scope_type: PackScopeType | None = None,
        scope_id: str | None = None,
    ) -> Sequence[dict[str, object]]:
        """List v2 bundle metadata rows optionally filtered by scope."""
        ...

    async def get_bundle_v2(self, bundle_id_or_slug: str) -> dict[str, object] | None:
        """Fetch a v2 bundle metadata row by UUID `id`, `pack_id`, or `slug`."""
        ...

    async def delete_bundle(self, bundle_id: str) -> None:
        """Delete a pack bundle after checking run pinning and cross-draft memberships."""
        ...


__all__ = ["PackBundleRepositoryPort", "PackCodecPort"]
