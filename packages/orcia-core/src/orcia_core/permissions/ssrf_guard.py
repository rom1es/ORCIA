"""SSRF Policy Allowlist & Async DNS-Resolution Pinning Guard (`Story 26.1`, `AD-21` Rule 7)."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from orcia_core.permissions.ssrf_policy import (
    DUMMY_PLACEHOLDER_HOSTS,
    PERMANENT_BLOCKED_HOSTS,
    PERMANENT_BLOCKED_PORTS,
    UnsafeLlmEndpointUrlError,
    check_endpoint_url_policy,
    is_host_allowlisted,
    is_local_or_test_env,
    parse_allowed_private_hosts,
    validate_resolved_ip,
)


@dataclass(frozen=True, slots=True)
class PinnedEndpointTarget:
    """Resolved and DNS-pinned endpoint URL protected against DNS rebinding."""

    original_url: str
    pinned_url: str
    hostname: str
    pinned_ip: str
    port: int
    host_header: str


def validate_safe_llm_endpoint_url(url: str, *, instance: str | None = None) -> str:
    """Validate LLM endpoint URL strictly against `AD-21` Rule 7 SSRF policy."""
    raw, _, _ = check_endpoint_url_policy(url, allow_private_network=None, instance=instance)
    return raw


def is_safe_llm_endpoint_url(
    url: str,
    *,
    allow_private_network: bool | None = None,
    enforce_placeholder_block: bool = True,
) -> bool:
    """Boolean wrapper over `check_endpoint_url_policy`."""
    try:
        check_endpoint_url_policy(
            url,
            allow_private_network=allow_private_network,
            enforce_placeholder_block=enforce_placeholder_block,
        )
        return True
    except UnsafeLlmEndpointUrlError:
        return False


async def resolve_and_pin_safe_endpoint_url(
    url: str,
    *,
    allow_private_network: bool | None = None,
    allow_unresolvable_in_mock: bool = False,
    instance: str | None = None,
) -> PinnedEndpointTarget:
    """Resolve hostname via `socket.getaddrinfo`, validate all IPs, and return pinned URL."""
    clean_url, host, port = check_endpoint_url_policy(
        url, allow_private_network=allow_private_network, instance=instance
    )
    parsed = urlparse(clean_url)
    host_header = parsed.netloc
    try:
        ipaddress.ip_address(host)
        return PinnedEndpointTarget(clean_url, clean_url, host, host, port, host_header)
    except ValueError:
        pass

    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        if allow_unresolvable_in_mock:
            return PinnedEndpointTarget(clean_url, clean_url, host, host, port, host_header)
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"DNS resolution failed for endpoint host '{host}'.",
            instance=instance,
        ) from exc

    is_local_env = is_local_or_test_env()
    allow_hosts, allow_nets = parse_allowed_private_hosts()
    host_allowed = is_host_allowlisted(host, allow_hosts, allow_nets)

    resolved_ips: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        raw_ip = str(sockaddr[0]).split("%", 1)[0]
        ip = ipaddress.ip_address(raw_ip)
        validate_resolved_ip(
            ip,
            is_local_env=is_local_env,
            host_allowed=host_allowed,
            allow_private_network=allow_private_network,
            allow_nets=allow_nets,
            instance=instance,
        )
        resolved_ips.append(raw_ip)

    if not resolved_ips:
        if allow_unresolvable_in_mock:
            return PinnedEndpointTarget(clean_url, clean_url, host, host, port, host_header)
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"DNS resolution returned no usable addresses for '{host}'.",
            instance=instance,
        )

    pinned_ip = resolved_ips[0]
    pinned_netloc = f"[{pinned_ip}]:{port}" if ":" in pinned_ip else f"{pinned_ip}:{port}"
    pinned_url = urlunparse(parsed._replace(netloc=pinned_netloc))
    return PinnedEndpointTarget(
        original_url=clean_url,
        pinned_url=pinned_url,
        hostname=host,
        pinned_ip=pinned_ip,
        port=port,
        host_header=host_header,
    )


__all__ = [
    "DUMMY_PLACEHOLDER_HOSTS",
    "PERMANENT_BLOCKED_HOSTS",
    "PERMANENT_BLOCKED_PORTS",
    "PinnedEndpointTarget",
    "check_endpoint_url_policy",
    "is_safe_llm_endpoint_url",
    "resolve_and_pin_safe_endpoint_url",
    "validate_safe_llm_endpoint_url",
]
