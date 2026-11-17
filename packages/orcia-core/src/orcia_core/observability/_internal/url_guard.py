"""SSRF guard for observability endpoints (`LogSink` & `OTLP`, `NFR-SEC-1`, `AD-23`)."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from orcia_core.observability.errors import UnsafeLogSinkUrlError

_BLOCKED_METADATA_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",
        "100.100.100.200",
        "metadata.google.internal",
        "metadata.goog",
        "metadata.azure.com",
        "metadata",
        "instance-data",
    }
)
_LINK_LOCAL_V4 = ipaddress.ip_network("169.254.0.0/16")
_LINK_LOCAL_V6 = ipaddress.ip_network("fe80::/10")


def is_safe_observability_endpoint_url(url: str) -> bool:
    """Return `True` if `url` passes Cloud Metadata SSRF checks."""
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_METADATA_HOSTS or host.endswith(".google.internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_link_local
            or ip.is_unspecified
            or ip.is_multicast
            or (isinstance(ip, ipaddress.IPv4Address) and ip in _LINK_LOCAL_V4)
            or (isinstance(ip, ipaddress.IPv6Address) and ip in _LINK_LOCAL_V6)
        ):
            return False
    except ValueError:
        pass
    return True


def validate_safe_log_sink_url(url: str, *, instance: str | None = None) -> str:
    """Validate `url` against SSRF and return normalized URL without trailing slash."""
    if not is_safe_observability_endpoint_url(url):
        raise UnsafeLogSinkUrlError(
            detail_override=f"Log sink / OTLP URL rejected by SSRF guard: {url!r}",
            instance=instance,
        )
    return url.strip().rstrip("/")


__all__ = [
    "is_safe_observability_endpoint_url",
    "validate_safe_log_sink_url",
]
