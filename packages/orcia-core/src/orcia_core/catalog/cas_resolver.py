"""FederatedUriResolver & Content-Addressable Storage (`cas/<sha256>`, `< 50 ms`, AD-5, AD-20).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from typing import Protocol

from orcia_core.catalog.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.catalog.models import (
    ArchiveFormat,
    CasObjectEntry,
    CasResolutionResult,
    ParsedFederatedUri,
)
from orcia_kernel.ports import (
    get_registered_connector,
    is_registered_connector_scheme,
    list_registered_connector_schemes,
)

HEX_SHA_RE = re.compile(r"^[0-9a-f]{6,64}$")
FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def get_allowed_schemes() -> frozenset[str]:
    """Return dynamic set of registered connector schemes (`orcia_kernel.ports`, `AD-20`)."""
    return list_registered_connector_schemes()


def compute_bytes_sha256(payload: bytes) -> str:
    """Compute lowercase hexadecimal SHA-256 digest of `payload`."""
    return hashlib.sha256(payload).hexdigest()


def parse_federated_uri(raw_uri: str) -> ParsedFederatedUri:
    """Parse and validate a federated URI against the dynamic connector registry (`AD-5`)."""
    cleaned = raw_uri.strip()
    if "://" not in cleaned:
        raise ValidationDomainError(detail_override=f"Missing '://' in URI: {raw_uri!r}")
    scheme_raw, remainder = cleaned.split("://", 1)
    scheme_lower = scheme_raw.lower()
    if not is_registered_connector_scheme(scheme_lower):
        raise ValidationDomainError(detail_override=f"Unsupported URI scheme {scheme_raw!r}")
    remainder = remainder.strip()
    if "/" not in remainder:
        raise ValidationDomainError(detail_override=f"URI must include authority/path: {raw_uri!r}")
    authority, raw_path = [part.strip() for part in remainder.split("/", 1)]
    if not authority or not raw_path:
        raise ValidationDomainError(detail_override=f"Empty authority or path: {raw_uri!r}")

    connector = get_registered_connector(scheme_lower)
    resolution_mode = (
        connector.capabilities().version_resolution_mode
        if connector is not None
        else "ref_or_latest"
    )

    expected_sha256: str | None = None
    version_or_ref = "latest"
    path_part = raw_path
    if "@sha256:" in raw_path:
        path_part, sha_ref = raw_path.rsplit("@sha256:", 1)
        sha_clean = sha_ref.strip().lower()
        if not HEX_SHA_RE.match(sha_clean):
            raise ValidationDomainError(detail_override=f"Invalid @sha256 digest: {raw_uri!r}")
        expected_sha256 = sha_clean
        version_or_ref = f"sha256:{sha_clean[:12]}"
    elif "@" in raw_path:
        path_part, ref_part = raw_path.rsplit("@", 1)
        ref_clean = ref_part.strip()
        if not path_part.strip() or not ref_clean:
            raise ValidationDomainError(detail_override=f"Empty path or version ref: {raw_uri!r}")
        version_or_ref = ref_clean
    elif resolution_mode == "last_path_segment":
        segments = [seg for seg in path_part.split("/") if seg]
        version_or_ref = segments[-1] if segments else "latest"

    path_clean = path_part.strip().strip("/")
    if not path_clean:
        raise ValidationDomainError(detail_override=f"Empty normalized path: {raw_uri!r}")
    archive_format: ArchiveFormat = (
        "tar.gz"
        if path_clean.endswith((".tar.gz", ".tgz"))
        else ("zip" if path_clean.endswith(".zip") else "none")
    )
    return ParsedFederatedUri(
        raw_uri=cleaned,
        scheme=scheme_lower,
        authority=authority,
        path=path_clean,
        version_or_ref=version_or_ref,
        expected_sha256=expected_sha256,
        archive_format=archive_format,
    )


class CasObjectStoreProtocol(Protocol):
    """Port protocol for immutable Content-Addressable Storage (`cas/<sha256>`)."""

    def get_object(self, cas_key: str) -> CasObjectEntry | None: ...
    def put_object(self, entry: CasObjectEntry) -> None: ...
    def has_object(self, cas_key: str) -> bool: ...


class S3BucketBackendProtocol(Protocol):
    """Minimal structural protocol for an S3/MinIO bucket backend without external SDK imports."""

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None: ...
    def get_bytes(self, bucket: str, key: str) -> bytes | None: ...
    def head_key(self, bucket: str, key: str) -> bool: ...


def _verify_entry_integrity(entry: CasObjectEntry) -> None:
    if not FULL_SHA256_RE.match(entry.sha256) or entry.cas_key != f"cas/{entry.sha256}":
        raise ValidationDomainError(detail_override=f"Invalid CAS key {entry.cas_key!r}")
    actual_sha = compute_bytes_sha256(entry.content_bytes)
    if actual_sha != entry.sha256:
        raise ValidationDomainError(detail_override=f"CAS SHA-256 mismatch for {entry.cas_key!r}")


class InMemoryCasObjectStore:
    """Thread-safe in-memory CAS object store enforcing `cas/<sha256>` immutability."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._objects: dict[str, CasObjectEntry] = {}

    def get_object(self, cas_key: str) -> CasObjectEntry | None:
        with self._lock:
            return self._objects.get(cas_key)

    def put_object(self, entry: CasObjectEntry) -> None:
        _verify_entry_integrity(entry)
        with self._lock:
            existing = self._objects.get(entry.cas_key)
            if existing is not None and existing.content_bytes != entry.content_bytes:
                raise ValidationDomainError(detail_override=f"CAS collision on {entry.cas_key}")
            self._objects[entry.cas_key] = entry

    def has_object(self, cas_key: str) -> bool:
        with self._lock:
            return cas_key in self._objects


