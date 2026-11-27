"""Async SeaweedFS S3 v4 CAS storage adapter for pack `.zip` archives (`Story 31.2`)."""

from __future__ import annotations

import hashlib
import re

import httpx

from orcia_core.catalog._internal.seaweedfs_adapter import build_s3_sigv4_headers
from orcia_core.packs.ports import PackCasStoragePort

_SAFE_SEG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def build_pack_cas_key(*, slug: str, version: str, archive_sha256: str) -> str:
    """Return deterministic CAS key `packs/{slug}/{version}/{archive_sha256}.zip`."""
    clean_slug = _SAFE_SEG_RE.sub("-", slug.strip()).strip("-") or "pack"
    clean_ver = _SAFE_SEG_RE.sub("-", version.strip()).strip("-") or "0.0.0"
    clean_sha = archive_sha256.strip().lower()[:64]
    return f"packs/{clean_slug}/{clean_ver}/{clean_sha}.zip"


class SeaweedFsPackCasAdapter(PackCasStoragePort):
    """Non-blocking `httpx.AsyncClient` SeaweedFS S3 v4 CAS adapter for pack archives."""

    def __init__(
        self,
        *,
        endpoint_url: str = "http://localhost:9000",
        bucket_name: str = "orcia-cas",
        access_key: str = "orcia_seaweed",
        secret_key: str = "orcia_seaweed_secret",  # pragma: allowlist secret
        region: str = "us-east-1",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url.rstrip("/")
        self._bucket = bucket_name
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._http_client = http_client

    async def _request(
        self,
        *,
        method: str,
        key: str,
        payload: bytes = b"",
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = build_s3_sigv4_headers(
            method=method,
            endpoint_url=self._endpoint_url,
            bucket=self._bucket,
            key=key,
            payload=payload,
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
        )
        if extra_headers:
            headers.update(extra_headers)
        url = (
            f"{self._endpoint_url}/{self._bucket}/{key.lstrip('/')}"
            if key
            else f"{self._endpoint_url}/{self._bucket}"
        )
        if self._http_client is not None and not self._http_client.is_closed:
            return await self._http_client.request(method, url, content=payload, headers=headers)
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.request(method, url, content=payload, headers=headers)

    async def _ensure_bucket(self) -> None:
        resp = await self._request(method="PUT", key="", payload=b"")
        if resp.status_code not in (200, 204, 409):
            resp.raise_for_status()

    async def put_archive_zip(
        self,
        *,
        slug: str,
        version: str,
        archive_sha256: str,
        zip_bytes: bytes,
    ) -> str:
        """Persist `zip_bytes` to SeaweedFS S3 under `packs/{slug}/{version}/{sha256}.zip`."""
        computed = hashlib.sha256(zip_bytes).hexdigest()
        expected = archive_sha256.strip().lower()
        if computed != expected:
            raise ValueError(
                f"Pack archive SHA-256 mismatch: expected {expected}, computed {computed}."
            )
        cas_key = build_pack_cas_key(slug=slug, version=version, archive_sha256=expected)
        headers = {"Content-Type": "application/zip"}
        resp = await self._request(
            method="PUT", key=cas_key, payload=zip_bytes, extra_headers=headers
        )
        if resp.status_code == 404:
            await self._ensure_bucket()
            resp = await self._request(
                method="PUT", key=cas_key, payload=zip_bytes, extra_headers=headers
            )
        resp.raise_for_status()
        return cas_key

    async def get_archive_zip(self, cas_key: str) -> bytes | None:
        """Download raw `.zip` archive bytes from SeaweedFS CAS, or return `None`."""
        resp = await self._request(method="GET", key=cas_key)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content

    async def head_archive_zip(self, cas_key: str) -> bool:
        """Return `True` if `cas_key` exists in SeaweedFS S3."""
        resp = await self._request(method="HEAD", key=cas_key)
        return resp.status_code == 200


__all__ = ["SeaweedFsPackCasAdapter", "build_pack_cas_key"]
