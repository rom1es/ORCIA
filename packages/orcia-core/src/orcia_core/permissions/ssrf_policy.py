"""SSRF Policy Rules & Env Allowlist Parsers (`Story 26.1`, `AD-21` Rule 7)."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, OrciaDomainError, register_domain_error_catalog

SSRF_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_UNSAFE_LLM_ENDPOINT_URL": {
        "fr": LocalizedErrorCopy(
            "URL de fournisseur LLM non sécurisée (protection anti-SSRF)",
            "L'URL de l'endpoint LLM doit utiliser HTTP/HTTPS et ne peut pas cibler une adresse "
            "de métadonnées Cloud ou link-local (169.254.0.0/16, fe80::/10, "
            "metadata.google.internal, 100.100.100.200).",
        ),
        "en": LocalizedErrorCopy(
            "Unsafe LLM endpoint URL (SSRF protection)",
            "The LLM endpoint URL must use HTTP/HTTPS and must not target cloud metadata or "
            "link-local addresses (169.254.0.0/16, fe80::/10, metadata.google.internal, "
            "100.100.100.200).",
        ),
    },
}

register_domain_error_catalog(SSRF_ERROR_CATALOG)


class UnsafeLlmEndpointUrlError(OrciaDomainError):
    error_code = "ERR_UNSAFE_LLM_ENDPOINT_URL"
    http_status, type_slug = 422, "unsafe-llm-endpoint-url"


PERMANENT_BLOCKED_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",
        "100.100.100.200",
        "metadata.google.internal",
        "metadata.goog",
        "metadata.azure.com",
        "instance-data",
    }
)
DUMMY_PLACEHOLDER_HOSTS: frozenset[str] = frozenset(
    {
        "example.com",
        "api.example.com",
        "mock-llm",
        "mock-llm.local",
        "dummy-llm",
        "dummy.local",
        "placeholder.local",
    }
)
PERMANENT_BLOCKED_PORTS: frozenset[int] = frozenset({5432, 5433, 6379, 8333, 9333, 9000})
_LINK_LOCAL_V4 = ipaddress.ip_network("169.254.0.0/16")
_LINK_LOCAL_V6 = ipaddress.ip_network("fe80::/10")
_PRIVATE_HOST_SUFFIXES: tuple[str, ...] = (".local", ".internal", ".localhost")


def is_local_or_test_env() -> bool:
    """Return True only when ORCIA_ENV is explicitly 'local' or 'test'."""
    env = os.environ.get("ORCIA_ENV", "").strip().lower()
    return env in ("local", "test")


def parse_allowed_private_hosts() -> tuple[
    frozenset[str], tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
]:
    """Parse `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` into hostnames/suffixes and IP networks."""
    raw = os.environ.get("ORCIA_LLM_ALLOWED_PRIVATE_HOSTS", "")
    hosts: list[str] = []
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for item in raw.split(","):
        token = item.strip().lower().rstrip(".")
        if not token:
            continue
        if token.startswith("*."):
            token = token[1:]
        try:
            nets.append(ipaddress.ip_network(token, strict=False))
            continue
        except ValueError:
            pass
        hosts.append(token)
    return frozenset(hosts), tuple(nets)


def is_host_allowlisted(
    host: str,
    allow_hosts: frozenset[str],
    allow_nets: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
) -> bool:
    """Return True if hostname or IP literal matches the explicit ops allowlist."""
    if host in allow_hosts:
        return True
    for entry in allow_hosts:
        if entry.startswith(".") and (host.endswith(entry) or host == entry.lstrip(".")):
            return True
    try:
        ip = _unwrap_ipv4_mapped(ipaddress.ip_address(host))
        return any(ip in net for net in allow_nets)
    except ValueError:
        return False


def _unwrap_ipv4_mapped(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Unwrap IPv4-mapped IPv6 addresses (`::ffff:x.x.x.x`) before SSRF checks."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def is_ip_permanently_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True for link-local, metadata, unspecified, or multicast IPs (non-overridable)."""
    unwrapped = _unwrap_ipv4_mapped(ip)
    return bool(
        unwrapped.is_link_local
        or unwrapped.is_unspecified
        or unwrapped.is_multicast
        or str(unwrapped) in {"169.254.169.254", "100.100.100.200"}
        or (unwrapped.version == 4 and unwrapped in _LINK_LOCAL_V4)
        or (unwrapped.version == 6 and unwrapped in _LINK_LOCAL_V6)
    )


