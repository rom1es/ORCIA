"""Async DNS-Pinned HTTP Request Preparation (`Story 26.1`, `AD-21` Rule 7)."""

from __future__ import annotations

from typing import Any

import httpx

from orcia_core.permissions.ssrf_guard import resolve_and_pin_safe_endpoint_url


async def prepare_pinned_http_request(
    http_client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    *,
    instance: str | None = None,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Validate DNS resolution against SSRF/rebinding and return pinned URL, headers, extensions."""
    is_mock = isinstance(getattr(http_client, "_transport", None), httpx.MockTransport)
    target = await resolve_and_pin_safe_endpoint_url(
        url,
        allow_unresolvable_in_mock=is_mock,
        instance=instance,
    )
    if is_mock:
        return target.original_url, dict(headers), {}
    pinned_headers = dict(headers)
    pinned_headers["Host"] = target.host_header
    return target.pinned_url, pinned_headers, {"sni_hostname": target.hostname}


__all__ = ["prepare_pinned_http_request"]