class S3CompatibleCasObjectStore:
    """MinIO / S3-compatible CAS object store with L1 hot cache (`< 50 ms`, `AD-5`)."""

    def __init__(self, backend: S3BucketBackendProtocol, bucket_name: str = "orcia-cas") -> None:
        self._backend = backend
        self._bucket = bucket_name
        self._lock = threading.Lock()
        self._hot_cache: dict[str, CasObjectEntry] = {}

    def get_object(self, cas_key: str) -> CasObjectEntry | None:
        with self._lock:
            cached = self._hot_cache.get(cas_key)
        if cached is not None:
            return cached
        raw_bytes = self._backend.get_bytes(self._bucket, cas_key)
        if raw_bytes is None:
            return None
        entry = CasObjectEntry(
            sha256=cas_key.removeprefix("cas/"), cas_key=cas_key, content_bytes=raw_bytes
        )
        _verify_entry_integrity(entry)
        with self._lock:
            self._hot_cache[cas_key] = entry
        return entry

    def put_object(self, entry: CasObjectEntry) -> None:
        _verify_entry_integrity(entry)
        self._backend.put_bytes(
            self._bucket, entry.cas_key, entry.content_bytes, entry.content_type
        )
        with self._lock:
            self._hot_cache[entry.cas_key] = entry

    def has_object(self, cas_key: str) -> bool:
        with self._lock:
            if cas_key in self._hot_cache:
                return True
        return self._backend.head_key(self._bucket, cas_key)


def _matches_expected_sha(actual_sha256: str, expected_sha256: str | None) -> bool:
    if not expected_sha256:
        return True
    norm = expected_sha256.strip().lower()
    return bool(HEX_SHA_RE.match(norm) and actual_sha256.startswith(norm))