def validate_resolved_ip(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    is_local_env: bool,
    host_allowed: bool,
    allow_private_network: bool | None,
    allow_nets: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
    instance: str | None,
) -> None:
    """Validate a single IP address (literal or DNS-resolved) against SSRF policy."""
    unwrapped = _unwrap_ipv4_mapped(ip)
    if is_ip_permanently_blocked(unwrapped):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Target IP '{ip}' is blocked by permanent link-local SSRF policy.",
            instance=instance,
        )
    ip_allowed = host_allowed or any(unwrapped in net for net in allow_nets)
    if allow_private_network is not None:
        if (
            not allow_private_network
            and not ip_allowed
            and (unwrapped.is_private or unwrapped.is_loopback or unwrapped.is_reserved)
        ):
            raise UnsafeLlmEndpointUrlError(
                detail_override=(
                    f"Private/loopback IP '{ip}' requires explicit network authorization."
                ),
                instance=instance,
            )
        return
    if unwrapped.is_loopback and not (is_local_env or ip_allowed):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Loopback IP '{ip}' is forbidden outside local/test environments.",
            instance=instance,
        )
    if (unwrapped.is_private or unwrapped.is_reserved) and not (is_local_env or ip_allowed):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Private IP '{ip}' is not listed in ORCIA_LLM_ALLOWED_PRIVATE_HOSTS.",
            instance=instance,
        )


def check_endpoint_url_policy(
    url: str,
    *,
    allow_private_network: bool | None = None,
    enforce_placeholder_block: bool = True,
    instance: str | None = None,
) -> tuple[str, str, int]:
    """Validate URL syntax, port, scheme, and hostname/IP SSRF rules without DNS I/O."""
    raw = (url or "").strip()
    if not raw:
        raise UnsafeLlmEndpointUrlError(
            detail_override="Endpoint URL cannot be empty.", instance=instance
        )
    try:
        parsed = urlparse(raw)
    except ValueError as exc:
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Malformed endpoint URL: {raw}", instance=instance
        ) from exc
    if parsed.scheme not in ("http", "https"):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Invalid endpoint scheme '{parsed.scheme}'. Must be http or https.",
            instance=instance,
        )
    if parsed.username or parsed.password:
        raise UnsafeLlmEndpointUrlError(
            detail_override="Credentials embedded in endpoint authority are forbidden.",
            instance=instance,
        )
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise UnsafeLlmEndpointUrlError(
            detail_override="Endpoint hostname cannot be empty.", instance=instance
        )
    if host in PERMANENT_BLOCKED_HOSTS or host.endswith(".google.internal"):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Target host '{host}' is prohibited by permanent SSRF policy.",
            instance=instance,
        )
    if enforce_placeholder_block and (
        host in DUMMY_PLACEHOLDER_HOSTS or host.endswith(".example.com")
    ):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Placeholder host '{host}' is prohibited by SSRF policy.",
            instance=instance,
        )
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeLlmEndpointUrlError(
            detail_override="Invalid endpoint TCP port.", instance=instance
        ) from exc
    if port in PERMANENT_BLOCKED_PORTS:
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Target port '{port}' is blocked by internal service SSRF policy.",
            instance=instance,
        )

    is_local_env = is_local_or_test_env()
    allow_hosts, allow_nets = parse_allowed_private_hosts()
    host_allowed = is_host_allowlisted(host, allow_hosts, allow_nets)
    try:
        ip = ipaddress.ip_address(host)
        validate_resolved_ip(
            ip,
            is_local_env=is_local_env,
            host_allowed=host_allowed,
            allow_private_network=allow_private_network,
            allow_nets=allow_nets,
            instance=instance,
        )
        return raw, host, port
    except ValueError:
        pass

    is_loopback_name = host == "localhost" or host.endswith(".localhost")
    is_private_name = host.endswith(_PRIVATE_HOST_SUFFIXES) or "." not in host
    if allow_private_network is not None:
        if not allow_private_network and (is_loopback_name or is_private_name) and not host_allowed:
            raise UnsafeLlmEndpointUrlError(
                detail_override=(
                    f"Private hostname '{host}' requires explicit network authorization."
                ),
                instance=instance,
            )
        return raw, host, port

    if is_loopback_name and not (is_local_env or host_allowed):
        raise UnsafeLlmEndpointUrlError(
            detail_override=(
                "Loopback host 'localhost' is forbidden outside local/test environments."
            ),
            instance=instance,
        )
    if is_private_name and not (is_local_env or host_allowed):
        raise UnsafeLlmEndpointUrlError(
            detail_override=(
                f"Private hostname '{host}' is not listed in ORCIA_LLM_ALLOWED_PRIVATE_HOSTS."
            ),
            instance=instance,
        )
    return raw, host, port
