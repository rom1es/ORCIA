"""Fake non-SDLC SAP ERP Connector (`sap://`, `< 150` lines, `AD-20`, `Story 3.2e`, `AC-E4`).

Proves that a third-party non-SDLC connector (`sap://erp-prod/orders/4500012345@v1`) can be
plugged into ORCIA via `ConnectorPort` and `register_connector` with zero lines modified inside
`packages/orcia-kernel` or `packages/orcia-core`.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from orcia_kernel.errors import OrciaDomainError, ResourceNotFoundError, ValidationDomainError
from orcia_kernel.ports import (
    ConnectorCapabilities,
    ConnectorFetchResult,
    ConnectorHealthStatus,
    ConnectorInvokeResult,
    ConnectorPort,
    register_connector,
)


class FakeSapErpConnector(ConnectorPort):
    """Deterministic `sap://` ERP connector implementing `ConnectorPort` (`< 150` lines)."""

    def __init__(self) -> None:
        self._caps = ConnectorCapabilities(
            scheme="sap",
            display_name="SAP S/4HANA ERP Connector (Fake Fixture)",
            pack_name="orcia-connector-sap-fake",
            supports_read=True,
            supports_write=True,
            supports_passthrough_auth=True,
            supports_service_principal=True,
            version_resolution_mode="ref_or_latest",
        )
        self._lock = threading.Lock()
        self._idempotency_cache: dict[tuple[str, str], ConnectorInvokeResult] = {}

    def capabilities(self) -> ConnectorCapabilities:
        """Return SAP connector capabilities."""
        return self._caps

    def fetch(self, uri: str) -> ConnectorFetchResult:
        """Fetch a synthetic SAP ERP order/material payload by `sap://` URI."""
        cleaned = uri.strip()
        if not cleaned.lower().startswith("sap://"):
            raise self.map_error(ValueError(f"Expected 'sap://' scheme in {uri!r}"))
        remainder = cleaned[6:].strip()
        if "/" not in remainder:
            raise self.map_error(ValueError(f"Missing SAP system/path in {uri!r}"))
        authority, raw_path = [p.strip() for p in remainder.split("/", 1)]
        if not authority or not raw_path:
            raise self.map_error(ValueError(f"Empty SAP authority or path in {uri!r}"))
        if "404" in raw_path or "missing" in raw_path:
            raise self.map_error(FileNotFoundError(f"SAP ERP object not found: {uri!r}"))

        resolved_version = "latest"
        path_part = raw_path
        if "@" in raw_path:
            path_part, ref_part = raw_path.rsplit("@", 1)
            resolved_version = ref_part.strip() or "latest"

        payload_bytes = json.dumps(
            {
                "erp_system": authority,
                "object_path": path_part.strip("/"),
                "resolved_version": resolved_version,
                "scheme": "sap",
                "uri": cleaned,
            },
            sort_keys=True,
        ).encode("utf-8")
        return ConnectorFetchResult(
            uri=cleaned,
            scheme="sap",
            resolved_version=resolved_version,
            content_bytes=payload_bytes,
            content_type="application/json",
            sha256=hashlib.sha256(payload_bytes).hexdigest(),
        )

    def invoke(
        self, action: str, payload: dict[str, Any], idempotency_key: str
    ) -> ConnectorInvokeResult:
        """Execute an idempotent SAP BAPI/OData action keyed by `idempotency_key`."""
        clean_action, clean_key = action.strip(), idempotency_key.strip()
        if not clean_action or not clean_key:
            raise self.map_error(ValueError("SAP action and idempotency_key are required."))
        cache_key = (clean_action, clean_key)
        with self._lock:
            cached = self._idempotency_cache.get(cache_key)
            if cached is not None:
                return ConnectorInvokeResult(
                    scheme="sap",
                    action=cached.action,
                    idempotency_key=cached.idempotency_key,
                    replayed_from_idempotency_cache=True,
                    status=cached.status,
                    output=dict(cached.output),
                )
            res = ConnectorInvokeResult(
                scheme="sap",
                action=clean_action,
                idempotency_key=clean_key,
                replayed_from_idempotency_cache=False,
                status="SUCCEEDED",
                output={"sap_bapi": clean_action, "document_number": "4500012345", **payload},
            )
            self._idempotency_cache[cache_key] = res
            return res

    def health(self) -> ConnectorHealthStatus:
        """Return SAP connector health status."""
        return ConnectorHealthStatus(scheme="sap", state="HEALTHY", latency_ms=2.5, detail="SAP OK")

    def map_error(self, exc: Exception) -> OrciaDomainError:
        """Translate SAP connector exceptions into canonical `OrciaDomainError` (RFC 9457)."""
        if isinstance(exc, OrciaDomainError):
            return exc
        if isinstance(exc, FileNotFoundError):
            return ResourceNotFoundError(detail_override=str(exc))
        return ValidationDomainError(detail_override=str(exc))


def register_fake_sap_connector() -> FakeSapErpConnector:
    """Register `sap://` fake connector in `orcia_kernel.ports`."""
    connector = FakeSapErpConnector()
    register_connector(connector)
    return connector