class FederatedUriResolver:
    """On-the-fly Federated URI Resolver with immutable `cas/<sha256>` caching (`AD-5`, `AD-20`)."""

    def __init__(self, cas_store: CasObjectStoreProtocol | None = None) -> None:
        self.cas_store: CasObjectStoreProtocol = cas_store or InMemoryCasObjectStore()
        self._lock = threading.Lock()
        self._upstream_payloads: dict[str, tuple[bytes, str]] = {}
        self._resolved_index: dict[str, tuple[str, str]] = {}

    def register_upstream_payload(
        self,
        raw_uri: str,
        payload: bytes | str,
        *,
        resolved_version: str | None = None,
        prewarm_cas: bool = False,
    ) -> str:
        """Register an upstream resource payload and optionally pre-populate `cas/<sha256>`."""
        parsed = parse_federated_uri(raw_uri)
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        sha256 = compute_bytes_sha256(data)
        if not _matches_expected_sha(sha256, parsed.expected_sha256):
            raise ValidationDomainError(detail_override=f"SHA-256 mismatch for {raw_uri}")
        version = resolved_version or parsed.version_or_ref
        with self._lock:
            self._upstream_payloads[parsed.raw_uri] = (data, version)
            if prewarm_cas:
                self.cas_store.put_object(
                    CasObjectEntry(
                        sha256=sha256,
                        cas_key=f"cas/{sha256}",
                        content_bytes=data,
                        source_uri=parsed.raw_uri,
                    )
                )
                self._resolved_index[parsed.raw_uri] = (sha256, version)
            else:
                self._resolved_index.pop(parsed.raw_uri, None)
        return sha256

    def resolve(self, raw_uri: str, *, expected_sha256: str | None = None) -> CasResolutionResult:
        """Resolve a federated URI into `cas/<sha256>` (`< 50 ms` on hot cache, `NFR-PERF-3`)."""
        start_ns = time.perf_counter_ns()
        parsed = parse_federated_uri(raw_uri)
        effective_expected = expected_sha256 or parsed.expected_sha256

        with self._lock:
            indexed = self._resolved_index.get(parsed.raw_uri)
        if indexed is not None:
            cached_sha, cached_version = indexed
            cas_key = f"cas/{cached_sha}"
            if (cached_entry := self.cas_store.get_object(cas_key)) is not None:
                if not _matches_expected_sha(cached_sha, effective_expected):
                    raise ValidationDomainError(detail_override="Cached CAS SHA-256 mismatch")
                ms = round((time.perf_counter_ns() - start_ns) / 1_000_000, 4)
                return CasResolutionResult(
                    uri=parsed.raw_uri,
                    scheme=parsed.scheme,
                    resolved_version=cached_version,
                    sha256=cached_sha,
                    cas_key=cas_key,
                    cache_hit=True,
                    resolution_ms=ms,
                    content_text=cached_entry.content_text,
                )

        with self._lock:
            upstream = self._upstream_payloads.get(parsed.raw_uri)
        if upstream is not None:
            payload_bytes, resolved_version = upstream
        else:
            connector = get_registered_connector(parsed.scheme)
            if connector is not None:
                fetched = connector.fetch(parsed.raw_uri)
                payload_bytes = fetched.content_bytes
                resolved_version = fetched.resolved_version or parsed.version_or_ref
            else:
                resolved_version = parsed.version_or_ref
                payload_bytes = json.dumps(
                    {
                        "authority": parsed.authority,
                        "archive_format": parsed.archive_format,
                        "path": parsed.path,
                        "resolved_version": resolved_version,
                        "scheme": parsed.scheme,
                        "uri": parsed.raw_uri,
                    },
                    sort_keys=True,
                ).encode("utf-8")

        actual_sha = compute_bytes_sha256(payload_bytes)
        if not _matches_expected_sha(actual_sha, effective_expected):
            raise ValidationDomainError(detail_override="SHA-256 verification failed")
        cas_key = f"cas/{actual_sha}"
        entry = CasObjectEntry(
            sha256=actual_sha,
            cas_key=cas_key,
            content_bytes=payload_bytes,
            source_uri=parsed.raw_uri,
        )
        self.cas_store.put_object(entry)
        with self._lock:
            self._resolved_index[parsed.raw_uri] = (actual_sha, resolved_version)
        return CasResolutionResult(
            uri=parsed.raw_uri,
            scheme=parsed.scheme,
            resolved_version=resolved_version,
            sha256=actual_sha,
            cas_key=cas_key,
            cache_hit=False,
            resolution_ms=round((time.perf_counter_ns() - start_ns) / 1_000_000, 4),
            content_text=entry.content_text,
        )

    def get_cas_entry(self, sha256: str, *, instance: str | None = None) -> CasObjectEntry:
        """Fetch an immutable object by its 64-character `sha256` digest from `cas/<sha256>`."""
        clean_sha = sha256.strip().lower()
        if not FULL_SHA256_RE.match(clean_sha):
            raise ValidationDomainError(detail_override="Invalid SHA-256 format", instance=instance)
        if (entry := self.cas_store.get_object(f"cas/{clean_sha}")) is None:
            raise ResourceNotFoundError(instance=instance)
        _verify_entry_integrity(entry)
        return entry
