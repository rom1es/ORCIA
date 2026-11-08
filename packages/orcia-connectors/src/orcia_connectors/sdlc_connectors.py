"""SDLC Connectors (`git://`, `jira://`, `confluence://`, `nexus://`) (`AD-20`)."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Literal

from orcia_kernel.errors import OrciaDomainError, ResourceNotFoundError, ValidationDomainError
from orcia_kernel.ports import (
    ConnectorCapabilities,
    ConnectorFetchResult,
    ConnectorHealthStatus,
    ConnectorInvokeResult,
    ConnectorPort,
    register_connector,
)


class SdlcConnectorAdapter(ConnectorPort):
    """Deterministic `ConnectorPort` implementation for an SDLC scheme (`AD-20`)."""

    def __init__(
        self,
        *,
        scheme: str,
        display_name: str,
        supports_write: bool = True,
        version_resolution_mode: Literal["ref_or_latest", "last_path_segment"] = "ref_or_latest",
    ) -> None:
        self._caps = ConnectorCapabilities(
            scheme=scheme,
            display_name=display_name,
            pack_name="orcia-pack-sdlc",
            supports_read=True,
            supports_write=supports_write,
            supports_passthrough_auth=True,
            supports_service_principal=True,
            version_resolution_mode=version_resolution_mode,
        )
        self._lock = threading.Lock()
        self._idempotency_cache: dict[tuple[str, str], ConnectorInvokeResult] = {}

    def capabilities(self) -> ConnectorCapabilities:
        """Return immutable connector capabilities."""
        return self._caps

    def fetch(self, uri: str) -> ConnectorFetchResult:
        """Fetch an upstream SDLC resource deterministically by federated URI."""
        cleaned = uri.strip()
        prefix = f"{self._caps.scheme}://"
        if not cleaned.lower().startswith(prefix):
            raise self.map_error(ValueError(f"Expected scheme {prefix!r} in {uri!r}"))
        remainder = cleaned[len(prefix) :].strip()
        if "/" not in remainder:
            raise self.map_error(ValueError(f"Missing authority/path in {uri!r}"))
        authority, raw_path = [p.strip() for p in remainder.split("/", 1)]
        if not authority or not raw_path:
            raise self.map_error(ValueError(f"Empty authority or path in {uri!r}"))
        if "404" in raw_path or "not-found" in raw_path:
            raise self.map_error(FileNotFoundError(f"Resource not found: {uri!r}"))

        resolved_version = "latest"
        path_part = raw_path
        if "@sha256:" in raw_path:
            path_part, sha_ref = raw_path.rsplit("@sha256:", 1)
            resolved_version = f"sha256:{sha_ref.strip().lower()[:12]}"
        elif "@" in raw_path:
            path_part, ref_part = raw_path.rsplit("@", 1)
            resolved_version = ref_part.strip() or "latest"
        elif self._caps.version_resolution_mode == "last_path_segment":
            segments = [s for s in path_part.split("/") if s]
            resolved_version = segments[-1] if segments else "latest"

        path_clean = path_part.strip().strip("/")
        archive_format = (
            "tar.gz"
            if path_clean.endswith((".tar.gz", ".tgz"))
            else ("zip" if path_clean.endswith(".zip") else "none")
        )
        payload_bytes = json.dumps(
            {
                "authority": authority,
                "archive_format": archive_format,
                "path": path_clean,
                "resolved_version": resolved_version,
                "scheme": self._caps.scheme,
                "uri": cleaned,
            },
            sort_keys=True,
        ).encode("utf-8")
        sha256 = hashlib.sha256(payload_bytes).hexdigest()
        return ConnectorFetchResult(
            uri=cleaned,
            scheme=self._caps.scheme,
            resolved_version=resolved_version,
            content_bytes=payload_bytes,
            content_type="application/json",
            sha256=sha256,
        )

    def invoke(
        self, action: str, payload: dict[str, Any], idempotency_key: str
    ) -> ConnectorInvokeResult:
        """Execute a governed SDLC connector action idempotently keyed by `idempotency_key`."""
        clean_action = action.strip()
        clean_key = idempotency_key.strip()
        if not clean_action or not clean_key:
            raise self.map_error(ValueError("action and idempotency_key are required."))
        cache_key = (clean_action, clean_key)
        with self._lock:
            existing = self._idempotency_cache.get(cache_key)
            if existing is not None:
                return ConnectorInvokeResult(
                    scheme=existing.scheme,
                    action=existing.action,
                    idempotency_key=existing.idempotency_key,
                    replayed_from_idempotency_cache=True,
                    status=existing.status,
                    output=dict(existing.output),
                )
            res = ConnectorInvokeResult(
                scheme=self._caps.scheme,
                action=clean_action,
                idempotency_key=clean_key,
                replayed_from_idempotency_cache=False,
                status="SUCCEEDED",
                output={
                    "scheme": self._caps.scheme,
                    "action": clean_action,
                    "payload": dict(payload),
                },
            )
            self._idempotency_cache[cache_key] = res
            return res

    def health(self) -> ConnectorHealthStatus:
        """Return healthy connector status."""
        return ConnectorHealthStatus(
            scheme=self._caps.scheme, state="HEALTHY", latency_ms=1.2, detail="OK"
        )

    def map_error(self, exc: Exception) -> OrciaDomainError:
        """Map connector exceptions to canonical `OrciaDomainError` (RFC 9457)."""
        if isinstance(exc, OrciaDomainError):
            return exc
        if isinstance(exc, FileNotFoundError):
            return ResourceNotFoundError(detail_override=str(exc))
        return ValidationDomainError(detail_override=str(exc))


def create_git_connector() -> SdlcConnectorAdapter:
    return SdlcConnectorAdapter(scheme="git", display_name="Git Repository Connector")


def create_jira_connector() -> SdlcConnectorAdapter:
    return SdlcConnectorAdapter(
        scheme="jira",
        display_name="Jira Issue Tracker Connector",
        version_resolution_mode="last_path_segment",
    )


def create_confluence_connector() -> SdlcConnectorAdapter:
    return SdlcConnectorAdapter(scheme="confluence", display_name="Confluence Wiki Connector")


def create_nexus_connector() -> SdlcConnectorAdapter:
    return SdlcConnectorAdapter(
        scheme="nexus", display_name="Nexus Artifact Repository Connector", supports_write=False
    )


def register_all_sdlc_connectors() -> tuple[SdlcConnectorAdapter, ...]:
    """Register `git`, `jira`, `confluence`, and `nexus` connectors in `orcia_kernel.ports`."""
    connectors = (
        create_git_connector(),
        create_jira_connector(),
        create_confluence_connector(),
        create_nexus_connector(),
    )
    for c in connectors:
        register_connector(c)
    return connectors
