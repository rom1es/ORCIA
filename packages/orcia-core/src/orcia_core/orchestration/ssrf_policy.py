"""Re-export facade for canonical SSRF policy (`orcia_core.permissions.ssrf_policy`)."""

from __future__ import annotations

from orcia_core.permissions.ssrf_policy import (
    DUMMY_PLACEHOLDER_HOSTS,
    PERMANENT_BLOCKED_HOSTS,
    PERMANENT_BLOCKED_PORTS,
    check_endpoint_url_policy,
    is_host_allowlisted,
    is_ip_permanently_blocked,
    is_local_or_test_env,
    parse_allowed_private_hosts,
    validate_resolved_ip,
)

__all__ = [
    "DUMMY_PLACEHOLDER_HOSTS",
    "PERMANENT_BLOCKED_HOSTS",
    "PERMANENT_BLOCKED_PORTS",
    "check_endpoint_url_policy",
    "is_host_allowlisted",
    "is_ip_permanently_blocked",
    "is_local_or_test_env",
    "parse_allowed_private_hosts",
    "validate_resolved_ip",
]
