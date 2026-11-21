"""Re-export facade for canonical SSRF guard (`orcia_core.permissions.ssrf_guard`)."""

from __future__ import annotations

from orcia_core.permissions.ssrf_guard import (
    DUMMY_PLACEHOLDER_HOSTS,
    PERMANENT_BLOCKED_HOSTS,
    PERMANENT_BLOCKED_PORTS,
    PinnedEndpointTarget,
    check_endpoint_url_policy,
    is_safe_llm_endpoint_url,
    resolve_and_pin_safe_endpoint_url,
    validate_safe_llm_endpoint_url,
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
