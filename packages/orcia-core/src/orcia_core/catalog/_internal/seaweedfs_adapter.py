"""SeaweedFS 4.17 (`Apache-2.0`, `ARCH-P6`) S3 v4 adapter implementing `ObjectStoragePort`."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from orcia_core.catalog.cas_resolver import S3BucketBackendProtocol
from orcia_kernel.ports import CasStoredObject, ObjectStoragePort


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def build_s3_sigv4_headers(
    *,
    method: str,
    endpoint_url: str,
    bucket: str,
    key: str,
    payload: bytes,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    now: datetime | None = None,
) -> dict[str, str]:
    """Compute AWS Signature Version 4 headers for SeaweedFS S3 gateway requests."""
    ts = now if now is not None else datetime.now(tz=UTC)
    amz_date = ts.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = ts.strftime("%Y%m%d")
    parsed = urlparse(endpoint_url)
    host = parsed.netloc or "localhost:9000"
    canonical_uri = f"/{bucket}/{key.lstrip('/')}"
    payload_hash = hashlib.sha256(payload).hexdigest()

    canonical_headers = f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = (
        f"{method.upper()}\n{canonical_uri}\n\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )
    k_date = _hmac_sha256(f"AWS4{secret_key}".encode(), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, "s3")
    k_signing = _hmac_sha256(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": authorization,
    }


class SeaweedFsS3HttpBackend(S3BucketBackendProtocol):
    """HTTP S3 v4 backend targeting SeaweedFS (`chrislusf/seaweedfs:4.17`)."""

    def __init__(
        self,
        *,
        endpoint_url: str = "http://localhost:9000",
        access_key: str = "orcia_seaweed",
        secret_key: str = "orcia_seaweed_secret",  # pragma: allowlist secret
        region: str = "us-east-1",
        http_client: httpx.Client | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url.rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._client = http_client if http_client is not None else httpx.Client(timeout=10.0)

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        headers = build_s3_sigv4_headers(
            method="PUT",
            endpoint_url=self._endpoint_url,
            bucket=bucket,
            key=key,
            payload=data,
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
        )
        headers["Content-Type"] = content_type
        url = f"{self._endpoint_url}/{bucket}/{key.lstrip('/')}"
        resp = self._client.put(url, content=data, headers=headers)
        resp.raise_for_status()

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        headers = build_s3_sigv4_headers(
            method="GET",
            endpoint_url=self._endpoint_url,
            bucket=bucket,
            key=key,
            payload=b"",
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
        )
        url = f"{self._endpoint_url}/{bucket}/{key.lstrip('/')}"
        resp = self._client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content

    def head_key(self, bucket: str, key: str) -> bool:
        headers = build_s3_sigv4_headers(
            method="HEAD",
            endpoint_url=self._endpoint_url,
            bucket=bucket,
            key=key,
            payload=b"",
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
        )
        url = f"{self._endpoint_url}/{bucket}/{key.lstrip('/')}"
        resp = self._client.head(url, headers=headers)
        return resp.status_code == 200


class SeaweedFsObjectStorageAdapter(ObjectStoragePort):
    """Hexagonal `ObjectStoragePort` adapter backed by SeaweedFS S3 CAS (`cas/<sha256>`)."""

    def __init__(
        self,
        backend: S3BucketBackendProtocol,
        *,
        bucket_name: str = "orcia-cas",
    ) -> None:
        self._backend = backend
        self._bucket = bucket_name
        self._metadata_index: dict[str, tuple[str, str, str]] = {}

    def put_bytes(
        self,
        *,
        cas_key: str,
        sha256: str,
        source_uri: str,
        content_bytes: bytes,
        content_type: str = "application/octet-stream",
    ) -> CasStoredObject:
        computed = hashlib.sha256(content_bytes).hexdigest()
        normalized_sha = sha256.removeprefix("sha256:")
        if computed != normalized_sha:
            msg = f"CAS SHA-256 mismatch for {cas_key}: expected {normalized_sha}, got {computed}"
            raise ValueError(msg)

        normalized_key = cas_key if cas_key.startswith("cas/") else f"cas/{normalized_sha}"
        self._backend.put_bytes(self._bucket, normalized_key, content_bytes, content_type)
        self._metadata_index[normalized_key] = (normalized_sha, source_uri, content_type)
        return CasStoredObject(
            cas_key=normalized_key,
            sha256=normalized_sha,
            source_uri=source_uri,
            content_bytes=content_bytes,
            content_type=content_type,
        )

    def get_bytes(self, cas_key: str) -> CasStoredObject | None:
        raw = self._backend.get_bytes(self._bucket, cas_key)
        if raw is None:
            return None
        computed = hashlib.sha256(raw).hexdigest()
        meta = self._metadata_index.get(cas_key)
        sha256_val = meta[0] if meta is not None else computed
        source_uri = meta[1] if meta is not None else f"orcia://cas/{computed}"
        content_type = meta[2] if meta is not None else "application/octet-stream"
        if computed != sha256_val:
            msg = f"Corrupted CAS object in SeaweedFS for {cas_key}: SHA-256 mismatch"
            raise ValueError(msg)
        return CasStoredObject(
            cas_key=cas_key,
            sha256=sha256_val,
            source_uri=source_uri,
            content_bytes=raw,
            content_type=content_type,
        )
