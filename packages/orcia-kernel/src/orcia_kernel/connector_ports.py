"""Universal Connector Port & Dynamic Scheme Registry (`AD-20`, `Story 3.2e`).

Extracted from `orcia_kernel.ports` to maintain modular file size limits (`< 300` lines)
with zero framework or SDK dependencies.
"""

from __future__ import annotations

import importlib.metadata
import threading
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from orcia_kernel.errors import OrciaDomainError

ConnectorHealthState = Literal["HEALTHY", "DEGRADED", "UNREACHABLE"]


@dataclass(frozen=True, slots=True)
class ConnectorCapabilities:
    """Declarative capability metadata exposed by a `ConnectorPort` plugin (`AD-20`, `AC-E3`)."""

    scheme: str
    display_name: str
    pack_name: str
    supports_read: bool = True
    supports_write: bool = False
    supports_passthrough_auth: bool = True
    supports_service_principal: bool = True
    version_resolution_mode: Literal["ref_or_latest", "last_path_segment"] = "ref_or_latest"


@dataclass(frozen=True, slots=True)
class ConnectorFetchResult:
    """Resolved upstream payload returned by `ConnectorPort.fetch(uri)` (`AD-20`, `AC-E3`)."""

    uri: str
    scheme: str
    resolved_version: str
    content_bytes: bytes
    content_type: str = "application/json"
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class ConnectorInvokeResult:
    """Idempotent action invocation result returned by `ConnectorPort.invoke(...)` (`AD-20`)."""

    scheme: str
    action: str
    idempotency_key: str
    replayed_from_idempotency_cache: bool
    status: Literal["SUCCEEDED", "REJECTED"]
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConnectorHealthStatus:
    """Health check status returned by `ConnectorPort.health()` (`AD-20`, `AC-E3`)."""

    scheme: str
    state: ConnectorHealthState
    latency_ms: float = 0.0
    detail: str = "OK"


@runtime_checkable
class ConnectorPort(Protocol):
    """Universal connector contract discovered via `entry_points(group='orcia.connectors')`."""

    def capabilities(self) -> ConnectorCapabilities:
        """Return immutable connector capabilities and scheme metadata."""
        ...

    def fetch(self, uri: str) -> ConnectorFetchResult:
        """Fetch an upstream resource by federated URI (`<scheme>://...`)."""
        ...

    def invoke(
        self, action: str, payload: dict[str, Any], idempotency_key: str
    ) -> ConnectorInvokeResult:
        """Execute a governed action idempotently keyed by `idempotency_key`."""
        ...

    def health(self) -> ConnectorHealthStatus:
        """Check upstream connector reachability and readiness."""
        ...

    def map_error(self, exc: Exception) -> OrciaDomainError:
        """Translate a connector exception into a canonical `OrciaDomainError` (RFC 9457)."""
        ...


_CONNECTOR_LOCK = threading.Lock()
_CONNECTOR_REGISTRY: dict[str, ConnectorPort] = {}
_DEFAULT_SCHEMES: set[str] = {"orcia", "db", "mcp"}
_ENTRY_POINTS_LOADED: bool = False


def register_connector(connector: ConnectorPort) -> None:
    """Register a `ConnectorPort` instance into the dynamic scheme registry (`AD-20`, `AC-E3`)."""
    caps = connector.capabilities()
    scheme = caps.scheme.strip().lower()
    if not scheme:
        raise ValueError("Connector capabilities().scheme must be a non-empty string.")
    with _CONNECTOR_LOCK:
        _CONNECTOR_REGISTRY[scheme] = connector


def unregister_connector(scheme: str) -> None:
    """Remove a dynamically registered connector scheme (used in isolated tests)."""
    norm = scheme.strip().lower()
    with _CONNECTOR_LOCK:
        _CONNECTOR_REGISTRY.pop(norm, None)


def _ensure_entry_points_loaded() -> None:
    global _ENTRY_POINTS_LOADED
    with _CONNECTOR_LOCK:
        if _ENTRY_POINTS_LOADED:
            return
        _ENTRY_POINTS_LOADED = True
    try:
        eps = importlib.metadata.entry_points(group="orcia.connectors")
        for ep in eps:
            loaded = ep.load()
            instance = loaded() if callable(loaded) else loaded
            if isinstance(instance, ConnectorPort):
                register_connector(instance)
    except Exception:
        pass


def get_registered_connector(scheme: str) -> ConnectorPort | None:
    """Return the registered `ConnectorPort` for `scheme` or `None`."""
    _ensure_entry_points_loaded()
    norm = scheme.strip().lower()
    with _CONNECTOR_LOCK:
        return _CONNECTOR_REGISTRY.get(norm)


def list_registered_connector_schemes() -> frozenset[str]:
    """Return the single source of truth for all registered connector schemes (`AD-20`, `AC-E3`)."""
    _ensure_entry_points_loaded()
    with _CONNECTOR_LOCK:
        return frozenset(_DEFAULT_SCHEMES | set(_CONNECTOR_REGISTRY.keys()))


def is_registered_connector_scheme(scheme: str) -> bool:
    """Return True if `scheme` is a registered connector scheme (`AD-20`)."""
    return scheme.strip().lower() in list_registered_connector_schemes()


@runtime_checkable
class AccessRequestChannelPort(Protocol):
    """Port abstracting access request URL & hint generation (`DEC-ACC-01`, `AD-20`)."""

    @property
    def channel_name(self) -> str:
        """Return canonical channel identifier (e.g. `itsm`, `default`)."""
        ...

    def build_access_request_url(
        self,
        template: str,
        *,
        target_uri: str,
        required_role: str,
        approver_team: str,
        requester_email: str,
        step_key: str,
        execution_identity: str,
    ) -> str:
        """Render a URL-encoded pre-filled access request URL from `template`."""
        ...

    def build_access_request_hint(
        self,
        *,
        target_uri: str,
        required_role: str,
        approver_team: str,
        sla_hours: int,
    ) -> str:
        """Render a deterministic RFC 9457 `permission_broker_hint` URI."""
        ...


_ACCESS_CHANNEL_LOCK = threading.Lock()
_ACCESS_REQUEST_CHANNEL: AccessRequestChannelPort | None = None


def register_access_request_channel(channel: AccessRequestChannelPort) -> None:
    """Register the active `AccessRequestChannelPort` adapter (`DEC-ACC-01`)."""
    global _ACCESS_REQUEST_CHANNEL
    with _ACCESS_CHANNEL_LOCK:
        _ACCESS_REQUEST_CHANNEL = channel


def get_access_request_channel() -> AccessRequestChannelPort | None:
    """Return the currently registered `AccessRequestChannelPort` adapter or `None`."""
    _ensure_entry_points_loaded()
    with _ACCESS_CHANNEL_LOCK:
        return _ACCESS_REQUEST_CHANNEL


__all__ = [
    "AccessRequestChannelPort",
    "ConnectorCapabilities",
    "ConnectorFetchResult",
    "ConnectorHealthState",
    "ConnectorHealthStatus",
    "ConnectorInvokeResult",
    "ConnectorPort",
    "get_access_request_channel",
    "get_registered_connector",
    "is_registered_connector_scheme",
    "list_registered_connector_schemes",
    "register_access_request_channel",
    "register_connector",
    "unregister_connector",
]
